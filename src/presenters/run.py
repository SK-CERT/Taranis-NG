from app import create_app
import os
from dotenv import load_dotenv
from os import path
import sys

sys.path.append(path.abspath('../taranis-ng-common'))

load_dotenv()

app = create_app()

if __name__ == "__main__":
    app.run(port=os.getenv('FLASK_RUN_PORT'))
