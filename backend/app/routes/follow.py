from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt_identity
from app.database.mongo_db import db
from app.middleware.auth import jwt_required_custom
from app.utils.push_helper import send_push

follow_bp = Blueprint('follow', __name__)


def _notif(recipient_id, sender_id, ntype, message):
    if recipient_id != sender_id:
        db.notifications.insert({
            'recipient_id': recipient_id, 'sender_id': sender_id,
            'type': ntype, 'blog_id': '', 'message': message, 'is_read': 'False',
        })


@follow_bp.route('/request/<target_id>', methods=['POST'])
@jwt_required_custom
def send_request(target_id):
    uid = get_jwt_identity()
    if uid == target_id:
        return jsonify({'message': 'Cannot follow yourself'}), 400
    target = db.users.find_by_id(target_id)
    if not target:
        return jsonify({'message': 'User not found'}), 404
    if db.user_follows.find_one(follower_id=uid, followed_id=target_id):
        return jsonify({'message': 'Already following'}), 400
    if db.follow_requests.find_one(from_id=uid, to_id=target_id, status='pending'):
        return jsonify({'message': 'Request already sent'}), 400
    db.follow_requests.insert({'from_id': uid, 'to_id': target_id, 'status': 'pending', 'updated_at': ''})
    me = db.users.find_by_id(uid)
    _notif(target_id, uid, 'follow_request', f"{me['name']} sent you a follow request")
    send_push(target_id, 'New Follow Request', f"{me['name']} wants to follow you", '/notifications')
    return jsonify({'message': 'Follow request sent'}), 200


@follow_bp.route('/cancel/<target_id>', methods=['POST'])
@jwt_required_custom
def cancel_request(target_id):
    uid = get_jwt_identity()
    deleted = db.follow_requests.delete_where(from_id=uid, to_id=target_id, status='pending')
    if not deleted:
        return jsonify({'message': 'No pending request found to cancel'}), 404
    return jsonify({'message': 'Follow request cancelled'}), 200


@follow_bp.route('/accept/<from_id>', methods=['POST'])
@jwt_required_custom
def accept_request(from_id):
    uid = get_jwt_identity()
    req = db.follow_requests.find_one(from_id=from_id, to_id=uid, status='pending')
    if not req:
        return jsonify({'message': 'Request not found'}), 404
    db.follow_requests.update_by_id(req['id'], {'status': 'accepted'})
    db.user_follows.insert({'follower_id': from_id, 'followed_id': uid})
    me = db.users.find_by_id(uid)
    _notif(from_id, uid, 'follow_accept', f"{me['name']} accepted your follow request")
    send_push(from_id, '✅ Follow request accepted',
              f"{me['name']} accepted your follow request", '/notifications')
    return jsonify({'message': 'Follow request accepted'}), 200


@follow_bp.route('/reject/<from_id>', methods=['POST'])
@jwt_required_custom
def reject_request(from_id):
    uid = get_jwt_identity()
    req = db.follow_requests.find_one(from_id=from_id, to_id=uid, status='pending')
    if not req:
        return jsonify({'message': 'Request not found'}), 404
    db.follow_requests.update_by_id(req['id'], {'status': 'rejected'})
    return jsonify({'message': 'Follow request rejected'}), 200


@follow_bp.route('/unfollow/<target_id>', methods=['POST'])
@jwt_required_custom
def unfollow(target_id):
    uid = get_jwt_identity()
    deleted = db.user_follows.delete_where(follower_id=uid, followed_id=target_id)
    if not deleted:
        return jsonify({'message': 'Not following this user'}), 400
    return jsonify({'message': 'Unfollowed successfully'}), 200


@follow_bp.route('/requests', methods=['GET'])
@jwt_required_custom
def get_requests():
    uid = get_jwt_identity()
    reqs = db.follow_requests.find(to_id=uid, status='pending')
    result = []
    for r in reqs:
        sender = db.users.find_by_id(r['from_id'])
        if sender:
            result.append({
                'id': r['id'],
                'from_user': {
                    'id': sender['id'], 'name': sender['name'],
                    'profile_pic': sender.get('profile_pic', ''),
                },
                'created_at': r.get('created_at', ''),
            })
    return jsonify(result), 200


@follow_bp.route('/followers', methods=['GET'])
@jwt_required_custom
def get_followers():
    uid = get_jwt_identity()
    follows = db.user_follows.find(followed_id=uid)
    users = []
    for f in follows:
        u = db.users.find_by_id(f['follower_id'])
        if u:
            users.append({'id': u['id'], 'name': u['name'], 'profile_pic': u.get('profile_pic', '')})
    return jsonify(users), 200


@follow_bp.route('/following', methods=['GET'])
@jwt_required_custom
def get_following():
    uid = get_jwt_identity()
    follows = db.user_follows.find(follower_id=uid)
    users = []
    for f in follows:
        u = db.users.find_by_id(f['followed_id'])
        if u:
            users.append({'id': u['id'], 'name': u['name'], 'profile_pic': u.get('profile_pic', '')})
    return jsonify(users), 200
