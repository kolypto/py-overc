from flask import Blueprint
from flask.globals import g, request
from werkzeug.exceptions import Forbidden

from overc.lib.db import models
from overc.lib.flask.json import jsonapi

bp = Blueprint('api', __name__, url_prefix='/api')


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
        if server.key != server_spec['key']:
            raise Forbidden('Invalid server key')
    else:
        # Create
        server = models.Server(name=server_spec['name'], title=unicode(server_spec['name']), key=server_spec['key'])

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
        service = models.Service(server=server, name=service_name, title=unicode(service_name))
    return service


@bp.route('/set/service/status', methods=['POST'])
@jsonapi
def service_status():
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
        ('info' not in s or isinstance(s['info'], basestring)) and
        set(s.keys()) <= {'name', 'state', 'info'}
        for s in data['services']
    ), 'Data: "services" should be a list of objects with keys "name", "state", "info"'

    # Identify server or create
    server = _identify_server(ssn, data['server'])
    ssn.add(server)

    # Services
    for s in data['services']:
        # Identify service
        service = _identify_service(ssn, server, s['name'])

        # Update
        service.period = data['period']
        ssn.add(service)

        # State
        state = models.ServiceState(service=service, state=s['state'], info=s['info'])
        ssn.add(state)

    # Save
    ssn.commit()

    return {'ok': 1}
