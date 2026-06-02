from flask import Blueprint, jsonify
from app.database.mongo_db import db

stats_bp = Blueprint('stats', __name__)


@stats_bp.route('/public', methods=['GET'])
def public_stats():
    users_count = db.users.count(is_active='True')
    return jsonify({'users_count': users_count}), 200
