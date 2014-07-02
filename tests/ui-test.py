# -*- coding: utf-8 -*-

import unittest
from freezegun import freeze_time

from . import ApplicationTest
from overc.lib.db import models

class UITest(ApplicationTest, unittest.TestCase):
    """ Test UI """

    @freeze_time('2014-01-01 00:00:00')
    def test_api_status_server(self):
        """ Test /api/status/server """
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

        # Now test the API: get all services' state
        res, rv = self.test_client.jsonapi('GET', '/ui/api/status/server')
        self.assertEqual(rv.status_code, 200)
        self.assertIn('servers', res)
        self.assertEqual(len(res['servers']), 2)

        # Test server 1
        server = res['servers'][0]
        services = server.pop('services')
        self.assertDictEqual(server, {'id': 1, 'name': 'a.example.com', 'title': u'a.example.com', 'ip': None})
        self.assertEqual(services[0], {'id': 1, 'period': 60, 'name': 'app',   'title': u'app',   'state': {'rtime': '2014-01-01 00:00:00', 'timed_out': False, 'seen_ago': '0:00:00', 'state': 'OK', 'info': 'Fine'}})
        self.assertEqual(services[1], {'id': 2, 'period': 60, 'name': 'db',    'title': u'db',    'state': {'rtime': '2014-01-01 00:00:00', 'timed_out': False, 'seen_ago': '0:00:00', 'state': 'OK', 'info': 'Available'}})

        # Test server 2
        server = res['servers'][1]
        services = server.pop('services')
        self.assertEqual(services[0], {'id': 3, 'period': 90, 'name': 'nginx', 'title': u'nginx', 'state': {'rtime': '2014-01-01 00:00:00', 'timed_out': False, 'seen_ago': '0:00:00', 'state': 'OK', 'info': 'Running'}})

        # Now try to load a single server
        res, rv = self.test_client.jsonapi('GET', '/ui/api/status/server/2')
        # Test server 2
        server = res['servers'][0]
        services = server.pop('services')
        self.assertEqual(services[0], {'id': 3, 'period': 90, 'name': 'nginx', 'title': u'nginx', 'state': {'rtime': '2014-01-01 00:00:00', 'timed_out': False, 'seen_ago': '0:00:00', 'state': 'OK', 'info': 'Running'}})
