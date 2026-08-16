from functools import wraps
from flask import request, jsonify, g
from app.models import PiDevice

def pi_key_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        device_key = request.headers.get('X-Pi-Device-Key')
        if not device_key:
            return jsonify({"error": "Missing Pi device key header"}), 401
        
        device = PiDevice.query.filter_by(device_key=device_key).first()
        if not device:
            return jsonify({"error": "Invalid Pi device key"}), 401
        
        # Make the device object available to the route
        g.pi_device = device
        return f(*args, **kwargs)
    return decorated_function

