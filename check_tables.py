from app import create_app
from app.database import get_db

app = create_app()

with app.app_context():
    conn = get_db()
    cursor = conn.cursor()

    # Check tables
    try:
        cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'")
        tables = cursor.fetchall()

        print("\n📊 TABLES FOUND:")
        print("-" * 20)
        if tables:
            for table in tables:
                print(f" ✅ {table[0]}")
        else:
            print(" ❌ Database khaali hai!")
        print("-" * 20)
    except Exception as e:
        print(f"Error: {e}")