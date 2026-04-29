from flask import Flask, session, redirect, url_for, request
from config import Config
from datetime import timedelta


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.secret_key = Config.SECRET_KEY
    app.permanent_session_lifetime = timedelta(days=7)

    # Jinja2 helpers
    app.jinja_env.globals['enumerate'] = enumerate
    app.jinja_env.globals['now'] = __import__('datetime').datetime.now()

    from routes.auth import bp as auth_bp
    from routes.admin import bp as admin_bp
    from routes.dashboard import bp as dashboard_bp
    from routes.locks import bp as locks_bp
    from routes.maintenance import bp as maintenance_bp
    from routes.batteries import bp as batteries_bp
    from routes.reports import bp as reports_bp
    from routes.sectors import bp as sectors_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(locks_bp)
    app.register_blueprint(maintenance_bp)
    app.register_blueprint(batteries_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(sectors_bp)

    @app.before_request
    def require_login():
        public = {'auth.login', 'auth.logout', 'static'}
        if request.endpoint in public:
            return
        if 'user' not in session:
            return redirect(url_for('auth.login', next=request.url))

    @app.context_processor
    def inject_user():
        return {
            'current_user': session.get('full_name', ''),
            'current_username': session.get('user', ''),
            'current_role': session.get('role', ''),
            'current_user_id': session.get('user_id'),
        }

    return app


if __name__ == '__main__':
    app = create_app()
    print("\n  Locks Manager — PHA Hotel")
    print("  Acceso local:  http://localhost:5000")
    print("  Acceso red:    http://<tu-IP>:5000\n")
    app.run(host='0.0.0.0', port=5000, debug=False)
