#! /usr/bin/env python

import os
import logging
import multiprocessing

from overc import OvercApplication
from overc.lib.supervise import supervise_loop

# Load config
app_config_file = os.environ.get('OVERC_CONFIG', 'server.ini')
app_config = OvercApplication.loadConfigFile(app_config_file)

# Configure logging
logging.basicConfig(level=getattr(logging, app_config['LOGLEVEL']))

# Application
app = OvercApplication(
    __name__,
    app_config['INSTANCE_PATH'],
    app_config
)
wsgi_app = app.app

# Supervisor thread
p = multiprocessing.Process(name='supervisor', target=supervise_loop, args=(app,))
p.daemon = True
p.start()


# Debug mode
if __name__ == '__main__':
    # Serve static files in debug mode
    from werkzeug.wsgi import SharedDataMiddleware
    from werkzeug.serving import run_simple

    wsgi_app = SharedDataMiddleware(wsgi_app, {
        '/static/ui': ('overc.src.bps.ui', 'static')
    }, cache=False)

    run_simple(application=wsgi_app,
               hostname='0.0.0.0',
               port=5000,
               use_reloader=True,
               use_debugger=True
    )
