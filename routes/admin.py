from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database import query, query_one, execute, insert

bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required():
    return session.get('role') == 'admin'


@bp.route('/users')
def users():
    if not admin_required():
        flash('Acceso restringido a administradores.', 'danger')
        return redirect(url_for('dashboard.index'))
    all_users = query("SELECT * FROM users ORDER BY id")
    return render_template('admin/users.html', users=all_users)


@bp.route('/users/add', methods=['POST'])
def add_user():
    if not admin_required():
        return redirect(url_for('dashboard.index'))
    f = request.form
    username = f.get('username', '').strip().lower()
    password = f.get('password', '').strip()
    full_name = f.get('full_name', '').strip()
    role = f.get('role', 'technician')

    if not all([username, password, full_name]):
        flash('Todos los campos son obligatorios.', 'danger')
        return redirect(url_for('admin.users'))
    existing = query_one("SELECT id FROM users WHERE username=?", [username])
    if existing:
        flash(f'El usuario "{username}" ya existe.', 'danger')
        return redirect(url_for('admin.users'))

    insert("INSERT INTO users (username, password, full_name, role) VALUES (?,?,?,?)",
           [username, password, full_name, role])
    flash(f'Usuario "{full_name}" creado correctamente.', 'success')
    return redirect(url_for('admin.users'))


@bp.route('/users/<int:user_id>/edit', methods=['POST'])
def edit_user(user_id):
    if not admin_required():
        return redirect(url_for('dashboard.index'))
    f = request.form
    full_name = f.get('full_name', '').strip()
    role = f.get('role', 'technician')
    new_password = f.get('password', '').strip()

    if new_password:
        execute("UPDATE users SET full_name=?, role=?, password=? WHERE id=?",
                [full_name, role, new_password, user_id])
    else:
        execute("UPDATE users SET full_name=?, role=? WHERE id=?",
                [full_name, role, user_id])
    flash('Usuario actualizado.', 'success')
    return redirect(url_for('admin.users'))


@bp.route('/users/<int:user_id>/toggle', methods=['POST'])
def toggle_user(user_id):
    if not admin_required():
        return redirect(url_for('dashboard.index'))
    if user_id == session.get('user_id'):
        flash('No puedes desactivar tu propia cuenta.', 'danger')
        return redirect(url_for('admin.users'))
    execute("UPDATE users SET active = 1 - active WHERE id=?", [user_id])
    return redirect(url_for('admin.users'))


@bp.route('/users/<int:user_id>/delete', methods=['POST'])
def delete_user(user_id):
    if not admin_required():
        return redirect(url_for('dashboard.index'))
    if user_id == session.get('user_id'):
        flash('No puedes eliminar tu propia cuenta.', 'danger')
        return redirect(url_for('admin.users'))
    execute("DELETE FROM users WHERE id=?", [user_id])
    flash('Usuario eliminado.', 'success')
    return redirect(url_for('admin.users'))
