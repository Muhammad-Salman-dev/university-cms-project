from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from werkzeug.security import generate_password_hash
from app.database import get_db
import sqlite3

admin_bp = Blueprint('admin', __name__)

# ---------------------------------------------------
# 1. ADMIN DASHBOARD
# ---------------------------------------------------
@admin_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session.get('role') != 'Admin':
        return redirect(url_for('auth.login'))

    db = get_db()
    cursor = db.cursor()

    try:
        cursor.execute("SELECT COUNT(*) FROM Students")
        s_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM Faculty")
        f_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM Courses")
        c_count = cursor.fetchone()[0]

        stats_data = {
            'students': s_count,
            'faculty': f_count,
            'courses': c_count
        }
    except Exception as e:
        print(f"Dashboard Error: {e}")
        stats_data = {'students': 0, 'faculty': 0, 'courses': 0}

    return render_template('admin/dashboard.html', stats=stats_data)


# ---------------------------------------------------
# 2. COURSE MANAGEMENT
# ---------------------------------------------------
@admin_bp.route('/courses')
def list_courses():
    if 'user_id' not in session or session.get('role') != 'Admin':
        return redirect(url_for('auth.login'))

    db = get_db()
    cursor = db.cursor()

    try:
        cursor.execute("""
            SELECT
                c.CourseID,
                c.CourseCode,
                c.CourseName,
                f.Name,
                c.Credits,
                c.Room,
                c.Status
            FROM Courses c
            LEFT JOIN Faculty f ON c.FacultyID = f.FacultyID
        """)
        courses = cursor.fetchall()
    except Exception as e:
        print(f"List Courses Error: {e}")
        courses = []

    return render_template('admin/courses/list.html', courses=courses)


@admin_bp.route('/add_course', methods=['GET', 'POST'])
def add_course():
    if 'user_id' not in session or session.get('role') != 'Admin':
        return redirect(url_for('auth.login'))

    db = get_db()
    cursor = db.cursor()

    if request.method == 'POST':
        try:
            course_code = request.form['course_code']
            course_name = request.form['course_name']
            credits = request.form['credits']
            room = request.form['room']
            faculty_id = request.form['faculty_id']
            description = request.form.get('description', '')

            cursor.execute("""
                INSERT INTO Courses (CourseCode, CourseName, Description, FacultyID, Credits, Room)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (course_code, course_name, description, faculty_id, credits, room))

            db.commit()
            flash('Course Added Successfully!', 'success')
            return redirect(url_for('admin.list_courses'))

        except Exception as e:
            db.rollback()
            flash(f"Error: {e}", 'danger')

    cursor.execute("SELECT FacultyID, Name FROM Faculty")
    faculty_members = cursor.fetchall()

    return render_template('admin/courses/add.html', faculty_members=faculty_members)


# ---------------------------------------------------
# 3. FACULTY MANAGEMENT
# ---------------------------------------------------
@admin_bp.route('/faculty')
def list_faculty():
    if 'user_id' not in session or session.get('role') != 'Admin':
        return redirect(url_for('auth.login'))

    db = get_db()
    cursor = db.cursor()

    try:
        cursor.execute("""
            SELECT FacultyID, Name, Email, Department, Designation
            FROM Faculty
            ORDER BY FacultyID DESC
        """)
        faculty = cursor.fetchall()
    except Exception as e:
        print(f"List Faculty Error: {e}")
        faculty = []

    return render_template('admin/faculty/list.html', faculty=faculty)


@admin_bp.route('/faculty/add', methods=['GET', 'POST'])
def add_faculty():
    if 'user_id' not in session or session.get('role') != 'Admin':
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        department = request.form.get('department', '')
        designation = request.form.get('designation', '')

        hashed_password = generate_password_hash(password)

        db = get_db()
        cursor = db.cursor()

        try:
            cursor.execute("SELECT user_id FROM Users WHERE email = ?", (email,))
            if cursor.fetchone():
                flash('Error: Email already exists in system!', 'warning')
            else:
                cursor.execute("""
                    INSERT INTO Users (name, email, password, role)
                    VALUES (?, ?, ?, 'Faculty')
                """, (name, email, hashed_password))

                cursor.execute("""
                    INSERT INTO Faculty (Name, Email, Password, Department, Designation)
                    VALUES (?, ?, ?, ?, ?)
                """, (name, email, password, department, designation))

                db.commit()
                flash('Faculty Added Successfully!', 'success')
                return redirect(url_for('admin.list_faculty'))

        except Exception as e:
            db.rollback()
            flash(f'Error adding faculty: {str(e)}', 'danger')

    return render_template('admin/faculty/add.html')


# ---------------------------------------------------
# 4. STUDENT MANAGEMENT
# ---------------------------------------------------
@admin_bp.route('/students', methods=['GET'])
def list_students():
    if 'user_id' not in session or session.get('role') != 'Admin':
        return redirect(url_for('auth.login'))

    db = get_db()
    cursor = db.cursor()

    try:
        cursor.execute("""
            SELECT s.StudentID, s.Name, s.Email, s.Department, c.CourseName
            FROM Students s
            LEFT JOIN Enrollments e ON s.StudentID = e.StudentID
            LEFT JOIN Courses c ON e.CourseID = c.CourseID
            ORDER BY s.StudentID DESC
        """)
        raw_data = cursor.fetchall()

        students_map = {}

        for row in raw_data:
            s_id = row[0]

            if s_id not in students_map:
                students_map[s_id] = {
                    'id': row[0],
                    'name': row[1],
                    'email': row[2],
                    'department': row[3],
                    'courses': []
                }

            if row[4]:
                students_map[s_id]['courses'].append(row[4])

        students = list(students_map.values())

    except Exception as e:
        print(f"List Students Error: {e}")
        flash(f"Error fetching students: {e}", "danger")
        students = []

    return render_template('admin/students/list.html', students=students)


@admin_bp.route('/students/add', methods=['GET', 'POST'])
def add_student():
    if 'user_id' not in session or session.get('role') != 'Admin':
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        department = request.form.get('department', '')

        hashed_password = generate_password_hash(password)

        db = get_db()
        cursor = db.cursor()

        try:
            cursor.execute("SELECT user_id FROM Users WHERE email = ?", (email,))
            if cursor.fetchone():
                flash('Error: Email already exists in system!', 'warning')
            else:
                cursor.execute("""
                    INSERT INTO Users (name, email, password, role)
                    VALUES (?, ?, ?, 'Student')
                """, (name, email, hashed_password))

                cursor.execute("""
                    INSERT INTO Students (Name, Email, Password, Department)
                    VALUES (?, ?, ?, ?)
                """, (name, email, password, department))

                db.commit()
                flash('Student Added Successfully!', 'success')
                return redirect(url_for('admin.list_students'))

        except Exception as e:
            db.rollback()
            flash(f'Error adding student: {str(e)}', 'danger')

    return render_template('admin/students/add.html')
