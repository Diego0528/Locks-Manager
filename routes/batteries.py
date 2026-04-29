from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from database import query, query_one, execute, insert, calc_battery_pct, battery_color
from config import Config
from datetime import date

bp = Blueprint('batteries', __name__, url_prefix='/batteries')


@bp.route('/')
def index():
    sector_id = request.args.get('sector_id', '')
    filter_low = request.args.get('low', '')
    filter_stale = request.args.get('stale', '')

    where = ['1=1']
    params = []
    if sector_id:
        where.append('l.sector_id=?')
        params.append(sector_id)

    latest = query(f"""
        SELECT l.id AS lock_id, l.room_code, l.room_name, l.active,
               s.name AS sector_name, s.code AS sector_code,
               br.id AS reading_id, br.reading_date, br.voltage,
               br.percentage, br.batteries_changed, br.technician, br.notes,
               DATEDIFF(day, br.reading_date, GETDATE()) AS days_since
        FROM locks l
        JOIN sectors s ON s.id = l.sector_id
        LEFT JOIN battery_readings br ON br.id = (
            SELECT TOP 1 id FROM battery_readings
            WHERE lock_id = l.id ORDER BY reading_date DESC, id DESC
        )
        WHERE l.active=1 AND {' AND '.join(where)}
        ORDER BY s.code, l.room_code
    """, params)

    for row in latest:
        pct = row.get('percentage')
        row['color'] = battery_color(pct) if pct is not None else 'muted'
        days = row.get('days_since')
        row['stale'] = (days is None or days > Config.BATTERY_STALE_DAYS)

    if filter_low == '1':
        latest = [r for r in latest if r.get('percentage') is not None
                  and r['percentage'] < Config.BATTERY_ALERT_PCT]
    elif filter_stale == '1':
        latest = [r for r in latest if r['stale']]

    with_reading = [r for r in latest if r.get('percentage') is not None]
    avg_pct = round(sum(r['percentage'] for r in with_reading) / len(with_reading)) if with_reading else None
    low_count = sum(1 for r in with_reading if r['percentage'] < Config.BATTERY_ALERT_PCT)
    critical_count = sum(1 for r in with_reading if r['percentage'] < 10)
    no_reading = sum(1 for r in latest if r.get('percentage') is None)

    # Cerraduras sin lectura reciente (todos los sectores para stat card)
    stale_count = query_one(f"""
        SELECT COUNT(*) AS n FROM locks l
        LEFT JOIN battery_readings br ON br.id = (
            SELECT TOP 1 id FROM battery_readings WHERE lock_id=l.id
            ORDER BY reading_date DESC, id DESC
        )
        WHERE l.active=1
          AND (br.reading_date IS NULL OR DATEDIFF(day, br.reading_date, GETDATE()) > ?)
    """, [Config.BATTERY_STALE_DAYS])['n']

    avg_life = query_one("""
        SELECT AVG(CAST(DATEDIFF(day, prev.reading_date, curr.reading_date) AS FLOAT)) AS avg_days
        FROM battery_readings curr
        JOIN battery_readings prev ON prev.lock_id = curr.lock_id
            AND prev.reading_date < curr.reading_date
            AND curr.batteries_changed = 1
        WHERE prev.id = (
            SELECT MAX(id) FROM battery_readings br2
            WHERE br2.lock_id = curr.lock_id AND br2.reading_date < curr.reading_date
        )
    """)

    # Promedio de batería y vida por sector
    sector_stats = query("""
        SELECT s.name AS sector_name, s.code AS sector_code,
               AVG(CAST(br.percentage AS FLOAT)) AS avg_pct,
               COUNT(br.id) AS with_reading,
               COUNT(l.id) AS total_locks
        FROM locks l
        JOIN sectors s ON s.id = l.sector_id
        LEFT JOIN battery_readings br ON br.id = (
            SELECT TOP 1 id FROM battery_readings WHERE lock_id=l.id
            ORDER BY reading_date DESC, id DESC
        )
        WHERE l.active=1
        GROUP BY s.id, s.name, s.code
        ORDER BY s.code
    """)

    sectors = query("SELECT id, name FROM sectors WHERE active=1 ORDER BY code")

    return render_template('batteries/index.html',
                           readings=latest,
                           avg_pct=avg_pct,
                           low_count=low_count,
                           critical_count=critical_count,
                           no_reading=no_reading,
                           stale_count=stale_count,
                           avg_life_days=avg_life['avg_days'] if avg_life else None,
                           sector_stats=sector_stats,
                           sectors=sectors,
                           current_sector=sector_id,
                           filter_low=filter_low,
                           filter_stale=filter_stale,
                           alert_threshold=Config.BATTERY_ALERT_PCT,
                           stale_days=Config.BATTERY_STALE_DAYS)


@bp.route('/log', methods=['GET', 'POST'])
def log():
    if request.method == 'POST':
        f = request.form
        voltage = float(f['voltage'])
        pct = calc_battery_pct(voltage)
        changed = 1 if f.get('batteries_changed') else 0

        insert("""
            INSERT INTO battery_readings
                (lock_id, reading_date, technician, voltage, percentage, batteries_changed, notes)
            VALUES (?,?,?,?,?,?,?)
        """, [f['lock_id'], f['reading_date'],
              f.get('technician') or None,
              voltage, pct, changed,
              f.get('notes') or None])

        flash(f'Lectura registrada: {voltage}V → {pct}%', 'success')
        next_url = request.form.get('next') or url_for('batteries.index')
        return redirect(next_url)

    lock_id = request.args.get('lock_id')
    lk = query_one("""
        SELECT l.*, s.name AS sector_name
        FROM locks l JOIN sectors s ON s.id=l.sector_id WHERE l.id=?
    """, [lock_id]) if lock_id else None

    locks = query("""
        SELECT l.id, l.room_code, l.room_name, s.name AS sector_name, s.code AS sector_code
        FROM locks l JOIN sectors s ON s.id=l.sector_id
        WHERE l.active=1 ORDER BY s.code, l.room_code
    """)

    return render_template('batteries/log.html',
                           lock=lk, locks=locks,
                           today=date.today().isoformat(),
                           max_v=Config.BATTERY_MAX_V,
                           min_v=Config.BATTERY_MIN_V)


@bp.route('/<int:reading_id>/delete', methods=['POST'])
def delete_reading(reading_id):
    rec = query_one("SELECT lock_id FROM battery_readings WHERE id=?", [reading_id])
    if not rec:
        flash('Lectura no encontrada.', 'danger')
        return redirect(url_for('batteries.index'))
    execute("DELETE FROM battery_readings WHERE id=?", [reading_id])
    flash('Lectura de batería eliminada.', 'success')
    return redirect(url_for('locks.detail', lock_id=rec['lock_id']))


@bp.route('/api/calc')
def api_calc():
    try:
        v = float(request.args.get('voltage', 0))
        pct = calc_battery_pct(v)
        color = battery_color(pct)
        return jsonify({'voltage': v, 'percentage': pct, 'color': color})
    except Exception:
        return jsonify({'error': 'voltaje inválido'}), 400


@bp.route('/api/latest/<int:lock_id>')
def api_latest(lock_id):
    row = query_one("""
        SELECT TOP 1 reading_date, voltage, percentage, technician,
               batteries_changed, notes,
               DATEDIFF(day, reading_date, GETDATE()) AS days_ago
        FROM battery_readings
        WHERE lock_id=?
        ORDER BY reading_date DESC, id DESC
    """, [lock_id])
    if not row:
        return jsonify(None)
    if row.get('reading_date'):
        row['reading_date'] = row['reading_date'].isoformat()
    return jsonify(row)


@bp.route('/api/history/<int:lock_id>')
def api_history(lock_id):
    rows = query("""
        SELECT reading_date, voltage, percentage, batteries_changed
        FROM battery_readings WHERE lock_id=?
        ORDER BY reading_date ASC
    """, [lock_id])
    return jsonify(rows)
