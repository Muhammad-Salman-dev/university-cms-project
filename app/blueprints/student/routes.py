import os
from flask import render_template, session, redirect, url_for, request, flash, current_app
from . import student_bp
from app.database import get_db
from datetime import datetime


# --- DASHBOARD ---
@student_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session.get('role') != 'Student':
        return redirect(url_for('auth.login'))

    user_id = session.get('user_id')
    db = get_db()
    cursor = db.cursor()

    # Fetch student basic information
    cursor.execute("""
        SELECT s.StudentID, s.Name
        FROM Students s
        JOIN Users u ON s.Name = u.name
        WHERE u.user_id = ?
    """, (user_id,))
    student = cursor.fetchone()
    student_id = student[0] if student else None

    # Calculate enrolled courses count
    cursor.execute("SELECT COUNT(*) FROM Enrollments WHERE StudentID = ?", (student_id,))
    courses_count = cursor.fetchone()[0]

    # GPA calculation
    cursor.execute("SELECT Grade FROM Enrollments WHERE StudentID = ?", (student_id,))
    grades = cursor.fetchall()
    total_points = 0
    valid_grades_count = 0
    for g in grades:
        if g[0]:
            valid_grades_count += 1
            if g[0] == 'A':
                total_points += 4.0
            elif g[0] == 'B':
                total_points += 3.0
            else:
                total_points += 2.0
    gpa = round(total_points / valid_grades_count, 2) if valid_grades_count > 0 else 0.0

    # Fetch notifications
    cursor.execute("""
        SELECT Message, CreatedAt, IsRead
        FROM Notifications
        WHERE user_id = ?
        ORDER BY CreatedAt DESC
    """, (user_id,))
    user_notifications = cursor.fetchall()

    # Fetch unread messages count
    cursor.execute("""
        SELECT COUNT(*)
        FROM Messages
        WHERE ReceiverID = ? AND ReceiverType = 'Student' AND IsRead = 0
    """, (user_id,))
    unread_msg_count = cursor.fetchone()[0]

    announcements_list = [
        {'title': 'Notification', 'body': n[0], 'time': n[1]} for n in user_notifications[:3]
    ]

    stats = {
        'enrolled_courses': courses_count,
        'assignments_due': 0,
        'gpa': gpa,
        'unread_messages': unread_msg_count
    }

    return render_template(
        'student/dashboard.html',
        stats=stats,
        announcements=announcements_list,
        notifications=user_notifications
    )


# -------------------- MESSAGE SYSTEM --------------------
@student_bp.route('/messages')
def messages():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    db = get_db()
    cursor = db.cursor()

    # Inbox messages
    cursor.execute("""
        SELECT Subject, Body, SentAt, IsRead, MessageID
        FROM Messages
        WHERE ReceiverID = ? AND ReceiverType = 'Student'
        AND (IsDeleted = 0 OR IsDeleted IS NULL)
        AND (IsArchived = 0 OR IsArchived IS NULL)
        ORDER BY SentAt DESC
    """, (user_id,))
    msgs = cursor.fetchall()

    # Faculty list based on enrolled courses
    cursor.execute("""
        SELECT DISTINCT uf.user_id, f.Name
        FROM Faculty f
        JOIN Users uf ON f.Email = uf.Email
        JOIN Courses c ON f.FacultyID = c.FacultyID
        JOIN Enrollments e ON c.CourseID = e.CourseID
        JOIN Students s ON e.StudentID = s.StudentID
        JOIN Users us ON s.Name = us.name
        WHERE us.user_id = ?
    """, (user_id,))
    enrolled_faculty = cursor.fetchall()

    return render_template(
        'student/messages.html',
        messages=msgs,
        faculty_list=enrolled_faculty
    )


@student_bp.route('/archived_messages')
def archived_messages():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT Subject, Body, SentAt, IsRead, MessageID
        FROM Messages
        WHERE ReceiverID = ? AND ReceiverType = 'Student' AND IsArchived = 1
        AND (IsDeleted = 0 OR IsDeleted IS NULL)
        ORDER BY SentAt DESC
    """, (session['user_id'],))
    return render_template('student/archived_messages.html', messages=cursor.fetchall())


@student_bp.route('/trash_messages')
def trash_messages():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT Subject, Body, SentAt, IsRead, MessageID
        FROM Messages
        WHERE ReceiverID = ? AND ReceiverType = 'Student' AND IsDeleted = 1
        ORDER BY SentAt DESC
    """, (session['user_id'],))
    return render_template('student/trash_messages.html', messages=cursor.fetchall())


@student_bp.route('/send_message', methods=['POST'])
def send_message():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    db = get_db()
    cursor = db.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    receiver_id = request.form.get('receiver_id')
    subject = request.form.get('subject')
    body = request.form.get('body')

    cursor.execute("""
        INSERT INTO Messages (SenderID, ReceiverID, Subject, Body, ReceiverType, IsRead, SentAt)
        VALUES (?, ?, ?, ?, 'Faculty', 0, ?)
    """, (session['user_id'], receiver_id, subject, body, now))
    db.commit()
    flash('Message sent to faculty successfully.', 'success')
    return redirect(url_for('student.messages'))


# -------------------- NOTIFICATIONS --------------------
@student_bp.route('/notifications')
def notifications():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT Message, CreatedAt, IsRead
        FROM Notifications
        WHERE user_id = ?
        ORDER BY CreatedAt DESC
    """, (session['user_id'],))
    notifs = cursor.fetchall()
    cursor.execute("UPDATE Notifications SET IsRead = 1 WHERE user_id = ?", (session['user_id'],))
    db.commit()
    return render_template('student/notifications.html', notifications=notifs)


# -------------------- UTILITIES --------------------
@student_bp.route('/delete_message/<int:msg_id>')
def delete_message(msg_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        UPDATE Messages SET IsDeleted = 1
        WHERE MessageID = ? AND ReceiverID = ?
    """, (msg_id, session['user_id']))
    db.commit()
    return redirect(url_for('student.messages'))


@student_bp.route('/archive_message/<int:msg_id>')
def archive_message(msg_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        UPDATE Messages SET IsArchived = 1
        WHERE MessageID = ? AND ReceiverID = ?
    """, (msg_id, session['user_id']))
    db.commit()
    return redirect(url_for('student.messages'))


@student_bp.route('/restore_message/<int:msg_id>')
def restore_message(msg_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        UPDATE Messages SET IsArchived = 0, IsDeleted = 0
        WHERE MessageID = ? AND ReceiverID = ?
    """, (msg_id, session['user_id']))
    db.commit()
    return redirect(url_for('student.messages'))


@student_bp.context_processor
def inject_student_counts():
    if 'user_id' not in session:
        return dict(unread_count=0, unread_msg_count=0)

    db = get_db()
    cursor = db.cursor()
    user_id = session['user_id']

    cursor.execute("SELECT COUNT(*) FROM Notifications WHERE user_id = ? AND IsRead = 0", (user_id,))
    unread_notifications = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM Messages
        WHERE ReceiverID = ? AND ReceiverType = 'Student' AND IsRead = 0
    """, (user_id,))
    unread_messages = cursor.fetchone()[0]

    return dict(unread_count=unread_notifications, unread_msg_count=unread_messages)


# -------------------- COURSES & GRADES --------------------
@student_bp.route('/grades')
def grades():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT c.CourseName, c.CourseCode, e.Grade, e.EnrollmentDate
        FROM Enrollments e
        JOIN Courses c ON e.CourseID = c.CourseID
        JOIN Students s ON e.StudentID = s.StudentID
        JOIN Users u ON s.Name = u.name
        WHERE u.user_id = ?
    """, (session['user_id'],))
    return render_template('student/grades.html', grades=cursor.fetchall())


@student_bp.route('/courses')
def courses():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT c.CourseName, c.CourseCode, f.Name, c.Description, c.Credits, c.Room, c.CourseID
        FROM Courses c
        JOIN Enrollments e ON c.CourseID = e.CourseID
        JOIN Students s ON e.StudentID = s.StudentID
        JOIN Users u ON s.Name = u.name
        LEFT JOIN Faculty f ON c.FacultyID = f.FacultyID
        WHERE u.user_id = ?
    """, (session['user_id'],))
    return render_template('student/courses.html', courses=cursor.fetchall())


@student_bp.route('/mark_as_read/<int:msg_id>')
def mark_as_read(msg_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        UPDATE Messages
        SET IsRead = 1
        WHERE MessageID = ? AND ReceiverID = ? AND ReceiverType = 'Student'
    """, (msg_id, session['user_id']))
    db.commit()
    return redirect(url_for('student.messages'))


# ---------- COURSE DETAIL ----------
@student_bp.route('/course_detail/<int:course_id>')
def course_detail(course_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("SELECT s.StudentID FROM Students s JOIN Users u ON s.Name = u.name WHERE u.user_id = ?", (session['user_id'],))
        student_id = cursor.fetchone()[0]

        cursor.execute("SELECT CourseName, CourseCode, Room FROM Courses WHERE CourseID = ?", (course_id,))
        course_info = cursor.fetchone()

        cursor.execute("SELECT AssignmentID, Title, Description FROM Assignments WHERE CourseID = ?", (course_id,))
        assignments = cursor.fetchall()

        cursor.execute("SELECT AssignmentID FROM Submissions WHERE StudentID = ?", (student_id,))
        submitted_ids = [row[0] for row in cursor.fetchall()]

        cursor.execute("SELECT Status, AttendanceDate FROM Attendance WHERE CourseID = ? AND StudentID = ?", (course_id, student_id))
        attendance = cursor.fetchall()

        return render_template('student/course_view.html',
                               course=course_info,
                               assignments=assignments,
                               attendance=attendance,
                               submitted_ids=submitted_ids,
                               course_id=course_id)
    except Exception as e:
        return f"Error: {str(e)}"


@student_bp.route('/submit_assignment/<int:assignment_id>', methods=['POST'])
def submit_assignment(assignment_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    file = request.files.get('file')
    if not file or file.filename == '':
        flash('No file selected!', 'danger')
        return redirect(request.referrer)

    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("SELECT StudentID FROM Students s JOIN Users u ON s.Name = u.name WHERE u.user_id = ?", (session['user_id'],))
        student_id = cursor.fetchone()[0]

        filename = file.filename
        upload_path = os.path.join(current_app.root_path, 'static', 'uploads', filename)
        os.makedirs(os.path.dirname(upload_path), exist_ok=True)
        file.save(upload_path)

        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("""
            INSERT INTO Submissions (AssignmentID, StudentID, FilePath, SubmissionDate)
            VALUES (?, ?, ?, ?)
        """, (assignment_id, student_id, filename, now))
        db.commit()
        flash('Assignment submitted successfully!', 'success')
    except Exception as e:
        db.rollback()
        flash(f'Submission failed: {str(e)}', 'danger')
    return redirect(request.referrer)


# ---------- ENROLLMENT ----------
@student_bp.route('/enrollment')
def enrollment():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT CourseID, CourseCode, CourseName, Credits FROM Courses WHERE Status = 'active'")
    live_courses = cursor.fetchall()
    return render_template('student/enrollment.html', courses=live_courses)


@student_bp.route('/enroll/<int:course_id>', methods=['POST'])
def enroll_in_course(course_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user_id = session.get('user_id')
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("SELECT s.StudentID FROM Students s JOIN Users u ON s.Name = u.name WHERE u.user_id = ?", (user_id,))
        student = cursor.fetchone()
        if not student:
            flash("Student profile not found!", "danger")
            return redirect(url_for('student.enrollment'))
        student_id = student[0]

        cursor.execute("SELECT * FROM Enrollments WHERE StudentID = ? AND CourseID = ?", (student_id, course_id))
        if cursor.fetchone():
            flash("You are already enrolled in this course!", "warning")
            return redirect(url_for('student.enrollment'))

        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("INSERT INTO Enrollments (StudentID, CourseID, EnrollmentDate) VALUES (?, ?, ?)", (student_id, course_id, now))
        db.commit()
        flash("Successfully enrolled!", "success")
    except Exception as e:
        db.rollback()
        print(f"!!! DATABASE ERROR: {e}")
        flash(f"Enrollment failed: {str(e)}", "danger")
    return redirect(url_for('student.enrollment'))


@student_bp.route('/drop_course/<int:course_id>', methods=['POST'])
def drop_course(course_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("SELECT StudentID FROM Students s JOIN Users u ON s.Name = u.name WHERE u.user_id = ?", (session['user_id'],))
        student = cursor.fetchone()
        if student:
            student_id = student[0]
            cursor.execute("DELETE FROM Enrollments WHERE CourseID = ? AND StudentID = ?", (course_id, student_id))
            db.commit()
            flash("Course successfully dropped!", "success")
        else:
            flash("Error: Student record not found.", "danger")
    except Exception as e:
        db.rollback()
        print(f"Drop Error: {e}")
        flash(f"Error dropping course: {str(e)}", "danger")
    return redirect(url_for('student.enrollment'))
