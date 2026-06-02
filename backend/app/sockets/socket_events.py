"""
WebSocket event handlers using Flask-SocketIO.
All real-time features (chat, notifications) are handled here.
"""
from flask_socketio import join_room, leave_room, emit
from flask_jwt_extended import decode_token
from app.database.mongo_db import db
from app.utils.push_helper import send_push

# Track connected users: { user_id: socket_id }
online_users: dict = {}


def register_events(socketio):

    @socketio.on('connect')
    def on_connect(auth):
        token = (auth or {}).get('token', '')
        try:
            decoded = decode_token(token)
            user_id = decoded['sub']
            online_users[user_id] = True
            join_room(f'user_{user_id}')          # personal notification room
            emit('connected', {'user_id': user_id})
            emit('online_users', list(online_users.keys()), broadcast=True)
        except Exception:
            pass  # unauthenticated connection — still allow

    @socketio.on('disconnect')
    def on_disconnect():
        # Remove from online_users if present
        to_remove = [k for k, v in online_users.items()]
        # We can't easily get user_id on disconnect without session tracking,
        # so we broadcast the updated list
        emit('online_users', list(online_users.keys()), broadcast=True)

    # ── Personal Chat ─────────────────────────────────────────────────────────

    @socketio.on('send_message')
    def on_send_message(data):
        """
        data: { token, receiver_id, text }
        Saves to CSV and emits to receiver's personal room.
        """
        print(f'[socket] send_message event received: {data}')
        try:
            decoded = decode_token(data.get('token', ''))
            sender_id = decoded['sub']
            print(f'[socket] message from user {sender_id}')
        except Exception as e:
            print(f'[socket] auth error: {e}')
            emit('error', {'message': 'Unauthorized'})
            return

        receiver_id = data.get('receiver_id', '')
        text = data.get('text', '').strip()
        if not receiver_id or not text:
            print(f'[socket] invalid message data: receiver_id={receiver_id}, text_len={len(text)}')
            return

        msg = db.messages.insert({
            'sender_id': sender_id, 'receiver_id': receiver_id,
            'group_id': '', 'text': text, 'is_group': 'False', 'is_read': 'False',
        })
        print(f'[socket] message saved with id: {msg["id"]}')
        sender = db.users.find_by_id(sender_id)
        payload = {
            'id': msg['id'],
            'sender': {'id': sender_id, 'name': sender.get('name', ''),
                       'profile_pic': sender.get('profile_pic', '')},
            'receiver_id': receiver_id,
            'text': text,
            'is_group': False,
            'created_at': msg.get('created_at', ''),
        }
        # Emit to receiver's room and back to sender
        print(f'[socket] emitting to user_{receiver_id} and user_{sender_id}')
        emit('new_message', payload, to=f'user_{receiver_id}')
        emit('new_message', payload, to=f'user_{sender_id}')
        # Push notification when receiver is not connected via WebSocket
        if receiver_id not in online_users:
            preview = text[:60] + ('…' if len(text) > 60 else '')
            send_push(receiver_id, f"New message from {sender.get('name', 'Someone')}", preview, '/chat')

    # ── Group Chat ────────────────────────────────────────────────────────────

    @socketio.on('join_group')
    def on_join_group(data):
        group_id = data.get('group_id', '')
        if group_id:
            join_room(f'group_{group_id}')
            emit('joined_group', {'group_id': group_id})

    @socketio.on('leave_group')
    def on_leave_group(data):
        group_id = data.get('group_id', '')
        if group_id:
            leave_room(f'group_{group_id}')

    @socketio.on('send_group_message')
    def on_send_group_message(data):
        """
        data: { token, group_id, text }
        """
        try:
            decoded = decode_token(data.get('token', ''))
            sender_id = decoded['sub']
        except Exception:
            emit('error', {'message': 'Unauthorized'})
            return

        group_id = data.get('group_id', '')
        text = data.get('text', '').strip()
        if not group_id or not text:
            return

        if not db.group_members.find_one(group_id=group_id, user_id=sender_id):
            emit('error', {'message': 'Not a group member'})
            return

        msg = db.messages.insert({
            'sender_id': sender_id, 'receiver_id': '', 'group_id': group_id,
            'text': text, 'is_group': 'True', 'is_read': 'False',
        })
        sender = db.users.find_by_id(sender_id)
        payload = {
            'id': msg['id'],
            'group_id': group_id,
            'sender': {'id': sender_id, 'name': sender.get('name', ''),
                       'profile_pic': sender.get('profile_pic', '')},
            'text': text,
            'is_group': True,
            'created_at': msg.get('created_at', ''),
        }
        emit('new_group_message', payload, to=f'group_{group_id}')

    # ── Typing indicators ─────────────────────────────────────────────────────

    @socketio.on('typing')
    def on_typing(data):
        """data: { token, receiver_id, is_typing }"""
        try:
            decoded = decode_token(data.get('token', ''))
            sender_id = decoded['sub']
            sender = db.users.find_by_id(sender_id)
            emit('user_typing', {
                'sender_id': sender_id,
                'sender_name': sender.get('name', ''),
                'is_typing': data.get('is_typing', False),
            }, to=f"user_{data.get('receiver_id', '')}")
        except Exception:
            pass

    @socketio.on('group_typing')
    def on_group_typing(data):
        """data: { token, group_id, is_typing }"""
        try:
            decoded = decode_token(data.get('token', ''))
            sender_id = decoded['sub']
            sender = db.users.find_by_id(sender_id)
            emit('group_user_typing', {
                'sender_id': sender_id,
                'sender_name': sender.get('name', ''),
                'is_typing': data.get('is_typing', False),
            }, to=f"group_{data.get('group_id', '')}")
        except Exception:
            pass

    # ── Notifications ─────────────────────────────────────────────────────────

    @socketio.on('mark_notification_read')
    def on_mark_read(data):
        notif_id = data.get('notification_id', '')
        if notif_id:
            db.notifications.update_by_id(notif_id, {'is_read': 'True'})

    return socketio
