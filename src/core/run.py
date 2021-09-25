from os import path
import sys
from flask_sse import sse

sys.path.append(path.abspath('../taranis-ng-common'))

from app import create_app

app = create_app()
app.register_blueprint(sse, url_prefix='/sse')
