import logging
from time import sleep
import os, tempfile

from overc.src.init import init_db_engine, init_db_session
from overc.lib.db import models
from overc.lib import alerts

logger = logging.getLogger(__name__)

# TODO: these routines should obtain an exclusive lock so multiple supervise processes does not issue alerts multiple times


def _check_service_states(ssn):
    """ Test all service states, raise alerts if necessary
    :param ssn: Database session
    :type ssn: sqlalchemy.orm.session.Session
    :returns: The number of new alerts reported
    :rtype: int
    """
    # Fetch all states that are not yet checked
    service_states = ssn.query(models.ServiceState)\
        .filter(models.ServiceState.checked == False)\
        .order_by(models.ServiceState.id.asc())\
        .all()

    # Check them one by one
    new_alerts = 0
    for s in service_states:
        logger.debug(u'Checking service {server}:`{service}` state #{id}: {state}'.format(id=s.id, server=s.service.server, service=s.service, state=s.state))

        # Report state changes and abnormal states
        if s.state != (s.prev.state if s.prev else 'OK'):
            ssn.add(models.Alert(
                server=s.service.server,
                service=s.service,
                service_state=s,
                channel='service:state',
                event=s.state,
                message=u'State changed: "{}" -> "{}"'.format(s.prev.state if s.prev else '(?)', s.state)
            ))
            new_alerts += 1

        # Save
        s.checked = True
        ssn.add(s)

    # Finish
    ssn.commit()
    return new_alerts


def _check_service_timeouts(ssn):
    """ Test all services for timeouts
    :param ssn: Database session
    :type ssn: sqlalchemy.orm.session.Session
    :returns: The number of new alerts reported
    :rtype: int
    """
    # Fetch all services which have enough data
    services = ssn.query(models.Service)\
        .filter(
            models.Service.period is not None,
            models.Service.state is not None
        ).all()

    # Detect timeouts
    new_alerts = 0
    for s in services:
        # Update state
        was_timed_out = s.timed_out
        seen_ago = s.update_timed_out()

        logger.debug(u'Checking service {service}: seen_ago={seen_ago}: {timed_out}{was_timed_out}'.format(
            service=s, seen_ago=seen_ago,
            timed_out='TIMED OUT' if s.timed_out else 'ok',
            was_timed_out=', and was timed out' if was_timed_out else ''))

        # Changed?
        if was_timed_out != s.timed_out:
            alert = models.Alert(
                server=s.server,
                service=s,
                service_state=s.state,
                channel='plugin'
            )
            alert.event = 'offline' if s.timed_out else 'online'
            alert.message = u'Monitoring plugin offline' if s.timed_out else u'Monitoring plugin back online'

            ssn.add(alert)
            ssn.add(s)
            new_alerts += 1

    # Finish
    ssn.commit()
    return new_alerts


def _send_pending_alerts(ssn, alert_plugins):
    """ Send pending alerts
    :param ssn: Database session
    :type ssn: sqlalchemy.orm.session.Session
    :param alert_plugins: Application config for alerts
    :type alert_plugins: list[alerts.AlertPlugin]
    :returns: The number of alerts sent
    :rtype: int
    """
    # Fetch all alerts which were not reported
    pending_alerts = ssn.query(models.Alert)\
        .filter(models.Alert.reported == False)\
        .all()

    # Report them one by one
    for a in pending_alerts:
        logger.debug(u'Sending alert #{id}: server={server}, service={service}, [{channel}/{event}]'.format(id=a.id, server=a.server, service=a.service, channel=a.channel, event=a.event))

        # Prepare alert message
        alert_message = unicode(a) + "\n"
        if a.service and a.service.state:
            s = a.service.state
            alert_message += u"Current: {}: {}\n".format(s.state, s.info)

        # Potential exceptions are handled & logged down there
        alerts.send_alert_with_plugins(alert_plugins, alert_message)
        a.reported = True
        ssn.add(a)

    # Finish
    ssn.commit()
    return len(pending_alerts)


def supervise_once(app, ssn):
    """ Perform all background actions once:

    * Check service states
    * Check for service timeouts
    * Send alerts

    :param app: Application
    :type app: OvercApplication
    :returns: (New alerts created, Alerts sent)
    :rtype: (int, int)
    """
    # Act
    new_alerts, sent_alerts = 0, 0
    new_alerts += _check_service_states(ssn)
    new_alerts += _check_service_timeouts(ssn)
    sent_alerts = _send_pending_alerts(ssn, app.app.config['ALERT_PLUGINS'])

    # Finish
    logger.debug('Supervise loop finished: {} new alerts, {} sent alerts'.format(new_alerts, sent_alerts))
    return new_alerts, sent_alerts





import signal, errno
from contextlib import contextmanager
import fcntl

@contextmanager
def flock_timeout(filename, seconds): # TODO: if this works, move to lib/
    original_handler = signal.signal(signal.SIGALRM, lambda signum, frame: None)
    try:
        signal.alarm(seconds)
        with open(filename, 'w') as f:
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                yield
            except IOError as e:
                if e.errno != errno.EINTR:
                    raise e  # Some problem
                else:
                    yield # TODO: Lock timed out. Throw a special exception!
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, original_handler)


def supervise_loop(app):
    """ Supervisor main loop which performs background actions
    :param app: Application
    :type app: OvercApplication
    """
    db_engine = init_db_engine(app.app.config['DATABASE'])
    Session = init_db_session(db_engine)

    lockfile = os.path.join(tempfile.gettempdir(), 'overc.lock')

    while True:
        sleep(3)

        # Locking
        with flock_timeout(lockfile, seconds=2):
            # Supervise
            ssn = Session()
            try:
                # TODO: receive notifications from the API for immediate supervision
                supervise_once(app, ssn)
            except Exception:
                logger.exception('Supervise loop error')
            finally:
                Session.remove()
