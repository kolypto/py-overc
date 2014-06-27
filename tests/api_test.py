import unittest
import base64
from datetime import datetime
from werkzeug.datastructures import Headers

from . import ApplicationTest
from overc.lib.db import models

class ReceiverTest(ApplicationTest, unittest.TestCase):
    """ Test API: /api """

    def send_service_status(self, server, services, period=60):
        h = Headers()
        h.add('Authorization', 'Basic ' + base64.b64encode(server))
        return self.test_client.jsonapi('POST', '/api/service/status', {
            'period': period,
            'services': services
        }, headers=h)

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

            self.assertEqual(service.state.id, expected[i]['state']['id'])
            self.assertEqual(service.state.checked, expected[i]['state']['checked'])
            self.assertIsInstance(service.state.rtime, datetime)
            self.assertEqual(service.state.state, expected[i]['state']['state'])
            self.assertEqual(service.state.info, expected[i]['state']['info'])

    def test_service_status_single(self):
        """ Test /api/service/ """

        # Send the first status
        res, rv = self.send_service_status('localhost:1234', [
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
        res, rv = self.send_service_status('localhost:1234', [
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
        res, rv = self.send_service_status('localhost:1--4', [])
        self.assertEqual(rv.status_code, 403)
        self.assertDictEqual(res, {'error': 'Invalid server key'})
