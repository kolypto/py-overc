import os.path

from flask import Flask, Request
from flask.ctx import _AppCtxGlobals

from overc import __version__
from overc.src.init import init_sqlalchemy

class OvercFlask(Flask):
    """ Custom Flask """

class OvercApplication(object):
    """ OverC Application """
    version = __version__

    def __init__(self, import_name, instance_path):
        """ Initialize app
        :param import_name: Declaring module nmae
        :type import_name: str
        :param instance_path: Application instance path
        :type instance_path: str
        """
        # Init app
        self.app = OvercFlask(import_name,
            template_folder='templates',
            instance_path=instance_path,
            static_folder='static',
            static_url_path='/static'
        )
        self.app.config.from_pyfile(os.path.join(instance_path, 'config.py'))
        self.app.debug = self.app.config['DEBUG']

        # Init DB
        self.db_engine, self.db = init_sqlalchemy(self.app, self.app.config['DB_CONNECT'])

        # Globals
        class DignioAppCtxGlobals(_AppCtxGlobals):
            """ Flask `g` overrides """
            app = self
            db = self.db
        self.app.app_ctx_globals_class = DignioAppCtxGlobals

        # Blueprints
        from .bps import api
        self.app.register_blueprint(api.bp, url_prefix='/api')

    def run(self, bindto):
        """ Launch application """
        host, port = bindto.split(':')
        self.app.run(
            host=host or '0.0.0.0',
            port=int(port)
        )
