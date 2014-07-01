import json, urlparse, urllib2

class Overclient(object):
    """ OverC API client """

    def __init__(self, url, server_name, server_key):
        """ Initialize the client
        :param url: OverC server URL
        :type url: str
        :param server_name: Server identification: name
        :type server_name: str
        :param server_key: Server identification: key
        :type server_key: str
        """
        self._url = url
        self._server_id = {'name': server_name, 'key': server_key}

    def _jsonpost(self, path, data=None):
        """ Execute an API method
        :param path: Method URI
        :type path: str
        :param data: Data to POST (optional)
        :type data: dict
        :return: Response
        :rtype: dict
        :exception urllib2.URLError: Connection errors
        """
        # Prepare
        url = urlparse.urljoin(self._url, path)
        req = urllib2.Request(url)
        if data:
            req.add_header('Content-Type', 'application/json')

        # Request
        response = urllib2.urlopen(req, json.dumps(data) if data else None)

        # Read
        res_str = response.read()
        res = json.loads(res_str)
        return res

    def ping(self):
        """ Test connection
        :exception urllib2.URLError: Connection errors
        """
        return self._jsonpost('/api/ping', {
            'server': self._server_id
        })

    def set_service_status(self, period, services):
        """ Send services' status
        :param period: Promised reporting period
        :type period: int
        :param services: List of services to report
        :type services: list
        :exception urllib2.URLError: Connection errors
        """
        return self._jsonpost('/api/set/service/status', {
            'server': self._server_id,
            'period': period,
            'services': services
        })

    def set_alerts(self, alerts):
        """ Send alerts
        :param alerts: Alerts to report
        :type alerts: list
        :exception urllib2.URLError: Connection errors
        """
        return self._jsonpost('/api/set/alerts', {
            'server': self._server_id,
            'alerts': alerts
        })
