from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash
from app.database import get_db

auth_bp = Blueprint('auth', __name__)

# ---------------------------------------------------
# USER LOGIN
# ---------------------------------------------------
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Redirect logged-in users based on role
    if 'user_id' in session:
        role = session.get('role')
        if role == 'Admin':
            return redirect(url_for('admin.dashboard'))
        elif role == 'Faculty':
            return redirect(url_for('faculty.dashboard'))
        elif role == 'Student':
            return redirect(url_for('student.dashboard'))

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        db = get_db()
        cursor = db.cursor()

        cursor.execute("""
            SELECT user_id, name, password, role
            FROM Users
            WHERE email = ?
        """, (email,))
        user = cursor.fetchone()

        if user:
            user_id, name, db_password, role = user

            if isinstance(db_password, str):
                db_password = db_password.strip()

            password_match = False

            # Check hashed password
            try:
                if check_password_hash(db_password, password):
                    password_match = True
            except:
                pass

            # Fallback check for plain-text passwords
            if not password_match and db_password == password:
                password_match = True

            if password_match:
                session['user_id'] = user_id
                session['name'] = name
                session['role'] = role

                flash(f"Welcome back, {name}!", "success")

                if role == 'Admin':
                    return redirect(url_for('admin.dashboard'))
                elif role == 'Faculty':
                    return redirect(url_for('faculty.dashboard'))
                elif role == 'Student':
                    return redirect(url_for('student.dashboard'))
                else:
                    return redirect(url_for('student.dashboard'))
            else:
                flash("Incorrect password.", "danger")
        else:
            flash("Email not found.", "danger")

    return render_template('auth/login.html')


# ---------------------------------------------------
# USER LOGOUT
# ---------------------------------------------------
@auth_bp.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('auth.login'))
