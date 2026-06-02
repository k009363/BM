from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from app.database.mongo_db import db
from app.middleware.auth import jwt_required_custom

chat_bp = Blueprint('chat', __name__)


def _fmt_msg(m):
    sender = db.users.find_by_id(m['sender_id'])
    return {
        'id': m['id'],
        'sender': {
            'id': sender['id'], 'name': sender.get('name', ''),
            'profile_pic': sender.get('profile_pic', ''),
        } if sender else None,
        'receiver_id': m.get('receiver_id', ''),
        'group_id': m.get('group_id', ''),
        'text': m.get('text', ''),
        'is_group': m.get('is_group') == 'True',
        'is_read': m.get('is_read') == 'True',
        'created_at': m.get('created_at', ''),
    }


# ── Personal chat ─────────────────────────────────────────────────────────────

@chat_bp.route('/send', methods=['POST'])
@jwt_required_custom
def send_message():
    uid = get_jwt_identity()
    d = request.get_json() or {}
    receiver_id = d.get('receiver_id', '')
    text = d.get('text', '').strip()
    if not receiver_id or not text:
        return jsonify({'message': 'receiver_id and text are required'}), 400
    msg = db.messages.insert({
        'sender_id': uid, 'receiver_id': receiver_id, 'group_id': '',
        'text': text, 'is_group': 'False', 'is_read': 'False',
    })
    return jsonify(_fmt_msg(msg)), 201


@chat_bp.route('/messages/<user_id>', methods=['GET'])
@jwt_required_custom
def get_messages(user_id):
    uid = get_jwt_identity()
    msgs = db.messages.find_by_filter(
        lambda m: m.get('is_group') != 'True' and (
            (m['sender_id'] == uid and m.get('receiver_id') == user_id) or
            (m['sender_id'] == user_id and m.get('receiver_id') == uid)
        )
    )
    # Mark received as read
    for m in msgs:
        if m.get('receiver_id') == uid and m.get('is_read') != 'True':
            db.messages.update_by_id(m['id'], {'is_read': 'True'})
    msgs.sort(key=lambda m: m.get('created_at', ''))
    return jsonify([_fmt_msg(m) for m in msgs]), 200


@chat_bp.route('/unread-count', methods=['GET'])
@jwt_required_custom
def get_unread_count():
    uid = get_jwt_identity()
    msgs = db.messages.find_by_filter(
        lambda m: m.get('is_group') != 'True' and
                  m.get('receiver_id') == uid and m.get('is_read') != 'True'
    )
    return jsonify({'unread_count': len(msgs)}), 200


@chat_bp.route('/conversations', methods=['GET'])
@jwt_required_custom
def get_conversations():
    uid = get_jwt_identity()
    msgs = db.messages.find_by_filter(
        lambda m: m.get('is_group') != 'True' and
                  (m['sender_id'] == uid or m.get('receiver_id') == uid)
    )
    seen = set()
    convos = []
    for m in sorted(msgs, key=lambda x: x.get('created_at', ''), reverse=True):
        partner_id = m.get('receiver_id') if m['sender_id'] == uid else m['sender_id']
        if partner_id in seen:
            continue
        seen.add(partner_id)
        partner = db.users.find_by_id(partner_id)
        if partner:
            unread = db.messages.find_by_filter(
                lambda x: x['sender_id'] == partner_id and
                          x.get('receiver_id') == uid and x.get('is_read') != 'True'
            )
            convos.append({
                'user': {'id': partner['id'], 'name': partner['name'],
                         'profile_pic': partner.get('profile_pic', '')},
                'last_message': m.get('text', ''),
                'last_time': m.get('created_at', ''),
                'unread_count': len(unread),
            })
    return jsonify(convos), 200


# ── Group chat ────────────────────────────────────────────────────────────────

@chat_bp.route('/group/create', methods=['POST'])
@jwt_required_custom
def create_group():
    uid = get_jwt_identity()
    d = request.get_json() or {}
    name = d.get('name', '').strip()
    if not name:
        return jsonify({'message': 'Group name required'}), 400
    group = db.groups.insert({'name': name, 'description': d.get('description', ''),
                               'avatar': '', 'admin_id': uid, 'updated_at': ''})
    db.group_members.insert({'group_id': group['id'], 'user_id': uid})
    for mid in d.get('member_ids', []):
        if mid != uid:
            db.group_members.insert({'group_id': group['id'], 'user_id': mid})
    return jsonify(_fmt_group(group)), 201


@chat_bp.route('/groups', methods=['GET'])
@jwt_required_custom
def get_groups():
    uid = get_jwt_identity()
    memberships = db.group_members.find(user_id=uid)
    groups = []
    for m in memberships:
        g = db.groups.find_by_id(m['group_id'])
        if g:
            groups.append(_fmt_group(g))
    return jsonify(groups), 200


@chat_bp.route('/group/<group_id>/send', methods=['POST'])
@jwt_required_custom
def send_group_message(group_id):
    uid = get_jwt_identity()
    if not db.group_members.find_one(group_id=group_id, user_id=uid):
        return jsonify({'message': 'Not a group member'}), 403
    text = (request.get_json() or {}).get('text', '').strip()
    if not text:
        return jsonify({'message': 'Text required'}), 400
    msg = db.messages.insert({
        'sender_id': uid, 'receiver_id': '', 'group_id': group_id,
        'text': text, 'is_group': 'True', 'is_read': 'False',
    })
    return jsonify(_fmt_msg(msg)), 201


@chat_bp.route('/group/<group_id>/messages', methods=['GET'])
@jwt_required_custom
def get_group_messages(group_id):
    uid = get_jwt_identity()
    if not db.group_members.find_one(group_id=group_id, user_id=uid):
        return jsonify({'message': 'Not a group member'}), 403
    msgs = db.messages.find(group_id=group_id)
    msgs.sort(key=lambda m: m.get('created_at', ''))
    return jsonify([_fmt_msg(m) for m in msgs]), 200


@chat_bp.route('/group/<group_id>/add/<user_id>', methods=['POST'])
@jwt_required_custom
def add_member(group_id, user_id):
    uid = get_jwt_identity()
    group = db.groups.find_by_id(group_id)
    if not group or group['admin_id'] != uid:
        return jsonify({'message': 'Only group admin can add members'}), 403
    if not db.group_members.find_one(group_id=group_id, user_id=user_id):
        db.group_members.insert({'group_id': group_id, 'user_id': user_id})
    return jsonify({'message': 'Member added'}), 200


@chat_bp.route('/group/<group_id>/remove/<user_id>', methods=['DELETE'])
@jwt_required_custom
def remove_member(group_id, user_id):
    uid = get_jwt_identity()
    group = db.groups.find_by_id(group_id)
    if not group or group['admin_id'] != uid:
        return jsonify({'message': 'Only group admin can remove members'}), 403
    db.group_members.delete_where(group_id=group_id, user_id=user_id)
    return jsonify({'message': 'Member removed'}), 200


def _fmt_group(g):
    members = db.group_members.find(group_id=g['id'])
    admin = db.users.find_by_id(g['admin_id'])
    last_msg = db.messages.find_by_filter(lambda m: m.get('group_id') == g['id'])
    last_msg.sort(key=lambda m: m.get('created_at', ''), reverse=True)
    return {
        'id': g['id'],
        'name': g['name'],
        'description': g.get('description', ''),
        'avatar': g.get('avatar', ''),
        'admin': {'id': admin['id'], 'name': admin.get('name', '')} if admin else None,
        'members_count': len(members),
        'member_ids': [m['user_id'] for m in members],
        'last_message': last_msg[0].get('text', '') if last_msg else '',
        'created_at': g.get('created_at', ''),
    }
