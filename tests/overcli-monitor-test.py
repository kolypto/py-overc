import os
from datetime import datetime
import unittest
from freezegun import freeze_time

from overcli.monitor import Service, ServicesMonitor


class MonitorTest(unittest.TestCase):
    """ Test overclient monitor """

    def assertServiceStates(self, service_states, expected_service_states):
        """ Test that the two service states are equal """
        f = lambda a, b: cmp(a['name'], b['name'])
        service_states.sort(f)
        expected_service_states.sort(f)
        self.assertListEqual(service_states, expected_service_states)

    def test_monitor(self):
        cwd = os.path.realpath('tests/data/overcli-config')

        # Create the monitor
        services = {
            'app': Service(15, 'app', cwd, './plugin.d/app.sh'),
            'que': Service(30, 'que', cwd, './plugin.d/que.sh'),
            'cpu': Service(30, 'cpu', cwd, './plugin.d/cpu.sh'),
            'echo': Service(15, 'echo', cwd, 'echo 1'),
        }
        monitor = ServicesMonitor(services.values())

        # Make sure it adjusted real periods
        self.assertAlmostEqual(services['app'].real_period, 15*0.8, delta=0.5)
        self.assertAlmostEqual(services['que'].real_period, 30*0.8, delta=0.5)
        self.assertAlmostEqual(services['cpu'].real_period, 30*0.8, delta=0.5)

        # Test sleep time
        self.assertEqual(monitor.sleep_time(), 0.0)  # should test immediately

        with freeze_time('2014-01-01 00:00:00'):
            # Now, test all services
            period, service_states = monitor.check()

            # Should have tested all of them
            self.assertAlmostEqual(period, 30.0, delta=0.1)  # period = max of all
            self.assertServiceStates(service_states, [
                {'name': 'app', 'state': 'OK', 'info': u'Running fine'},
                {'name': 'que', 'state': 'UNK', 'info': u'5 items'},
                {'name': 'cpu', 'state': 'WARN', 'info': u'50%'},
                {'name': 'echo', 'state': 'OK', 'info': u'1'},
            ])

            # Sleep time should be 15
            self.assertAlmostEqual(monitor.sleep_time(), 15.0*0.8, delta=0.5)

        with freeze_time('2014-01-01 00:00:11'): # 1 sec earlier
            self.assertAlmostEqual(monitor.sleep_time(), 1.0, delta=0.5)

            # No tests should be run
            period, service_states = monitor.check()
            self.assertEqual(period, 0)
            self.assertEqual(service_states, [])

        with freeze_time('2014-01-01 00:00:12'):
            self.assertEqual(monitor.sleep_time(), 0.0)

            # Run
            period, service_states = monitor.check()

            # Only `app` and `echo` should be tested
            self.assertAlmostEqual(period, 15.0, delta=0.1)
            self.assertServiceStates(service_states, [
                {'name': 'app', 'state': 'OK', 'info': u'Running fine'},
                {'name': 'echo', 'state': 'OK', 'info': u'1'},
            ])

            # Sleep time should be 15
            self.assertAlmostEqual(monitor.sleep_time(), 15.0 * 0.8, delta=0.5)

        with freeze_time('2014-01-01 00:00:24'):
            self.assertEqual(monitor.sleep_time(), 0.0)

            # Run
            period, service_states = monitor.check()

            # Should test all of them
            self.assertAlmostEqual(period, 30.0, delta=0.1)
            self.assertServiceStates(service_states, [
                {'name': 'app', 'state': 'OK', 'info': u'Running fine'},
                {'name': 'que', 'state': 'UNK', 'info': u'5 items'},
                {'name': 'cpu', 'state': 'WARN', 'info': u'50%'},
                {'name': 'echo', 'state': 'OK', 'info': u'1'},
            ])

            # Sleep time should be 15
            self.assertAlmostEqual(monitor.sleep_time(), 15.0 * 0.8, delta=0.5)

    def test_monitor_lag(self):
        """ Test monitoring of lagging tasks """
        cwd = os.path.realpath('tests/data/overcli-config')

        # Create the monitor
        services = {
            'lag1': Service(15, 'lag1', cwd, './plugin.d/lag.sh'),
            'lag2': Service(15, 'lag2', cwd, './plugin.d/lag.sh'),
            'lag3': Service(15, 'lag3', cwd, './plugin.d/lag.sh'),
            'lag4': Service(15, 'lag4', cwd, './plugin.d/lag.sh'),
        }
        monitor = ServicesMonitor(services.values())

        # Test all services, measure the time
        start = datetime.utcnow()
        period, service_states = monitor.check()
        finish = datetime.utcnow()
        finished_in = (finish - start).total_seconds()

        # Each task lags ~3sec, but they should've been run in parallel
        self.assertEqual(period, 15.0)
        self.assertEqual(len(service_states), 4)
        self.assertAlmostEqual(finished_in, 3.0, delta=1.0)

        # Lags should've been updated
        for s in services.values():
            self.assertAlmostEqual(s.lag, 3.0, delta=1.0)
