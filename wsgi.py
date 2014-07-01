#! /usr/bin/env python

import os, argparse
import multiprocessing

from overc import OvercApplication
from overc.lib.supervise import supervise_loop

# Arguments
parser = argparse.ArgumentParser(description='WSGI application launcher')
parser.add_argument('--verbose', '-v', action='count', default=0, help='Be more verbose. -vv includes debug output')
parser.add_argument('--bindto', default=":5000", help="Interface to bind to")
parser.add_argument('instance_path', help="Application instance path (configs & runtime data)")
args = parser.parse_args()

# Configure logging
import logging
logging.basicConfig(level=[ logging.WARN, logging.INFO, logging.DEBUG, logging.NOTSET ][args.verbose])

# Application
app = OvercApplication(
    __name__,
    os.path.realpath(args.instance_path)
)

if __name__ == '__main__':
    # Only if in the main thread (not Werkzeug "reloader" thread)
    if not os.environ.get('WERKZEUG_RUN_MAIN'):
        # Supervisor thread
        p = multiprocessing.Process(name='supervisor', target=supervise_loop, args=(app,))
        p.daemon = True
        p.start()

    # Launch app
    app.run(args.bindto)
