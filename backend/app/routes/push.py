import os
from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from app.database.mongo_db import db
from app.middleware.auth import jwt_required_custom

push_bp = Blueprint('push', __name__)


@push_bp.route('/vapid-key', methods=['GET'])
def vapid_key():
    return jsonify({'public_key': os.getenv('VAPID_PUBLIC_KEY', '')}), 200


@push_bp.route('/subscribe', methods=['POST'])
@jwt_required_custom
def subscribe():
    uid = get_jwt_identity()
    data = request.get_json() or {}
    endpoint = data.get('endpoint', '')
    keys = data.get('keys', {})
    if not endpoint or not keys.get('p256dh') or not keys.get('auth'):
        return jsonify({'message': 'Invalid subscription data'}), 400
    # upsert: replace any existing record for this endpoint
    db.push_subscriptions.delete_where(endpoint=endpoint)
    db.push_subscriptions.insert({
        'user_id': uid,
        'endpoint': endpoint,
        'p256dh': keys['p256dh'],
        'auth': keys['auth'],
    })
    return jsonify({'message': 'Subscribed'}), 200


@push_bp.route('/unsubscribe', methods=['POST'])
@jwt_required_custom
def unsubscribe():
    uid = get_jwt_identity()
    data = request.get_json() or {}
    endpoint = data.get('endpoint', '')
    if endpoint:
        db.push_subscriptions.delete_where(user_id=uid, endpoint=endpoint)
    else:
        db.push_subscriptions.delete_where(user_id=uid)
    return jsonify({'message': 'Unsubscribed'}), 200
