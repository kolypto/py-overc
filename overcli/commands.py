import os
import time
import logging
import argparse
from ConfigParser import ConfigParser

from . import __author__, __email__, __version__
from .overclient import Overclient
from .monitor import ServicesMonitor, Service

logger = logging.getLogger(__name__)


def cmd_ping(args, overc):
    """ Ping server (api: /api/ping) """
    overc.ping()


def cmd_service_status(args, overc):
    """ Report single service status (api: /api/set/service/status) """
    overc.set_service_status(args.period, [
        { 'name': args.name, 'state': args.state, 'info': args.info }
    ])


def cmd_alert(args, overc):
    """ Report single alert (api: /api/set/alert) """
    alert = {'message': args.message}
    if args.service:
        alert['service'] = args.service
    overc.set_alerts([ alert ])

def cmd_monitor(args, overc):
    try:
        _cmd_monitor_wrapped(args, overc)
    except Exception as e:
        overc.set_alerts([
            u'Monitoring failure: {}: {}'.format(e.name, e.message)
        ])
        raise

def _cmd_monitor_wrapped(args, overc):
    """ Perform continuous monitoring """
    cwd = os.path.dirname(args.config)
    if not os.path.exists(args.config):
        raise OSError('Config file does not exist: {}'.format(args.config))

    # First, ping the server
    overc.ping()  # exception when fails

    # Read config file
    services = []
    ini = ConfigParser()
    ini.read(args.config)

    # Parse config file
    for section in ini.sections():
        type, name = section.split(':')
        if section.startswith('service:'):
            services.append(Service(
                ini.getint(section, 'period'),
                name,
                cwd,
                ini.get(section, 'command')
            ))
        else:
            raise ValueError('Unknown section type: "{}"'.format(type))

    # Init monitor
    monitor = ServicesMonitor(services)

    while True:
        # Determine sleep time
        delay = monitor.sleep_time()
        time.sleep(delay)

        # Check
        period, service_states = monitor.check()

        # Report
        try:
            overc.set_service_status(period, service_states)
        except Exception as e:
            logger.exception('Failed to report service status!')
            # proceed

def main():
    # Arguments
    versionstr = 'v{} (c) {} <{}>'.format(__version__, __author__, __email__)
    parser = argparse.ArgumentParser(
        prog='overcli',
        description='OverC client',
        epilog=versionstr
    )
    parser.add_argument('--verbose', '-v', action='count', default=0, help='Be more verbose. -vv includes debug output')
    parser.add_argument('-s', '--server', dest='server_url', help='OverC Server URL: "http://<host>:<port>/"')
    parser.add_argument('-i', '--server-id', dest='server_id', help='Server identification: "<name>:<key>"')
    # TODO: for `monitor`, move server/server-id into the config file

    # Subcommands
    sub = parser.add_subparsers(dest='command_name', title='Command')

    cmd = sub.add_parser('ping', help='Ping server')
    cmd.set_defaults(func=cmd_ping)

    cmd = sub.add_parser('service-status', help=cmd_service_status.__doc__)
    cmd.add_argument('period', help='Reporting period')
    cmd.add_argument('name', help='Service name')
    cmd.add_argument('state', help='Service state')
    cmd.add_argument('info', nargs='?', default='', help='Additional information')
    cmd.set_defaults(func=cmd_service_status)

    cmd = sub.add_parser('alert', help=cmd_alert.__doc__)
    cmd.add_argument('--service', nargs='?', default=None, help='Service to report the alert for')
    cmd.add_argument('message', help='Alert message')
    cmd.set_defaults(func=cmd_alert)

    cmd = sub.add_parser('monitor', help=cmd_monitor.__doc__)
    cmd.add_argument('config', help='Monitoring configuration file')
    cmd.set_defaults(func=cmd_monitor)

    # Parse
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(level=[logging.WARN, logging.INFO, logging.DEBUG, logging.NOTSET][args.verbose])

    # Server
    args.server_id = args.server_id.split(':', 1)
    overc = Overclient(args.server_url, *args.server_id)

    # Command
    args.func(args, overc)
