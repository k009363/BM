from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from app.database.mongo_db import db


def jwt_required_custom(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            user = db.users.find_by_id(user_id)
            if not user or user.get('is_active') != 'True':
                return jsonify({'message': 'Account not found or deactivated'}), 401
            # Check token version (for force logout)
            from flask_jwt_extended import get_jwt
            token = get_jwt()
            token_version = int(token.get('version', 0))
            user_version = int(user.get('token_version', 0))
            if token_version < user_version:
                return jsonify({'message': 'Session expired. Please login again'}), 401
            return fn(*args, **kwargs)
        except Exception as e:
            return jsonify({'message': 'Token invalid or expired', 'error': str(e)}), 401
    return wrapper


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            user = db.users.find_by_id(user_id)
            if not user or user.get('role') != 'admin':
                return jsonify({'message': 'Admin access required'}), 403
            return fn(*args, **kwargs)
        except Exception as e:
            return jsonify({'message': 'Unauthorized', 'error': str(e)}), 401
    return wrapper
