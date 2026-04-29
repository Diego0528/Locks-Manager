from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from database import query, query_one, execute, insert, calc_battery_pct
from config import Config
from datetime import date, datetime

bp = Blueprint('maintenance', __name__, url_prefix='/maintenance')


def current_quarter():
    m = date.today().month
    return (m - 1) // 3 + 1


@bp.route('/')
def index():
    q = int(request.args.get('quarter', current_quarter()))
    yr = int(request.args.get('year', date.today().year))
    sector_id = request.args.get('sector_id', '')

    # Locks scheduled for this quarter
    where_extra = " AND l.sector_id = ?" if sector_id else ""
    params = [q] + ([sector_id] if sector_id else [])

    scheduled = query(f"""
        SELECT l.id AS lock_id, l.room_code, l.room_name, l.active,
               s.name AS sector_name, s.code AS sector_code,
               mr.id AS maint_id, mr.maintenance_date, mr.technician,
               mr.supervisor, mr.status, mr.annotations, mr.maintenance_type
        FROM locks l
        JOIN sectors s ON s.id = l.sector_id
        JOIN sector_quarters sq ON sq.sector_id = l.sector_id AND sq.quarter = ? AND sq.active=1
        LEFT JOIN maintenance_records mr ON mr.lock_id = l.id
            AND mr.quarter = ? AND mr.year = ?
        WHERE l.active = 1 {where_extra}
        ORDER BY s.code, l.room_code
    """, [q, q, yr] + ([sector_id] if sector_id else []))

    total = len(scheduled)
    done = sum(1 for r in scheduled if r['status'] == 'Realizado')
    pending = total - done

    sectors = query("SELECT id, name FROM sectors WHERE active=1 ORDER BY code")
    years = list(range(date.today().year - 2, date.today().year + 2))

    # Progreso por sector para la gráfica
    sector_prog = query("""
        SELECT s.code AS sector_code, s.name AS sector_name,
               COUNT(l.id) AS total,
               SUM(CASE WHEN mr.status='Realizado' THEN 1 ELSE 0 END) AS done
        FROM locks l
        JOIN sectors s ON s.id = l.sector_id
        JOIN sector_quarters sq ON sq.sector_id=l.sector_id AND sq.quarter=? AND sq.active=1
        LEFT JOIN maintenance_records mr ON mr.lock_id=l.id AND mr.quarter=? AND mr.year=?
        WHERE l.active=1
        GROUP BY s.id, s.code, s.name
        ORDER BY s.code
    """, [q, q, yr])

    return render_template('maintenance/index.html',
                           records=scheduled,
                           q=q, yr=yr,
                           total=total, done=done, pending=pending,
                           sectors=sectors,
                           sector_prog=sector_prog,
                           current_sector=sector_id,
                           years=years)


@bp.route('/form', methods=['GET', 'POST'])
def form():
    lock_id = request.args.get('lock_id') or request.form.get('lock_id')
    q = int(request.args.get('quarter', current_quarter()))
    yr = int(request.args.get('year', date.today().year))

    if request.method == 'POST':
        f = request.form
        lock_id = f['lock_id']
        q = int(f['quarter'])
        yr = int(f['year'])

        existing = query_one(
            "SELECT id FROM maintenance_records WHERE lock_id=? AND quarter=? AND year=?",
            [lock_id, q, yr]
        )

        data = [
            f['maintenance_date'],
            f.get('maintenance_time') or None,
            f.get('technician') or None,
            f.get('supervisor') or None,
            f.get('maintenance_type', 'Preventivo'),
            q, yr,
            f.get('status', 'Realizado'),
            f.get('annotations') or None,
        ]

        if existing:
            execute("""
                UPDATE maintenance_records SET
                    maintenance_date=?, maintenance_time=?, technician=?,
                    supervisor=?, maintenance_type=?, quarter=?, year=?,
                    status=?, annotations=?
                WHERE id=?
            """, data + [existing['id']])
            flash('Registro de mantenimiento actualizado.', 'success')
        else:
            insert("""
                INSERT INTO maintenance_records
                    (lock_id, maintenance_date, maintenance_time, technician,
                     supervisor, maintenance_type, quarter, year, status, annotations)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, [lock_id] + data)
            flash('Mantenimiento registrado correctamente.', 'success')

        # Si se proporcionó voltaje, guardar lectura de batería
        voltage_str = f.get('battery_voltage', '').strip()
        if voltage_str:
            try:
                voltage = float(voltage_str)
                pct = calc_battery_pct(voltage)
                changed = 1 if f.get('batteries_changed') else 0
                insert("""
                    INSERT INTO battery_readings
                        (lock_id, reading_date, technician, voltage, percentage,
                         batteries_changed, notes)
                    VALUES (?,?,?,?,?,?,?)
                """, [
                    lock_id,
                    f['maintenance_date'],
                    f.get('technician') or None,
                    voltage, pct, changed,
                    f'Registrado durante mantenimiento Q{q}/{yr}',
                ])
                flash(f'Batería registrada: {voltage}V → {pct}%.', 'success')
            except (ValueError, TypeError):
                pass

        return redirect(url_for('maintenance.index', quarter=q, year=yr))

    # GET
    lk = query_one("""
        SELECT l.*, s.name AS sector_name
        FROM locks l JOIN sectors s ON s.id=l.sector_id
        WHERE l.id=?
    """, [lock_id]) if lock_id else None

    existing = query_one(
        "SELECT * FROM maintenance_records WHERE lock_id=? AND quarter=? AND year=?",
        [lock_id, q, yr]
    ) if lock_id else None

    locks = query("""
        SELECT l.id, l.room_code, l.room_name, s.name AS sector_name
        FROM locks l JOIN sectors s ON s.id=l.sector_id
        WHERE l.active=1 ORDER BY s.code, l.room_code
    """)

    return render_template('maintenance/form.html',
                           lock=lk, locks=locks,
                           existing=existing,
                           q=q, yr=yr,
                           today=date.today().isoformat(),
                           current_time=datetime.now().strftime('%H:%M'),
                           default_supervisor=Config.DEFAULT_SUPERVISOR,
                           technician_default=session.get('full_name', ''))


@bp.route('/history')
def history():
    """Todos los registros sin filtro de sector_quarters — para auditoría."""
    yr = int(request.args.get('year', date.today().year))
    q = request.args.get('quarter', '')
    sector_id = request.args.get('sector_id', '')
    technician = request.args.get('technician', '').strip()
    status = request.args.get('status', '')

    where = ['1=1']
    params = []
    where.append('mr.year=?')
    params.append(yr)
    if q:
        where.append('mr.quarter=?')
        params.append(int(q))
    if sector_id:
        where.append('l.sector_id=?')
        params.append(sector_id)
    if technician:
        where.append('mr.technician LIKE ?')
        params.append(f'%{technician}%')
    if status:
        where.append('mr.status=?')
        params.append(status)

    records = query(f"""
        SELECT mr.id, mr.maintenance_date, mr.maintenance_time, mr.quarter, mr.year,
               mr.technician, mr.supervisor, mr.status, mr.annotations, mr.maintenance_type,
               l.room_code, l.room_name, l.id AS lock_id,
               s.name AS sector_name, s.code AS sector_code
        FROM maintenance_records mr
        JOIN locks l ON l.id = mr.lock_id
        JOIN sectors s ON s.id = l.sector_id
        WHERE {' AND '.join(where)}
        ORDER BY mr.maintenance_date DESC, s.code, l.room_code
    """, params)

    sectors = query("SELECT id, name FROM sectors WHERE active=1 ORDER BY code")
    years = list(range(date.today().year - 2, date.today().year + 2))
    technicians = query("""
        SELECT DISTINCT technician FROM maintenance_records
        WHERE technician IS NOT NULL ORDER BY technician
    """)

    return render_template('maintenance/history.html',
                           records=records,
                           sectors=sectors,
                           years=years,
                           technicians=technicians,
                           yr=yr, q=q,
                           current_sector=sector_id,
                           current_tech=technician,
                           current_status=status)


@bp.route('/<int:record_id>/delete', methods=['POST'])
def delete(record_id):
    rec = query_one("SELECT lock_id, quarter, year FROM maintenance_records WHERE id=?", [record_id])
    if not rec:
        flash('Registro no encontrado.', 'danger')
        return redirect(url_for('maintenance.index'))
    execute("DELETE FROM maintenance_records WHERE id=?", [record_id])
    flash('Registro de mantenimiento eliminado.', 'success')
    return redirect(url_for('locks.detail', lock_id=rec['lock_id']))


@bp.route('/bulk', methods=['POST'])
def bulk_save():
    """Save multiple maintenance records at once (from the index table)."""
    records = request.json.get('records', [])
    saved = 0
    for r in records:
        lid = r.get('lock_id')
        q = r.get('quarter')
        yr = r.get('year')
        if not all([lid, q, yr]):
            continue
        existing = query_one(
            "SELECT id FROM maintenance_records WHERE lock_id=? AND quarter=? AND year=?",
            [lid, q, yr]
        )
        data = [
            r.get('maintenance_date', date.today().isoformat()),
            r.get('maintenance_time') or None,
            r.get('technician') or None,
            r.get('supervisor') or None,
            r.get('maintenance_type', 'Preventivo'),
            q, yr,
            r.get('status', 'Realizado'),
            r.get('annotations') or None,
        ]
        if existing:
            execute("""
                UPDATE maintenance_records SET
                    maintenance_date=?, maintenance_time=?, technician=?,
                    supervisor=?, maintenance_type=?, quarter=?, year=?,
                    status=?, annotations=?
                WHERE id=?
            """, data + [existing['id']])
        else:
            insert("""
                INSERT INTO maintenance_records
                    (lock_id, maintenance_date, maintenance_time, technician,
                     supervisor, maintenance_type, quarter, year, status, annotations)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, [lid] + data)
        saved += 1

    return jsonify({'saved': saved, 'ok': True})
