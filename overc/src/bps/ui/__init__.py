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


@bp.route('/', methods=['GET'])
def index():
    """ Index page """
    return render_template('pages/index.htm')
