import os
import bcrypt
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, get_jwt_identity
from app.database.mongo_db import db
from app.middleware.auth import jwt_required_custom
from app.utils.helpers import save_upload

auth_bp = Blueprint('auth', __name__)


def _get_security_config():
    """Get login security settings from database."""
    cfg = db.site_config.find_one(key='security')
    if not cfg:
        return {'max_attempts': 5, 'block_minutes': 30, 'enabled': 'True'}
    return {
        'max_attempts': int(cfg.get('max_login_attempts', 5)),
        'block_minutes': int(cfg.get('block_duration_minutes', 30)),
        'enabled': cfg.get('enable_blocking', 'True') == 'True'
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def format_user(u, private=False, current_user_id=None):
    uid = u['id']
    followers = db.user_follows.find(followed_id=uid)
    following = db.user_follows.find(follower_id=uid)
    data = {
        'id': uid,
        'name': u.get('name', ''),
        'email': u.get('email', ''),
        'bio': u.get('bio', ''),
        'profile_pic': u.get('profile_pic', ''),
        'role': u.get('role', 'user'),
        'is_active': u.get('is_active', 'True') == 'True',
        'followers_count': len(followers),
        'following_count': len(following),
        'followers': [f['follower_id'] for f in followers],
        'following': [f['followed_id'] for f in following],
        'created_at': u.get('created_at', ''),
    }
    if current_user_id and current_user_id != uid:
        data['is_following'] = db.user_follows.find_one(
            follower_id=current_user_id, followed_id=uid) is not None
        data['has_sent_request'] = db.follow_requests.find_one(
            from_id=current_user_id, to_id=uid, status='pending') is not None
    if private:
        pending = db.follow_requests.find(to_id=uid, status='pending')
        data['follow_requests'] = [r['from_id'] for r in pending]
    return data


# ── Routes ────────────────────────────────────────────────────────────────────

@auth_bp.route('/register', methods=['POST'])
def register():
    d = request.get_json() or {}
    name = d.get('name', '').strip()
    email = d.get('email', '').strip().lower()
    password = d.get('password', '')
    if not name or not email or not password:
        return jsonify({'message': 'Name, email and password are required'}), 400
    if len(password) < 6:
        return jsonify({'message': 'Password must be at least 6 characters'}), 400
    if db.users.find_one(email=email):
        return jsonify({'message': 'Email already registered'}), 409

    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    admin_email = os.getenv('ADMIN_EMAIL', '').strip().lower()
    role = 'admin' if (admin_email and email == admin_email) else 'user'
    user = db.users.insert({
        'name': name, 'email': email, 'password_hash': pw_hash,
        'bio': '', 'profile_pic': '', 'role': role,
        'is_active': 'True', 'updated_at': '',
        'login_attempts': 0, 'blocked_until': '', 'token_version': 0,
    })
    token = create_access_token(identity=user['id'], additional_claims={'version': 0})
    return jsonify({'token': token, 'user': format_user(user)}), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    d = request.get_json() or {}
    email = d.get('email', '').strip().lower()
    password = d.get('password', '')
    user = db.users.find_one(email=email)

    if not user:
        return jsonify({'message': 'Invalid credentials'}), 401

    if user.get('is_active') != 'True':
        return jsonify({'message': 'Account is deactivated'}), 403

    # ── Login attempt blocking ────────────────────────────────────────────
    config = _get_security_config()

    if config['enabled']:
        # Check if account is blocked
        blocked_until = user.get('blocked_until', '')
        if blocked_until:
            blocked_dt = datetime.fromisoformat(blocked_until)
            if datetime.utcnow() < blocked_dt:
                remaining = int((blocked_dt - datetime.utcnow()).total_seconds() / 60)
                return jsonify({'message': f'Account locked. Try again in {remaining} minutes'}), 429
            else:
                # Unlock account
                db.users.update_by_id(user['id'], {
                    'blocked_until': '',
                    'login_attempts': 0
                })

    # Check password
    if not bcrypt.checkpw(password.encode(), user['password_hash'].encode()):
        if config['enabled']:
            attempts = int(user.get('login_attempts', 0)) + 1
            updates = {'login_attempts': attempts}

            if attempts >= config['max_attempts']:
                block_until = datetime.utcnow() + timedelta(minutes=config['block_minutes'])
                updates['blocked_until'] = block_until.isoformat()
                db.users.update_by_id(user['id'], updates)
                return jsonify({'message': f'Account locked due to too many failed attempts. Try again in {config["block_minutes"]} minutes'}), 429
            else:
                db.users.update_by_id(user['id'], updates)
                remaining_attempts = config['max_attempts'] - attempts
                return jsonify({'message': f'Invalid credentials. {remaining_attempts} attempts remaining'}), 401
        return jsonify({'message': 'Invalid credentials'}), 401

    # Success - reset login attempts
    if config['enabled']:
        db.users.update_by_id(user['id'], {
            'login_attempts': 0,
            'blocked_until': ''
        })

    token = create_access_token(identity=user['id'], additional_claims={'version': int(user.get('token_version', 0))})
    return jsonify({'token': token, 'user': format_user(user, private=True)}), 200


@auth_bp.route('/me', methods=['GET'])
@jwt_required_custom
def get_me():
    user = db.users.find_by_id(get_jwt_identity())
    return jsonify(format_user(user, private=True)), 200


@auth_bp.route('/profile', methods=['PUT'])
@jwt_required_custom
def update_profile():
    uid = get_jwt_identity()
    updates = {}
    for field in ('name', 'bio'):
        if field in request.form:
            updates[field] = request.form.get(field, '').strip()
    if 'email' in request.form:
        new_email = request.form.get('email', '').strip().lower()
        existing = db.users.find_one(email=new_email)
        if existing and existing['id'] != uid:
            return jsonify({'message': 'Email already in use'}), 409
        updates['email'] = new_email
    if 'profilePic' in request.files:
        url = save_upload(request.files['profilePic'], 'profiles')
        if url:
            updates['profile_pic'] = url
    if not updates:
        return jsonify({'message': 'No updates provided'}), 400
    user = db.users.update_by_id(uid, updates)
    return jsonify({'message': 'Profile updated', 'user': format_user(user)}), 200


@auth_bp.route('/password', methods=['PUT'])
@jwt_required_custom
def change_password():
    uid = get_jwt_identity()
    d = request.get_json() or {}
    user = db.users.find_by_id(uid)
    if not bcrypt.checkpw(d.get('current_password', '').encode(), user['password_hash'].encode()):
        return jsonify({'message': 'Current password is incorrect'}), 400
    new_pw = d.get('new_password', '')
    if len(new_pw) < 6:
        return jsonify({'message': 'Password must be at least 6 characters'}), 400
    pw_hash = bcrypt.hashpw(new_pw.encode(), bcrypt.gensalt()).decode()
    db.users.update_by_id(uid, {'password_hash': pw_hash})
    return jsonify({'message': 'Password updated'}), 200


@auth_bp.route('/promote-admin', methods=['POST'])
def promote_admin():
    """
    One-time endpoint to promote an existing user to admin.
    Requires ADMIN_SETUP_KEY env var to be set and matched.
    POST { "email": "...", "setup_key": "..." }
    """
    setup_key = os.getenv('ADMIN_SETUP_KEY', '').strip()
    if not setup_key:
        return jsonify({'message': 'Admin setup is not enabled'}), 403
    d = request.get_json() or {}
    if d.get('setup_key', '') != setup_key:
        return jsonify({'message': 'Invalid setup key'}), 403
    email = d.get('email', '').strip().lower()
    user = db.users.find_one(email=email)
    if not user:
        return jsonify({'message': 'User not found'}), 404
    db.users.update_by_id(user['id'], {'role': 'admin'})
    return jsonify({'message': f"{user['name']} is now an admin"}), 200
