from flask import render_template, session, redirect, url_for, flash
from app.blueprints.faculty import faculty_bp
from app.database import get_db

@faculty_bp.route('/dashboard')
def dashboard():
    # 1. Check karo user logged in hai ya nahi
    # (Testing ke liye: Agar login nahi hai, to hum manually ID 1 set kar dete hain)
    if 'user_id' not in session:
        # TODO: Baad mein ye line hata denge jab Login page ban jayega
        session['user_id'] = 1
        session['role'] = 'faculty'
        flash('⚠️ Debug Mode: Auto-logged in as Dr. Ali (ID: 1)', 'info')

    # 2. Database se courses nikalo
    faculty_id = session['user_id']
    db = get_db()
    cursor = db.cursor()

    # Sirf us teacher ke courses jo logged in hai
    query = "SELECT * FROM Courses WHERE FacultyID = ?"
    cursor.execute(query, (faculty_id,))

    # Data fetch karo
    # Note: pyodbc mein dictionary ki tarah data nahi milta, isliye humein index use karna padega
    # CourseName column index 1 par hoga, CourseCode index 2 par (SQL Table ke hisab se)
    courses = cursor.fetchall()

    return render_template('faculty/dashboard.html', courses=courses)