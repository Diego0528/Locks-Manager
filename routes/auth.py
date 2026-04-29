from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash

bp = Blueprint('auth', __name__)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated


@bp.route('/login', methods=['GET', 'POST'])
def login():
    from database import query_one
    if 'user' in session:
        return redirect(url_for('dashboard.index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')
        user = query_one(
            "SELECT * FROM users WHERE username=? AND active=1", [username]
        )
        if user and user['password'] == password:
            session.permanent = True
            session['user'] = username
            session['full_name'] = user['full_name']
            session['role'] = user['role']
            session['user_id'] = user['id']
            next_url = request.args.get('next') or url_for('dashboard.index')
            return redirect(next_url)
        flash('Usuario o contraseña incorrectos.', 'danger')
    return render_template('auth/login.html')


@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
