import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.environ["DB_HOST"],
    "port": int(os.environ["DB_PORT"]),
    "service_name": os.environ["DB_SERVICE_NAME"],
    "user": os.environ["DB_USER"],
    "password": os.environ["DB_PASSWORD"],
}
