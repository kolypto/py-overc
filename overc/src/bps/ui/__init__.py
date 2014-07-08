from datetime import datetime, timedelta
from logging import getLogger
from collections import defaultdict
from sqlalchemy.orm import contains_eager, joinedload

from sqlalchemy.sql import func
from flask import Blueprint
from flask.templating import render_template
from flask.globals import g, request

from overc import __version__
from overc.lib.db import models
from overc.lib.flask.json import jsonapi

bp = Blueprint('ui', __name__, url_prefix='/ui', template_folder='templates',
               static_folder='static', static_url_path='/static'
               )
logger = getLogger(__name__)


#region UI

@bp.route('/', methods=['GET'])
def index():
    """ Index page """
    return render_template('pages/index.htm', overc_version=__version__)

#endregion

#region API

@bp.route('/api/status/')
@bp.route('/api/status/server/<int:server_id>')
@bp.route('/api/status/service/<int:service_id>')
@jsonapi
def api_status(server_id=None, service_id=None):
    """ Get all available information """
    ssn = g.db

    # Filter servers
    servers = ssn.query(models.Server) \
        .join(models.Server.services) \
        .options(contains_eager(models.Server.services)) \
        .filter(
            models.Server.id == server_id   if server_id  else True,
            models.Service.id == service_id if service_id else True
        ) \
        .all()

    # Count alerts for 24h
    alert_counts = ssn.query(
        models.Alert.server_id,
        models.Alert.service_id,
        func.count(models.Alert)
    ) \
        .filter(
            models.Alert.ctime >= (datetime.utcnow() - timedelta(hours=24)),
            models.Alert.server_id == server_id if server_id else True,
            models.Alert.service_id == service_id if service_id else True
        ) \
        .group_by(models.Alert.server_id, models.Alert.service_id) \
        .all()

    server_alerts = defaultdict(lambda: 0)
    service_alerts = defaultdict(lambda: 0)
    total_alerts = 0
    for (srv_id, svc_id, n) in alert_counts:
        total_alerts += n
        if svc_id:
            service_alerts[svc_id] += n
        elif srv_id:
            server_alerts[srv_id] += n

    # Test whether there are any service states not checked, which probably means the supervisor thread is no running
    last_checked = ssn.query(func.min(models.ServiceState.rtime)) \
        .filter(
            models.ServiceState.checked == False,
        ) \
        .scalar()
    supervisor_lag = (datetime.utcnow() - last_checked).total_seconds() if last_checked else 0.0

    # Last state id
    last_state_id = ssn.query(func.max(models.ServiceState.id)) \
        .filter(models.ServiceState.service_id == service_id if service_id else True) \
        .scalar()

    # Format
    return {
        # Statistics
        'stats': {
            'n_alerts': total_alerts,  # alerts today (for all selected servers)
            'last_state_id': last_state_id,  # Last ServiceState.id
            'supervisor_lag': supervisor_lag,  # Seconds ago the supervisor process last checked something
        },
        # Servers & Services
        'servers': sorted([
            {
                'id': server.id,
                'name': server.name,
                'title': server.title,
                'ip': server.ip,
                'n_alerts': server_alerts[server.id],  # alerts today, for this server
                'services': sorted([
                    {
                        'id': service.id,
                        'period': service.period,
                        'name': service.name,
                        'title': service.title,
                        'n_alerts': service_alerts[service.id],  # alerts today, for this service
                        'state': {
                            'rtime': service.state.rtime.isoformat(sep=' '),
                            'timed_out': service.timed_out,
                            'seen_ago': str(datetime.utcnow() - service.state.rtime).split('.')[0],
                            'state': service.state.state,
                            'info': service.state.info,
                        } if service.state else None
                    } for service in server.services
                ], cmp, lambda s: s['name'])
            } for server in servers
        ], cmp, lambda s: s['name'])
    }


@bp.route('/api/status/service/<int:service_id>/states')
@jsonapi
def api_status_service_states(service_id):
    """ Service states for 24h """
    ssn = g.db

    dtime = timedelta(hours=float(request.args.get('hours', default=24)))

    # Load states & alerts
    states = ssn.query(models.ServiceState) \
        .options(joinedload(models.ServiceState.alerts)) \
        .filter(
            models.ServiceState.rtime >= (datetime.utcnow() - dtime),
            models.ServiceState.service_id == service_id
        ) \
        .order_by(models.ServiceState.id.desc()) \
        .all()

    # Collapse
    groups = request.args.get('groups', default=False)
    if groups:
        # Go through states and detect sequences of states with no changes: these are replaced with Groups
        # A "change": state change or alerts

        #: List of groups to expand: [ (id1, id2), ... ]
        expand = request.args.getlist('expand', lambda v: map(int, v.split('-'))) if request.args.has_key('expand') else ()

        # Detect groups
        prev_state = None
        cur_group = None
        groups = []
        for i, s in enumerate(states):
            # Init group
            if cur_group is None:
                cur_group = [i, None]

            # Detect changes
            has_changes = s.state != prev_state
            has_changes |= len(s.alerts)
            if has_changes:
                # Put group
                groups.append(cur_group)
                # Unset group
                cur_group = None
            else:
                # Store id
                cur_group[1] = i

            # Memo
            prev_state = s.state
        groups.append(cur_group)

        # Filter groups
        groups = [ (grp[0], grp[1]-1)  # Always include both border items
                  for grp in groups if
                  grp is not None and  # Ignore: empty groups
                  grp[1] is not None and  # Ignore: incomplete groups
                  (grp[1] - grp[0]) > 1 # Ignore: small groups of 0,1 items
        ]

        # Replace groups
        for grp in reversed(groups):
            ss = (states[grp[1]], states[grp[0]])
            ss_ids = (ss[0].id, ss[1].id)

            # Skip expanded groups
            if any(ss_ids[0] <= e[0] <= ss_ids[1] or ss_ids[0] <= e[1] <= ss_ids[1] for e in expand):
                continue

            # Replace with group
            states[grp[0] : grp[1]+1] = [ {
                                              'id': ss[0].id,  # Just for Angular
                                              'state': ss[0].state,
                                              'group': '-'.join(map(str, ss_ids)),
                                              'group_count': grp[1] - grp[0] + 1
                                          } ]
    # Format
    return {
        'states': [
            {
                'id': state.id,
                'rtime': state.rtime.isoformat(sep=' '),
                'state': state.state,
                'info': state.info,

                'alerts': [ {
                        'id': alert.id,
                        'channel': alert.channel,
                        'event': alert.event,
                        'message': alert.message,
                        'severity': models.state_t.states[alert.severity]
                    } for alert in state.alerts ],
                'service': unicode(state.service),
                'service_id': state.service_id,
            } if isinstance(state, models.ServiceState) else state  # Groups :)
            for state in states
        ]
    }


@bp.route('/api/status/alerts/')
@bp.route('/api/status/alerts/server/<int:server_id>')
@bp.route('/api/status/alerts/service/<int:service_id>')
@jsonapi
def api_status_alerts(server_id=None, service_id=None):
    """ Alerts for 24h """
    ssn = g.db

    dtime = timedelta(hours=float(request.args.get('hours', default=24)))

    # Load alerts
    alerts = ssn.query(models.Alert) \
        .filter(
            models.Alert.ctime >= (datetime.utcnow() - dtime),
            models.Alert.server_id == server_id if server_id else True,
            models.Alert.service_id == service_id if service_id else True
        ) \
        .order_by(models.Alert.id.desc()) \
        .all()

    # Format
    return {
        'alerts': [
            {
                'id': alert.id,
                'server': unicode(alert.server) if alert.server else None,
                'server_id': alert.server_id,
                'service': unicode(alert.service) if alert.service else None,
                'service_id': alert.service_id,

                'ctime': alert.ctime.isoformat(sep=' '),
                'channel': alert.channel,
                'event': alert.event,
                'message': alert.message,
                'state_info': alert.service_state.info if alert.service_state else None
            }
            for alert in alerts
        ]
    }

#region Items

@bp.route('/api/item/server/<int:server_id>', methods=['DELETE'])
@jsonapi
def api_server_delete(server_id):
    """ Server CRUD: Delete """
    ssn = g.db

    server = ssn.query(models.Server).get(server_id)
    ssn.delete(server)
    ssn.commit()

    return {'ok': 1}


@bp.route('/api/item/service/<int:service_id>', methods=['DELETE'])
@jsonapi
def api_service_delete(service_id):
    """ Service CRUD: Delete """
    ssn = g.db

    service = ssn.query(models.Service).get(service_id)
    ssn.delete(service)
    ssn.commit()

    return {'ok': 1}

#endregion

# TODO: API to rename servers, services
# TODO: API to test alert plugins

#endregion
