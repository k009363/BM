from datetime import datetime
from flask import Blueprint, request, jsonify
from app.database.mongo_db import db
from app.middleware.auth import admin_required

config_bp = Blueprint('config', __name__)

SECTIONS = ('main', 'cloudinary', 'push', 'smtp', 'platform', 'security')


# ── Public endpoint (footer data) ────────────────────────────────────────────

@config_bp.route('', methods=['GET'])
def get_config():
    doc = db.site_config.find_one(key='main')
    if not doc:
        return jsonify({'powered_by': '', 'year': str(datetime.utcnow().year)}), 200
    return jsonify({
        'powered_by': doc.get('powered_by', ''),
        'year':       doc.get('year', str(datetime.utcnow().year)),
    }), 200


@config_bp.route('', methods=['PUT'])
@admin_required
def update_config():
    data = request.get_json() or {}
    _upsert('main', {'powered_by': data.get('powered_by', '').strip(),
                     'year':       data.get('year', '').strip()})
    return jsonify({'message': 'Config updated'}), 200


# ── Admin: get ALL settings ───────────────────────────────────────────────────

@config_bp.route('/settings', methods=['GET'])
@admin_required
def get_all_settings():
    result = {}
    for section in SECTIONS:
        doc = db.site_config.find_one(key=section) or {}
        result[section] = {k: v for k, v in doc.items() if k not in ('id', 'key', 'created_at', 'updated_at')}
    return jsonify(result), 200


# ── Admin: update a section ───────────────────────────────────────────────────

@config_bp.route('/settings/<section>', methods=['PUT'])
@admin_required
def update_section(section):
    if section not in SECTIONS:
        return jsonify({'message': 'Unknown settings section'}), 400
    data = request.get_json() or {}

    # For smtp/cloudinary: don't overwrite password/secret with empty string
    # (empty means "keep existing")
    existing = db.site_config.find_one(key=section) or {}
    protected = _protected_fields(section)
    for field in protected:
        if field in data and data[field] == '':
            data[field] = existing.get(field, '')

    _upsert(section, data)
    return jsonify({'message': f'{section} settings saved'}), 200


# ── Admin: test email ─────────────────────────────────────────────────────────

@config_bp.route('/settings/smtp/test', methods=['POST'])
@admin_required
def test_email():
    from app.utils.email_helper import send_email
    d = request.get_json() or {}
    to_email = d.get('to_email', '').strip()
    if not to_email:
        return jsonify({'message': 'to_email required'}), 400
    ok = send_email(
        to_email,
        subject='BlogMedia — SMTP Test',
        body_html='<h2>✅ SMTP is working!</h2><p>This is a test email from your BlogMedia platform.</p>',
        body_text='SMTP is working! This is a test email from your BlogMedia platform.',
    )
    if ok:
        return jsonify({'message': f'Test email sent to {to_email}'}), 200
    return jsonify({'message': 'Failed to send — check SMTP credentials'}), 500


# ── Helpers ───────────────────────────────────────────────────────────────────

def _upsert(key, data):
    existing = db.site_config.find_one(key=key)
    if existing:
        db.site_config.update_by_id(existing['id'], data)
    else:
        db.site_config.insert({'key': key, **data})


def _protected_fields(section):
    return {
        'cloudinary': ['api_secret'],
        'smtp':       ['password'],
    }.get(section, [])
