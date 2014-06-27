from flask import Blueprint
from flask.globals import g, request
from werkzeug.exceptions import Forbidden

from overc.lib.db import models
from overc.lib.flask.json import jsonapi

bp = Blueprint('api', __name__, url_prefix='/api')



@bp.route('/service/status', methods=['POST'])
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

    # Input validation: server
    assert 'server' in data, 'Data: "server" key is missing'
    assert isinstance(data['server'], dict), 'Data: "server" should be a dict'
    assert 'name' in data['server'] and isinstance(data['server']['name'], basestring), 'Data: "server.name" should be a string'
    assert 'key' in data['server'] and isinstance(data['server']['key'], basestring), 'Data: "server.key" should be a string'

    # Input validation: services
    if 'period' in data or 'services' in data:
        # period
        assert 'period' in data, 'Data: "period" key is missing'
        try: data['period'] = int(data['period'])
        except ValueError: raise AssertionError('Data: "period" should be an integer')

        # services
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

    # Input validation: alerts
    if 'alerts' in data:
        assert isinstance(data['alerts'], list) and \
               all(isinstance(s, basestring) for s in data['alerts']), 'Data: "alerts" should be a list of strings'

    # Identify server or create
    server = ssn.query(models.Server).filter(models.Server.name == data['server']['name']).first()
    if server is not None:
        # Check key
        if server.key != data['server']['key']:
            raise Forbidden('Invalid server key')
    else:
        # Create
        server = models.Server(name=data['server']['name'], title=unicode(data['server']['name']), key=data['server']['key'])
        ssn.add(server)

    # Services
    if 'services' in data:
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

    # Alerts
    if 'alerts' in data: # TODO: move alerts support to `/api/alert` and unit-test it
        for a in data['alerts']:
            alert = models.Alerts(server=server, severity=3, channel='remote', event='remote', message=a)
            ssn.add(alert)

    # Save
    ssn.commit()

    return {'ok': 1}
