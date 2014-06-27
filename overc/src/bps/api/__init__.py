from flask import Blueprint
from flask.globals import g, request
from werkzeug.exceptions import Forbidden

from overc.lib.db import models
from overc.lib.flask.json import jsonapi

bp = Blueprint('api', __name__, url_prefix='/api')



@bp.route('/service/status', methods=['GET', 'POST'])
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
    assert request.authorization is not None, 'Authorization not provided'
    assert isinstance(data, dict), 'Invalid data: should be JSON object'
    assert 'period' in data, 'Data: "period" key is missing'
    try: data['period'] = int(data['period'])
    except ValueError: raise AssertionError('Data: "period" should be an integer')

    # Input validation: services
    assert 'services' in data, 'Data: "services" key is missing'
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
    server_name, server_key = request.authorization.username, request.authorization.password
    server = ssn.query(models.Server).filter(models.Server.name == server_name).first()
    if server is not None:
        # Check key
        if server.key != server_key:
            raise Forbidden('Invalid server key')
    else:
        # Create
        server = models.Server(name=server_name, title=unicode(server_name), key=server_key)
        ssn.add(server)

    # Services
    for s in data['services']:
        # Identity service or create
        service = ssn.query(models.Service).filter(
            models.Service.server == server,
            models.Service.name == s['name']
        ).first()
        if service is None:
            service = models.Service(server=server, name=s['name'], title=unicode(s['name']))

        # Update
        service.period = data['period']
        ssn.add(service)

        # State
        state = models.ServiceState(service=service, state=s['state'], info=s['info'])
        ssn.add(state)

    # Save
    ssn.commit()

    return {'ok': 1}
