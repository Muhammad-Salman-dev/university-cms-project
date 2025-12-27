from flask import render_template, session, redirect, url_for, flash
from app.blueprints.faculty import faculty_bp
from app.database import get_db

@faculty_bp.route('/dashboard')
def dashboard():
    # 1. Security Check
    if 'user_id' not in session or session.get('role') != 'Faculty':
        return redirect(url_for('auth.login'))

    teacher_id = session['user_id']

    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("""
            SELECT CourseID, CourseCode, CourseName, Credits, RoomNumber
            FROM Courses
            WHERE FacultyID = ?
        """, (teacher_id,))

        courses = cursor.fetchall()
    except Exception as e:
        print(f"❌ Database Error: {e}")
        flash("Error fetching courses. Please check database columns.", "danger")
        courses = []

    return render_template('faculty/dashboard.html', courses=courses)