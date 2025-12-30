import os
from flask import (
    render_template, session, redirect, url_for,
    request, flash, current_app
)
from datetime import datetime
from . import student_bp
from app.database import get_db


# -------------------- DASHBOARD --------------------

@student_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session.get('role') != 'Student':
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    db = get_db()
    cursor = db.cursor()

    # Student basic info
    cursor.execute("""
        SELECT s.StudentID, s.Name
        FROM Students s
        JOIN Users u ON s.Name = u.name
        WHERE u.user_id = ?
    """, (user_id,))
    student = cursor.fetchone()
    student_id = student[0] if student else None

    # Enrolled courses count
    cursor.execute(
        "SELECT COUNT(*) FROM Enrollments WHERE StudentID = ?",
        (student_id,)
    )
    courses_count = cursor.fetchone()[0]

    # GPA calculation
    cursor.execute(
        "SELECT Grade FROM Enrollments WHERE StudentID = ?",
        (student_id,)
    )
    grades = cursor.fetchall()

    total_points = 0
    valid_count = 0
    for grade in grades:
        if grade[0]:
            valid_count += 1
            if grade[0] == 'A':
                total_points += 4.0
            elif grade[0] == 'B':
                total_points += 3.0
            else:
                total_points += 2.0

    gpa = round(total_points / valid_count, 2) if valid_count else 0.0

    # Notifications
    cursor.execute("""
        SELECT Message, CreatedAt, IsRead
        FROM Notifications
        WHERE user_id = ?
        ORDER BY CreatedAt DESC
    """, (user_id,))
    notifications = cursor.fetchall()

    # Unread messages count
    cursor.execute("""
        SELECT COUNT(*)
        FROM Messages
        WHERE ReceiverID = ?
        AND ReceiverType = 'Student'
        AND IsRead = 0
    """, (user_id,))
    unread_messages = cursor.fetchone()[0]

    announcements = [
        {'title': 'Notification', 'body': n[0], 'time': n[1]}
        for n in notifications[:3]
    ]

    stats = {
        'enrolled_courses': courses_count,
        'assignments_due': 0,
        'gpa': gpa,
        'unread_messages': unread_messages
    }

    return render_template(
        'student/dashboard.html',
        stats=stats,
        announcements=announcements,
        notifications=notifications
    )


# -------------------- MESSAGES --------------------

@student_bp.route('/messages')
def messages():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT Subject, Body, SentAt, IsRead, MessageID
        FROM Messages
        WHERE ReceiverID = ?
        AND ReceiverType = 'Student'
        AND (IsDeleted = 0 OR IsDeleted IS NULL)
        AND (IsArchived = 0 OR IsArchived IS NULL)
        ORDER BY SentAt DESC
    """, (user_id,))
    messages = cursor.fetchall()

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
    faculty_list = cursor.fetchall()

    return render_template(
        'student/messages.html',
        messages=messages,
        faculty_list=faculty_list
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
        WHERE ReceiverID = ?
        AND ReceiverType = 'Student'
        AND IsArchived = 1
        AND (IsDeleted = 0 OR IsDeleted IS NULL)
        ORDER BY SentAt DESC
    """, (session['user_id'],))

    return render_template(
        'student/archived_messages.html',
        messages=cursor.fetchall()
    )


@student_bp.route('/trash_messages')
def trash_messages():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT Subject, Body, SentAt, IsRead, MessageID
        FROM Messages
        WHERE ReceiverID = ?
        AND ReceiverType = 'Student'
        AND IsDeleted = 1
        ORDER BY SentAt DESC
    """, (session['user_id'],))

    return render_template(
        'student/trash_messages.html',
        messages=cursor.fetchall()
    )


@student_bp.route('/send_message', methods=['POST'])
def send_message():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        INSERT INTO Messages
        (SenderID, ReceiverID, Subject, Body, ReceiverType, IsRead, SentAt)
        VALUES (?, ?, ?, ?, 'Faculty', 0, ?)
    """, (
        session['user_id'],
        request.form.get('receiver_id'),
        request.form.get('subject'),
        request.form.get('body'),
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ))

    db.commit()
    flash('Message sent successfully.', 'success')
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

    notifications = cursor.fetchall()

    cursor.execute(
        "UPDATE Notifications SET IsRead = 1 WHERE user_id = ?",
        (session['user_id'],)
    )
    db.commit()

    return render_template(
        'student/notifications.html',
        notifications=notifications
    )


# -------------------- MESSAGE ACTIONS --------------------

@student_bp.route('/delete_message/<int:msg_id>')
def delete_message(msg_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        UPDATE Messages
        SET IsDeleted = 1
        WHERE MessageID = ? AND ReceiverID = ?
    """, (msg_id, session['user_id']))
    db.commit()
    return redirect(url_for('student.messages'))


@student_bp.route('/archive_message/<int:msg_id>')
def archive_message(msg_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        UPDATE Messages
        SET IsArchived = 1
        WHERE MessageID = ? AND ReceiverID = ?
    """, (msg_id, session['user_id']))
    db.commit()
    return redirect(url_for('student.messages'))


@student_bp.route('/restore_message/<int:msg_id>')
def restore_message(msg_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        UPDATE Messages
        SET IsArchived = 0, IsDeleted = 0
        WHERE MessageID = ? AND ReceiverID = ?
    """, (msg_id, session['user_id']))
    db.commit()
    return redirect(url_for('student.messages'))
