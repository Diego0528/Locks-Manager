from flask import Blueprint, render_template, jsonify
from database import query, query_one
from datetime import date

bp = Blueprint('dashboard', __name__)


def current_quarter():
    m = date.today().month
    return (m - 1) // 3 + 1


def get_stats():
    today = date.today()
    q = current_quarter()
    yr = today.year

    total = query_one("SELECT COUNT(*) AS n FROM locks WHERE active=1")['n']
    inactive = query_one("SELECT COUNT(*) AS n FROM locks WHERE active=0")['n']

    # Locks with unresolved events
    issues = query_one(
        "SELECT COUNT(DISTINCT lock_id) AS n FROM lock_events WHERE resolved=0"
    )['n']

    # Maintenance done this quarter
    done = query_one(
        "SELECT COUNT(*) AS n FROM maintenance_records WHERE quarter=? AND year=? AND status='Realizado'",
        [q, yr]
    )['n']

    # Locks scheduled for this quarter
    scheduled = query_one("""
        SELECT COUNT(*) AS n FROM locks l
        JOIN sector_quarters sq ON sq.sector_id = l.sector_id
        WHERE l.active=1 AND sq.quarter=? AND sq.active=1
    """, [q])['n']

    # Low battery alerts
    low_battery = query("""
        SELECT l.room_code, s.name AS sector_name,
               br.voltage, br.percentage, br.reading_date
        FROM battery_readings br
        JOIN locks l ON l.id = br.lock_id
        JOIN sectors s ON s.id = l.sector_id
        WHERE br.id IN (
            SELECT MAX(id) FROM battery_readings GROUP BY lock_id
        ) AND br.percentage < 25
        ORDER BY br.percentage ASC
    """)

    # Battery avg by sector
    battery_by_sector = query("""
        SELECT s.name AS sector_name,
               AVG(CAST(br.percentage AS FLOAT)) AS avg_pct,
               COUNT(*) AS readings
        FROM battery_readings br
        JOIN locks l ON l.id = br.lock_id
        JOIN sectors s ON s.id = l.sector_id
        WHERE br.id IN (SELECT MAX(id) FROM battery_readings GROUP BY lock_id)
        GROUP BY s.id, s.name
        ORDER BY s.name
    """)

    # Recent maintenance (last 10)
    recent_maint = query("""
        SELECT TOP 10 mr.maintenance_date, mr.technician, mr.status,
               mr.annotations, l.room_code, s.name AS sector_name
        FROM maintenance_records mr
        JOIN locks l ON l.id = mr.lock_id
        JOIN sectors s ON s.id = l.sector_id
        ORDER BY mr.created_at DESC
    """)

    # Maintenance history per quarter (last 4 quarters)
    hist = query("""
        SELECT quarter, year, COUNT(*) AS total,
               SUM(CASE WHEN status='Realizado' THEN 1 ELSE 0 END) AS done
        FROM maintenance_records
        WHERE year >= ?
        GROUP BY quarter, year
        ORDER BY year, quarter
    """, [yr - 1])

    # Battery distribution by tier (for donut chart)
    batt_dist = query_one("""
        SELECT
            SUM(CASE WHEN percentage >= 75 THEN 1 ELSE 0 END) AS good,
            SUM(CASE WHEN percentage >= 25 AND percentage < 75 THEN 1 ELSE 0 END) AS medium,
            SUM(CASE WHEN percentage >= 10 AND percentage < 25 THEN 1 ELSE 0 END) AS low,
            SUM(CASE WHEN percentage < 10 THEN 1 ELSE 0 END) AS critical
        FROM battery_readings br
        WHERE br.id IN (SELECT MAX(id) FROM battery_readings GROUP BY lock_id)
    """)

    # Maintenance progress by sector for current quarter (for bar chart)
    sector_progress = query("""
        SELECT s.code AS sector_code, s.name AS sector_name,
               COUNT(l.id) AS total,
               SUM(CASE WHEN mr.status='Realizado' THEN 1 ELSE 0 END) AS done
        FROM locks l
        JOIN sectors s ON s.id = l.sector_id
        JOIN sector_quarters sq ON sq.sector_id = l.sector_id AND sq.quarter=? AND sq.active=1
        LEFT JOIN maintenance_records mr ON mr.lock_id=l.id AND mr.quarter=? AND mr.year=?
        WHERE l.active=1
        GROUP BY s.id, s.code, s.name
        ORDER BY s.code
    """, [q, q, yr])

    return {
        'total_locks': total,
        'inactive_locks': inactive,
        'active_locks': total,
        'issues_count': issues,
        'done_this_quarter': done,
        'scheduled_this_quarter': scheduled,
        'pct_done': round(done / scheduled * 100) if scheduled else 0,
        'low_battery': low_battery,
        'battery_by_sector': battery_by_sector,
        'recent_maintenance': recent_maint,
        'maintenance_history': hist,
        'battery_distribution': batt_dist,
        'sector_progress': sector_progress,
        'current_quarter': q,
        'current_year': yr,
    }


@bp.route('/')
def index():
    stats = get_stats()
    return render_template('dashboard.html', stats=stats)


@bp.route('/api/stats')
def api_stats():
    return jsonify(get_stats())
