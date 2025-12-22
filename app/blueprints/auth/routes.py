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
        cursor.execute("SELECT user_id, name, password, role FROM Users WHERE email = ?", (email,))
        user = cursor.fetchone()

        # User check logic
        if user:
            # Note: Agar plain text password use kar rahe ho to 'if user[2] == password:' use karo
            # Agar hash use kar rahe ho to bcrypt check karo.
            # Filhal simple rakhne ke liye direct compare (assuming plain text for testing):
            if user[2] == password:
                session['user_id'] = user[0]
                session['name'] = user[1]
                session['role'] = user[3]

                flash('Login Successful!', 'success')

                # Role ke hisaab se redirect
                if user[3] == 'Admin':
                    return redirect(url_for('admin.dashboard'))
                elif user[3] == 'Student':
                    return redirect(url_for('student.dashboard'))
                elif user[3] == 'Faculty':
                    # Faculty dashboard abhi banaya nahi, filhal home bhej do
                    return redirect(url_for('auth.login'))
            else:
                flash('Invalid Password', 'error')
        else:
            flash('User not found', 'error')

    return render_template('auth/login.html')

# --- LOGOUT ROUTE (Ye Missing Tha!) ---
@auth_bp.route('/logout')
def logout():
    session.clear()  # Saara data saaf karo
    flash("You have been logged out.", "info")
    return redirect(url_for('auth.login'))