from flask import Blueprint, jsonify, g, request, current_app
from app.utils.decorators import pi_key_required
from app.services import redis_service
from app.services import minio_service
from app.models import Photo
from app import db
import datetime

pi_bp = Blueprint('pi', __name__)

@pi_bp.route('/heartbeat', methods=['POST'])
@pi_key_required
def heartbeat():
    """
    Pi device heartbeat endpoint.
    Updates the last_seen timestamp to monitor device health.
    Pi should call this every 30 seconds.
    """
    # g.pi_device is from the decorator
    g.pi_device.last_seen = datetime.datetime.utcnow()
    db.session.commit()
    
    current_app.logger.debug(f"Heartbeat from Pi device {g.pi_device.id} ({g.pi_device.name})")
    
    return jsonify({
        "status": "ok", 
        "device_id": g.pi_device.id,
        "device_name": g.pi_device.name,
        "timestamp": g.pi_device.last_seen.isoformat()
    }), 200

@pi_bp.route('/get-session-qr', methods=['GET'])
@pi_key_required
def get_session_qr():
    """
    Generate a new session key for QR code display.
    This session key is used to link a mobile user to this Pi device.
    
    The Pi should:
    1. Call this endpoint to get a session key
    2. Generate a QR code with: dots://link?session={session_key}
    3. Display the QR code for users to scan
    4. Refresh every 60 seconds or after a photo is taken
    """
    # g.pi_device is from the decorator
    session_key = redis_service.create_pi_session(g.pi_device.id)
    
    current_app.logger.info(f"New session created for Pi device {g.pi_device.id}: {session_key}")
    
    return jsonify({
        "session_key": session_key,
        "device_id": g.pi_device.id,
        "device_name": g.pi_device.name,
        "qr_url": f"dots://link?session={session_key}"
    }), 200

@pi_bp.route('/listen-for-trigger', methods=['GET'])
@pi_key_required
def listen_for_trigger():
    """
    Long-polling endpoint for trigger listening.
    
    The Pi should continuously call this endpoint in a loop:
    1. This call will BLOCK for up to 30 seconds
    2. If a trigger is received, returns {"action": "trigger"}
    3. If timeout (no trigger), returns 204 No Content
    4. Pi should immediately call this again after handling
    
    This creates a continuous listening mechanism without constant polling.
    """
    # This is a long-polling endpoint
    # It will block until a message is received from Redis Pub/Sub
    pi_device_id = g.pi_device.id
    current_app.logger.debug(f"Pi device {pi_device_id} ({g.pi_device.name}) listening for trigger...")
    
    try:
        # Subscribe and wait (blocks for ~30 seconds)
        message = redis_service.subscribe_to_triggers(pi_device_id)
        
        if message == "trigger_photo":
            current_app.logger.info(f"🎯 TRIGGER received for Pi device {pi_device_id} ({g.pi_device.name})")
            return jsonify({
                "action": "trigger",
                "device_id": pi_device_id,
                "device_name": g.pi_device.name
            }), 200
        else:
            # Timeout - no message received
            current_app.logger.debug(f"Listen timeout for Pi device {pi_device_id}, reconnecting...")
            
    except Exception as e:
        current_app.logger.error(f"❌ Error in listen_for_trigger for Pi {pi_device_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500
    
    # Fallback for timeout - return 204 (no content)
    return jsonify({"action": "none"}), 204

@pi_bp.route('/upload-photo', methods=['POST'])
@pi_key_required
def upload_photo():
    """
    Upload a captured photo to storage.
    
    Required:
    - session_key: The active session key (from QR code)
    - image: The photo file (multipart/form-data)
    
    Process:
    1. Validate session is linked to a user
    2. Upload photo to MinIO (S3-compatible storage)
    3. Save photo metadata to PostgreSQL
    4. Return success with object name
    """
    session_key = request.form.get('session_key')
    
    # Validation
    if 'image' not in request.files:
        current_app.logger.error(f"Pi device {g.pi_device.id}: No image file in upload request")
        return jsonify({"error": "No image file provided"}), 400
        
    file = request.files['image']
    if not session_key:
        current_app.logger.error(f"Pi device {g.pi_device.id}: No session key in upload request")
        return jsonify({"error": "Missing session key"}), 400
        
    # Validate session
    session_data = redis_service.get_session_data(session_key)
    if not session_data or not session_data.get('user_id'):
        current_app.logger.error(f"Pi device {g.pi_device.id}: Invalid session {session_key}")
        return jsonify({"error": "Invalid or unlinked session"}), 400

    user_id = session_data['user_id']
    pi_device_id = session_data.get('pi_device_id')
    
    # Security check: ensure photo is being uploaded by the correct Pi
    if pi_device_id != g.pi_device.id:
        current_app.logger.error(
            f"Pi device {g.pi_device.id} tried to upload for session belonging to Pi {pi_device_id}"
        )
        return jsonify({"error": "Session does not belong to this device"}), 403
    
    current_app.logger.info(
        f"📤 Uploading photo from Pi {g.pi_device.id} ({g.pi_device.name}) "
        f"for user {user_id}, session {session_key}"
    )
    
    # Get file stream and length for MinIO
    file.stream.seek(0, 2)  # Seek to end to get length
    file_length = file.stream.tell()
    file.stream.seek(0)  # Reset stream pointer to beginning
    
    current_app.logger.debug(f"Photo size: {file_length} bytes")
    
    # Upload to MinIO
    object_name = minio_service.upload_photo_to_minio(
        file.stream, 
        file_length, 
        user_id
    )
    
    if not object_name:
        current_app.logger.error(f"Failed to upload photo to MinIO for user {user_id}")
        return jsonify({"error": "Failed to upload to storage"}), 500
        
    # Save metadata to Postgres
    new_photo = Photo(
        user_id=user_id,
        minio_object_name=object_name
    )
    db.session.add(new_photo)
    db.session.commit()
    
    current_app.logger.info(
        f"✅ Photo uploaded successfully! "
        f"User: {user_id}, Photo ID: {new_photo.id}, Object: {object_name}"
    )
    
    return jsonify({
        "status": "success", 
        "photo_id": new_photo.id,
        "object_name": object_name,
        "user_id": user_id
    }), 201

@pi_bp.route('/session-status/<session_key>', methods=['GET'])
@pi_key_required
def check_session_status(session_key):
    """
    Check the status of a session.
    
    Useful for:
    - Debugging session issues
    - Checking if a session has been linked by a user
    - Monitoring session lifecycle
    
    Returns:
    - Session data if exists
    - 404 if session not found or expired
    """
    session_data = redis_service.get_session_data(session_key)
    
    if not session_data:
        current_app.logger.debug(f"Session {session_key} not found or expired")
        return jsonify({
            "error": "Session not found or expired",
            "session_key": session_key
        }), 404
    
    # Check if this session belongs to this Pi device
    if session_data.get('pi_device_id') != g.pi_device.id:
        current_app.logger.warning(
            f"Pi device {g.pi_device.id} tried to check session belonging to Pi {session_data.get('pi_device_id')}"
        )
        return jsonify({
            "error": "Session does not belong to this device"
        }), 403
    
    # Get remaining TTL
    from app import redis_client
    ttl = redis_client.ttl(f"session:{session_key}")
    
    return jsonify({
        "session_key": session_key,
        "pi_device_id": session_data.get('pi_device_id'),
        "user_id": session_data.get('user_id'),
        "status": session_data.get('status'),
        "is_linked": session_data.get('user_id') is not None,
        "ttl_seconds": ttl if ttl > 0 else 0
    }), 200

