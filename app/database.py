import pyodbc
from flask import current_app, g


def get_db():
    """
    Returns a database connection for the current request.
    Creates a new connection if one does not already exist.
    """
    if 'db' not in g:
        conn_str = current_app.config.get('DB_CONNECTION_STRING')
        if not conn_str:
            raise RuntimeError("Database connection string not configured")

        g.db = pyodbc.connect(conn_str)

    return g.db


def close_db(e=None):
    """
    Closes the database connection at the end of the request.
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_app(app):
    """
    Registers database teardown handler with the Flask app.
    """
    app.teardown_appcontext(close_db)
