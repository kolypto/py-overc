# -*- coding: utf-8 -*-

import unittest
from freezegun import freeze_time

from . import ApplicationTest
from overc.lib.db import models

class UITest(ApplicationTest, unittest.TestCase):
    """ Test UI """

    def assertItemsCount(self, servers, services, alerts):
        """ Count items in the DB """
        self.assertEqual(self.db.query(models.Server).count(), servers)
        self.assertEqual(self.db.query(models.Service).count(), services)
        self.assertEqual(self.db.query(models.Alert).count(), alerts)

    @freeze_time('2014-01-01 00:00:00')
    def test_api_status_server(self):
        """ Test /api/status/server/:server_id """
        # First, report data about two servers
        res, rv = self.test_client.jsonapi('POST', '/api/set/service/status', {
            'server': {'name': 'a.example.com', 'key': '1234'},
            'period': 60,
            'services': [
                {'name': 'app', 'state': 'OK', 'info': 'Fine'},  # id=1
                {'name': 'db', 'state': 'OK', 'info': 'Available'},  # id=2
            ]
        })
        self.assertEqual(rv.status_code, 200)
        res, rv = self.test_client.jsonapi('POST', '/api/set/service/status', {
            'server': {'name': 'b.example.com', 'key': '9876'},
            'period': 90,
            'services': [
                {'name': 'nginx', 'state': 'OK', 'info': 'Running'},  # id=3
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
        res, rv = self.test_client.jsonapi('GET', '/ui/api/status/')
        self.assertEqual(rv.status_code, 200)
        self.assertDictEqual(res['stats'], { 'n_alerts': 3, 'last_state_id': 3, 'supervisor_lag': 0.0 })
        self.assertIn('servers', res)
        self.assertEqual(len(res['servers']), 2)

        # Test server 1
        server = res['servers'][0]
        services = server.pop('services')
        self.assertEqual(len(services), 2)
        self.assertDictEqual(server, {'id': 1, 'name': 'a.example.com', 'title': u'a.example.com', 'ip': None, 'n_alerts': 2})
        self.assertEqual(services[0], {'id': 1, 'period': 60, 'name': 'app',   'title': u'app',   'n_alerts': 0,
                                       'state': {'rtime': '2014-01-01 00:00:00', 'timed_out': False, 'seen_ago': '0:00:00', 'state': 'OK', 'info': 'Fine'}})
        self.assertEqual(services[1], {'id': 2, 'period': 60, 'name': 'db',    'title': u'db',    'n_alerts': 1,
                                       'state': {'rtime': '2014-01-01 00:00:00', 'timed_out': False, 'seen_ago': '0:00:00', 'state': 'OK', 'info': 'Available'}})

        # Test server 2
        server = res['servers'][1]
        services = server.pop('services')
        self.assertEqual(len(services), 1)
        self.assertEqual(services[0], {'id': 3, 'period': 90, 'name': 'nginx', 'title': u'nginx', 'n_alerts': 0,
                                       'state': {'rtime': '2014-01-01 00:00:00', 'timed_out': False, 'seen_ago': '0:00:00', 'state': 'OK', 'info': 'Running'}})



        # Now try to load a single server: /server/:server_id
        res, rv = self.test_client.jsonapi('GET', '/ui/api/status/server/2')
        self.assertEqual(rv.status_code, 200)
        self.assertDictEqual(res['stats'], {'n_alerts': 0, 'last_state_id': 3, 'supervisor_lag': 0.0})
        self.assertEqual(len(res['servers']), 1)
        self.assertEqual(len(res['servers'][0]['services']), 1)
        # Test server 2
        server = res['servers'][0]
        services = server.pop('services')
        self.assertEqual(services[0], {'id': 3, 'period': 90, 'name': 'nginx', 'title': u'nginx', 'n_alerts': 0,
                                       'state': {'rtime': '2014-01-01 00:00:00', 'timed_out': False, 'seen_ago': '0:00:00', 'state': 'OK', 'info': 'Running'}})



        # Now, try to load a single service: /service/:service_id
        res, rv = self.test_client.jsonapi('GET', '/ui/api/status/service/2')
        self.assertEqual(rv.status_code, 200)
        self.assertDictEqual(res['stats'], {'n_alerts': 1, 'last_state_id': 2, 'supervisor_lag': 0.0})
        self.assertEqual(len(res['servers']), 1)
        self.assertEqual(len(res['servers'][0]['services']), 1)
        # Test server 1
        server = res['servers'][0]
        services = server.pop('services')
        self.assertEqual(services[0], {'id': 2, 'period': 60, 'name': 'db',    'title': u'db',    'n_alerts': 1,
                                       'state': {'rtime': '2014-01-01 00:00:00', 'timed_out': False, 'seen_ago': '0:00:00', 'state': 'OK', 'info': 'Available'}})



        # Now, load service states: /service/:service_id/states
        res, rv = self.test_client.jsonapi('GET', '/ui/api/status/service/2/states')
        self.assertEqual(rv.status_code, 200)
        states = res.pop('states')
        self.assertEqual(len(states), 1)
        self.assertDictEqual(states[0], {
            'id': 2, 'rtime': '2014-01-01 00:00:00', 'state': 'OK', 'info': 'Available',
            'alerts': [],
            'service_id': 2, 'service': 'db'
        })

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
            {'id': 1, 'server': 'a.example.com', 'server_id': 1, 'service': None, 'service_id': None, 'ctime': '2014-01-01 00:00:00', 'channel': 'api', 'event': 'alert', 'message': 'o_O',   'state_info': None},
            {'id': 2, 'server': 'a.example.com', 'server_id': 1, 'service': None, 'service_id': None, 'ctime': '2014-01-01 00:00:00', 'channel': 'api', 'event': 'alert', 'message': 'Hurts', 'state_info': None},
            {'id': 3, 'server': 'a.example.com', 'server_id': 1, 'service': 'a',  'service_id': 1,    'ctime': '2014-01-01 00:00:00', 'channel': 'api', 'event': 'alert', 'message': 'Sick',  'state_info': None},
            {'id': 4, 'server': 'b.example.com', 'server_id': 2, 'service': None, 'service_id': None, 'ctime': '2014-01-01 00:00:00', 'channel': 'api', 'event': 'alert', 'message': 'WOW',   'state_info': None}
        ]

        # Test: /ui/api/status/alerts/server
        res, rv = self.test_client.jsonapi('GET', '/ui/api/status/alerts/')
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


    def test_api_items_delete(self):
        """ Test items API: DELETE /api/item/* """
        # First, report something
        res, rv = self.test_client.jsonapi('POST', '/api/set/service/status', {
            'server': {'name': 'a.example.com', 'key': '1234'},
            'period': 60,
            'services': [ {'name': str(i), 'state': 'OK', 'info': 'Fine'} for i in range(1, 5) ]
        })
        self.assertEqual(rv.status_code, 200)

        res, rv = self.test_client.jsonapi('POST', '/api/set/alerts', {
            'server': {'name': 'a.example.com', 'key': '1234'},
            'alerts': [{'message': '0'}] + [ {'message': str(i), 'service': str(i)} for i in range(1, 5) ]
        })
        self.assertEqual(rv.status_code, 200)

        self.assertItemsCount(1, 4, 5)  # 1 server, 4 services, 4 service alerts, 1 server alert

        # Try to delete service
        res, rv = self.test_client.jsonapi('DELETE', '/ui/api/item/service/4')
        self.assertEqual(rv.status_code, 200)
        self.assertIsNone(self.db.query(models.Service).get(4))
        self.assertItemsCount(1, 3, 4)  # -1 service: -1 service alert

        # Try to delete server
        res, rv = self.test_client.jsonapi('DELETE', '/ui/api/item/server/1')
        self.assertEqual(rv.status_code, 200)
        self.assertIsNone(self.db.query(models.Server).get(1))
        self.assertItemsCount(0, 0, 0)  # -1 server: -3 services, -3 service alerts, -1 server alert
