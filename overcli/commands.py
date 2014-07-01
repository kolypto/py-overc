import os, sys
import argparse

from . import __author__, __email__, __version__
from overclient import Overclient

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

def cmd_monitor(args):
    """ Perform continuous monitoring """
    raise NotImplementedError()

def main():
    versionstr = 'v{} (c) {} <{}>'.format(__version__, __author__, __email__)
    parser = argparse.ArgumentParser(
        prog='overcli',
        description='OverC client',
        epilog=versionstr
    )
    parser.add_argument('-v', '--version', action='version', version=versionstr)
    parser.add_argument('-s', '--server', dest='server_url', help='OverC Server URL: "http://<host>:<port>/"')
    parser.add_argument('-i', '--server-id', dest='server_id', help='Server identification: "<name>:<key>"')

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

    # Server
    args.server_id = args.server_id.split(':', 1)
    overc = Overclient(args.server_url, *args.server_id)

    # Command
    args.func(args, overc)
