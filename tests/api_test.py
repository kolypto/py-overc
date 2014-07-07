# -*- coding: utf-8 -*-

from time import sleep
import unittest
import os
from datetime import datetime

from . import ApplicationTest
from overc.lib.db import models
from overc.lib.alerts import AlertPlugin
from overc.lib.supervise import supervise_once


class ApiTest(ApplicationTest, unittest.TestCase):
    """ Test API: /api """

    def send_service_status(self, server, services, period=60):
        return self.test_client.jsonapi('POST', '/api/set/service/status', {
            'server': server,
            'period': period,
            'services': services
        })

    def send_alerts(self, server, alerts):
        return self.test_client.jsonapi('POST', '/api/set/alerts', {
            'server': server,
            'alerts': alerts,
        })

    def assertServices(self, server, expected):
        """ Helper to test for services' states """
        # Get services
        services = list(server.services)
        services.sort(lambda a, b: cmp(a.id, b.id))
        self.assertEqual(len(services), len(expected))

        # Iterate
        for i, service in enumerate(services):
            self.assertEqual(service.id, expected[i]['id'])
            self.assertEqual(service.period, expected[i]['period'])
            self.assertEqual(service.name, expected[i]['name'])
            self.assertEqual(service.title, expected[i]['title'])

            if expected[i]['state'] is None:
                self.assertIsNone(service.state)
            else:
                self.assertEqual(service.state.id, expected[i]['state']['id'])
                self.assertEqual(service.state.checked, expected[i]['state']['checked'])
                self.assertIsInstance(service.state.rtime, datetime)
                self.assertEqual(service.state.state, expected[i]['state']['state'])
                self.assertEqual(service.state.info, expected[i]['state']['info'])

    def assertAlerts(self, server, expected):
        """ Helper to test for server alerts """
        # Get alerts
        alerts = list(server.alerts)
        alerts.sort(lambda a, b: cmp(a.id, b.id))
        self.assertEqual(len(alerts), len(expected))

        # Iterate
        for i, alert in enumerate(alerts):
            self.assertEqual(alert.id, expected[i]['id'])
            self.assertEqual(alert.service_id, expected[i]['service_id'])
            self.assertEqual(alert.reported, expected[i]['reported'])
            self.assertIsInstance(alert.ctime, datetime)
            self.assertEqual(alert.channel, expected[i]['channel'])
            self.assertEqual(alert.event, expected[i]['event'])
            self.assertEqual(alert.message, expected[i]['message'])

    def test_ping(self):
        """ Test /api/ping """
        # First ping: server is created
        res, rv = self.test_client.jsonapi('POST', '/api/ping', { 'server': { 'name': 'localhost', 'key': '1234' } })
        self.assertEqual(rv.status_code, 200)

        # Server was created
        server = self.db.query(models.Server).filter(models.Server.id == 1).first()
        self.assertIsNotNone(server)
        self.assertEqual(server.name, 'localhost')
        self.assertEqual(server.title, 'localhost')
        self.assertEqual(server.key, '1234')

        # Second ping: still fine
        res, rv = self.test_client.jsonapi('POST', '/api/ping', {'server': {'name': 'localhost', 'key': '1234'}})
        self.assertEqual(rv.status_code, 200)

        # Ping with a wrong key: error
        res, rv = self.test_client.jsonapi('POST', '/api/ping', {'server': {'name': 'localhost', 'key': '1__4'}})
        self.assertEqual(rv.status_code, 403)

    def test_service_status(self):
        """ Test /api/set/service/status """

        # Test validation: 'server'
        res, rv = self.send_service_status({'name': 'localhost'}, [])
        self.assertEqual(rv.status_code, 400)
        self.assertDictEqual(res, {'error': 'Data: "server.key" should be a string'})

        # Send the first status
        res, rv = self.send_service_status({'name': 'localhost', 'key': '1234'}, [
            dict(name='app', state='OK', info='up 30s'),
            dict(name='cpu', state='OK', info='50% ok'),
            dict(name='que', state='HEY', info='2 ok'), # unsupported state
        ])
        self.assertEqual(rv.status_code, 200)

        # A server should've been created
        server = self.db.query(models.Server).filter(models.Server.id == 1).first()
        self.assertEqual(server.name, 'localhost')
        self.assertEqual(server.title, 'localhost')
        self.assertEqual(server.key, '1234')

        # Services should've been created
        self.assertServices(server, [
            dict(id=1, period=60, name='app', title=u'app', state=dict(id=1, checked=False, state='OK', info='up 30s')),
            dict(id=2, period=60, name='cpu', title=u'cpu', state=dict(id=2, checked=False, state='OK', info='50% ok')),
            dict(id=3, period=60, name='que', title=u'que', state=dict(id=3, checked=False, state='UNK', info='2 ok (sent unsupported state: "HEY")')),
        ])

        # Update with more status
        res, rv = self.send_service_status({'name': 'localhost', 'key': '1234'}, [
            dict(name='app', state='OK', info='up 40s'),
            dict(name='cpu', state='OK', info='30% ok'),
            dict(name='que', state='OK', info='3 ok'),
            dict(name='moo', state='OK', info=':)')
        ])
        self.assertEqual(rv.status_code, 200)

        # Test Services
        server = self.db.query(models.Server).filter(models.Server.id == 1).first()
        self.assertServices(server, [
            dict(id=1, period=60, name='app', title=u'app', state=dict(id=4, checked=False, state='OK', info='up 40s')),
            dict(id=2, period=60, name='cpu', title=u'cpu', state=dict(id=5, checked=False, state='OK', info='30% ok')),
            dict(id=3, period=60, name='que', title=u'que', state=dict(id=6, checked=False, state='OK', info='3 ok')),
            dict(id=4, period=60, name='moo', title=u'moo', state=dict(id=7, checked=False, state='OK', info=':)')),
        ])

        # Try to update with an invalid server key
        res, rv = self.send_service_status({'name': 'localhost', 'key': '____'}, [])
        self.assertEqual(rv.status_code, 403)
        self.assertDictEqual(res, {'error': 'Invalid server key'})

        # Finally, try to report a single service multiple times and make sure it does not make duplicates
        res, rv = self.send_service_status({'name': 'localhost', 'key': '1234'}, [
            dict(name='test', state='OK', info='1'),
            dict(name='test', state='OK', info='2', period=13),
        ])
        self.assertEqual(rv.status_code, 200)

        server = self.db.query(models.Server).filter(models.Server.id == 1).first()
        self.assertServices(server, [
            dict(id=1, period=60, name='app', title=u'app', state=dict(id=4, checked=False, state='OK', info='up 40s')),
            dict(id=2, period=60, name='cpu', title=u'cpu', state=dict(id=5, checked=False, state='OK', info='30% ok')),
            dict(id=3, period=60, name='que', title=u'que', state=dict(id=6, checked=False, state='OK', info='3 ok')),
            dict(id=4, period=60, name='moo', title=u'moo', state=dict(id=7, checked=False, state='OK', info=':)')),
            dict(id=5, period=13, name='test', title=u'test', state=dict(id=9, checked=False, state='OK', info='2')),
        ])

    def test_alerts(self):
        """ Test /api/set/alerts """
        # Send the first bunch of alerts
        res, rv = self.send_alerts({ 'name': 'localhost', 'key': '1234' }, [
            dict(message='Server lags'),
            dict(message='Too much logs'),
            dict(message='Service down', service='test'),
            dict(message='Service down again', service='test'),
        ])
        self.assertEqual(rv.status_code, 200)

        # Check services
        server = self.db.query(models.Server).filter(models.Server.id == 1).first()
        self.assertServices(server, [
            dict(id=1, period=None, name='test', title=u'test', state=None),
        ])

        # Check alerts
        self.assertAlerts(server, [
            dict(id=1, service_id=None, reported=False, channel='api', event='alert', message=u'Server lags'),
            dict(id=2, service_id=None, reported=False, channel='api', event='alert', message=u'Too much logs'),
            dict(id=3, service_id=1, reported=False, channel='api', event='alert', message=u'Service down'),
            dict(id=4, service_id=1, reported=False, channel='api', event='alert', message=u'Service down again'),
        ])

    def test_supervisor(self): # TODO: use freezegun
        """ Test how alerts are created when the service state changes """
        # Prerequisites
        def overc_readlog():
            """ Read overc.log and remove """
            overc_log = '/tmp/overc.log'
            if not os.path.exists(overc_log):
                return None
            try:
                with open(overc_log, 'r') as f:
                    return f.read().encode('utf-8')
            finally:
                os.unlink(overc_log)
        overc_readlog()

        # Dry run first
        self.assertEqual(supervise_once(self.app, self.db), (0, 0))
        self.assertIsNone(overc_readlog())

        # Test a: OK
        # Nothing should be alerted or reported
        res, rv = self.send_service_status({'name': 'localhost', 'key': '1234'}, [
            {'name': 'a', 'state': 'OK', 'info': 'hey1'},
        ])
        self.assertEqual(res['ok'], 1)
        self.assertEqual(supervise_once(self.app, self.db), (0, 0))
        self.assertIsNone(overc_readlog())

        # Test b: UNK
        # UNKs should always be reported
        # Also, that's the first reported state, and it should only be reported once
        res, rv = self.send_service_status({'name': 'localhost', 'key': '1234'}, [
            {'name': 'b', 'state': 'BULLSHIT', 'info': 'hey2'},
        ])
        self.assertEqual(res['ok'], 1)
        self.assertEqual(supervise_once(self.app, self.db), (1, 1)) # 1 alert
        self.assertMultiLineEqual(
            overc_readlog(),
            u'localhost b: '
            u'[service:state/UNK] '
            u'State changed: "(?)" -> "UNK"'
            '\n'
            u'Current: UNK: hey2 (sent unsupported state: "BULLSHIT")'
            '\n'
        )

        # Test a: OK -> WARN
        # State change should be reported
        res, rv = self.send_service_status({'name': 'localhost', 'key': '1234'}, [
            {'name': 'a', 'state': 'WARN', 'info': 'hey3'},
        ])
        self.assertEqual(res['ok'], 1)
        self.assertEqual(supervise_once(self.app, self.db), (1, 1)) # 1 alert
        self.assertMultiLineEqual(
            overc_readlog(),
            u'localhost a: '
            u'[service:state/WARN] '
            u'State changed: "OK" -> "WARN"'
            '\n'
            u'Current: WARN: hey3'
            '\n'
        )

        # Test a: WARN -> WARN
        # State not changed, no alert
        res, rv = self.send_service_status({'name': 'localhost', 'key': '1234'}, [
            {'name': 'a', 'state': 'WARN', 'info': 'hey4'},
        ])
        self.assertEqual(res['ok'], 1)
        self.assertEqual(supervise_once(self.app, self.db), (0, 0))  # no alerts

        # Test a: WARN -> OK
        # State change should be reported
        res, rv = self.send_service_status({'name': 'localhost', 'key': '1234'}, [
            {'name': 'a', 'state': 'OK', 'info': 'hey5'},
        ])
        self.assertEqual(res['ok'], 1)
        self.assertEqual(supervise_once(self.app, self.db), (1, 1))  # 1 alert
        self.assertMultiLineEqual(
            overc_readlog(),
            u'localhost a: '
            u'[service:state/OK] '
            u'State changed: "WARN" -> "OK"'
            '\n'
            u'Current: OK: hey5'
            '\n'
        )

        # Test a: OK -> (timeout)
        res, rv = self.send_service_status({'name': 'localhost', 'key': '1234'}, [
            {'name': 'a', 'state': 'OK', 'info': 'hey6'},
        ], period=1)
        self.assertEqual(res['ok'], 1)
        self.assertEqual(supervise_once(self.app, self.db), (0, 0))  # all ok

        sleep(2)

        self.assertEqual(supervise_once(self.app, self.db), (1, 1))  # 1 alert
        self.assertMultiLineEqual(
            overc_readlog(),
            u'localhost a: '
            u'[plugin/offline] '
            u'Monitoring plugin offline'
            '\n'
            u'Current: OK: hey6'
            '\n'
        )

        # Still offline, it should not report again
        self.assertEqual(supervise_once(self.app, self.db), (0, 0))  # no alerts

        # Test a: OK back again
        res, rv = self.send_service_status({'name': 'localhost', 'key': '1234'}, [
            {'name': 'a', 'state': 'OK', 'info': 'hey7'},
        ], period=60)
        self.assertEqual(res['ok'], 1)
        self.assertEqual(supervise_once(self.app, self.db), (1, 1))  # 1 alert
        self.assertMultiLineEqual(
            overc_readlog(),
            u'localhost a: '
            u'[plugin/online] '
            u'Monitoring plugin back online'
            '\n' +
            u'Current: OK: hey7'
            '\n'
        )

        # Still online, it should not report again
        self.assertEqual(supervise_once(self.app, self.db), (0, 0))  # no alerts



        # Test manual alerts
        self.send_alerts({'name': 'localhost', 'key': '1234'}, [
            dict(message='Server lags'),
            dict(message='Service down again', service='test'),
        ])
        self.assertEqual(res['ok'], 1)
        self.assertEqual(supervise_once(self.app, self.db), (0, 2))  # 2 alerts

        self.assertMultiLineEqual(
            overc_readlog(),
            u'localhost: '
            u'[api/alert] '
            u'Server lags'
            '\n'
            u'localhost test: '
            u'[api/alert] '
            u'Service down again'
            '\n'
        )

        # Should not report again
        self.assertEqual(supervise_once(self.app, self.db), (0, 0))  # no alerts



        # See how a failing script behaves
        self.app.app.config['ALERT_PLUGINS'].append(
            AlertPlugin(name='error', cwd=self.app.app.instance_path, command='./alert.d/error.sh')
        )

        self.send_alerts({'name': 'localhost', 'key': '1234'}, [
            dict(message='Server lags'),
        ])
        self.assertEqual(res['ok'], 1)
        self.assertEqual(supervise_once(self.app, self.db), (0, 1))  # 1 alert, but 1 additional fatal

        self.assertMultiLineEqual(
            overc_readlog(),
            u'localhost: '
            u'[api/alert] '
            u'Server lags'
            '\n'
            u'Alert plugin `error` failed: Command \'./alert.d/error.sh\' returned non-zero exit status 1'
            '\n'
        )

        # See how a missing script behaves
        self.app.app.config['ALERT_PLUGINS'].pop()
        self.app.app.config['ALERT_PLUGINS'].append(
            AlertPlugin(name='nonexistent', cwd=self.app.app.instance_path, command='./alert.d/nonexistent')
        )

        self.send_alerts({'name': 'localhost', 'key': '1234'}, [
            dict(message='Server lags'),
        ])
        self.assertEqual(res['ok'], 1)
        self.assertEqual(supervise_once(self.app, self.db), (0, 1))  # 1 alert, but 1 additional fatal

        self.assertMultiLineEqual(
            overc_readlog(),
            u'localhost: '
            u'[api/alert] '
            u'Server lags'
            '\n'
            u'Alert plugin `nonexistent` failed: [Errno 2] No such file or directory'
            '\n'
        )

    def test_unicode(self):
        """ Check how API handles unicode """
        res, rv = self.send_service_status({'name': u'сервер', 'key': u'ключ'}, [
            { 'name': u'сервис', 'state': u'ХОРОШО', 'info': u'Всё отлично' }
        ])
        self.assertEqual(rv.status_code, 200)
