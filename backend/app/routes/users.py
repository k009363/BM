from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from app.database.mongo_db import db
from app.middleware.auth import jwt_required_custom
from app.routes.auth import format_user

users_bp = Blueprint('users', __name__)


@users_bp.route('/search', methods=['GET'])
@jwt_required_custom
def search_users():
    q = request.args.get('q', '').strip().lower()
    me = get_jwt_identity()
    if not q:
        return jsonify([]), 200
    results = db.users.find_by_filter(
        lambda u: (q in u.get('name', '').lower() or q in u.get('email', '').lower())
                  and u['id'] != me and u.get('is_active') == 'True'
    )
    return jsonify([format_user(u, current_user_id=me) for u in results[:20]]), 200


@users_bp.route('/<user_id>', methods=['GET'])
@jwt_required_custom
def get_user(user_id):
    me = get_jwt_identity()
    user = db.users.find_by_id(user_id)
    if not user or user.get('is_active') != 'True':
        return jsonify({'message': 'User not found'}), 404
    return jsonify(format_user(user, current_user_id=me)), 200
