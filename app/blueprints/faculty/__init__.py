from flask import Blueprint

# Blueprint define kar rahe hain
faculty_bp = Blueprint('faculty', __name__, template_folder='templates')

from . import routes