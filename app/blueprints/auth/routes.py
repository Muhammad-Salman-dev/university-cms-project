from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.database import get_db

auth_bp = Blueprint('auth', __name__)

# --- LOGIN ROUTE ---
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        db = get_db()
        cursor = db.cursor()

        # ---------------------------------------------------------
        # CHECK 1: Kya user 'Users' table (Admin/Student) mein hai?
        # ---------------------------------------------------------
        cursor.execute("SELECT user_id, name, password, role FROM Users WHERE email = ?", (email,))
        user = cursor.fetchone()

        if user:
            # user[2] password hai
            if user[2] == password:
                session['user_id'] = user[0]
                session['name'] = user[1]
                session['role'] = user[3] # Role DB se aayega (Admin/Student)

                flash('Login Successful!', 'success')

                if user[3] == 'Admin':
                    return redirect(url_for('admin.dashboard'))
                elif user[3] == 'Student':
                    return redirect(url_for('student.dashboard'))
            else:
                flash('Invalid Password', 'danger')
                return render_template('auth/login.html')

        # ---------------------------------------------------------
        # CHECK 2: Agar Users mein nahi mila, to 'Faculty' table check karo
        # ---------------------------------------------------------
        else:
            # Faculty table: FacultyID, Name, Email, Department, Designation, Password
            cursor.execute("SELECT FacultyID, Name, Password FROM Faculty WHERE Email = ?", (email,))
            teacher = cursor.fetchone()

            if teacher:
                # teacher[2] password hai
                if teacher[2] == password:
                    session['user_id'] = teacher[0]
                    session['name'] = teacher[1]
                    session['role'] = 'faculty'  # Hum manually role set kar rahe hain

                    flash('Welcome Faculty!', 'success')
                    return redirect(url_for('faculty.dashboard'))
                else:
                    flash('Invalid Password', 'danger')
            else:
                # Na Users mein mila, na Faculty mein
                flash('User not found. Please check your email.', 'danger')

    return render_template('auth/login.html')

# --- LOGOUT ROUTE ---
@auth_bp.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('auth.login'))