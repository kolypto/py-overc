#! /usr/bin/env python

import os
import logging
import multiprocessing

from overc import OvercApplication
from overc.lib.supervise import supervise_loop

def init_application(app_config_file):
    """ Initialize application from config file path
       :rtype: OvercApplication
       """
    # Load config
    app_config = OvercApplication.loadConfigFile(app_config_file)

    # Configure logging
    logging.basicConfig(level=getattr(logging, app_config['LOGLEVEL']))
    # TODO: multi-process app does not log everything fine! make it log to stdout, always

    # Applicaton
    application = OvercApplication(
        __name__,
        app_config['INSTANCE_PATH'],
        app_config
    )

    # Supervisor thread
    p = multiprocessing.Process(name='supervisor', target=supervise_loop, args=(application,))
    p.daemon = True
    p.start()

    # Finish
    return application

# Application
application = init_application(
    os.environ.get('OVERC_CONFIG', 'server.ini')
)

# WSGI entry point
app = application.app

# Serve static files
from werkzeug.wsgi import SharedDataMiddleware

app = SharedDataMiddleware(app, {
    '/ui/static/': ('overc.src.bps.ui', 'static')
}, cache=False)

# Debug mode
if __name__ == '__main__':
    from werkzeug.serving import run_simple
    run_simple(application=app,
               hostname='0.0.0.0',
               port=5000,
               use_reloader=True,
               use_debugger=True
    )
