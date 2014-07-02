from logging import getLogger

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

@bp.route('/api/refresh', defaults={'server_id': None})
@bp.route('/api/refresh/<server_id>')
@jsonapi
def api_refresh(server_id=None):
    """ Get all available information """
    ssn = g.db

    # Filter servers
    servers = ssn.query(models.Server)
    if server_id:
        servers = servers.filter(models.Server.id == server_id)
    servers = servers.all()

    # Prepare response
    return {
        'servers': sorted([
            {
                'id': server.id,
                'name': server.name,
                'title': server.title,
                'ip': server.ip,
                'services': sorted([
                    {
                        'id': service.id,
                        'period': service.period,
                        'timed_out': service.timed_out,
                        'name': service.name,
                        'title': service.title,
                        'state': {
                            'rtime': service.state.rtime.isoformat(sep=' '),
                            'state': service.state.state,
                            'info': service.state.info,
                        } if service.state else {
                            'rtime': None,
                            'state': 'UNK',
                            'info': ''
                        }
                    } for service in server.services
                ], cmp, lambda s: s['state']['rtime'])
            } for server in servers
        ], cmp, lambda s: s['name'])
    }

#endregion
