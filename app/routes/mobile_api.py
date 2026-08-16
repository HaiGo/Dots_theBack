from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services import redis_service
from app.models import Photo
from app.services import minio_service
from app import db
from io import BytesIO

mobile_bp = Blueprint('mobile', __name__)

@mobile_bp.route('/start-session', methods=['POST'])
@jwt_required()
def start_session():
    user_id = int(get_jwt_identity())  # Convert back to int
    data = request.get_json()
    session_key = data.get('session_key')
    
    if not session_key:
        return jsonify({"error": "Session key is required"}), 400
        
    success, message = redis_service.link_user_to_session(session_key, user_id)
    if not success:
        return jsonify({"error": message}), 404
        
    return jsonify({"message": "Session linked successfully"}), 200

@mobile_bp.route('/trigger-photo', methods=['POST'])
@jwt_required()
def trigger_photo():
    from flask import current_app
    
    data = request.get_json()
    session_key = data.get('session_key')
    
    current_app.logger.info(f"Trigger requested for session: {session_key}")
    
    session_data = redis_service.get_session_data(session_key)
    if not session_data or session_data['user_id'] != int(get_jwt_identity()):
        current_app.logger.error(f"Invalid session or not authorized. Session data: {session_data}")
        return jsonify({"error": "Invalid session or not authorized"}), 403
        
    pi_device_id = session_data.get('pi_device_id')
    if not pi_device_id:
        current_app.logger.error(f"No Pi device ID in session")
        return jsonify({"error": "Session is not linked to a Pi device"}), 500
    
    current_app.logger.info(f"Publishing trigger to Pi device {pi_device_id}")
    redis_service.publish_trigger(pi_device_id)
    current_app.logger.info(f"Trigger published successfully to channel: pi_trigger:{pi_device_id}")
    
    return jsonify({"status": "triggered", "pi_device_id": pi_device_id}), 200

@mobile_bp.route('/gallery', methods=['GET'])
@jwt_required()
def get_gallery():
    user_id = int(get_jwt_identity())  # Convert back to int
    photos = Photo.query.filter_by(user_id=user_id).order_by(Photo.created_at.desc()).all()
    
    gallery_data = []
    for photo in photos:
        gallery_data.append({
            "id": photo.id,
            "url": minio_service.get_public_photo_url(photo.minio_object_name),
            "created_at": photo.created_at.isoformat()
        })
    
    return jsonify({
        "success": True,
        "code": "SUCCESS_GALLERY_RETRIEVED",
        "message": "Gallery retrieved successfully",
        "data": {
            "photos": gallery_data,
            "count": len(gallery_data)
        }
    }), 200

@mobile_bp.route('/upload-photo', methods=['POST'])
@jwt_required()
def upload_photo():
    """Upload photo directly from mobile device to user's gallery"""
    user_id = int(get_jwt_identity())
    
    if 'image' not in request.files:
        return jsonify({
            "success": False,
            "error": {
                "code": "PHOTO_MISSING",
                "message": "No image file provided"
            }
        }), 400
    
    image_file = request.files['image']
    
    if image_file.filename == '':
        return jsonify({
            "success": False,
            "error": {
                "code": "PHOTO_MISSING",
                "message": "No image file selected"
            }
        }), 400
    
    # Validate file type
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    file_ext = image_file.filename.rsplit('.', 1)[1].lower() if '.' in image_file.filename else ''
    
    if file_ext not in allowed_extensions:
        return jsonify({
            "success": False,
            "error": {
                "code": "PHOTO_INVALID_FORMAT",
                "message": "Invalid file type. Allowed: png, jpg, jpeg, gif, webp"
            }
        }), 400
    
    try:
        # Read file content
        image_file.seek(0)
        file_content = image_file.read()
        file_length = len(file_content)
        
        # Create file stream
        file_stream = BytesIO(file_content)
        
        # Upload to MinIO
        object_name = minio_service.upload_photo_to_minio(file_stream, file_length, user_id)
        
        if not object_name:
            return jsonify({
                "success": False,
                "error": {
                    "code": "PHOTO_UPLOAD_FAILED",
                    "message": "Failed to upload image"
                }
            }), 500
        
        # Create photo record
        photo = Photo(user_id=user_id, minio_object_name=object_name)
        db.session.add(photo)
        db.session.commit()
        
        # Get public URL
        photo_url = minio_service.get_public_photo_url(object_name)
        
        current_app.logger.info(f"✅ Photo uploaded by user {user_id}: {object_name}")
        
        return jsonify({
            "success": True,
            "code": "SUCCESS_PHOTO_UPLOADED",
            "message": "Photo uploaded successfully",
            "data": {
                "photo_id": photo.id,
                "url": photo_url,
                "created_at": photo.created_at.isoformat()
            }
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Error uploading photo from mobile: {e}")
        return jsonify({
            "success": False,
            "error": {
                "code": "PHOTO_UPLOAD_FAILED",
                "message": "Failed to upload photo"
            }
        }), 500

@mobile_bp.route('/delete-photo/<int:photo_id>', methods=['DELETE'])
@jwt_required()
def delete_photo(photo_id):
    """Delete a photo from user's gallery"""
    user_id = int(get_jwt_identity())
    
    photo = Photo.query.get(photo_id)
    
    if not photo:
        return jsonify({
            "success": False,
            "error": {
                "code": "PHOTO_NOT_FOUND",
                "message": "Photo not found"
            }
        }), 404
    
    # Check ownership
    if photo.user_id != user_id:
        return jsonify({
            "success": False,
            "error": {
                "code": "PHOTO_NOT_AUTHORIZED",
                "message": "You don't have permission to delete this photo"
            }
        }), 403
    
    try:
        # Delete from MinIO
        minio_service.delete_photo_from_minio(photo.minio_object_name)
        
        # Delete from database
        db.session.delete(photo)
        db.session.commit()
        
        current_app.logger.info(f"✅ Photo deleted by user {user_id}: {photo_id}")
        
        return jsonify({
            "success": True,
            "code": "SUCCESS_PHOTO_DELETED",
            "message": "Photo deleted successfully"
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error deleting photo: {e}")
        return jsonify({
            "success": False,
            "error": {
                "code": "PHOTO_DELETE_FAILED",
                "message": "Failed to delete photo"
            }
        }), 500

