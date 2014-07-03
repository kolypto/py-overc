import os

from flask.testing import FlaskClient
from flask import request, json

from overc import OvercApplication
from overc.lib.db import models



class CustomFlaskClient(FlaskClient):
    """ Custom Flask client for tests """

    def jsonapi(self, method, uri, body=None, **kwargs):
        """ Call a JSON API method
        :param method: HTTP method name
        :type method: str
        :param uri: URI
        :type uri: str
        :param body: Data to submit
        :type body: *
        :return: The response tuple
        :rtype: (basestring|dict, flask.wrappers.Response)
        """
        # Send
        rv = self.open(
            uri,
            method=method,
            content_type='application/json',
            data=json.dumps(body or {}),
            **kwargs
        )

        # JSON?
        if rv.mimetype == 'application/json':
            return json.loads(rv.get_data()), rv

        # Non-JSON
        return rv.get_data(), rv


class ApplicationTest(object):
    """ Mixin to initialize the app """

    def setUp(self):
        # Load config
        app_config_file = 'tests/data/overc-server/server.ini'
        app_config = OvercApplication.loadConfigFile(app_config_file)

        # Init app
        self.instance_path = app_config['INSTANCE_PATH']
        self.app = OvercApplication(__name__, self.instance_path, app_config)
        self.app.app.config.update(TESTING=True)

        # Customize
        self.app.app.test_client_class = CustomFlaskClient

        # Reset DB
        models.Base.metadata.drop_all(bind=self.app.db_engine)
        models.Base.metadata.create_all(bind=self.app.db_engine)

    def tearDown(self):
        # Close & reset DB
        self.app.db.close()
        models.Base.metadata.drop_all(bind=self.app.db_engine)

    #region Helpers

    @property
    def db(self):
        """ Get DB session
            :rtype: sqlalchemy.orm.session.Session
        """
        return self.app.db

    @property
    def test_client(self):
        """ Get test client
        :rtype: CustomFlaskClient
        """
        return self.app.app.test_client()

    #endregion
