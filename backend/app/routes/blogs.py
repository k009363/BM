from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from app.database.mongo_db import db
from app.middleware.auth import jwt_required_custom
from app.utils.helpers import save_upload, paginate
from app.utils.push_helper import send_push

blog_bp = Blueprint('blogs', __name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def format_blog(b, current_user_id=None):
    author = db.users.find_by_id(b['author_id'])
    likes = db.blog_likes.find(blog_id=b['id'])
    comments_count = db.comments.count(blog_id=b['id'])
    liked_ids = [l['user_id'] for l in likes]
    return {
        'id': b['id'],
        'author': {
            'id': author['id'],
            'name': author.get('name', ''),
            'profile_pic': author.get('profile_pic', ''),
        } if author else None,
        'title': b.get('title', ''),
        'content': b.get('content', ''),
        'cover_image': b.get('cover_image', ''),
        'visibility': b.get('visibility', 'public'),
        'tags': [t.strip() for t in b.get('tags', '').split(',') if t.strip()],
        'template': b.get('template', 'default'),
        'likes_count': len(likes),
        'likes': liked_ids,
        'is_liked': current_user_id in liked_ids if current_user_id else False,
        'comments_count': comments_count,
        'shares_count': int(b.get('shares_count', 0) or 0),
        'created_at': b.get('created_at', ''),
        'updated_at': b.get('updated_at', ''),
    }


def can_see(blog, uid):
    if blog.get('is_deleted') == 'True':
        return False
    if blog.get('visibility') == 'public':
        return True
    if not uid:
        return False
    if blog['author_id'] == uid:
        return True
    return db.user_follows.find_one(follower_id=uid, followed_id=blog['author_id']) is not None


# ── Routes ────────────────────────────────────────────────────────────────────

@blog_bp.route('', methods=['POST'])
@jwt_required_custom
def create_blog():
    uid = get_jwt_identity()
    title = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()
    if not title or not content:
        return jsonify({'message': 'Title and content are required'}), 400
    cover_image = ''
    if 'coverImage' in request.files:
        cover_image = save_upload(request.files['coverImage'], 'blogs')
    blog = db.blogs.insert({
        'author_id': uid,
        'title': title,
        'content': content,
        'cover_image': cover_image,
        'visibility': request.form.get('visibility', 'public'),
        'tags': request.form.get('tags', ''),
        'template': request.form.get('template', 'default'),
        'shares_count': '0',
        'is_deleted': 'False',
        'updated_at': '',
    })
    # notify followers of new public post
    if blog.get('visibility') == 'public':
        author = db.users.find_by_id(uid)
        followers = db.user_follows.find(followed_id=uid)
        for f in followers[:50]:  # cap at 50 to keep request fast
            send_push(
                f['follower_id'],
                f"New post by {author.get('name', 'Someone')}",
                title,
                f"/blog/{blog['id']}",
            )
    return jsonify(format_blog(blog, uid)), 201


@blog_bp.route('', methods=['GET'])
@jwt_required_custom
def get_blogs():
    uid = get_jwt_identity()
    page = int(request.args.get('page', 1))
    tag = request.args.get('tag', '')
    all_blogs = db.blogs.find_by_filter(
        lambda b: b.get('is_deleted') != 'True' and can_see(b, uid)
    )
    if tag:
        all_blogs = [b for b in all_blogs if tag in b.get('tags', '')]
    all_blogs.sort(key=lambda b: b.get('created_at', ''), reverse=True)
    paged = paginate(all_blogs, page, 10)
    paged['items'] = [format_blog(b, uid) for b in paged['items']]
    return jsonify(paged), 200


@blog_bp.route('/<blog_id>', methods=['GET'])
@jwt_required_custom
def get_blog(blog_id):
    uid = get_jwt_identity()
    blog = db.blogs.find_by_id(blog_id)
    if not blog or not can_see(blog, uid):
        return jsonify({'message': 'Blog not found or access denied'}), 404
    return jsonify(format_blog(blog, uid)), 200


@blog_bp.route('/user/<user_id>', methods=['GET'])
@jwt_required_custom
def get_user_blogs(user_id):
    uid = get_jwt_identity()
    page = int(request.args.get('page', 1))
    blogs = db.blogs.find_by_filter(
        lambda b: b['author_id'] == user_id
                  and b.get('is_deleted') != 'True'
                  and can_see(b, uid)
    )
    blogs.sort(key=lambda b: b.get('created_at', ''), reverse=True)
    paged = paginate(blogs, page, 10)
    paged['items'] = [format_blog(b, uid) for b in paged['items']]
    return jsonify(paged), 200


@blog_bp.route('/<blog_id>', methods=['PUT'])
@jwt_required_custom
def update_blog(blog_id):
    uid = get_jwt_identity()
    blog = db.blogs.find_by_id(blog_id)
    if not blog or blog.get('is_deleted') == 'True':
        return jsonify({'message': 'Blog not found'}), 404
    if blog['author_id'] != uid:
        return jsonify({'message': 'Not authorized'}), 403
    updates = {}
    for field in ('title', 'content', 'visibility', 'tags', 'template'):
        if field in request.form:
            updates[field] = request.form.get(field, '')
    if 'coverImage' in request.files:
        url = save_upload(request.files['coverImage'], 'blogs')
        if url:
            updates['cover_image'] = url
    updated = db.blogs.update_by_id(blog_id, updates)
    return jsonify(format_blog(updated, uid)), 200


@blog_bp.route('/<blog_id>', methods=['DELETE'])
@jwt_required_custom
def delete_blog(blog_id):
    uid = get_jwt_identity()
    blog = db.blogs.find_by_id(blog_id)
    if not blog or blog.get('is_deleted') == 'True':
        return jsonify({'message': 'Blog not found'}), 404
    user = db.users.find_by_id(uid)
    if blog['author_id'] != uid and user.get('role') != 'admin':
        return jsonify({'message': 'Not authorized'}), 403
    db.blogs.update_by_id(blog_id, {'is_deleted': 'True'})
    return jsonify({'message': 'Blog deleted'}), 200


@blog_bp.route('/upload-image', methods=['POST'])
@jwt_required_custom
def upload_image():
    if 'image' not in request.files:
        return jsonify({'message': 'No image provided'}), 400
    url = save_upload(request.files['image'], 'blogs')
    if not url:
        return jsonify({'message': 'Invalid file type'}), 400
    return jsonify({'url': url}), 200
