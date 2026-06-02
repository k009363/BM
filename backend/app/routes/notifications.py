from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt_identity
from app.database.mongo_db import db
from app.middleware.auth import jwt_required_custom

notification_bp = Blueprint('notifications', __name__)


@notification_bp.route('', methods=['GET'])
@jwt_required_custom
def get_notifications():
    uid = get_jwt_identity()
    notifs = db.notifications.find(recipient_id=uid)
    notifs.sort(key=lambda n: n.get('created_at', ''), reverse=True)
    return jsonify([_fmt(n) for n in notifs[:50]]), 200


@notification_bp.route('/unread-count', methods=['GET'])
@jwt_required_custom
def unread_count():
    uid = get_jwt_identity()
    count = db.notifications.count(recipient_id=uid, is_read='False')
    return jsonify({'count': count}), 200


@notification_bp.route('/<notif_id>/read', methods=['PUT'])
@jwt_required_custom
def mark_read(notif_id):
    uid = get_jwt_identity()
    notif = db.notifications.find_by_id(notif_id)
    if not notif or notif['recipient_id'] != uid:
        return jsonify({'message': 'Not found'}), 404
    db.notifications.update_by_id(notif_id, {'is_read': 'True'})
    return jsonify({'message': 'Marked as read'}), 200


@notification_bp.route('/read-all', methods=['PUT'])
@jwt_required_custom
def mark_all_read():
    uid = get_jwt_identity()
    notifs = db.notifications.find(recipient_id=uid, is_read='False')
    for n in notifs:
        db.notifications.update_by_id(n['id'], {'is_read': 'True'})
    return jsonify({'message': 'All notifications marked as read'}), 200


def _fmt(n):
    sender = db.users.find_by_id(n.get('sender_id', ''))
    return {
        'id': n['id'],
        'type': n.get('type', ''),
        'message': n.get('message', ''),
        'blog_id': n.get('blog_id', ''),
        'is_read': n.get('is_read') == 'True',
        'sender': {'id': sender['id'], 'name': sender['name'],
                   'profile_pic': sender.get('profile_pic', '')} if sender else None,
        'created_at': n.get('created_at', ''),
    }
