from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash
from app.database import get_db

auth_bp = Blueprint('auth', __name__)
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        role = session.get('role')
        if role == 'Admin': return redirect(url_for('admin.dashboard'))
        elif role == 'Faculty': return redirect(url_for('faculty.dashboard'))
        elif role == 'Student': return redirect(url_for('student.dashboard'))

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        db = get_db()
        cursor = db.cursor()

        cursor.execute("SELECT user_id, name, password, role FROM Users WHERE email = ?", (email,))
        user = cursor.fetchone()

        if user:
            user_id = user[0]
            name = user[1]
            db_password = user[2]
            role = user[3]
            
            if isinstance(db_password, str):
                db_password = db_password.strip()

            print(f"🔍 DEBUG CHECK:")
            print(f"   -> DB Password: '{db_password}'")
            print(f"   -> Input Pass : '{password}'")

            # Password Check Logic
            password_match = False
            try:
                if check_password_hash(db_password, password):
                    password_match = True
            except:
                pass

            # Fallback for plain text
            if not password_match and db_password == password:
                password_match = True

            if password_match:
                session['user_id'] = user_id
                session['name'] = name
                session['role'] = role
                flash(f"Welcome back, {name}!", "success")

                if role == 'Admin': return redirect(url_for('admin.dashboard'))
                elif role == 'Faculty': return redirect(url_for('faculty.dashboard'))
                elif role == 'Student': return redirect(url_for('main.home'))
                else: return redirect(url_for('main.home'))
            else:
                flash("❌ Incorrect Password", "danger")
        else:
            flash("❌ Email not found", "danger")

    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('auth.login'))