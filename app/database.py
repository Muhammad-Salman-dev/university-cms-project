import pyodbc
from flask import current_app, g

def get_db():
    if 'db' not in g:
        try:
            # Config se connection string le raha hai
            conn_str = current_app.config['DB_CONNECTION_STRING']
            g.db = pyodbc.connect(conn_str)
        except Exception as e:
            print(f"❌ Database Connection Error: {e}")
            return None
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_app(app):
    # Jab request khatam ho, connection band kar do
    app.teardown_appcontext(close_db)