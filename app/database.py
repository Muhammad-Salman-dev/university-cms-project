import pyodbc
from flask import current_app, g

def get_db():
    """
    Establishes a connection to the database if one does not already exist
    in the current application context.
    """
    if 'db' not in g:
        try:
            # Retrieve connection string from Flask configuration
            conn_str = current_app.config['DB_CONNECTION_STRING']
            g.db = pyodbc.connect(conn_str)
        except Exception as e:
            print(f"❌ Database Connection Error: {e}")
            return None
    return g.db

def close_db(e=None):
    """
    Closes the database connection when the request ends.
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_app(app):
    """
    Registers the close_db function to run automatically
    when the application context is torn down.
    """
    app.teardown_appcontext(close_db)