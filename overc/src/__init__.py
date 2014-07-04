import os
from ConfigParser import ConfigParser

from flask import Flask, Request
from flask.ctx import _AppCtxGlobals

from overc import __version__
from overc.src.init import init_db_engine, init_db_session_for_flask
from overc.lib.alerts import AlertPlugin

class OvercFlask(Flask):
    """ Custom Flask """

class OvercApplication(object):
    """ OverC Application """
    version = __version__

    @staticmethod
    def loadConfigFile(filename):
        """ Load OverC config file and parse it
        Any config option <name> can be overriden from environment: `OVERC_<name>`

        :param filename: Config file path
        :type filename: str
        :return: Configuration
        :rtype: dict
        """
        # Default config
        app_config = dict(
            DEBUG=False,
            TESTING=False,
            VERBOSE=0,
            SERVER_NAME=None,
            APPLICATION_ROOT=None,
            PREFERRED_URL_SCHEME='http',

            INSTANCE_PATH='/',
            DATABASE='mysql://user:pass@127.0.0.1/overc',
            ALERT_PLUGINS=[],
        )

        # Load config
        if not os.path.exists(filename):
            raise OSError('Config file does not exist: {}'.format(filename))
        app_config['INSTANCE_PATH'] = os.path.dirname(os.path.realpath(filename))

        ini = ConfigParser()
        ini.read(filename)

        # Parse: [overc]
        if ini.has_section('overc'):
            app_config['DATABASE'] = ini.get('overc', 'database')
            app_config['LOGLEVEL'] = ini.get('overc', 'loglevel')

        # Parse: [alert:*]
        for s in ini.sections():
            if s.startswith('alert:'):
                app_config['ALERT_PLUGINS'].append(
                    AlertPlugin(
                        name=s.split(':', 1)[1],
                        cwd=app_config['INSTANCE_PATH'],
                        command=ini.get(s, 'command')
                    )
                )

        # Override from environment
        for name, value in os.environ.items():
            if name.startswith('OVERC_'):
                app_config[name[len('OVERC_'):]] = value

        # Finish
        return app_config

    def __init__(self, import_name, instance_path, config):
        """ Initialize app
        :param import_name: Declaring module nmae
        :type import_name: str
        :param instance_path: Application instance path
        :type instance_path: str
        :param config: Application configuration object
        :type config: dict
        """
        # Init app
        self.app = OvercFlask(import_name,
            template_folder='templates',
            instance_path=instance_path,
            static_folder='static',
            static_url_path='/static'
        )
        self.app.config.update(config)
        self.app.debug = config.get('DEBUG', False)

        # Init DB
        self.db_engine = init_db_engine(self.app.config['DATABASE'])
        self.db = init_db_session_for_flask(self.db_engine, self.app)

        # Globals
        class DignioAppCtxGlobals(_AppCtxGlobals):
            """ Flask `g` overrides """
            app = self
            db = self.db
        self.app.app_ctx_globals_class = DignioAppCtxGlobals

        # Blueprints
        from .bps import api
        from .bps import ui
        self.app.register_blueprint(api.bp, url_prefix='/api')
        self.app.register_blueprint(ui.bp, url_prefix='/ui')
