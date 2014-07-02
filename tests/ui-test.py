# -*- coding: utf-8 -*-

import unittest
from freezegun import freeze_time

from . import ApplicationTest
from overc.lib.db import models

class UITest(ApplicationTest, unittest.TestCase):
    """ Test UI """

    @freeze_time('2014-01-01 00:00:00')
    def test_api_status_server(self):
        """ Test /api/status/server/:server_id """
        # First, report data about two servers
        res, rv = self.test_client.jsonapi('POST', '/api/set/service/status', {
            'server': {'name': 'a.example.com', 'key': '1234'},
            'period': 60,
            'services': [
                {'name': 'app', 'state': 'OK', 'info': 'Fine'},
                {'name': 'db', 'state': 'OK', 'info': 'Available'},
            ]
        })
        self.assertEqual(rv.status_code, 200)
        res, rv = self.test_client.jsonapi('POST', '/api/set/service/status', {
            'server': {'name': 'b.example.com', 'key': '9876'},
            'period': 90,
            'services': [
                {'name': 'nginx', 'state': 'OK', 'info': 'Running'},
            ]
        })
        self.assertEqual(rv.status_code, 200)

        # Send some alerts
        res, rv = self.test_client.jsonapi('POST', '/api/set/alerts', {
            'server': {'name': 'a.example.com', 'key': '1234'},
            'alerts': [
                {'message': 'Something wrong'},
                {'message': 'Something very wrong'},
                {'message': 'Service too warm', 'service': 'db'},
            ]
        })
        self.assertEqual(rv.status_code, 200)

        # Now test the API: get all services' state
        res, rv = self.test_client.jsonapi('GET', '/ui/api/status/server')
        self.assertEqual(rv.status_code, 200)
        self.assertIn('servers', res)
        self.assertEqual(len(res['servers']), 2)

        # Test server 1
        server = res['servers'][0]
        services = server.pop('services')
        self.assertDictEqual(server, {'id': 1, 'name': 'a.example.com', 'title': u'a.example.com', 'ip': None, 'n_alerts': 2})
        self.assertEqual(services[0], {'id': 1, 'period': 60, 'name': 'app',   'title': u'app',   'n_alerts': 0,
                                       'state': {'rtime': '2014-01-01 00:00:00', 'timed_out': False, 'seen_ago': '0:00:00', 'state': 'OK', 'info': 'Fine'}})
        self.assertEqual(services[1], {'id': 2, 'period': 60, 'name': 'db',    'title': u'db',    'n_alerts': 1,
                                       'state': {'rtime': '2014-01-01 00:00:00', 'timed_out': False, 'seen_ago': '0:00:00', 'state': 'OK', 'info': 'Available'}})

        # Test server 2
        server = res['servers'][1]
        services = server.pop('services')
        self.assertEqual(services[0], {'id': 3, 'period': 90, 'name': 'nginx', 'title': u'nginx', 'n_alerts': 0,
                                       'state': {'rtime': '2014-01-01 00:00:00', 'timed_out': False, 'seen_ago': '0:00:00', 'state': 'OK', 'info': 'Running'}})

        # Now try to load a single server: /:server_id
        res, rv = self.test_client.jsonapi('GET', '/ui/api/status/server/2')
        # Test server 2
        server = res['servers'][0]
        services = server.pop('services')
        self.assertEqual(services[0], {'id': 3, 'period': 90, 'name': 'nginx', 'title': u'nginx', 'n_alerts': 0,
                                       'state': {'rtime': '2014-01-01 00:00:00', 'timed_out': False, 'seen_ago': '0:00:00', 'state': 'OK', 'info': 'Running'}})

    @freeze_time('2014-01-01 00:00:00')
    def test_api_status_alerts(self):
        """ Test /api/status/alerts/ """
        # Report alerts from two servers
        res, rv = self.test_client.jsonapi('POST', '/api/set/alerts', {
            'server': {'name': 'a.example.com', 'key': '1234'},
            'alerts': [
                {'message': 'o_O',},
                {'message': 'Hurts',},
                {'message': 'Sick', 'service': 'a'},
            ]
        })
        self.assertEqual(rv.status_code, 200)

        res, rv = self.test_client.jsonapi('POST', '/api/set/alerts', {
            'server': {'name': 'b.example.com', 'key': '9876'},
            'alerts': [
                {'message': 'WOW', },
            ]
        })
        self.assertEqual(rv.status_code, 200)

        # Alerts
        alerts = [
            None,
            {'id': 1, 'server': 'a.example.com', 'server_id': 1, 'service': None, 'service_id': None, 'ctime': '2014-01-01 00:00:00', 'channel': 'api', 'event': 'alert', 'message': 'o_O'},
            {'id': 2, 'server': 'a.example.com', 'server_id': 1, 'service': None, 'service_id': None, 'ctime': '2014-01-01 00:00:00', 'channel': 'api', 'event': 'alert', 'message': 'Hurts'},
            {'id': 3, 'server': 'a.example.com', 'server_id': 1, 'service': 'a',  'service_id': 1,    'ctime': '2014-01-01 00:00:00', 'channel': 'api', 'event': 'alert', 'message': 'Sick'},
            {'id': 4, 'server': 'b.example.com', 'server_id': 2, 'service': None, 'service_id': None, 'ctime': '2014-01-01 00:00:00', 'channel': 'api', 'event': 'alert', 'message': 'WOW'}
        ]

        # Test: /ui/api/status/alerts/server
        res, rv = self.test_client.jsonapi('GET', '/ui/api/status/alerts/server')
        self.assertIn('alerts', res)
        self.assertEqual(len(res['alerts']), 4)
        self.assertDictEqual(res['alerts'][0], alerts[4])
        self.assertDictEqual(res['alerts'][1], alerts[3])
        self.assertDictEqual(res['alerts'][2], alerts[2])
        self.assertDictEqual(res['alerts'][3], alerts[1])

        # Test: /ui/api/status/alerts/server/<server_id>
        res, rv = self.test_client.jsonapi('GET', '/ui/api/status/alerts/server/1')
        self.assertIn('alerts', res)
        self.assertEqual(len(res['alerts']), 3)
        self.assertDictEqual(res['alerts'][0], alerts[3])
        self.assertDictEqual(res['alerts'][1], alerts[2])
        self.assertDictEqual(res['alerts'][2], alerts[1])

        # Test: /ui/api/status/alerts/service/<service_id>
        res, rv = self.test_client.jsonapi('GET', '/ui/api/status/alerts/service/1')
        self.assertIn('alerts', res)
        self.assertEqual(len(res['alerts']), 1)
        self.assertDictEqual(res['alerts'][0], alerts[3])
