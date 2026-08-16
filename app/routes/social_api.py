from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import User, Friendship, LocationSharingPermission
from app.services import minio_service
import datetime
import uuid
from werkzeug.utils import secure_filename

social_bp = Blueprint('social', __name__)


@social_bp.route('/search-user', methods=['GET'])
@jwt_required()
def search_user():
    """Smart search for users by userid with fuzzy matching"""
    query = request.args.get('query') or request.args.get('userid')
    limit = request.args.get('limit', 10, type=int)
    
    if not query:
        return jsonify({
            "success": False,
            "error": {
                "code": "VALIDATION_MISSING_QUERY",
                "message": "Search query is required"
            }
        }), 400
    
    # Limit results to prevent abuse
    if limit > 50:
        limit = 50
    
    # Smart search: exact match first, then partial matches
    users = []
    
    # 1. Exact match
    exact_match = User.query.filter_by(userid=query).first()
    if exact_match:
        users.append(exact_match)
    
    # 2. Starts with query (case insensitive)
    if len(users) < limit:
        starts_with = User.query.filter(
            User.userid.ilike(f"{query}%"),
            User.userid != query  # Exclude exact match already added
        ).limit(limit - len(users)).all()
        users.extend(starts_with)
    
    # 3. Contains query (case insensitive)
    if len(users) < limit:
        contains = User.query.filter(
            User.userid.ilike(f"%{query}%"),
            ~User.userid.ilike(f"{query}%")  # Exclude already added
        ).limit(limit - len(users)).all()
        users.extend(contains)
    
    if not users:
        return jsonify({
            "success": True,
            "code": "SEARCH_NO_RESULTS",
            "message": "No users found",
            "data": {
                "users": [],
                "count": 0,
                "query": query
            }
        }), 200
    
    return jsonify({
        "success": True,
        "code": "SEARCH_SUCCESS",
        "message": f"Found {len(users)} user(s)",
        "data": {
            "users": [user.to_dict() for user in users],
            "count": len(users),
            "query": query
        }
    }), 200


@social_bp.route('/update-userid', methods=['PUT'])
@jwt_required()
def update_userid():
    """Update the userid for the authenticated user"""
    current_user_id = int(get_jwt_identity())
    data = request.get_json()
    new_userid = data.get('userid')
    
    if not new_userid:
        return jsonify({"error": "userid is required"}), 400
    
    # Check if the new userid is already taken
    existing_user = User.query.filter_by(userid=new_userid).first()
    if existing_user and existing_user.id != current_user_id:
        return jsonify({"error": "User ID already taken"}), 409
    
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    user.userid = new_userid
    db.session.commit()
    
    return jsonify({
        "message": "User ID updated successfully",
        "user": user.to_dict()
    }), 200


@social_bp.route('/update-location', methods=['POST'])
@jwt_required()
def update_location():
    """Update the current location of the authenticated user"""
    current_user_id = int(get_jwt_identity())
    data = request.get_json()
    
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    
    if latitude is None or longitude is None:
        return jsonify({"error": "latitude and longitude are required"}), 400
    
    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid latitude or longitude format"}), 400
    
    # Validate latitude and longitude ranges
    if not (-90 <= latitude <= 90):
        return jsonify({"error": "Latitude must be between -90 and 90"}), 400
    if not (-180 <= longitude <= 180):
        return jsonify({"error": "Longitude must be between -180 and 180"}), 400
    
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    user.latitude = latitude
    user.longitude = longitude
    user.last_location_update = datetime.datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        "message": "Location updated successfully",
        "location": {
            "latitude": user.latitude,
            "longitude": user.longitude,
            "last_update": user.last_location_update.isoformat()
        }
    }), 200


@social_bp.route('/add-friend', methods=['POST'])
@jwt_required()
def add_friend():
    """Add a friend connection between users"""
    current_user_id = int(get_jwt_identity())
    data = request.get_json()
    
    friend_userid = data.get('friend_userid')
    friend_id = data.get('friend_id')
    
    # Find friend by userid or id
    if friend_userid:
        friend = User.query.filter_by(userid=friend_userid).first()
    elif friend_id:
        friend = User.query.get(friend_id)
    else:
        return jsonify({"error": "friend_userid or friend_id is required"}), 400
    
    if not friend:
        return jsonify({"error": "Friend user not found"}), 404
    
    if friend.id == current_user_id:
        return jsonify({"error": "Cannot add yourself as a friend"}), 400
    
    # Check if friendship already exists
    existing_friendship = Friendship.query.filter(
        ((Friendship.user_id == current_user_id) & (Friendship.friend_id == friend.id)) |
        ((Friendship.user_id == friend.id) & (Friendship.friend_id == current_user_id))
    ).first()
    
    if existing_friendship:
        return jsonify({"error": "Friendship already exists"}), 409
    
    # Create bidirectional friendship
    friendship1 = Friendship(user_id=current_user_id, friend_id=friend.id)
    friendship2 = Friendship(user_id=friend.id, friend_id=current_user_id)
    
    db.session.add(friendship1)
    db.session.add(friendship2)
    db.session.commit()
    
    return jsonify({
        "message": "Friend added successfully",
        "friend": friend.to_dict()
    }), 201


@social_bp.route('/remove-friend', methods=['DELETE'])
@jwt_required()
def remove_friend():
    """Remove a friend connection"""
    current_user_id = int(get_jwt_identity())
    data = request.get_json()
    
    friend_userid = data.get('friend_userid')
    friend_id = data.get('friend_id')
    
    # Find friend by userid or id
    if friend_userid:
        friend = User.query.filter_by(userid=friend_userid).first()
    elif friend_id:
        friend = User.query.get(friend_id)
    else:
        return jsonify({"error": "friend_userid or friend_id is required"}), 400
    
    if not friend:
        return jsonify({"error": "Friend user not found"}), 404
    
    # Remove both sides of the friendship
    Friendship.query.filter(
        ((Friendship.user_id == current_user_id) & (Friendship.friend_id == friend.id)) |
        ((Friendship.user_id == friend.id) & (Friendship.friend_id == current_user_id))
    ).delete()
    
    db.session.commit()
    
    return jsonify({"message": "Friend removed successfully"}), 200


@social_bp.route('/friends', methods=['GET'])
@jwt_required()
def get_friends():
    """Get list of user's friends with their locations (respects privacy settings)"""
    current_user_id = int(get_jwt_identity())
    
    # Get all friendships for the current user
    friendships = Friendship.query.filter_by(user_id=current_user_id).all()
    
    friends_list = []
    for friendship in friendships:
        friend = User.query.get(friendship.friend_id)
        if friend:
            # Pass requesting_user_id for privacy checks
            friends_list.append(friend.to_dict(include_location=True, requesting_user_id=current_user_id))
    
    return jsonify({
        "count": len(friends_list),
        "friends": friends_list
    }), 200


@social_bp.route('/find-by-phones', methods=['POST'])
@jwt_required()
def find_by_phones():
    """Find users by a list of phone numbers"""
    data = request.get_json()
    phone_numbers = data.get('phone_numbers', [])
    
    if not isinstance(phone_numbers, list):
        return jsonify({"error": "phone_numbers must be a list"}), 400
    
    if not phone_numbers:
        return jsonify({"error": "phone_numbers list cannot be empty"}), 400
    
    # Limit the number of phone numbers to prevent abuse
    if len(phone_numbers) > 500:
        return jsonify({"error": "Maximum 500 phone numbers allowed per request"}), 400
    
    # Find users with matching phone numbers
    users = User.query.filter(User.phone_number.in_(phone_numbers)).all()
    
    users_list = [user.to_dict() for user in users]
    
    return jsonify({
        "count": len(users_list),
        "users": users_list
    }), 200


@social_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get the current user's profile"""
    current_user_id = int(get_jwt_identity())
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    return jsonify(user.to_dict(include_location=True)), 200


@social_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update user profile information"""
    current_user_id = int(get_jwt_identity())
    data = request.get_json()
    
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Update userid if provided
    if 'userid' in data:
        new_userid = data['userid']
        if new_userid:
            existing_user = User.query.filter_by(userid=new_userid).first()
            if existing_user and existing_user.id != current_user_id:
                return jsonify({"error": "User ID already taken"}), 409
            user.userid = new_userid
    
    # Update phone_number if provided
    if 'phone_number' in data:
        new_phone = data['phone_number']
        if new_phone:
            existing_user = User.query.filter_by(phone_number=new_phone).first()
            if existing_user and existing_user.id != current_user_id:
                return jsonify({"error": "Phone number already registered"}), 409
            user.phone_number = new_phone
    
    db.session.commit()
    
    return jsonify({
        "message": "Profile updated successfully",
        "user": user.to_dict()
    }), 200


@social_bp.route('/upload-profile-picture', methods=['POST'])
@jwt_required()
def upload_profile_picture():
    """Upload profile picture to MinIO"""
    current_user_id = int(get_jwt_identity())
    
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400
    
    image_file = request.files['image']
    
    if image_file.filename == '':
        return jsonify({"error": "No image file selected"}), 400
    
    # Validate file type
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    file_ext = image_file.filename.rsplit('.', 1)[1].lower() if '.' in image_file.filename else ''
    
    if file_ext not in allowed_extensions:
        return jsonify({"error": "Invalid file type. Allowed: png, jpg, jpeg, gif, webp"}), 400
    
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    try:
        # Delete old profile picture if exists
        if user.profile_picture:
            try:
                minio_service.delete_photo_from_minio(user.profile_picture)
            except Exception as e:
                current_app.logger.warning(f"Failed to delete old profile picture: {e}")
        
        # Read file content
        image_file.seek(0)  # Reset file pointer
        file_content = image_file.read()
        file_length = len(file_content)
        
        # Create file stream
        from io import BytesIO
        file_stream = BytesIO(file_content)
        
        # Upload to MinIO
        object_name = minio_service.upload_photo_to_minio(file_stream, file_length, current_user_id)
        
        if not object_name:
            return jsonify({"error": "Failed to upload image"}), 500
        
        # Update user record
        user.profile_picture = object_name
        db.session.commit()
        
        return jsonify({
            "message": "Profile picture uploaded successfully",
            "profile_picture_url": minio_service.get_public_photo_url(object_name)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error uploading profile picture: {e}")
        return jsonify({"error": "Failed to upload profile picture"}), 500


@social_bp.route('/location-sharing-settings', methods=['GET'])
@jwt_required()
def get_location_sharing_settings():
    """Get current location sharing settings"""
    current_user_id = int(get_jwt_identity())
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Get list of friends with selective permissions
    selective_permissions = LocationSharingPermission.query.filter_by(user_id=current_user_id).all()
    selective_friends = []
    
    for permission in selective_permissions:
        friend = User.query.get(permission.friend_id)
        if friend:
            selective_friends.append({
                'id': friend.id,
                'userid': friend.userid,
                'email': friend.email
            })
    
    return jsonify({
        "share_location_globally": user.share_location_globally,
        "selective_sharing_enabled": len(selective_friends) > 0,
        "friends_with_access": selective_friends
    }), 200


@social_bp.route('/location-sharing-settings', methods=['PUT'])
@jwt_required()
def update_location_sharing_settings():
    """Update global location sharing toggle"""
    current_user_id = int(get_jwt_identity())
    data = request.get_json()
    
    share_globally = data.get('share_location_globally')
    
    if share_globally is None:
        return jsonify({"error": "share_location_globally is required"}), 400
    
    if not isinstance(share_globally, bool):
        return jsonify({"error": "share_location_globally must be a boolean"}), 400
    
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    user.share_location_globally = share_globally
    db.session.commit()
    
    return jsonify({
        "message": "Location sharing settings updated successfully",
        "share_location_globally": user.share_location_globally
    }), 200


@social_bp.route('/share-location-with', methods=['POST'])
@jwt_required()
def share_location_with_friend():
    """Add selective location sharing permission for a specific friend"""
    current_user_id = int(get_jwt_identity())
    data = request.get_json()
    
    friend_userid = data.get('friend_userid')
    friend_id = data.get('friend_id')
    
    # Find friend by userid or id
    if friend_userid:
        friend = User.query.filter_by(userid=friend_userid).first()
    elif friend_id:
        friend = User.query.get(friend_id)
    else:
        return jsonify({"error": "friend_userid or friend_id is required"}), 400
    
    if not friend:
        return jsonify({"error": "Friend not found"}), 404
    
    if friend.id == current_user_id:
        return jsonify({"error": "Cannot add yourself"}), 400
    
    # Check if they are friends
    friendship = Friendship.query.filter(
        ((Friendship.user_id == current_user_id) & (Friendship.friend_id == friend.id)) |
        ((Friendship.user_id == friend.id) & (Friendship.friend_id == current_user_id))
    ).first()
    
    if not friendship:
        return jsonify({"error": "You must be friends to share location"}), 400
    
    # Check if permission already exists
    existing_permission = LocationSharingPermission.query.filter_by(
        user_id=current_user_id,
        friend_id=friend.id
    ).first()
    
    if existing_permission:
        return jsonify({"error": "Location sharing permission already exists"}), 409
    
    # Create permission
    permission = LocationSharingPermission(
        user_id=current_user_id,
        friend_id=friend.id
    )
    
    db.session.add(permission)
    db.session.commit()
    
    return jsonify({
        "message": "Location sharing enabled for friend",
        "friend": friend.to_dict()
    }), 201


@social_bp.route('/stop-sharing-location-with', methods=['DELETE'])
@jwt_required()
def stop_sharing_location_with_friend():
    """Remove selective location sharing permission for a specific friend"""
    current_user_id = int(get_jwt_identity())
    data = request.get_json()
    
    friend_userid = data.get('friend_userid')
    friend_id = data.get('friend_id')
    
    # Find friend by userid or id
    if friend_userid:
        friend = User.query.filter_by(userid=friend_userid).first()
    elif friend_id:
        friend = User.query.get(friend_id)
    else:
        return jsonify({"error": "friend_userid or friend_id is required"}), 400
    
    if not friend:
        return jsonify({"error": "Friend not found"}), 404
    
    # Remove permission
    LocationSharingPermission.query.filter_by(
        user_id=current_user_id,
        friend_id=friend.id
    ).delete()
    
    db.session.commit()
    
    return jsonify({"message": "Location sharing disabled for friend"}), 200

