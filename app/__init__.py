from flask import Flask
from config import Config
from app import database

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize Database
    database.init_app(app)

    # --- Register Blueprints ---
    # Importing inside the function to avoid circular import issues
    from app.blueprints.auth.routes import auth_bp
    from app.blueprints.admin.routes import admin_bp
    from app.blueprints.faculty.routes import faculty_bp


    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(faculty_bp, url_prefix='/faculty')

    # Root Route
    @app.route('/')
    def home():
        return "<h1>Go to <a href='/auth/login'>/auth/login</a> to sign in.</h1>"

    return app