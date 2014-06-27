from functools import wraps
from flask import request, jsonify, make_response
from werkzeug.exceptions import HTTPException

def json_response(res, code=200):
    """ Make up a Response object from data
    :param res: Response data
    :type res: *
    :param code: Response code
    :type code: int
    :rtype: flask.Response
    """
    response = make_response(jsonify(res), code)
    return response

def jsonapi(f):
    """ Declare a view as JSON API method """
    @wraps(f)
    def wrapper(*args, **kwargs):
        # Invoke
        try:
            res = f(*args, **kwargs)
        except HTTPException as e:
            return json_response({'error': e.description}, e.code)
        except AssertionError as e:
            return json_response({ 'error': e.message }, 400)

        # Tuple response
        c = 200
        if isinstance(res, tuple):
            result, c = res

        # Finish
        return json_response(res, c)
    return wrapper
