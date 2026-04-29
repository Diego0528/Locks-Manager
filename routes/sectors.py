from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from database import query, query_one, execute, insert

bp = Blueprint('sectors', __name__, url_prefix='/sectors')


@bp.route('/')
def index():
    sectors = query("""
        SELECT s.id, s.code, s.name, s.description, s.active,
               COUNT(DISTINCT l.id) AS lock_count,
               STRING_AGG(CAST(sq.quarter AS NVARCHAR), ', ')
                   WITHIN GROUP (ORDER BY sq.quarter) AS quarters
        FROM sectors s
        LEFT JOIN locks l ON l.sector_id = s.id AND l.active=1
        LEFT JOIN sector_quarters sq ON sq.sector_id = s.id AND sq.active=1
        GROUP BY s.id, s.code, s.name, s.description, s.active
        ORDER BY s.code
    """)
    return render_template('sectors/index.html', sectors=sectors)


@bp.route('/add', methods=['POST'])
def add():
    f = request.form
    code = f['code'].strip().upper()
    if query_one("SELECT id FROM sectors WHERE code=?", [code]):
        flash('Ya existe un sector con ese código.', 'danger')
        return redirect(url_for('sectors.index'))

    sid = insert(
        "INSERT INTO sectors (code, name, description) VALUES (?,?,?)",
        [code, f['name'].strip(), f.get('description') or None]
    )

    quarters = f.getlist('quarters')
    for q in quarters:
        insert("INSERT INTO sector_quarters (sector_id, quarter) VALUES (?,?)", [sid, int(q)])

    flash(f'Sector {code} agregado.', 'success')
    return redirect(url_for('sectors.index'))


@bp.route('/<int:sid>/edit', methods=['POST'])
def edit(sid):
    f = request.form
    execute(
        "UPDATE sectors SET name=?, description=? WHERE id=?",
        [f['name'].strip(), f.get('description') or None, sid]
    )

    # Update quarters
    execute("UPDATE sector_quarters SET active=0 WHERE sector_id=?", [sid])
    quarters = f.getlist('quarters')
    for q in quarters:
        existing = query_one(
            "SELECT id FROM sector_quarters WHERE sector_id=? AND quarter=?", [sid, int(q)]
        )
        if existing:
            execute("UPDATE sector_quarters SET active=1 WHERE id=?", [existing['id']])
        else:
            insert("INSERT INTO sector_quarters (sector_id, quarter) VALUES (?,?)", [sid, int(q)])

    flash('Sector actualizado.', 'success')
    return redirect(url_for('sectors.index'))


@bp.route('/<int:sid>/toggle', methods=['POST'])
def toggle(sid):
    s = query_one("SELECT active FROM sectors WHERE id=?", [sid])
    if s:
        execute("UPDATE sectors SET active=? WHERE id=?", [0 if s['active'] else 1, sid])
    flash('Estado de sector actualizado.', 'success')
    return redirect(url_for('sectors.index'))


@bp.route('/api/list')
def api_list():
    sectors = query("SELECT id, code, name FROM sectors WHERE active=1 ORDER BY code")
    return jsonify(sectors)
