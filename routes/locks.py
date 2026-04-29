from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash
from database import query, query_one, execute, insert, calc_battery_pct, battery_color
from datetime import date

bp = Blueprint('locks', __name__, url_prefix='/locks')


@bp.route('/')
def index():
    sector_id = request.args.get('sector_id', '')
    status = request.args.get('status', '')
    search = request.args.get('search', '')

    where = ['1=1']
    params = []

    if sector_id:
        where.append('l.sector_id = ?')
        params.append(sector_id)
    if status == 'active':
        where.append('l.active = 1')
    elif status == 'inactive':
        where.append('l.active = 0')
    if search:
        where.append("(l.room_code LIKE ? OR l.room_name LIKE ?)")
        params += [f'%{search}%', f'%{search}%']

    locks = query(f"""
        SELECT l.id, l.room_code, l.room_name, l.active, l.model,
               l.installation_date, l.serial_number,
               s.name AS sector_name, s.code AS sector_code,
               (SELECT TOP 1 percentage FROM battery_readings WHERE lock_id=l.id ORDER BY reading_date DESC) AS last_battery_pct,
               (SELECT TOP 1 voltage FROM battery_readings WHERE lock_id=l.id ORDER BY reading_date DESC) AS last_voltage,
               (SELECT TOP 1 reading_date FROM battery_readings WHERE lock_id=l.id ORDER BY reading_date DESC) AS last_battery_date,
               (SELECT COUNT(*) FROM lock_events WHERE lock_id=l.id AND resolved=0) AS open_events,
               (SELECT TOP 1 maintenance_date FROM maintenance_records WHERE lock_id=l.id ORDER BY maintenance_date DESC) AS last_maint
        FROM locks l
        JOIN sectors s ON s.id = l.sector_id
        WHERE {' AND '.join(where)}
        ORDER BY s.code, l.room_code
    """, params)

    for lk in locks:
        pct = lk.get('last_battery_pct')
        lk['battery_color'] = battery_color(pct) if pct is not None else 'muted'

    sectors = query("SELECT id, name FROM sectors WHERE active=1 ORDER BY code")
    return render_template('locks/index.html', locks=locks, sectors=sectors,
                           current_sector=sector_id, current_status=status, search=search)


@bp.route('/<int:lock_id>')
def detail(lock_id):
    lk = query_one("""
        SELECT l.*, s.name AS sector_name, s.code AS sector_code
        FROM locks l JOIN sectors s ON s.id = l.sector_id
        WHERE l.id = ?
    """, [lock_id])

    if not lk:
        flash('Cerradura no encontrada', 'danger')
        return redirect(url_for('locks.index'))

    battery_history = query("""
        SELECT id, reading_date, technician, voltage, percentage,
               batteries_changed, notes
        FROM battery_readings
        WHERE lock_id = ?
        ORDER BY reading_date DESC
    """, [lock_id])

    for b in battery_history:
        b['color'] = battery_color(b['percentage'])

    maintenance_history = query("""
        SELECT id, maintenance_date, maintenance_time, technician, supervisor,
               maintenance_type, quarter, year, status, annotations
        FROM maintenance_records
        WHERE lock_id = ?
        ORDER BY maintenance_date DESC
    """, [lock_id])

    clock_history = query("""
        SELECT id, config_date, technician, notes
        FROM clock_configs WHERE lock_id = ?
        ORDER BY config_date DESC
    """, [lock_id])

    events = query("""
        SELECT id, event_date, event_type, description, resolved, resolved_date
        FROM lock_events WHERE lock_id = ?
        ORDER BY event_date DESC
    """, [lock_id])

    last_battery = battery_history[0] if battery_history else None
    lk['battery_color'] = battery_color(last_battery['percentage']) if last_battery else 'muted'

    return render_template('locks/detail.html',
                           lock=lk,
                           battery_history=battery_history,
                           maintenance_history=maintenance_history,
                           clock_history=clock_history,
                           events=events,
                           last_battery=last_battery)


@bp.route('/add', methods=['GET', 'POST'])
def add():
    sectors = query("SELECT id, code, name FROM sectors WHERE active=1 ORDER BY code")
    if request.method == 'POST':
        f = request.form
        sid = f['sector_id']
        room_code = f['room_code'].strip().upper()
        existing = query_one(
            "SELECT id FROM locks WHERE sector_id=? AND room_code=?", [sid, room_code]
        )
        if existing:
            flash(f'Ya existe una cerradura con código {room_code} en ese sector.', 'danger')
            return render_template('locks/add.html', sectors=sectors, form=f)

        lid = insert("""
            INSERT INTO locks (sector_id, room_code, room_name, installation_date,
                               model, serial_number, notes)
            VALUES (?,?,?,?,?,?,?)
        """, [sid,
              room_code,
              f.get('room_name') or None,
              f.get('installation_date') or None,
              f.get('model') or '790',
              f.get('serial_number') or None,
              f.get('notes') or None])
        flash('Cerradura agregada correctamente.', 'success')
        return redirect(url_for('locks.detail', lock_id=lid))

    return render_template('locks/add.html', sectors=sectors, form={})


@bp.route('/<int:lock_id>/edit', methods=['GET', 'POST'])
def edit(lock_id):
    lk = query_one("SELECT * FROM locks WHERE id=?", [lock_id])
    if not lk:
        return redirect(url_for('locks.index'))

    sectors = query("SELECT id, code, name FROM sectors WHERE active=1 ORDER BY code")

    if request.method == 'POST':
        f = request.form
        execute("""
            UPDATE locks SET sector_id=?, room_code=?, room_name=?,
                installation_date=?, model=?, serial_number=?, notes=?,
                last_clock_config=?
            WHERE id=?
        """, [f['sector_id'],
              f['room_code'].strip().upper(),
              f.get('room_name') or None,
              f.get('installation_date') or None,
              f.get('model') or '790',
              f.get('serial_number') or None,
              f.get('notes') or None,
              f.get('last_clock_config') or None,
              lock_id])
        flash('Cerradura actualizada.', 'success')
        return redirect(url_for('locks.detail', lock_id=lock_id))

    return render_template('locks/edit.html', lock=lk, sectors=sectors)


@bp.route('/<int:lock_id>/toggle', methods=['POST'])
def toggle(lock_id):
    lk = query_one("SELECT active FROM locks WHERE id=?", [lock_id])
    if lk:
        new_val = 0 if lk['active'] else 1
        execute("UPDATE locks SET active=? WHERE id=?", [new_val, lock_id])
        flash('Estado de cerradura actualizado.', 'success')
    return redirect(url_for('locks.detail', lock_id=lock_id))


@bp.route('/<int:lock_id>/event', methods=['POST'])
def add_event(lock_id):
    f = request.form
    insert("""
        INSERT INTO lock_events (lock_id, event_date, event_type, description)
        VALUES (?,?,?,?)
    """, [lock_id, f['event_date'], f['event_type'], f.get('description') or None])
    flash('Evento registrado.', 'success')
    return redirect(url_for('locks.detail', lock_id=lock_id))


@bp.route('/event/<int:event_id>/resolve', methods=['POST'])
def resolve_event(event_id):
    ev = query_one("SELECT lock_id FROM lock_events WHERE id=?", [event_id])
    execute(
        "UPDATE lock_events SET resolved=1, resolved_date=? WHERE id=?",
        [date.today().isoformat(), event_id]
    )
    flash('Evento marcado como resuelto.', 'success')
    if ev:
        return redirect(url_for('locks.detail', lock_id=ev['lock_id']))
    return redirect(url_for('locks.index'))


@bp.route('/<int:lock_id>/clock-config', methods=['POST'])
def add_clock_config(lock_id):
    f = request.form
    insert("""
        INSERT INTO clock_configs (lock_id, config_date, technician, notes)
        VALUES (?,?,?,?)
    """, [lock_id, f['config_date'], f.get('technician') or None, f.get('notes') or None])
    execute(
        "UPDATE locks SET last_clock_config=? WHERE id=?",
        [f['config_date'], lock_id]
    )
    flash('Configuración de reloj registrada.', 'success')
    return redirect(url_for('locks.detail', lock_id=lock_id))


@bp.route('/api/list')
def api_list():
    sector_id = request.args.get('sector_id', '')
    locks = query(
        "SELECT id, room_code, room_name FROM locks WHERE active=1"
        + (" AND sector_id=?" if sector_id else "")
        + " ORDER BY room_code",
        [sector_id] if sector_id else []
    )
    return jsonify(locks)
