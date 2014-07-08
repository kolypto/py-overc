import logging
import subprocess, shlex
import threading
from datetime import datetime

logger = logging.getLogger(__name__)


class Service(object):
    def __init__(self, period, name, cwd, command, max_lag=None):
        """ Define a service to be monitored
        :param period: Test period, seconds
        :type period: int
        :param name: Service name
        :type name: str
        :param cwd: Current working directory
        :type cwd: str
        :param command: Full command path that test service state
        :type command: str
        """
        self.period = period
        self.name = name
        self.cwd = cwd
        self.command = command

        #: Plugin execution time
        self.lag = 0
        self.max_lag = max_lag

        #: Timestamp when this service was tested last time
        self.last_tested = None

    def __str__(self):
        return self.name

    PERIOD_MARGIN_FACTOR = 0.8
    LAG_MARGIN_FACTOR = 3.0

    @property
    def real_period(self):
        """ Real update period, including lags and safety reserves """
        return max(
            self.period * self.PERIOD_MARGIN_FACTOR -
            (self.max_lag if self.max_lag else self.lag * self.LAG_MARGIN_FACTOR),
            0.0)

    def next_update_in(self, now):
        """ Get the relative time for the next update
        :param now: Current datetime
        :type now: datetime
        :return: Delay, seconds
        :rtype: float
        """
        # Never updated: NOW!
        if self.last_tested is None:
            return 0.0

        # Was updated
        seconds_ago = (now - self.last_tested).total_seconds()
        delay = self.real_period - seconds_ago
        return max(delay, 0.0)  # don't allow it to be negative


    def get_state(self):
        """ Execute plugin and get service's state
        :return: Process state for the API
        :rtype: dict
        :exception OSError: Failed to execute plugin
        """
        # Execute command
        try:
            process = subprocess.Popen(
                shlex.split(self.command),
                cwd=self.cwd,
                stdin=None,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT
            )
            process.wait()
        except OSError, e:
            error_msg = u'Failed to execute plugin `{}` by command `{}`: {}'.format(self.name, self.command, e.message)
            logger.exception(error_msg)
            return {
                'name': self.name,
                'state': 'UNK',
                'info': error_msg,
                'period': self.period
            }

        # Analyze the result
        try:
            # Info
            info = process.stdout.read()

            # Determine state
            try:
                state = ['OK', 'WARN', 'FAIL', 'UNK'][process.returncode]
            except IndexError:
                logger.error(u'Plugin `{}` failed with code {}: {}'.format(self.name, process.returncode, info))
                state = 'UNK'

            # Finish
            return {
                'name': self.name,
                'state': state,
                'info': unicode(info).rstrip()
            }
        finally:
            process.stdout.close()


class ServicesMonitor(object):
    def __init__(self, services):
        """ Monitor for Services
        :param services: List of Services to be monitored
        :type services: list
        """
        self.services = services

    def _check_services(self, services):
        """ Check services provided as an argument
        :param services: List of services to test
        :type services: list[Service]
        :return: `services` argument value for reporting
        :rtype: list
        """
        now = datetime.utcnow()

        # Worker
        service_states = []
        def task(service):
            # Get state, measure lag
            start = datetime.utcnow()
            state = service.get_state()
            finish = datetime.utcnow()

            # Update lag
            service.lag = (finish - start).total_seconds()

            # Add state
            service_states.append(state)
            logger.debug(u'Checked service {} (lag={}, real_period={}): last checked {} ago, state={}: {}'.format(
                service.name,
                service.lag,
                service.real_period,
                now - service.last_tested if service.last_tested else '(never)',
                state['state'], state['info']
            ))

            # Update timestamp
            service.last_tested = now

        # Run
        threads = [threading.Thread(target=task, args=(service,)) for service in services]
        for t in threads: t.start()
        for t in threads: t.join()
        # TODO: declare max waiting time. If any process doesnt manage to finish in time -- report it as a separate request

        return service_states

    def sleep_time(self):
        """ Determine how many seconds is it ok to sleep before any service state should be reported
        :rtype: float
        """
        now = datetime.utcnow()
        return min(service.next_update_in(now) for service in self.services)

    def check(self):
        """ Check services whose time has come, once.
        :return: (period, service_states) to be reported to the API
        :rtype: (int, dict)
        """
        # Determine which services to test
        # TODO: use a smarter algorithm to detect which services to check
        max_lag = max(service.lag for service in self.services)
        now = datetime.utcnow()
        services = [ service
                     for service in self.services
                     if service.next_update_in(now) <= max_lag
        ]
        if not services:
            return 0, []

        period = max(service.period for service in services)

        # Test them
        service_states = self._check_services(services)

        # Report
        return int(period), service_states
