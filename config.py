import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')

    # Database configuration
    SQL_DRIVER = os.environ.get('DB_DRIVER')
    SQL_SERVER = os.environ.get('DB_SERVER')
    SQL_DB = os.environ.get('DB_DATABASE')
    SQL_UID = os.environ.get('DB_USER')
    SQL_PWD = os.environ.get('DB_PASSWORD')

    # Build database connection string
    if SQL_UID and SQL_PWD:
        DB_CONNECTION_STRING = (
            f"DRIVER={SQL_DRIVER};"
            f"SERVER={SQL_SERVER};"
            f"DATABASE={SQL_DB};"
            f"UID={SQL_UID};"
            f"PWD={SQL_PWD}"
        )
    else:
        DB_CONNECTION_STRING = (
            f"DRIVER={SQL_DRIVER};"
            f"SERVER={SQL_SERVER};"
            f"DATABASE={SQL_DB};"
            f"Trusted_Connection=yes;"
        )
