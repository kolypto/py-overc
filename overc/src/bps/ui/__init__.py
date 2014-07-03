from datetime import datetime, timedelta
from logging import getLogger
from collections import defaultdict

from sqlalchemy.sql import func
from flask import Blueprint
from flask.templating import render_template
from flask.globals import g, request

from overc.lib.db import models
from overc.lib.flask.json import jsonapi

bp = Blueprint('ui', __name__, url_prefix='/', template_folder='templates',
               static_folder='static', static_url_path='static/ui'
               )
logger = getLogger(__name__)


#region UI

@bp.route('/', methods=['GET'])
def index():
    """ Index page """
    return render_template('pages/index.htm')

#endregion

#region API

@bp.route('/api/status/server')
@bp.route('/api/status/server/<server_id>')
@jsonapi
def api_status_server(server_id=None):
    """ Get all available information """
    ssn = g.db

    # Filter servers
    servers = ssn.query(models.Server)
    if server_id:
        servers = servers.filter(models.Server.id == server_id)
    servers = servers.all()

    # Count alerts for 24h
    alert_counts = ssn.query(
        models.Alert.server_id,
        models.Alert.service_id,
        func.count(models.Alert)
    ) \
        .filter(
            models.Alert.ctime >= (datetime.utcnow() - timedelta(hours=24)),
            models.Alert.server_id == server_id if server_id else True
        ) \
        .group_by(models.Alert.server_id, models.Alert.service_id) \
        .all()
    server_alerts = defaultdict(lambda: 0)
    service_alerts = defaultdict(lambda: 0)
    total_alerts = 0
    for (server_id, service_id, n) in alert_counts:
        total_alerts += n
        if service_id:
            service_alerts[service_id] += n
        elif server_id:
            server_alerts[server_id] += n

    # Test whether there are any service states not checked, which probably means the supervisor thread is no running
    last_checked = ssn.query(func.min(models.ServiceState.rtime)) \
        .filter(
            models.ServiceState.checked == False,
        ) \
        .scalar()
    supervisor_lag = (datetime.utcnow() - last_checked).total_seconds() if last_checked else 0.0

    #     Format
    return {
        'n_alerts': total_alerts,  # alerts today (for all selected servers)
        'supervisor_lag': supervisor_lag,  # Seconds ago the supervisor process last checked something
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


@bp.route('/api/status/alerts/server')
@bp.route('/api/status/alerts/server/<server_id>')
@bp.route('/api/status/alerts/service/<service_id>')
@jsonapi
def api_status_alerts(server_id=None, service_id=None):
    """ Alerts for 24h """
    ssn = g.db

    dtime = timedelta(hours=int(request.args.get('hours', default=24)))

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
                'message': alert.message
            }
            for alert in alerts
        ]
    }

#endregion
