from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from app.database.mongo_db import db
from app.middleware.auth import jwt_required_custom
from app.utils.push_helper import send_push
from app.utils.helpers import save_upload

wish_bp = Blueprint('wishes', __name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_expired(wish):
    exp = wish.get('expires_at', '')
    if not exp:
        return False
    try:
        return datetime.utcnow() > datetime.fromisoformat(exp.rstrip('Z'))
    except Exception:
        return False


def _fmt(wish, uid=None):
    author = db.users.find_by_id(wish['author_id'])
    shares_count = db.wish_shares.count(wish_id=wish['id'])
    shared_to_me = (
        uid and uid != wish['author_id'] and
        db.wish_shares.find_one(wish_id=wish['id'], to_user_id=uid) is not None
    )
    return {
        'id':           wish['id'],
        'title':        wish.get('title', ''),
        'message':      wish.get('message', ''),
        'template':     wish.get('template', 'birthday'),
        'visibility':   wish.get('visibility', 'public'),
        'expires_at':   wish.get('expires_at', ''),
        'is_expired':   _is_expired(wish),
        'is_owner':     uid == wish['author_id'],
        'shares_count': shares_count,
        'shared_to_me': shared_to_me,
        'icon':         wish.get('icon', ''),
        'font_family':  wish.get('font_family', 'sans'),
        'font_size':    wish.get('font_size', 'md'),
        'text_style':   wish.get('text_style', 'normal'),
        'text_align':   wish.get('text_align', 'center'),
        'bg_type':      wish.get('bg_type', 'gradient'),
        'bg_color1':    wish.get('bg_color1', ''),
        'bg_color2':    wish.get('bg_color2', ''),
        'text_color':   wish.get('text_color', ''),
        'border_style': wish.get('border_style', 'none'),
        'pattern':      wish.get('pattern', 'dots'),
        'cover_image':  wish.get('cover_image', ''),
        'author': {
            'id':          author['id'],
            'name':        author.get('name', ''),
            'profile_pic': author.get('profile_pic', ''),
        } if author else None,
        'created_at':   wish.get('created_at', ''),
        'updated_at':   wish.get('updated_at', ''),
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@wish_bp.route('', methods=['POST'])
@jwt_required_custom
def create_wish():
    uid = get_jwt_identity()
    d = request.get_json() or {}
    title = d.get('title', '').strip()
    if not title:
        return jsonify({'message': 'Title is required'}), 400
    wish = db.wishes.insert({
        'author_id':    uid,
        'title':        title,
        'message':      d.get('message', '').strip(),
        'template':     d.get('template', 'birthday'),
        'visibility':   d.get('visibility', 'public'),
        'expires_at':   d.get('expires_at', ''),
        # style fields
        'icon':         d.get('icon', ''),
        'font_family':  d.get('font_family', 'sans'),
        'font_size':    d.get('font_size', 'md'),
        'text_style':   d.get('text_style', 'normal'),
        'text_align':   d.get('text_align', 'center'),
        'bg_type':      d.get('bg_type', 'gradient'),
        'bg_color1':    d.get('bg_color1', ''),
        'bg_color2':    d.get('bg_color2', ''),
        'text_color':   d.get('text_color', ''),
        'border_style': d.get('border_style', 'none'),
        'pattern':      d.get('pattern', 'dots'),
        'cover_image':  d.get('cover_image', ''),
        'is_deleted':   'False',
        'updated_at':   '',
    })
    return jsonify(_fmt(wish, uid)), 201


@wish_bp.route('', methods=['GET'])
@jwt_required_custom
def get_feed():
    uid = get_jwt_identity()
    all_wishes = db.wishes.find_by_filter(
        lambda w: w.get('is_deleted') != 'True'
                  and w.get('visibility') == 'public'
                  and not _is_expired(w)
    )
    all_wishes.sort(key=lambda w: w.get('created_at', ''), reverse=True)
    return jsonify([_fmt(w, uid) for w in all_wishes[:60]]), 200


@wish_bp.route('/my', methods=['GET'])
@jwt_required_custom
def my_wishes():
    uid = get_jwt_identity()
    wishes = db.wishes.find_by_filter(
        lambda w: w['author_id'] == uid and w.get('is_deleted') != 'True'
    )
    wishes.sort(key=lambda w: w.get('created_at', ''), reverse=True)
    return jsonify([_fmt(w, uid) for w in wishes]), 200


@wish_bp.route('/shared-to-me', methods=['GET'])
@jwt_required_custom
def shared_to_me():
    uid = get_jwt_identity()
    shares = db.wish_shares.find(to_user_id=uid)
    result = []
    seen = set()
    for s in shares:
        wid = s['wish_id']
        if wid in seen:
            continue
        seen.add(wid)
        w = db.wishes.find_by_id(wid)
        if w and w.get('is_deleted') != 'True' and not _is_expired(w):
            result.append(_fmt(w, uid))
    result.sort(key=lambda w: w.get('created_at', ''), reverse=True)
    return jsonify(result), 200


@wish_bp.route('/<wish_id>', methods=['GET'])
@jwt_required_custom
def get_wish(wish_id):
    uid = get_jwt_identity()
    wish = db.wishes.find_by_id(wish_id)
    if not wish or wish.get('is_deleted') == 'True':
        return jsonify({'message': 'Wish not found'}), 404
    if wish.get('visibility') != 'public' and wish['author_id'] != uid:
        if not db.wish_shares.find_one(wish_id=wish_id, to_user_id=uid):
            return jsonify({'message': 'Access denied'}), 403
    return jsonify(_fmt(wish, uid)), 200


@wish_bp.route('/<wish_id>', methods=['PUT'])
@jwt_required_custom
def update_wish(wish_id):
    uid = get_jwt_identity()
    wish = db.wishes.find_by_id(wish_id)
    if not wish or wish.get('is_deleted') == 'True':
        return jsonify({'message': 'Wish not found'}), 404
    if wish['author_id'] != uid:
        return jsonify({'message': 'Not authorized'}), 403
    d = request.get_json() or {}
    all_fields = ('title','message','template','visibility','expires_at',
                  'icon','font_family','font_size','text_style','text_align',
                  'bg_type','bg_color1','bg_color2','text_color','border_style','pattern',
                  'cover_image')
    updates = {k: d[k] for k in all_fields if k in d}
    updated = db.wishes.update_by_id(wish_id, updates)
    return jsonify(_fmt(updated, uid)), 200


@wish_bp.route('/<wish_id>', methods=['DELETE'])
@jwt_required_custom
def delete_wish(wish_id):
    uid = get_jwt_identity()
    wish = db.wishes.find_by_id(wish_id)
    if not wish or wish.get('is_deleted') == 'True':
        return jsonify({'message': 'Wish not found'}), 404
    if wish['author_id'] != uid:
        return jsonify({'message': 'Not authorized'}), 403
    db.wishes.update_by_id(wish_id, {'is_deleted': 'True'})
    return jsonify({'message': 'Wish deleted'}), 200


@wish_bp.route('/<wish_id>/share/user', methods=['POST'])
@jwt_required_custom
def share_to_user(wish_id):
    uid = get_jwt_identity()
    wish = db.wishes.find_by_id(wish_id)
    if not wish or wish.get('is_deleted') == 'True':
        return jsonify({'message': 'Wish not found'}), 404
    d = request.get_json() or {}
    to_uid = d.get('user_id', '')
    if not to_uid:
        return jsonify({'message': 'user_id required'}), 400
    target = db.users.find_by_id(to_uid)
    if not target:
        return jsonify({'message': 'User not found'}), 404
    if not db.wish_shares.find_one(wish_id=wish_id, to_user_id=to_uid):
        db.wish_shares.insert({'wish_id': wish_id, 'from_user_id': uid, 'to_user_id': to_uid})
        me = db.users.find_by_id(uid)
        send_push(to_uid, f"Wish from {me.get('name','Someone')}",
                  wish.get('title', ''), f"/wishes/{wish_id}")
        db.notifications.insert({
            'recipient_id': to_uid,
            'sender_id':    uid,
            'type':         'wish_share',
            'blog_id':      '',
            'message':      f"{me.get('name','Someone')} shared a wish with you: {wish.get('title','')}",
            'is_read':      'False',
        })
    return jsonify({'message': 'Wish shared'}), 200


@wish_bp.route('/<wish_id>/share/platform', methods=['POST'])
@jwt_required_custom
def share_to_platform(wish_id):
    wish = db.wishes.find_by_id(wish_id)
    if not wish or wish.get('is_deleted') == 'True':
        return jsonify({'message': 'Wish not found'}), 404
    current = db.wish_shares.count(wish_id=wish_id)
    return jsonify({'shares_count': current}), 200


@wish_bp.route('/<wish_id>/share-status', methods=['GET'])
@jwt_required_custom
def share_status(wish_id):
    uid = get_jwt_identity()
    wish = db.wishes.find_by_id(wish_id)
    if not wish or wish.get('is_deleted') == 'True':
        return jsonify({'message': 'Wish not found'}), 404
    if wish['author_id'] != uid:
        return jsonify({'message': 'Not authorized'}), 403
    shares = db.wish_shares.find(wish_id=wish_id)
    result = []
    for s in shares:
        u = db.users.find_by_id(s['to_user_id'])
        if u:
            result.append({
                'user': {'id': u['id'], 'name': u.get('name',''), 'profile_pic': u.get('profile_pic','')},
                'shared_at': s.get('created_at', ''),
            })
    return jsonify(result), 200


@wish_bp.route('/upload-image', methods=['POST'])
@jwt_required_custom
def upload_image():
    if 'image' not in request.files:
        return jsonify({'message': 'No image provided'}), 400
    url = save_upload(request.files['image'], 'wishes')
    if not url:
        return jsonify({'message': 'Invalid file type'}), 400
    return jsonify({'url': url}), 200
