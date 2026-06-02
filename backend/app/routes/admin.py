from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from datetime import datetime
from app.database.mongo_db import db
from app.middleware.auth import admin_required
from app.utils.push_helper import send_push

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/users', methods=['GET'])
@admin_required
def get_all_users():
    users = db.users.read_all()
    result = []
    for u in users:
        followers = db.user_follows.find(followed_id=u['id'])
        following = db.user_follows.find(follower_id=u['id'])
        blogs_count = db.blogs.count(author_id=u['id'])
        result.append({
            'id': u['id'], 'name': u['name'], 'email': u['email'],
            'role': u.get('role', 'user'), 'is_active': u.get('is_active') == 'True',
            'profile_pic': u.get('profile_pic', ''),
            'followers_count': len(followers), 'following_count': len(following),
            'blogs_count': blogs_count, 'created_at': u.get('created_at', ''),
        })
    result.sort(key=lambda u: u.get('created_at', ''), reverse=True)
    return jsonify(result), 200


@admin_bp.route('/users/<user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    me = get_jwt_identity()
    if user_id == me:
        return jsonify({'message': 'Cannot delete yourself'}), 400
    user = db.users.find_by_id(user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404
    db.users.update_by_id(user_id, {'is_active': 'False'})
    return jsonify({'message': 'User deactivated'}), 200


@admin_bp.route('/users/<user_id>/toggle', methods=['PUT'])
@admin_required
def toggle_user(user_id):
    user = db.users.find_by_id(user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404
    new_status = 'False' if user.get('is_active') == 'True' else 'True'
    db.users.update_by_id(user_id, {'is_active': new_status})
    return jsonify({'message': 'User status toggled', 'is_active': new_status == 'True'}), 200


@admin_bp.route('/blogs', methods=['GET'])
@admin_required
def get_all_blogs():
    blogs = db.blogs.find_by_filter(lambda b: b.get('is_deleted') != 'True')
    result = []
    for b in blogs:
        author = db.users.find_by_id(b['author_id'])
        likes = db.blog_likes.find(blog_id=b['id'])
        result.append({
            'id': b['id'], 'title': b['title'],
            'visibility': b.get('visibility', 'public'),
            'author': {'id': author['id'], 'name': author['name']} if author else None,
            'likes_count': len(likes),
            'shares_count': int(b.get('shares_count', 0) or 0),
            'created_at': b.get('created_at', ''),
        })
    result.sort(key=lambda b: b.get('created_at', ''), reverse=True)
    return jsonify(result), 200


@admin_bp.route('/blogs/<blog_id>', methods=['DELETE'])
@admin_required
def delete_blog(blog_id):
    blog = db.blogs.find_by_id(blog_id)
    if not blog or blog.get('is_deleted') == 'True':
        return jsonify({'message': 'Blog not found'}), 404
    db.blogs.update_by_id(blog_id, {'is_deleted': 'True'})
    return jsonify({'message': 'Blog deleted'}), 200


@admin_bp.route('/stats', methods=['GET'])
@admin_required
def get_stats():
    total_users = db.users.count()
    active_users = db.users.count(is_active='True')
    total_blogs = db.blogs.find_by_filter(lambda b: b.get('is_deleted') != 'True')
    total_comments = db.comments.count()
    total_messages = db.messages.count()
    return jsonify({
        'total_users': total_users,
        'active_users': active_users,
        'total_blogs': len(total_blogs),
        'total_comments': total_comments,
        'total_messages': total_messages,
    }), 200


# ── Force Logout All Users ────────────────────────────────────────────────────

@admin_bp.route('/force-logout-all', methods=['POST'])
@admin_required
def force_logout_all():
    users = db.users.read_all()
    for user in users:
        version = int(user.get('token_version', 0)) + 1
        db.users.update_by_id(user['id'], {'token_version': version})
    return jsonify({'message': f'Force logged out {len(users)} users'}), 200


# ── Admin Notices ─────────────────────────────────────────────────────────────

@admin_bp.route('/notices', methods=['POST'])
@admin_required
def create_notice():
    admin_id = get_jwt_identity()
    data = request.get_json() or {}
    title = data.get('title', '').strip()
    body = data.get('body', '').strip()
    notice_type = data.get('type', 'info')  # info, alert, warning

    if not title or not body:
        return jsonify({'message': 'Title and body are required'}), 400

    notice = db.notices.insert({
        'admin_id': admin_id,
        'title': title,
        'body': body,
        'type': notice_type,
        'created_at': datetime.utcnow().isoformat(),
    })

    # Send to all users
    users = db.users.read_all()
    for user in users:
        # In-app notification
        db.notifications.insert({
            'recipient_id': user['id'],
            'sender_id': admin_id,
            'type': 'admin_notice',
            'message': body,
            'is_read': 'False',
        })

        # Push notification
        icon = {'alert': '⚠️', 'warning': '🚨', 'info': 'ℹ️'}.get(notice_type, 'ℹ️')
        send_push(user['id'], f'{icon} {title}', body, '/notices')

    return jsonify({'message': f'Notice sent to {len(users)} users', 'notice': notice}), 201


@admin_bp.route('/notices', methods=['GET'])
@admin_required
def get_notices():
    notices = db.notices.find()
    notices.sort(key=lambda n: n.get('created_at', ''), reverse=True)
    return jsonify(notices[:50]), 200  # Last 50 notices


@admin_bp.route('/notices/<notice_id>', methods=['DELETE'])
@admin_required
def delete_notice(notice_id):
    db.notices.delete_by_id(notice_id)
    return jsonify({'message': 'Notice deleted'}), 200
