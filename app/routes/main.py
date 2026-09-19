from flask import Blueprint, render_template

bp = Blueprint('main', __name__)

@bp.route('/')
def dashboard():
    return render_template('dashboard.html')

@bp.route('/create-lesson')
def create_lesson():
    return render_template('create_lesson.html')

@bp.route('/lesson/result')
def lesson_result():
    # The lesson plan will be loaded from session storage by JavaScript
    return render_template('lesson_result.html')