import os
from flask import Blueprint, render_template, session, redirect, url_for, flash, request, current_app
from werkzeug.utils import secure_filename
from app.database import get_db

faculty_bp = Blueprint('faculty', __name__)

# --- 1. DASHBOARD (FIXED) ---
@faculty_bp.route('/dashboard')
def dashboard():
    # Security Check
    if 'user_id' not in session or session.get('role') != 'Faculty':
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    db = get_db()
    cursor = db.cursor()

    try:
        # --- FIX 1: Column Name 'user_id' (lowercase) use kiya hai ---
        cursor.execute("SELECT email FROM Users WHERE user_id = ?", (user_id,))
        user_row = cursor.fetchone()

        if not user_row:
            flash("User record not found.", "danger")
            return redirect(url_for('auth.login'))

        # --- FIX 2: Tuple Indexing (user_row[0]) use kiya hai, .Email nahi ---
        user_email = user_row[0]

        # --- FIX 3: Email se Faculty ID nikalna ---
        cursor.execute("SELECT FacultyID, Name FROM Faculty WHERE Email = ?", (user_email,))
        faculty_row = cursor.fetchone()

        if not faculty_row:
            flash("Faculty profile not found. Contact Admin.", "danger")
            return redirect(url_for('auth.login'))

        faculty_id = faculty_row[0]
        faculty_name = faculty_row[1]

        # Courses nikalna
        cursor.execute("SELECT * FROM Courses WHERE FacultyID = ?", (faculty_id,))
        courses = cursor.fetchall()

        return render_template('faculty/dashboard.html', courses=courses, name=faculty_name)

    except Exception as e:
        print(f"Dashboard Error: {e}")
        flash("System error loading dashboard.", "danger")
        return redirect(url_for('auth.login'))


# --- 2. MANAGE COURSE (Grading + View) ---
@faculty_bp.route('/manage_course/<int:course_id>', methods=['GET'])
def manage_course(course_id):
    if 'user_id' not in session or session.get('role') != 'Faculty':
        return redirect(url_for('auth.login'))

    db = get_db()
    cursor = db.cursor()

    try:
        # Course Details
        cursor.execute("SELECT * FROM Courses WHERE CourseID = ?", (course_id,))
        course = cursor.fetchone()

        # Students List with Grades
        cursor.execute("""
            SELECT E.EnrollmentID, S.StudentID, S.Name, E.Grade
            FROM Enrollments E
            JOIN Students S ON E.StudentID = S.StudentID
            WHERE E.CourseID = ?
        """, (course_id,))
        students = cursor.fetchall()

        # Assignments List
        cursor.execute("SELECT * FROM Assignments WHERE CourseID = ?", (course_id,))
        assignments = cursor.fetchall()

        return render_template('faculty/manage_course.html',
                               course=course,
                               students=students,
                               assignments=assignments)
    except Exception as e:
        print(f"Manage Course Error: {e}")
        flash("Error loading course details.", "danger")
        return redirect(url_for('faculty.dashboard'))


# --- 3. UPDATE GRADE ---
@faculty_bp.route('/update_grade/<int:course_id>', methods=['POST'])
def update_grade(course_id):
    if 'user_id' not in session or session.get('role') != 'Faculty':
        return redirect(url_for('auth.login'))

    student_id = request.form.get('student_id')
    grade = request.form.get('grade')

    db = get_db()
    cursor = db.cursor()

    try:
        cursor.execute("UPDATE Enrollments SET Grade = ? WHERE CourseID = ? AND StudentID = ?", (grade, course_id, student_id))
        db.commit()
        flash("Grade updated successfully!", "success")
    except Exception as e:
        db.rollback()
        flash(f"Error updating grade: {e}", "danger")

    return redirect(url_for('faculty.manage_course', course_id=course_id))


# --- 4. MARK ATTENDANCE ---
@faculty_bp.route('/mark_attendance/<int:course_id>', methods=['POST'])
def mark_attendance(course_id):
    if 'user_id' not in session or session.get('role') != 'Faculty':
        return redirect(url_for('auth.login'))

    db = get_db()
    cursor = db.cursor()
    date = request.form.get('attendance_date')
    student_ids = request.form.getlist('student_ids')

    try:
        for sid in student_ids:
            status = request.form.get(f'status_{sid}')
            if status:
                cursor.execute("""
                    INSERT INTO Attendance (CourseID, StudentID, AttendanceDate, Status)
                    VALUES (?, ?, ?, ?)
                """, (course_id, sid, date, status))
        db.commit()
        flash("Attendance marked successfully!", "success")
    except Exception as e:
        db.rollback()
        print(f"Attendance Error: {e}")
        flash("Error marking attendance.", "danger")

    return redirect(url_for('faculty.manage_course', course_id=course_id))


# --- 5. ADD ASSIGNMENT ---
@faculty_bp.route('/add_assignment/<int:course_id>', methods=['POST'])
def add_assignment(course_id):
    if 'user_id' not in session or session.get('role') != 'Faculty':
        return redirect(url_for('auth.login'))

    title = request.form.get('title')
    description = request.form.get('description')
    deadline = request.form.get('deadline')

    # File handling
    file = request.files.get('file') # HTML name attribute 'file' hona chahiye
    file_path = None

    if file and file.filename != '':
        filename = secure_filename(file.filename)
        # Folder create karein agar nahi hai
        upload_folder = os.path.join(current_app.root_path, 'static/uploads')
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        # File save karein
        save_path = os.path.join(upload_folder, filename)
        file.save(save_path)

        # DB ke liye relative path
        file_path = f'uploads/{filename}'

    db = get_db()
    cursor = db.cursor()

    try:
        cursor.execute("""
            INSERT INTO Assignments (CourseID, Title, Description, Deadline, AttachmentPath, CreatedAt)
            VALUES (?, ?, ?, ?, ?, GETDATE())
        """, (course_id, title, description, deadline, file_path))

        db.commit()
        flash("Assignment uploaded successfully!", "success")
    except Exception as e:
        db.rollback()
        print(f"Assignment Error: {e}")
        flash("Error adding assignment.", "danger")

    return redirect(url_for('faculty.manage_course', course_id=course_id))

# --- 6. FACULTY SETTINGS / PROFILE (FIXED) ---
@faculty_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user_id' not in session or session.get('role') != 'Faculty':
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    db = get_db()
    cursor = db.cursor()

    if request.method == 'POST':
        new_password = request.form.get('password')

        try:
            if new_password:
                # FIX: 'UserID' ko 'user_id' kar diya
                cursor.execute("UPDATE Users SET Password = ? WHERE user_id = ?", (new_password, user_id))

            db.commit()
            flash("Settings updated successfully!", "success")
        except Exception as e:
            db.rollback()
            flash(f"Error updating settings: {e}", "danger")

        return redirect(url_for('faculty.settings'))

    # GET Request: Data show karein
    # FIX: 'U.UserID' ko 'U.user_id' kar diya
    cursor.execute("""
        SELECT F.Name, F.Email, F.Department, F.Designation, U.Password
        FROM Faculty F
        JOIN Users U ON F.Email = U.Email
        WHERE U.user_id = ?
    """, (user_id,))
    user_info = cursor.fetchone()

    return render_template('faculty/settings.html', user=user_info)


# --- 7. REPORTS (Analytics) (FIXED) ---
@faculty_bp.route('/reports')
def reports():
    if 'user_id' not in session or session.get('role') != 'Faculty':
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    db = get_db()
    cursor = db.cursor()

    # 1. Total Students
    # FIX: 'U.UserID' ko 'U.user_id' kar diya
    cursor.execute("""
        SELECT COUNT(DISTINCT E.StudentID)
        FROM Enrollments E
        JOIN Courses C ON E.CourseID = C.CourseID
        JOIN Faculty F ON C.FacultyID = F.FacultyID
        JOIN Users U ON F.Email = U.Email
        WHERE U.user_id = ?
    """, (user_id,))
    total_students = cursor.fetchone()[0]

    # 2. Total Courses
    # FIX: 'U.UserID' ko 'U.user_id' kar diya
    cursor.execute("""
        SELECT COUNT(*) FROM Courses C
        JOIN Faculty F ON C.FacultyID = F.FacultyID
        JOIN Users U ON F.Email = U.Email
        WHERE U.user_id = ?
    """, (user_id,))
    total_courses = cursor.fetchone()[0]

    # 3. Average Class Performance
    # FIX: 'U.UserID' ko 'U.user_id' kar diya
    cursor.execute("""
        SELECT COUNT(E.Grade)
        FROM Enrollments E
        JOIN Courses C ON E.CourseID = C.CourseID
        JOIN Faculty F ON C.FacultyID = F.FacultyID
        JOIN Users U ON F.Email = U.Email
        WHERE U.user_id = ? AND (E.Grade = 'A' OR E.Grade = 'B')
    """, (user_id,))
    top_performers = cursor.fetchone()[0]

    return render_template('faculty/reports.html',
                           total_students=total_students,
                           total_courses=total_courses,
                           top_performers=top_performers)

# --- 8. MY COURSES (Detailed List) ---
@faculty_bp.route('/my_courses')
def my_courses():
    if 'user_id' not in session or session.get('role') != 'Faculty':
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    db = get_db()
    cursor = db.cursor()

    # Get all courses for this faculty
    # Note: Using correct column 'user_id'
    cursor.execute("""
        SELECT C.CourseID, C.CourseName, C.CourseCode, C.Credits, C.Room, C.Description
        FROM Courses C
        JOIN Faculty F ON C.FacultyID = F.FacultyID
        JOIN Users U ON F.Email = U.Email
        WHERE U.user_id = ?
    """, (user_id,))
    courses = cursor.fetchall()

    return render_template('faculty/my_courses.html', courses=courses)


# --- 9. ALL STUDENTS LIST ---
@faculty_bp.route('/students')
def students():
    if 'user_id' not in session or session.get('role') != 'Faculty':
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    db = get_db()
    cursor = db.cursor()

    # Get all students enrolled in ANY course taught by this faculty
    # Note: Using correct column 'user_id'
    cursor.execute("""
        SELECT S.StudentID, S.Name, S.Email, S.Department, C.CourseName
        FROM Students S
        JOIN Enrollments E ON S.StudentID = E.StudentID
        JOIN Courses C ON E.CourseID = C.CourseID
        JOIN Faculty F ON C.FacultyID = F.FacultyID
        JOIN Users U ON F.Email = U.Email
        WHERE U.user_id = ?
        ORDER BY C.CourseName, S.Name
    """, (user_id,))
    students = cursor.fetchall()

    return render_template('faculty/students.html', students=students)

    # --- 10. NOTIFICATION SYSTEM (Final) ---

# A. Yeh function har page pe 'unread_count' bheje ga (Header ke liye)
@faculty_bp.context_processor
def inject_notifications():
    # Agar user login nahi hai to 0 return karo
    if 'user_id' not in session:
        return dict(unread_count=0)

    current_user_id = session['user_id']
    db = get_db()
    cursor = db.cursor()

    try:
        # Sirf UNREAD (IsRead = 0) count karein
        # Note: 'user_id' ab database wala hi use ho raha hai
        cursor.execute("SELECT COUNT(*) FROM Notifications WHERE user_id = ? AND IsRead = 0", (current_user_id,))
        count_row = cursor.fetchone()
        count = count_row[0] if count_row else 0
    except Exception as e:
        count = 0

    return dict(unread_count=count)


# B. Notifications Page Route (List dikhane ke liye)
@faculty_bp.route('/notifications')
def notifications():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    current_user_id = session['user_id']
    db = get_db()
    cursor = db.cursor()

    # 1. Saare Notifications nikalein (Jo naye hain wo pehle)
    cursor.execute("""
        SELECT Message, CreatedAt, IsRead
        FROM Notifications
        WHERE user_id = ?
        ORDER BY CreatedAt DESC
    """, (current_user_id,))
    notifs = cursor.fetchall()

    # 2. Page khulte hi sabko 'Read' (1) mark kar dein
    cursor.execute("UPDATE Notifications SET IsRead = 1 WHERE user_id = ?", (current_user_id,))
    db.commit()

    return render_template('faculty/notifications.html', notifications=notifs)

@faculty_bp.context_processor
def inject_messages_count():
    if 'user_id' not in session:
        return dict(unread_msg_count=0)

    current_user_id = session['user_id']
    db = get_db()
    cursor = db.cursor()

    try:
        # Sirf Messages table se UNREAD count karein
        cursor.execute("SELECT COUNT(*) FROM Messages WHERE ReceiverID = ? AND IsRead = 0", (current_user_id,))
        count_row = cursor.fetchone()
        count = count_row[0] if count_row else 0
    except:
        count = 0

    return dict(unread_msg_count=count)

@faculty_bp.route('/messages')
def messages():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    current_user_id = session['user_id']
    db = get_db()
    cursor = db.cursor()

    # 1. Saare Messages nikalein
    cursor.execute("""
        SELECT Subject, Body, SentAt, IsRead, MessageID
        FROM Messages
        WHERE ReceiverID = ?
        ORDER BY SentAt DESC
    """, (current_user_id,))
    msgs = cursor.fetchall()

    # 2. Page khulte hi sabko 'Read' mark kar dein
    cursor.execute("UPDATE Messages SET IsRead = 1 WHERE ReceiverID = ?", (current_user_id,))
    db.commit()

    return render_template('faculty/messages.html', messages=msgs)


@faculty_bp.route('/send_message', methods=['POST'])
def send_message():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    sender_id = session['user_id']
    receiver_type = request.form.get('receiver_type') # 'Admin' or 'Student'
    subject = request.form.get('subject')
    body = request.form.get('body')

    db = get_db()
    cursor = db.cursor()

    if receiver_type == 'Admin':
        receiver_id = 1 # Hamara Admin ID 1 hai
    else:
        receiver_id = request.form.get('student_id') # Form se student ki ID ayegi

    cursor.execute("""
        INSERT INTO Messages (SenderID, ReceiverID, Subject, Body, ReceiverType, IsRead, SentAt)
        VALUES (?, ?, ?, ?, ?, 0, GETDATE())
    """, (sender_id, receiver_id, subject, body, receiver_type))

    db.commit()
    flash('Message sent successfully!', 'success')
    return redirect(url_for('faculty.messages'))