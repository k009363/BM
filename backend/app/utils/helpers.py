import os
import cloudinary
import cloudinary.uploader

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _cloudinary_creds():
    """Return Cloudinary credentials — DB settings override env vars."""
    try:
        from app.database.mongo_db import db
        cfg = db.site_config.find_one(key='cloudinary')
        if cfg and cfg.get('cloud_name') and cfg.get('api_key') and cfg.get('api_secret'):
            return cfg['cloud_name'], cfg['api_key'], cfg['api_secret']
    except Exception:
        pass
    return (
        os.getenv('CLOUDINARY_CLOUD_NAME'),
        os.getenv('CLOUDINARY_API_KEY'),
        os.getenv('CLOUDINARY_API_SECRET'),
    )


def save_upload(file, folder: str) -> str:
    """Upload a file to Cloudinary and return its secure URL."""
    if not file or not allowed_file(file.filename):
        return ''
    cloud_name, api_key, api_secret = _cloudinary_creds()
    cloudinary.config(cloud_name=cloud_name, api_key=api_key, api_secret=api_secret)
    result = cloudinary.uploader.upload(
        file,
        folder=f'blog_media/{folder}',
        resource_type='image',
    )
    return result.get('secure_url', '')


def paginate(items: list, page: int = 1, per_page: int = 10) -> dict:
    total = len(items)
    start = (page - 1) * per_page
    end = start + per_page
    return {
        'items': items[start:end],
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page,
    }
