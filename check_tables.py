from app import create_app
from app.database import get_db

app = create_app()

with app.app_context():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE = 'BASE TABLE'
    """)

    tables = cursor.fetchall()

    if not tables:
        raise RuntimeError("No tables found in the database")

    for table in tables:
        pass  # Tables successfully retrieved
