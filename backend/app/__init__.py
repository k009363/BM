import os
import time
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
from dotenv import load_dotenv

load_dotenv()

socketio = SocketIO(
    cors_allowed_origins="*",
    logger=False,
    engineio_logger=False,
    transports=['websocket', 'polling']
)
jwt = JWTManager()

# Simple in-memory cache for platform settings (refreshed every 60s)
_platform_cache = {'data': {}, 'at': 0}

def _get_platform():
    if time.time() - _platform_cache['at'] < 60:
        return _platform_cache['data']
    try:
        from app.database.mongo_db import db
        cfg = db.site_config.find_one(key='platform') or {}
        _platform_cache['data'] = cfg
        _platform_cache['at']   = time.time()
        return cfg
    except Exception:
        return {}


def create_app():
    app = Flask(__name__)

    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'changeme')
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'jwtsecret')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = False
    app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB

    # CORS setup
    env = os.getenv('FLASK_ENV', 'development')

    # Always allow all origins in development
    CORS(app, origins='*', supports_credentials=True,
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH'],
         allow_headers=['Content-Type', 'Authorization'],
         expose_headers=['Content-Type', 'Authorization'])

    print('[CORS] Allowing all origins (*)')
    print('[CORS] Methods: GET, POST, PUT, DELETE, OPTIONS, PATCH')
    print('[CORS] Headers: Content-Type, Authorization')

    jwt.init_app(app)
    socketio.init_app(app)

    # ── Request Logging ───────────────────────────────────────────────────────
    @app.before_request
    def log_request():
        print(f'\n[REQUEST] {request.method} {request.path}')
        print(f'  Origin: {request.headers.get("Origin", "no-origin")}')
        print(f'  Host: {request.headers.get("Host", "unknown")}')
        print(f'  User-Agent: {request.headers.get("User-Agent", "unknown")[:50]}')

    @app.after_request
    def after_request(response):
        origin = request.headers.get('Origin', 'no-origin')
        print(f'[RESPONSE] Status: {response.status_code} | Origin: {origin} | Path: {request.path}')
        return response

    # ── Platform checks ───────────────────────────────────────────────────────
    @app.before_request
    def platform_guard():
        # Always allow: health, config, admin, auth login
        exempt = ('/api/health', '/api/stats/public', '/api/push/vapid-key')
        if (request.path in exempt
                or request.path.startswith('/api/admin')
                or request.path.startswith('/api/config')
                or request.path == '/api/auth/login'):
            return None

        cfg = _get_platform()

        # Maintenance mode — block all non-admin traffic
        if cfg.get('maintenance_mode') == 'True':
            return jsonify({
                'success': False,
                'message': cfg.get('maintenance_message') or 'Platform is under maintenance. Please check back later.',
            }), 503

        # Registration disabled
        if request.path == '/api/auth/register' and cfg.get('registration_enabled') == 'False':
            return jsonify({'message': 'New registrations are currently disabled.'}), 403

    # ── Register blueprints ───────────────────────────────────────────────────
    from app.routes.auth import auth_bp
    from app.routes.blogs import blog_bp
    from app.routes.interactions import interaction_bp
    from app.routes.follow import follow_bp
    from app.routes.chat import chat_bp
    from app.routes.admin import admin_bp
    from app.routes.notifications import notification_bp
    from app.routes.users import users_bp
    from app.routes.stats import stats_bp
    from app.routes.push import push_bp
    from app.routes.config import config_bp
    from app.routes.wishes import wish_bp

    app.register_blueprint(auth_bp,          url_prefix='/api/auth')
    app.register_blueprint(blog_bp,          url_prefix='/api/blogs')
    app.register_blueprint(interaction_bp,   url_prefix='/api/interactions')
    app.register_blueprint(follow_bp,        url_prefix='/api/follow')
    app.register_blueprint(chat_bp,          url_prefix='/api/chat')
    app.register_blueprint(admin_bp,         url_prefix='/api/admin')
    app.register_blueprint(notification_bp,  url_prefix='/api/notifications')
    app.register_blueprint(users_bp,         url_prefix='/api/users')
    app.register_blueprint(stats_bp,         url_prefix='/api/stats')
    app.register_blueprint(push_bp,          url_prefix='/api/push')
    app.register_blueprint(config_bp,        url_prefix='/api/config')
    app.register_blueprint(wish_bp,          url_prefix='/api/wishes')

    # Socket.IO events
    from app.sockets.socket_events import register_events
    register_events(socketio)

    @app.route('/api/health')
    def health():
        return {
            'status': 'OK',
            'message': 'Blog Media Flask API',
            'environment': os.getenv('FLASK_ENV', 'development'),
            'database': 'MongoDB Atlas' if os.getenv('MONGO_URI', '').startswith('mongodb+srv') else 'MongoDB',
            'image_storage': 'Cloudinary',
            'push_notifications': 'Web Push (VAPID)',
        }

    @app.route('/api/server-info')
    def server_info():
        import socket
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
        except Exception:
            hostname = 'unknown'
            local_ip = 'unknown'

        external_url = os.getenv('RENDER_EXTERNAL_URL', '')

        return {
            'service': 'Blog Media Backend',
            'environment': os.getenv('FLASK_ENV', 'development'),
            'hostname': hostname,
            'local_ip': local_ip,
            'render_url': external_url or 'http://localhost:' + os.getenv('PORT', '5000'),
            'port': os.getenv('PORT', '5000'),
            'timezone': os.getenv('TZ', 'UTC'),
        }

    return app
