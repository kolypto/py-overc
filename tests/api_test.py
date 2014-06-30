import unittest
import base64
from datetime import datetime
from werkzeug.datastructures import Headers

from . import ApplicationTest
from overc.lib.db import models

class ReceiverTest(ApplicationTest, unittest.TestCase):
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
            self.assertEqual(alert.title, expected[i]['title'])
            self.assertEqual(alert.message, expected[i]['message'])

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
            dict(name='que', state='OK', info='2 ok'),
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
            dict(id=3, period=60, name='que', title=u'que', state=dict(id=3, checked=False, state='OK', info='2 ok')),
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
            dict(name='test', state='OK', info='2'),
        ])
        self.assertEqual(rv.status_code, 200)

        server = self.db.query(models.Server).filter(models.Server.id == 1).first()
        self.assertServices(server, [
            dict(id=1, period=60, name='app', title=u'app', state=dict(id=4, checked=False, state='OK', info='up 40s')),
            dict(id=2, period=60, name='cpu', title=u'cpu', state=dict(id=5, checked=False, state='OK', info='30% ok')),
            dict(id=3, period=60, name='que', title=u'que', state=dict(id=6, checked=False, state='OK', info='3 ok')),
            dict(id=4, period=60, name='moo', title=u'moo', state=dict(id=7, checked=False, state='OK', info=':)')),
            dict(id=5, period=60, name='test', title=u'test', state=dict(id=9, checked=False, state='OK', info='2')),
        ])

    def test_alerts(self):
        """ Test /api/set/alerts """
        # Send the first bunch of alerts
        res, rv = self.send_alerts({ 'name': 'localhost', 'key': '1234' }, [
            dict(title='Server lags'),
            dict(title='Too much logs', message='1000 lines'),
            dict(title='Service down', service='test'),
            dict(title='Service down again', service='test'),
        ])
        self.assertEqual(rv.status_code, 200)

        # Check services
        server = self.db.query(models.Server).filter(models.Server.id == 1).first()
        self.assertServices(server, [
            dict(id=1, period=None, name='test', title=u'test', state=None),
        ])

        # Check alerts
        self.assertAlerts(server, [
            dict(id=1, service_id=None, reported=False, channel='api', event='api', title=u'Server lags', message=u''),
            dict(id=2, service_id=None, reported=False, channel='api', event='api', title=u'Too much logs', message=u'1000 lines'),
            dict(id=3, service_id=1, reported=False, channel='api', event='api', title=u'Service down', message=u''),
            dict(id=4, service_id=1, reported=False, channel='api', event='api', title=u'Service down again', message=u''),
        ])
