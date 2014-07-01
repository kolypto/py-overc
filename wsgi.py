#! /usr/bin/env python

import os, argparse
from threading import Thread

from overc import OvercApplication
from overc.lib.supervise import supervise_loop

# Arguments
parser = argparse.ArgumentParser(description='WSGI application launcher')
parser.add_argument('instance_path', help="Application instance path (configs & runtime data)")
parser.add_argument('--bindto', default=":5000", help="Interface to bind to")
args = parser.parse_args()

# Application
app = OvercApplication(
    __name__,
    os.path.realpath(args.instance_path)
)

if __name__ == '__main__':
    # Supervisor thread
    Thread(target=supervise_loop, args=(app,))

    # Launch app
    app.run(args.bindto)
