from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from app.database.mongo_db import db
from app.middleware.auth import jwt_required_custom
from app.utils.push_helper import send_push

interaction_bp = Blueprint('interactions', __name__)


def make_notification(recipient_id, sender_id, notif_type, message, blog_id=''):
    if recipient_id == sender_id:
        return
    db.notifications.insert({
        'recipient_id': recipient_id,
        'sender_id': sender_id,
        'type': notif_type,
        'blog_id': blog_id,
        'message': message,
        'is_read': 'False',
    })


# ── Like ──────────────────────────────────────────────────────────────────────

@interaction_bp.route('/like/<blog_id>', methods=['POST'])
@jwt_required_custom
def like_blog(blog_id):
    uid = get_jwt_identity()
    blog = db.blogs.find_by_id(blog_id)
    if not blog or blog.get('is_deleted') == 'True':
        return jsonify({'message': 'Blog not found'}), 404
    existing = db.blog_likes.find_one(blog_id=blog_id, user_id=uid)
    if existing:
        return jsonify({'message': 'Already liked'}), 400
    db.blog_likes.insert({'blog_id': blog_id, 'user_id': uid})
    liker = db.users.find_by_id(uid)
    make_notification(blog['author_id'], uid, 'like',
                      f"{liker['name']} liked your blog", blog_id)
    send_push(blog['author_id'], f"❤️ {liker['name']} liked your blog",
              blog.get('title', '')[:60], f"/blog/{blog_id}")
    likes = db.blog_likes.find(blog_id=blog_id)
    return jsonify({'likes_count': len(likes), 'likes': [l['user_id'] for l in likes]}), 200


@interaction_bp.route('/unlike/<blog_id>', methods=['DELETE'])
@jwt_required_custom
def unlike_blog(blog_id):
    uid = get_jwt_identity()
    db.blog_likes.delete_where(blog_id=blog_id, user_id=uid)
    likes = db.blog_likes.find(blog_id=blog_id)
    return jsonify({'likes_count': len(likes), 'likes': [l['user_id'] for l in likes]}), 200


# ── Comment ───────────────────────────────────────────────────────────────────

@interaction_bp.route('/comment/<blog_id>', methods=['POST'])
@jwt_required_custom
def add_comment(blog_id):
    uid = get_jwt_identity()
    blog = db.blogs.find_by_id(blog_id)
    if not blog or blog.get('is_deleted') == 'True':
        return jsonify({'message': 'Blog not found'}), 404
    text = (request.get_json() or {}).get('text', '').strip()
    if not text:
        return jsonify({'message': 'Comment text required'}), 400
    comment = db.comments.insert({'blog_id': blog_id, 'author_id': uid, 'text': text})
    author = db.users.find_by_id(uid)
    make_notification(blog['author_id'], uid, 'comment',
                      f"{author['name']} commented on your blog", blog_id)
    send_push(blog['author_id'], f"💬 {author['name']} commented",
              text[:60], f"/blog/{blog_id}")
    return jsonify(_fmt_comment(comment)), 201


@interaction_bp.route('/comment/<comment_id>', methods=['DELETE'])
@jwt_required_custom
def delete_comment(comment_id):
    uid = get_jwt_identity()
    comment = db.comments.find_by_id(comment_id)
    if not comment:
        return jsonify({'message': 'Comment not found'}), 404
    user = db.users.find_by_id(uid)
    if comment['author_id'] != uid and user.get('role') != 'admin':
        return jsonify({'message': 'Not authorized'}), 403
    db.comments.delete_by_id(comment_id)
    return jsonify({'message': 'Comment deleted'}), 200


@interaction_bp.route('/comments/<blog_id>', methods=['GET'])
@jwt_required_custom
def get_comments(blog_id):
    comments = db.comments.find(blog_id=blog_id)
    comments.sort(key=lambda c: c.get('created_at', ''))
    return jsonify([_fmt_comment(c) for c in comments]), 200


# ── Share ─────────────────────────────────────────────────────────────────────

@interaction_bp.route('/share/<blog_id>', methods=['POST'])
@jwt_required_custom
def share_blog(blog_id):
    uid = get_jwt_identity()
    blog = db.blogs.find_by_id(blog_id)
    if not blog or blog.get('is_deleted') == 'True':
        return jsonify({'message': 'Blog not found'}), 404
    count = int(blog.get('shares_count', 0) or 0) + 1
    db.blogs.update_by_id(blog_id, {'shares_count': str(count)})
    sharer = db.users.find_by_id(uid)
    make_notification(blog['author_id'], uid, 'share',
                      f"{sharer['name']} shared your blog", blog_id)
    send_push(blog['author_id'], f"🔗 {sharer['name']} shared your blog",
              blog.get('title', '')[:60], f"/blog/{blog_id}")
    return jsonify({'shares_count': count}), 200


# ── Internal helpers ──────────────────────────────────────────────────────────

def _fmt_comment(c):
    author = db.users.find_by_id(c['author_id'])
    return {
        'id': c['id'],
        'blog_id': c['blog_id'],
        'author': {
            'id': author['id'],
            'name': author.get('name', ''),
            'profile_pic': author.get('profile_pic', ''),
        } if author else None,
        'text': c['text'],
        'created_at': c.get('created_at', ''),
    }
