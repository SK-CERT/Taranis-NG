from os import path
import sys
import os

sys.path.append(path.abspath('../taranis-ng-common'))

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(port=os.getenv('FLASK_RUN_PORT'))
