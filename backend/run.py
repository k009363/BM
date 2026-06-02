import os
import socket
from app import create_app, socketio

app = create_app()

def get_public_ip():
    """Get public IP address or hostname."""
    # On Render: use the RENDER_EXTERNAL_URL env var
    external_url = os.getenv('RENDER_EXTERNAL_URL')
    if external_url:
        return external_url.replace('https://', '').replace('http://', '')

    # Fallback: get local IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return 'localhost'

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    env = os.getenv('FLASK_ENV', 'development')
    public_ip = get_public_ip()

    print('\n' + '='*70)
    print('🚀 BlogMedia Backend Server Starting')
    print('='*70)
    print(f'Environment:       {env.upper()}')
    print(f'Host:              0.0.0.0')
    print(f'Port:              {port}')
    print(f'Public IP/URL:     {public_ip}')
    print(f'API Endpoint:      https://{public_ip}/api' if env == 'production' else f'API Endpoint:      http://{public_ip}:{port}/api')
    print(f'Health Check:      https://{public_ip}/api/health' if env == 'production' else f'Health Check:      http://{public_ip}:{port}/api/health')
    print('='*70)
    print('Press CTRL+C to stop the server')
    print('='*70 + '\n')

    socketio.run(app, host='0.0.0.0', port=port, debug=(env=='development'), use_reloader=False, allow_unsafe_werkzeug=True)
