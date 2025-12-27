from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from werkzeug.security import generate_password_hash
from app.database import get_db
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import sqlite3

admin_bp = Blueprint('admin', __name__)

# --- 1. DASHBOARD ---
@admin_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session.get('role') != 'Admin':
        return redirect(url_for('auth.login'))

    db = get_db()
    cursor = db.cursor()

    try:
        # Counting from specific tables to ensure accuracy
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


# --- 2. COURSE MANAGEMENT ---

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
                c.Room
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

    # Fetch faculty list for dropdown
    cursor.execute("SELECT FacultyID, Name FROM Faculty")
    faculty_members = cursor.fetchall()

    return render_template('admin/courses/add.html', faculty_members=faculty_members)


# --- 3. FACULTY MANAGEMENT ---

@admin_bp.route('/faculty')
def list_faculty():
    if 'user_id' not in session or session.get('role') != 'Admin':
        return redirect(url_for('auth.login'))

    db = get_db()
    cursor = db.cursor()

    try:
        # Fetching directly from Faculty table
        cursor.execute("SELECT FacultyID, Name, Email, Department, Designation FROM Faculty ORDER BY FacultyID DESC")
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

        # Hash password for Users table security
        hashed_password = generate_password_hash(password)

        db = get_db()
        cursor = db.cursor()

        try:
            # Check if email exists in Users
            cursor.execute("SELECT user_id FROM Users WHERE email = ?", (email,))
            if cursor.fetchone():
                flash('Error: Email already exists in system!', 'warning')
            else:
                # 1. Insert into Users (For Login)
                cursor.execute("""
                    INSERT INTO Users (name, email, password, role)
                    VALUES (?, ?, ?, 'Faculty')
                """, (name, email, hashed_password))

                # 2. Insert into Faculty (For Data Management)
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


# --- 4. STUDENT MANAGEMENT ---

@admin_bp.route('/students', methods=['GET'])
def list_students():
    # 1. Purani Auth Logic (Same rahegi)
    if 'user_id' not in session or session.get('role') != 'Admin':
        return redirect(url_for('auth.login'))

    db = get_db()
    cursor = db.cursor()

    try:
        query = """
            SELECT s.StudentID, s.Name, s.Email, s.Department, c.CourseName
            FROM Students s
            LEFT JOIN Enrollments e ON s.StudentID = e.StudentID
            LEFT JOIN Courses c ON e.CourseID = c.CourseID
            ORDER BY s.StudentID DESC
        """
        cursor.execute(query)
        raw_data = cursor.fetchall()

        students_map = {}

        for row in raw_data:
            s_id = row[0]

    #If Student Added First Time
            if s_id not in students_map:
                students_map[s_id] = {
                    'id': row[0],        # HTML mein student.id
                    'name': row[1],      # HTML mein student.name
                    'email': row[2],     # HTML mein student.email
                    'department': row[3],# HTML mein student.department
                    'courses': []        # courses list
                }
            if row[4]:
                students_map[s_id]['courses'].append(row[4])

        students = list(students_map.values())

    except Exception as e:
        print(f"List Students Error: {e}")
        flash(f"Error fetching students: {e}", "danger")
        students = []

    # 4. Render Template
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

        # Hash password for Users table security
        hashed_password = generate_password_hash(password)

        db = get_db()
        cursor = db.cursor()

        try:
            # Check if email exists in Users
            cursor.execute("SELECT user_id FROM Users WHERE email = ?", (email,))
            if cursor.fetchone():
                flash('Error: Email already exists in system!', 'warning')
            else:
                # 1. Insert into Users (For Login)
                cursor.execute("""
                    INSERT INTO Users (name, email, password, role)
                    VALUES (?, ?, ?, 'Student')
                """, (name, email, hashed_password))

                # 2. Insert into Students (For Data Management)
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


# --- 5. MANAGE ENROLLMENTS ---
@admin_bp.route('/manage_enrollments', methods=['GET', 'POST'])
def manage_enrollments():
    if 'user_id' not in session or session.get('role') != 'Admin':
        return redirect(url_for('auth.login'))

    db = get_db()
    cursor = db.cursor()

    # --- POST Logic
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'enroll':
            student_id = request.form.get('student_id')
            course_id = request.form.get('course_id')

            try:
                cursor.execute("SELECT * FROM Enrollments WHERE StudentID=? AND CourseID=?", (student_id, course_id))
                if cursor.fetchone():
                    flash("Student is already enrolled!", "warning")
                else:
                    cursor.execute("INSERT INTO Enrollments (StudentID, CourseID) VALUES (?, ?)", (student_id, course_id))
                    db.commit()
                    flash("Student Enrolled Successfully!", "success")
            except Exception as e:
                flash(f"Error enrolling: {e}", "danger")

        elif action == 'drop':
            enrollment_id = request.form.get('enrollment_id')
            try:
                cursor.execute("DELETE FROM Enrollments WHERE EnrollmentID = ?", (enrollment_id,))
                db.commit()
                flash("Student Dropped Successfully!", "success")
            except Exception as e:
                flash(f"Error dropping: {e}", "danger")

            return redirect(url_for('admin.manage_enrollments'))

    # --- GET Logic ---
    try:
        # 1. Fetch Raw Data (Added s.StudentID to query for grouping)
        cursor.execute("""
            SELECT e.EnrollmentID, s.StudentID, s.Name, s.Email, c.CourseCode, c.CourseName
            FROM Enrollments e
            JOIN Students s ON e.StudentID = s.StudentID
            JOIN Courses c ON e.CourseID = c.CourseID
            ORDER BY s.StudentID DESC
        """)
        raw_data = cursor.fetchall()

        # 2. Data Grouping Logic (Python)
        enrollment_map = {}

        for row in raw_data:
            # Row index: 0=EnrollID, 1=StudID, 2=Name, 3=Email, 4=Code, 5=CourseName
            s_id = row[1]

            if s_id not in enrollment_map:
                enrollment_map[s_id] = {
                    'student_id': row[1],
                    'name': row[2],
                    'email': row[3],
                    'courses': []
                }

            # Course add in list
            enrollment_map[s_id]['courses'].append({
                'enrollment_id': row[0],
                'code': row[4],
                'name': row[5]
            })

        enrollments = list(enrollment_map.values())

        # Fetch All Students for Dropdown
        cursor.execute("SELECT StudentID, Name, Email FROM Students")
        all_students = cursor.fetchall()

        # Fetch All Courses for Dropdown
        cursor.execute("SELECT CourseID, CourseCode, CourseName FROM Courses")
        all_courses = cursor.fetchall()

    except Exception as e:
        print(f"Enrollment View Error: {e}")
        flash(f"Database Error: {e}", "danger")
        enrollments = []
        all_students = []
        all_courses = []

    return render_template('admin/students/manage.html',
                           enrollments=enrollments,
                           all_students=all_students,
                           all_courses=all_courses)
# # ---------------------------------------------------
# # DELETE COURSE ROUTE
# # ---------------------------------------------------
# @admin_bp.route('/course/delete/<int:id>')
# def delete_course(id):
#     if 'user_id' not in session or session.get('role') != 'admin':
#         return redirect(url_for('auth.login'))

#     conn = sqlite3.connect('university.db')
#     c = conn.cursor()
#     try:
#         c.execute("DELETE FROM courses WHERE id=?", (id,))
#         conn.commit()
#         flash('Course deleted successfully!', 'success')
#     except sqlite3.Error as e:
#         flash(f'Error deleting course: {e}', 'danger')
#     finally:
#         conn.close()

#     return redirect(url_for('admin.list_courses'))

# # ---------------------------------------------------
# # DELETE FACULTY ROUTE
# # ---------------------------------------------------


# @admin_bp.route('/faculty/delete/<int:id>')
# def delete_faculty(id):
#     # Security Check
#     if 'user_id' not in session or session.get('role') != 'Admin':
#         return redirect(url_for('auth.login'))

#     db = get_db()
#     cursor = db.cursor()

#     try:
#         cursor.execute("DELETE FROM Faculty WHERE FacultyID = ?", (id,))
#         db.commit()
#         flash('Faculty member deleted successfully!', 'success')
#     except Exception as e:
#         print(f"Delete Faculty Error: {e}")
#         flash('Error deleting faculty member.', 'danger')

#     return redirect(url_for('admin.list_faculty'))



# --- 6. ADMIN MESSAGING & NOTIFICATIONS (NEW) ---

@admin_bp.route('/messages')
def admin_messages():
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT
            M.Subject,      -- [0]
            M.Body,         -- [1]
            M.SentAt,       -- [2]
            U.name,         -- [3]
            U.role,         -- [4]
            M.MessageID,    -- [5]
            M.SenderID      -- [6]
        FROM Messages M
        JOIN Users U ON M.SenderID = U.user_id
        WHERE M.ReceiverID = 1
        ORDER BY M.SentAt DESC
    """)
    messages = cursor.fetchall()
    return render_template('admin/messages.html', messages=messages)

@admin_bp.route('/send_broadcast', methods=['POST'])
def send_broadcast():
    if 'user_id' not in session or session.get('role') != 'Admin':
        return redirect(url_for('auth.login'))

    target = request.form.get('target') # 'Student' or 'Faculty' or 'All'
    msg_text = request.form.get('message')

    db = get_db()
    cursor = db.cursor()

    try:
        if target == 'All':
            cursor.execute("SELECT user_id FROM Users WHERE role IN ('Student', 'Faculty')")
        else:
            cursor.execute("SELECT user_id FROM Users WHERE role = ?", (target,))

        users = cursor.fetchall()

        for user in users:
            cursor.execute("""
                INSERT INTO Notifications (user_id, Message, IsRead, CreatedAt)
                VALUES (?, ?, 0, GETDATE())
            """, (user[0], msg_text))

        db.commit()
        flash(f"Broadcast sent successfully to {target}!", "success")
    except Exception as e:
        db.rollback()
        flash(f"Broadcast failed: {e}", "danger")

    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/reply_message', methods=['POST'])
def reply_message():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    receiver_id = request.form.get('receiver_id')
    reply_body = request.form.get('reply_body')
    original_msg_id = request.form.get('original_message_id')
    admin_id = session.get('user_id')

    db = get_db()
    cursor = db.cursor()

    try:
        cursor.execute("""
            INSERT INTO Messages (SenderID, ReceiverID, Subject, Body, SentAt, IsRead)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, 0)
        """, (admin_id, receiver_id, "Reply from Admin", reply_body))

        cursor.execute("DELETE FROM Messages WHERE MessageID = ?", (original_msg_id,))

        db.commit()
    except Exception as e:
        print(f"Reply Error: {e}")
        db.rollback()

    return redirect(url_for('admin.admin_messages'))