import os
import logging
from datetime import datetime, timedelta
from time import sleep
from sqlalchemy.orm.session import sessionmaker

from overc.lib.db import models
from overc.lib import alerts

logger = logging.getLogger(__name__)

# TODO: these routines should obtain an exclusive lock so multiple supervise processes does not issue alerts multiple times


def _check_service_states(db_engine):
    """ Test all service states, raise alerts if necessary
    :param db_engine: Database engine
    :type db_engine: sqlalchemy.engine.Engine
    :returns: The number of new alerts reported
    :rtype: int
    """
    ssn = sessionmaker(bind=db_engine)

    # Fetch all states that are not yet checked
    service_states = ssn.query(models.ServiceState)\
        .filter(models.ServiceState.checked == False)\
        .order_by(models.ServiceState.id.asc())\
        .all()

    # Check them one by one
    new_alerts = 0
    for s in service_states:
        alert = None

        # Report state changes
        if s.state != s.prev.state:
            ssn.add(models.Alert(
                server_id=s.service.server_id,
                service_id=s.service_id,
                channel='service:state',
                event='changed',
                message=u'State changed: "{}" -> "{}"'.format(s.state, s.prev.state)
            ))
            new_alerts += 1

            # In addition, report "UNK" states!
            if s.state == 'UNK':
                ssn.add(models.Alert(
                    server_id=s.service.server_id,
                    service_id=s.service_id,
                    channel='service:state',
                    event='unk',
                    message=u'Service state unknown!'
                ))
                new_alerts += 1

        # Save
        s.checked = True
        ssn.add(s)

    # Finish
    ssn.commit()
    return new_alerts


def _check_service_timeouts(db_engine):
    """ Test all services for timeouts
    :param db_engine: Database engine
    :type db_engine: sqlalchemy.engine.Engine
    :returns: The number of new alerts reported
    :rtype: int
    """
    ssn = sessionmaker(bind=db_engine)

    # Fetch all services which have enough data
    services = ssn.query(models.Service)\
        .filter(
            models.Service.period is not None,
            models.Service.state is not None
        ).all()

    # Detect timeouts
    new_alerts = 0
    for s in services:
        timed_out, seen_timeago = s.check_timed_out()
        if timed_out:
            ssn.add(models.Alert(
                server_id=s.service.server_id,
                service_id=s.service_id,
                channel='service',
                event='timeout',
                message=u'Service timed out: last seen {} ago'.format(seen_timeago)
            ))
            new_alerts += 1

    # Finish
    ssn.commit()
    return new_alerts


def _send_pending_alerts(db_engine, alertd_path, alerts_config):
    """ Send pending alerts
    :param app: Overc Application
    :type app: OvercApplication
    :returns: The number of alerts sent
    :rtype: int
    """
    ssn = sessionmaker(bind=db_engine)

    # Fetch all alerts which were not reported
    pending_alerts = ssn.query(models.Alert)\
        .filter(models.Alert.reported == False)\
        .all()

    # Report them one by one
    for a in pending_alerts:
        # Potential exceptions are handled & logged down there
        alerts.send_alert_to_subscribers(alertd_path, alerts_config, unicode(a))
        ssn.add(a)

    # Finish
    ssn.commit()
    return len(pending_alerts)


def supervise_once(app):
    """ Perform all background actions once:

    * Check service states
    * Check for service timeouts
    * Send alerts

    :param app: Application
    :type app: OvercApplication
    """
    alertd_path = os.path.join(app.app.instance_path, 'alert.d')
    alerts_config = app.app.config['ALERTS']

    _check_service_states(app.db_engine)
    _check_service_timeouts(app.db_engine)
    _send_pending_alerts(app.db_engine, alertd_path, alerts_config)


def supervise_loop(app):
    """ Supervisor main loop which performs background actions
    :param app: Application
    :type app: OvercApplication
    """
    while True:
        try:
            supervise_once(app)
            sleep(5)
        except Exception as e:
            logger.exception('Supervise loop error')
            # proceed: this loop is important and should never halt
