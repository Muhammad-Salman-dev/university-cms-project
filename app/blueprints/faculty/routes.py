import os
from flask import Blueprint, render_template, session, redirect, url_for, flash, request, current_app
from werkzeug.utils import secure_filename
from app.database import get_db
from datetime import datetime

faculty_bp = Blueprint('faculty', __name__)


# --- HELPER: Get Actual Faculty ID from User Session ---
def get_faculty_id_from_session(cursor, user_id):
    cursor.execute(
        "SELECT FacultyID FROM Faculty F JOIN Users U ON F.Email = U.Email WHERE U.user_id = ?",
        (user_id,)
    )
    row = cursor.fetchone()
    return row[0] if row else None


# --- 1. DASHBOARD ---
@faculty_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session.get('role') != 'Faculty':
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    db = get_db()
    cursor = db.cursor()

    try:
        cursor.execute("SELECT email FROM Users WHERE user_id = ?", (user_id,))
        user_row = cursor.fetchone()
        if not user_row:
            flash("User record not found.", "danger")
            return redirect(url_for('auth.login'))

        user_email = user_row[0]
        cursor.execute("SELECT FacultyID, Name FROM Faculty WHERE Email = ?", (user_email,))
        faculty_row = cursor.fetchone()
        if not faculty_row:
            flash("Faculty profile not found. Contact Admin.", "danger")
            return redirect(url_for('auth.login'))

        faculty_id, faculty_name = faculty_row
        cursor.execute("SELECT * FROM Courses WHERE FacultyID = ?", (faculty_id,))
        courses = cursor.fetchall()
        return render_template('faculty/dashboard.html', courses=courses, name=faculty_name)
    except Exception as e:
        print(f"Dashboard Error: {e}")
        flash("System error loading dashboard.", "danger")
        return redirect(url_for('auth.login'))


# --- 2. MANAGE COURSE ---
@faculty_bp.route('/manage_course/<int:course_id>', methods=['GET'])
def manage_course(course_id):
    if 'user_id' not in session or session.get('role') != 'Faculty':
        return redirect(url_for('auth.login'))

    db = get_db()
    cursor = db.cursor()

    try:
        cursor.execute("SELECT * FROM Courses WHERE CourseID = ?", (course_id,))
        course = cursor.fetchone()

        cursor.execute("""
            SELECT E.EnrollmentID, S.StudentID, S.Name, E.Grade
            FROM Enrollments E
            JOIN Students S ON E.StudentID = S.StudentID
            WHERE E.CourseID = ?
        """, (course_id,))
        students = cursor.fetchall()

        cursor.execute("SELECT * FROM Assignments WHERE CourseID = ?", (course_id,))
        assignments = cursor.fetchall()

        return render_template('faculty/manage_course.html', course=course, students=students, assignments=assignments)
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
        cursor.execute(
            "UPDATE Enrollments SET Grade = ? WHERE CourseID = ? AND StudentID = ?",
            (grade, course_id, student_id)
        )
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
    file = request.files.get('file')
    file_path = None

    if file and file.filename != '':
        filename = secure_filename(file.filename)
        upload_folder = os.path.join(current_app.root_path, 'static/uploads')
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
        save_path = os.path.join(upload_folder, filename)
        file.save(save_path)
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


# --- 6. SETTINGS ---
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
                cursor.execute("UPDATE Users SET Password = ? WHERE user_id = ?", (new_password, user_id))
                db.commit()
                flash("Settings updated successfully!", "success")
        except Exception as e:
            db.rollback()
            flash(f"Error updating settings: {e}", "danger")
        return redirect(url_for('faculty.settings'))

    cursor.execute("""
        SELECT F.Name, F.Email, F.Department, F.Designation, U.Password
        FROM Faculty F
        JOIN Users U ON F.Email = U.Email
        WHERE U.user_id = ?
    """, (user_id,))
    user_info = cursor.fetchone()

    return render_template('faculty/settings.html', user=user_info)


# --- 7. REPORTS ---
@faculty_bp.route('/reports')
def reports():
    if 'user_id' not in session or session.get('role') != 'Faculty':
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    db = get_db()
    cursor = db.cursor()

    # Total students
    cursor.execute("""
        SELECT COUNT(DISTINCT E.StudentID)
        FROM Enrollments E
        JOIN Courses C ON E.CourseID = C.CourseID
        JOIN Faculty F ON C.FacultyID = F.FacultyID
        JOIN Users U ON F.Email = U.Email
        WHERE U.user_id = ?
    """, (user_id,))
    total_students = cursor.fetchone()[0]

    # Total courses
    cursor.execute("""
        SELECT COUNT(*)
        FROM Courses C
        JOIN Faculty F ON C.FacultyID = F.FacultyID
        JOIN Users U ON F.Email = U.Email
        WHERE U.user_id = ?
    """, (user_id,))
    total_courses = cursor.fetchone()[0]

    # Top performers
    cursor.execute("""
        SELECT COUNT(E.Grade)
        FROM Enrollments E
        JOIN Courses C ON E.CourseID = C.CourseID
        JOIN Faculty F ON C.FacultyID = F.FacultyID
        JOIN Users U ON F.Email = U.Email
        WHERE U.user_id = ? AND (E.Grade = 'A' OR E.Grade = 'B')
    """, (user_id,))
    top_performers = cursor.fetchone()[0]

    return render_template('faculty/reports.html', total_students=total_students, total_courses=total_courses, top_performers=top_performers)


# --- 8. MY COURSES ---
@faculty_bp.route('/my_courses')
def my_courses():
    if 'user_id' not in session or session.get('role') != 'Faculty':
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT C.CourseID, C.CourseName, C.CourseCode, C.Credits, C.Room, C.Description
        FROM Courses C
        JOIN Faculty F ON C.FacultyID = F.FacultyID
        JOIN Users U ON F.Email = U.Email
        WHERE U.user_id = ?
    """, (user_id,))
    courses = cursor.fetchall()

    return render_template('faculty/my_courses.html', courses=courses)


# --- 9. STUDENTS LIST ---
@faculty_bp.route('/students')
def students():
    if 'user_id' not in session or session.get('role') != 'Faculty':
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    db = get_db()
    cursor = db.cursor()
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
    students_list = cursor.fetchall()

    return render_template('faculty/students.html', students=students_list)


# --- 10. NOTIFICATION & MESSAGE SYSTEM ---
@faculty_bp.context_processor
def inject_notifications():
    if 'user_id' not in session:
        return dict(unread_count=0)

    current_user_id = session['user_id']
    db = get_db()
    cursor = db.cursor()

    try:
        cursor.execute("SELECT COUNT(*) FROM Notifications WHERE user_id = ? AND IsRead = 0", (current_user_id,))
        count_row = cursor.fetchone()
        count = count_row[0] if count_row else 0
    except:
        count = 0

    return dict(unread_count=count)


@faculty_bp.route('/notifications')
def notifications():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    current_user_id = session['user_id']
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT Message, CreatedAt, IsRead
        FROM Notifications
        WHERE user_id = ?
        ORDER BY CreatedAt DESC
    """, (current_user_id,))
    notifs = cursor.fetchall()

    cursor.execute("UPDATE Notifications SET IsRead = 1 WHERE user_id = ?", (current_user_id,))
    db.commit()

    return render_template('faculty/notifications.html', notifications=notifs)


@faculty_bp.context_processor
def inject_messages_count():
    if 'user_id' not in session:
        return dict(unread_msg_count=0)

    user_id = session['user_id']
    db = get_db()
    cursor = db.cursor()

    try:
        faculty_id = get_faculty_id_from_session(cursor, user_id)
        cursor.execute("""
            SELECT COUNT(*) FROM Messages
            WHERE ReceiverID = ? AND ReceiverType = 'Faculty' AND IsRead = 0
        """, (faculty_id,))
        count_row = cursor.fetchone()
        count = count_row[0] if count_row else 0
    except:
        count = 0

    return dict(unread_msg_count=count)


# --- 11. MESSAGES ---
@faculty_bp.route('/messages')
def messages():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    db = get_db()
    cursor = db.cursor()

    try:
        faculty_id = get_faculty_id_from_session(cursor, user_id)
        cursor.execute("""
            SELECT Subject, Body, SentAt, IsRead, MessageID
            FROM Messages
            WHERE ReceiverID = ? AND ReceiverType = 'Faculty' AND (IsDeleted = 0 OR IsDeleted IS NULL)
                  AND (IsArchived = 0 OR IsArchived IS NULL)
            ORDER BY SentAt DESC
        """, (faculty_id,))
        msgs = cursor.fetchall()

        cursor.execute("""
            UPDATE Messages
            SET IsRead = 1
            WHERE ReceiverID = ? AND ReceiverType = 'Faculty' AND IsRead = 0 AND (IsDeleted = 0 OR IsDeleted IS NULL)
        """, (faculty_id,))
        db.commit()
    except Exception as e:
        print(f"Messages Fetch Error: {e}")
        msgs = []

    return render_template('faculty/messages.html', messages=msgs)


@faculty_bp.route('/send_message', methods=['POST'])
def send_message():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    sender_id = session['user_id']
    receiver_type = request.form.get('receiver_type')
    subject = request.form.get('subject')
    body = request.form.get('body')
    db = get_db()
    cursor = db.cursor()

    if receiver_type == 'Admin':
        receiver_id = 1
    else:
        student_id = request.form.get('student_id')
        cursor.execute("""
            SELECT u.user_id
            FROM Users u
            JOIN Students s ON u.name = s.Name
            WHERE s.StudentID = ?
        """, (student_id,))
        res = cursor.fetchone()
        receiver_id = res[0] if res else None

    cursor.execute("""
        INSERT INTO Messages (SenderID, ReceiverID, Subject, Body, ReceiverType, IsRead, SentAt)
        VALUES (?, ?, ?, ?, ?, 0, GETDATE())
    """, (sender_id, receiver_id, subject, body, receiver_type))
    db.commit()
    flash('Message sent successfully!', 'success')

    return redirect(url_for('faculty.messages'))


# --- 12. DELETE MESSAGE ---
@faculty_bp.route('/delete_message/<int:msg_id>')
def delete_message(msg_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    db = get_db()
    cursor = db.cursor()

    try:
        faculty_id = get_faculty_id_from_session(cursor, session['user_id'])
        cursor.execute("UPDATE Messages SET IsDeleted = 1 WHERE MessageID = ? AND ReceiverID = ?", (msg_id, faculty_id))
        db.commit()
        flash('Message moved to trash!', 'success')
    except Exception as e:
        db.rollback()
        flash('Error deleting message.', 'danger')
        print(f"Delete Error: {e}")

    return redirect(url_for('faculty.messages'))


# --- 13. ARCHIVE MESSAGE ---
@faculty_bp.route('/archive_message/<int:msg_id>')
def archive_message(msg_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    db = get_db()
    cursor = db.cursor()

    try:
        faculty_id = get_faculty_id_from_session(cursor, session['user_id'])
        cursor.execute("UPDATE Messages SET IsArchived = 1 WHERE MessageID = ? AND ReceiverID = ?", (msg_id, faculty_id))
        db.commit()
        flash('Message archived successfully!', 'info')
    except Exception as e:
        db.rollback()
        flash('Error archiving message.', 'danger')

    return redirect(url_for('faculty.messages'))


# --- 14. MARK AS READ ---
@faculty_bp.route('/mark_as_read/<int:msg_id>')
def mark_as_read(msg_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    db = get_db()
    cursor = db.cursor()

    try:
        faculty_id = get_faculty_id_from_session(cursor, session['user_id'])
        cursor.execute("UPDATE Messages SET IsRead = 1 WHERE MessageID = ? AND ReceiverID = ?", (msg_id, faculty_id))
        db.commit()
    except Exception as e:
        db.rollback()

    return redirect(url_for('faculty.messages'))


# --- 15. ARCHIVED MESSAGES ---
@faculty_bp.route('/archived_messages')
def archived_messages():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    db = get_db()
    cursor = db.cursor()
    faculty_id = get_faculty_id_from_session(cursor, user_id)

    cursor.execute("""
        SELECT Subject, Body, SentAt, IsRead, MessageID
        FROM Messages
        WHERE ReceiverID = ? AND ReceiverType = 'Faculty' AND IsArchived = 1 AND (IsDeleted = 0 OR IsDeleted IS NULL)
        ORDER BY SentAt DESC
    """, (faculty_id,))
    archived_msgs = cursor.fetchall()

    return render_template('faculty/archived_messages.html', messages=archived_msgs)


@faculty_bp.route('/unarchive_message/<int:msg_id>')
def unarchive_message(msg_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    db = get_db()
    cursor = db.cursor()
    faculty_id = get_faculty_id_from_session(cursor, session['user_id'])
    cursor.execute("UPDATE Messages SET IsArchived = 0 WHERE MessageID = ? AND ReceiverID = ?", (msg_id, faculty_id))
    db.commit()
    flash('Message restored to inbox!', 'success')

    return redirect(url_for('faculty.archived_messages'))


# --- 16. TRASH MESSAGES ---
@faculty_bp.route('/trash_messages')
def trash_messages():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    db = get_db()
    cursor = db.cursor()
    faculty_id = get_faculty_id_from_session(cursor, user_id)

    cursor.execute("""
        SELECT Subject, Body, SentAt, IsRead, MessageID
        FROM Messages
        WHERE ReceiverID = ? AND ReceiverType = 'Faculty' AND IsDeleted = 1
        ORDER BY SentAt DESC
    """, (faculty_id,))
    msgs = cursor.fetchall()

    return render_template('faculty/trash_messages.html', messages=msgs, title="Trash")


# --- 17. RESTORE MESSAGE ---
@faculty_bp.route('/restore_message/<int:msg_id>')
def restore_message(msg_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    db = get_db()
    cursor = db.cursor()
    faculty_id = get_faculty_id_from_session(cursor, session['user_id'])
    cursor.execute("""
        UPDATE Messages SET IsArchived = 0, IsDeleted = 0
        WHERE MessageID = ? AND ReceiverID = ?
    """, (msg_id, faculty_id))
    db.commit()
    flash('Message restored to inbox!', 'success')

    return redirect(url_for('faculty.messages'))


# --- 18. VIEW SUBMISSIONS ---
@faculty_bp.route('/view_submissions/<int:assignment_id>')
def view_submissions(assignment_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT s.Name, sub.FilePath, sub.SubmissionDate, sub.SubmissionID
        FROM Submissions sub
        JOIN Students s ON sub.StudentID = s.StudentID
        WHERE sub.AssignmentID = ?
        ORDER BY sub.SubmissionDate DESC
    """, (assignment_id,))
    submissions = cursor.fetchall()

    cursor.execute("SELECT Title FROM Assignments WHERE AssignmentID = ?", (assignment_id,))
    assignment_title = cursor.fetchone()[0]

    return render_template('faculty/submissions_list.html', submissions=submissions, title=assignment_title)
