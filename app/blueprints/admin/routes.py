from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from app.database import get_db

admin_bp = Blueprint('admin', __name__)

# --- 1. DASHBOARD ---
@admin_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session.get('role') != 'Admin':
        return redirect(url_for('auth.login'))

    db = get_db()
    cursor = db.cursor()

    # 1. Count Students
    cursor.execute("SELECT COUNT(*) FROM Users WHERE role='Student'")
    s_count = cursor.fetchone()[0]

    # 2. Count Faculty
    cursor.execute("SELECT COUNT(*) FROM Users WHERE role='Faculty'")
    f_count = cursor.fetchone()[0] # Yahan shayad query alag ho agar table alag hai, par logic yehi hai

    # 3. Count Courses
    cursor.execute("SELECT COUNT(*) FROM Courses")
    c_count = cursor.fetchone()[0]

    # --- YAHAN CHANGE HAI ---
    # Data ko ek 'dictionary' mein pack kar rahe hain taaki HTML padh sake
    stats_data = {
        'students': s_count,
        'faculty': f_count,
        'courses': c_count
    }

    # Hum 'stats' naam se bhej rahe hain
    return render_template('admin/dashboard.html', stats=stats_data)

# --- 2. MANAGE LISTS (Sidebar Links) ---
@admin_bp.route('/courses')
def list_courses():
    if 'user_id' not in session or session.get('role') != 'Admin': return redirect(url_for('auth.login'))
    db = get_db()
    cursor = db.cursor()
    # Teacher ka naam bhi saath mein la rahe hain
    cursor.execute("SELECT c.course_code, c.course_name, c.credits, u.name FROM Courses c LEFT JOIN Users u ON c.teacher_id = u.user_id")
    courses = cursor.fetchall()
    return render_template('admin/courses/list.html', courses=courses)

@admin_bp.route('/faculty')
def list_faculty():
    if 'user_id' not in session or session.get('role') != 'Admin': return redirect(url_for('auth.login'))
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT name, email FROM Users WHERE role='Faculty'")
    faculty = cursor.fetchall()
    return render_template('admin/faculty/list.html', faculty=faculty)

@admin_bp.route('/students')
def list_students():
    if 'user_id' not in session or session.get('role') != 'Admin': return redirect(url_for('auth.login'))
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT user_id, name, email FROM Users WHERE role='Student'")
    students = cursor.fetchall()
    return render_template('admin/students/list.html', students=students)

# --- 3. ADD FUNCTIONS ---
@admin_bp.route('/add_course', methods=['GET', 'POST'])
def add_course():
    if 'user_id' not in session or session.get('role') != 'Admin': return redirect(url_for('auth.login'))
    db = get_db()
    cursor = db.cursor()

    if request.method == 'POST':
        try:
            cursor.execute("INSERT INTO Courses (course_code, course_name, credits, room_number, teacher_id) VALUES (?, ?, ?, ?, ?)",
                           (request.form['code'], request.form['name'], request.form['credits'], request.form['room'], request.form['teacher']))
            db.commit()
            flash("✅ Course Created Successfully!", "success")
            return redirect(url_for('admin.dashboard'))
        except Exception as e:
            flash(f"Error: {e}", "error")

    cursor.execute("SELECT user_id, name FROM Users WHERE role='Faculty'")
    return render_template('admin/courses/add.html', faculty=cursor.fetchall())

@admin_bp.route('/add_faculty', methods=['GET', 'POST'])
def add_faculty():
    if 'user_id' not in session or session.get('role') != 'Admin': return redirect(url_for('auth.login'))
    if request.method == 'POST':
        db = get_db()
        try:
            db.execute("INSERT INTO Users (name, email, password, role) VALUES (?, ?, ?, 'Faculty')",
                       (request.form['name'], request.form['email'], request.form['password']))
            db.commit()
            flash(f"✅ Faculty Added!", "success")
            return redirect(url_for('admin.dashboard'))
        except Exception as e:
            flash(f"Error: {e}", "error")
    return render_template('admin/faculty/add.html')

# --- NEW: ADD STUDENT ---
@admin_bp.route('/add_student', methods=['GET', 'POST'])
def add_student():
    if 'user_id' not in session or session.get('role') != 'Admin': return redirect(url_for('auth.login'))
    if request.method == 'POST':
        db = get_db()
        try:
            db.execute("INSERT INTO Users (name, email, password, role) VALUES (?, ?, ?, 'Student')",
                       (request.form['name'], request.form['email'], request.form['password']))
            db.commit()
            flash(f"✅ Student Added Successfully!", "success")
            return redirect(url_for('admin.dashboard'))
        except Exception as e:
            flash(f"Error: {e}", "error")
    return render_template('admin/students/add.html')
# --- 4. MANAGE/DROP STUDENT (Correct Logic) ---
@admin_bp.route('/manage_enrollments', methods=['GET', 'POST'])
def manage_enrollments():
    if 'user_id' not in session or session.get('role') != 'Admin':
        return redirect(url_for('auth.login'))

    db = get_db()
    cursor = db.cursor()

    # --- ACTION HANDLE KARO (Enroll ya Drop) ---
    if request.method == 'POST':
        action = request.form.get('action') # Hidden input batayega kya karna hai

        # 🟢 CASE 1: Student ko Course mein Enroll karna
        if action == 'enroll':
            student_id = request.form.get('student_id')
            course_id = request.form.get('course_id')

            # Check karo pehle se enrolled to nahi?
            cursor.execute("SELECT * FROM Enrollments WHERE student_id=? AND course_id=?", (student_id, course_id))
            if cursor.fetchone():
                flash("Student is already enrolled in this course!", "error")
            else:
                try:
                    cursor.execute("INSERT INTO Enrollments (student_id, course_id) VALUES (?, ?)", (student_id, course_id))
                    cursor.execute("UPDATE Courses SET enrolled_count = enrolled_count + 1 WHERE course_id = ?", (course_id,))
                    db.commit()
                    flash("Student Enrolled Successfully! ✅", "success")
                except Exception as e:
                    flash(f"Error enrolling: {e}", "error")

        # 🔴 CASE 2: Student ko Drop karna
        elif action == 'drop':
            enrollment_id = request.form.get('enrollment_id')
            course_id = request.form.get('course_id') # Count kam karne ke liye chahiye

            try:
                cursor.execute("DELETE FROM Enrollments WHERE enrollment_id = ?", (enrollment_id,))
                cursor.execute("UPDATE Courses SET enrolled_count = enrolled_count - 1 WHERE course_id = ?", (course_id,))
                db.commit()
                flash("Student Dropped Successfully! 🚫", "success")
            except Exception as e:
                flash(f"Error dropping: {e}", "error")

    # --- DATA LOAD KARO (Dropdowns aur Table ke liye) ---

    # 1. Table ke liye Enrollments list
    cursor.execute("""
        SELECT e.enrollment_id, u.name, u.email, c.course_code, c.course_name, c.course_id
        FROM Enrollments e
        JOIN Users u ON e.student_id = u.user_id
        JOIN Courses c ON e.course_id = c.course_id
    """)
    enrollments = cursor.fetchall()

    # 2. Dropdown ke liye All Students
    cursor.execute("SELECT user_id, name, email FROM Users WHERE role='Student'")
    all_students = cursor.fetchall()

    # 3. Dropdown ke liye All Courses
    cursor.execute("SELECT course_id, course_code, course_name FROM Courses")
    all_courses = cursor.fetchall()

    return render_template('admin/students/manage.html',
                           enrollments=enrollments,
                           all_students=all_students,
                           all_courses=all_courses)