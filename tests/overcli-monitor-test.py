import os
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
        }
        monitor = ServicesMonitor(services.values())

        # Make sure it has measured lags for services
        for s in services.values():
            self.assertGreater(s.lag, 0.0)
            self.assertAlmostEqual(s.lag, 0.0, delta=0.5)  # should be very fast

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

            # Only `app` should be tested
            self.assertAlmostEqual(period, 15.0, delta=0.1)
            self.assertServiceStates(service_states, [
                {'name': 'app', 'state': 'OK', 'info': u'Running fine'},
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
            ])

            # Sleep time should be 15
            self.assertAlmostEqual(monitor.sleep_time(), 15.0 * 0.8, delta=0.5)
