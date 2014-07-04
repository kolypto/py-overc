from datetime import datetime
from logging import getLogger

from flask import Blueprint
from flask.globals import g, request
from werkzeug.exceptions import Forbidden

from overc.lib.db import models
from overc.lib.flask.json import jsonapi

bp = Blueprint('api', __name__, url_prefix='/api')
logger = getLogger(__name__)


def _identify_server(ssn, server_spec):
    """ Identity the server, create if missing
    :param ssn: Database session
    :type ssn: sqlalchemy.orm.session.Session
    :param server_spec: Server identification dictionary: {name: String, key: String}
    :type server_spec: dict
    :rtype: models.Server
    :exception AssertionError: Validation error
    :exception Forbidden: Invalid server key
    """

    # Input validation: server
    assert isinstance(server_spec, dict), 'Data: "server" should be a dict'
    assert 'name' in server_spec and isinstance(server_spec['name'], basestring), 'Data: "server.name" should be a string'
    assert 'key'  in server_spec and isinstance(server_spec['key'],  basestring), 'Data: "server.key" should be a string'

    # Identify server or create
    server = ssn.query(models.Server).filter(models.Server.name == server_spec['name']).first()
    if server is not None:
        # Check key
        key_ok = server.key != server_spec['key']
        if key_ok:
            logger.warning(u'Invalid server key supplied: name="{name}", key="{key}"'.format(**server_spec))
            raise Forbidden('Invalid server key')
    else:
        # Create
        server = models.Server(
            name=server_spec['name'],
            title=unicode(server_spec['name']),
            key=server_spec['key']
        )
        logger.info(u'Created new Server(name="{name}")'.format(**server_spec))

    # Update IP
    server.ip = request.remote_addr

    # Finish
    logger.debug(u'Identified server by name="{name}", id={id}'.format(id=server.id or '<new server>', **server_spec))
    return server


def _identify_service(ssn, server, service_name):
    """ Identify the service, create if missing
    :param ssn: Database session
    :type ssn: sqlalchemy.orm.session.Session
    :param server: Server to lookup the service at
    :type server: models.Server
    :param service_name: Service name on the server
    :type service_name: str
    :rtype: models.Service
    """
    service = ssn.query(models.Service).filter(
        models.Service.server == server,
        models.Service.name == service_name
    ).first()
    if service is None:
        service = models.Service(
            server=server,
            name=service_name,
            title=unicode(service_name)
        )
        logger.info(u'Created new Service(name="{name}", server="{server}")'.format(name=service.name, server=server.name))
    return service


@bp.route('/ping', methods=['POST'])
@jsonapi
def ping():
    """ Test connection and server credentials

        Status codes:
            400 invalid input
            403 invalid server key
    """
    ssn = g.db

    # Input validation
    data = request.get_json()
    assert isinstance(data, dict), 'Invalid data: should be JSON object'
    assert 'server' in data, 'Data: "server" key is missing'

    # Identify server (will raise exception if not fine)
    server = _identify_server(ssn, data['server'])
    ssn.add(server)
    ssn.commit()

    return {'pong': 1}


@bp.route('/set/service/status', methods=['POST'])
@jsonapi
def set_service_status():
    """ Receive single service status

        Status codes:
            400 invalid input
            403 invalid server key
    """
    ssn = g.db

    # Input validation
    data = request.get_json()
    assert isinstance(data, dict), 'Invalid data: should be JSON object'
    assert 'server' in data, 'Data: "server" key is missing'
    assert 'period' in data, 'Data: "period" key is missing'
    assert 'services' in data, 'Data: "services" key is missing'

    # Input validation: period
    try:
        data['period'] = int(data['period'])
    except ValueError:
        raise AssertionError('Data: "period" should be an integer')

    # Input validation: services
    assert isinstance(data['services'], list), 'Data: "services" should be a list'
    assert all(
        isinstance(s, dict) and
        'name' in s and isinstance(s['name'], basestring) and
        'state' in s and isinstance(s['state'], basestring) and
        ('info' not in s or isinstance(s['info'], basestring))
        for s in data['services']
    ), 'Data: "services" should be a list of objects with keys "name", "state", "info"?, "period"?'

    # Identify server
    server = _identify_server(ssn, data['server'])
    ssn.add(server)

    # Services
    services_cache = {}
    for s in data['services']:
        # Identify service
        try:
            service = services_cache[s['name']]
        except KeyError:
            service = _identify_service(ssn, server, s['name'])
            services_cache[service.name] = service
        ssn.add(service)

        # Update period
        try:
            service_period = int(s['period'])
        except (KeyError, ValueError):
            service_period = data['period']

        service.period = service_period

        # State
        if not models.state_t.is_valid(s['state']):
            s['info'] += u' (sent unsupported state: "{}")'.format(s['state'])
            s['state'] = 'UNK'
        state = models.ServiceState(
            service=service,
            rtime=datetime.utcnow(),
            state=s['state'],
            info=s['info']
        )
        ssn.add(state)
        logger.debug(u'Service {server}:`{name}` state update: {state}: {info}'.format(server=server.name, **s))

    # Save
    ssn.commit()

    return {'ok': 1}


@bp.route('/set/alerts', methods=['POST'])
@jsonapi
def set_alerts():
    """ Receive custom alerts

        Status codes:
            400 invalid input
            403 invalid server key
    """
    ssn = g.db

    # Input validation
    data = request.get_json()
    assert isinstance(data, dict), 'Invalid data: should be JSON object'
    assert 'server' in data, 'Data: "server" key is missing'
    assert 'alerts' in data, 'Data: "alerts" key is missing'

    # Input validation: alerts
    assert isinstance(data['alerts'], list), 'Data: "alerts" should be a list'
    assert all(
        isinstance(s, dict) and
        'message' in s and isinstance(s['message'], basestring) and
        ('service' not in s or isinstance(s['service'], basestring)) and
        set(s.keys()) <= {'title', 'message', 'service'}
        for s in data['alerts']
    ), 'Data: "alerts" should be a list of objects with keys "title", "message"?, "service"?'

    # Identify server
    server = _identify_server(ssn, data['server'])
    ssn.add(server)

    # Alerts
    services_cache = {}
    for a in data['alerts']:
        # Identify service (if any)
        service = None
        if 'service' in a:
            try:
                service = services_cache[a['service']]
            except KeyError:
                service = _identify_service(ssn, server, a['service'])
                services_cache[service.name] = service
                ssn.add(service)

        # Raise
        alert = models.Alert(
            server=server,
            service=service,
            ctime=datetime.utcnow(),
            channel='api',
            event='alert',
            message=unicode(a['message'])
        )
        ssn.add(alert)
        logger.debug(u'Alert reported for {server}:`{service}`: {message}'.format(server=server.name, service=service.name if service else '-', message=a['message']))

    # Save
    ssn.commit()

    return {'ok': 1}
