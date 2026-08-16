from flask import Blueprint, request, jsonify, redirect, current_app, make_response
from app import db, mail
from app.models import User, PasswordResetCode
from app.services.email_service import send_verification_email, send_password_reset_email
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature
from app.utils.response_codes import *
import random
import string
import os

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/check-email', methods=['GET'])
def check_email_availability():
    """Check if an email is available for registration"""
    email = request.args.get('email')
    
    if not email:
        return jsonify({
            "error": "Email parameter is required"
        }), 400
    
    existing_user = User.query.filter_by(email=email).first()
    
    return jsonify({
        "email": email,
        "available": existing_user is None
    }), 200


@auth_bp.route('/check-userid', methods=['GET'])
def check_userid_availability():
    """Check if a userid (username) is available for registration"""
    userid = request.args.get('userid')
    
    if not userid:
        return jsonify({
            "error": "Userid parameter is required"
        }), 400
    
    existing_user = User.query.filter_by(userid=userid).first()
    
    return jsonify({
        "userid": userid,
        "available": existing_user is None
    }), 200


@auth_bp.route('/check-phone', methods=['GET'])
def check_phone_availability():
    """Check if a phone number is available for registration"""
    phone_number = request.args.get('phone_number')
    
    if not phone_number:
        return jsonify({
            "error": "Phone number parameter is required"
        }), 400
    
    existing_user = User.query.filter_by(phone_number=phone_number).first()
    
    return jsonify({
        "phone_number": phone_number,
        "available": existing_user is None
    }), 200


@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """Request password reset code via email"""
    data = request.get_json()
    email = data.get('email')
    
    if not email:
        return error_response(AUTH_MISSING_FIELDS, 400)
    
    user = User.query.filter_by(email=email).first()
    
    # For security, always return success even if email doesn't exist
    # This prevents email enumeration attacks
    if not user:
        current_app.logger.info(f"Password reset requested for non-existent email: {email}")
        # Still return success to prevent email enumeration
        return success_response(SUCCESS_PASSWORD_RESET_EMAIL_SENT, {"email": email}, 200)
    
    # Generate 6-digit code
    reset_code = ''.join(random.choices(string.digits, k=6))
    
    # Invalidate any previous unused codes for this email
    PasswordResetCode.query.filter_by(email=email, used=False).update({'used': True})
    
    # Save new code to database
    code_entry = PasswordResetCode(email=email, reset_code=reset_code)
    db.session.add(code_entry)
    db.session.commit()
    
    try:
        send_password_reset_email(user.email, reset_code)
        current_app.logger.info(f"Password reset code sent to: {email}")
        return success_response(SUCCESS_PASSWORD_RESET_EMAIL_SENT, {"email": email}, 200)
    except Exception as e:
        current_app.logger.error(f"Failed to send password reset email: {e}")
        return error_response({
            "code": "EMAIL_SEND_FAILED",
            "message": "Failed to send password reset email. Please try again later."
        }, 500)


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """Reset password using code from email and new password"""
    data = request.get_json()
    email = data.get('email')
    code = data.get('code')
    new_password = data.get('new_password')
    
    if not email or not code or not new_password:
        return error_response(AUTH_MISSING_FIELDS, 400)
    
    # Validate password length
    if len(new_password) < 6:
        return error_response(AUTH_PASSWORD_TOO_SHORT, 400)
    
    # Find the most recent unused code for this email
    code_entry = PasswordResetCode.query.filter_by(
        email=email,
        reset_code=code,
        used=False
    ).order_by(PasswordResetCode.created_at.desc()).first()
    
    if not code_entry:
        current_app.logger.warning(f"Invalid reset code attempted for email: {email}")
        return error_response(AUTH_PASSWORD_RESET_CODE_INVALID, 400)
    
    # Check if code is expired (15 minutes)
    if code_entry.is_expired():
        current_app.logger.warning(f"Expired reset code used for email: {email}")
        return error_response(AUTH_PASSWORD_RESET_CODE_EXPIRED, 400)
    
    # Find user
    user = User.query.filter_by(email=email).first()
    if not user:
        return error_response(AUTH_USER_NOT_FOUND, 404)
    
    # Update password
    user.set_password(new_password)
    
    # Mark code as used
    code_entry.used = True
    
    db.session.commit()
    
    current_app.logger.info(f"✅ Password reset successful for user: {email}")
    
    return success_response(SUCCESS_PASSWORD_RESET, {"email": email}, 200)


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    userid = data.get('userid')  # Optional unique user identifier
    phone_number = data.get('phone_number')  # Optional phone number

    if not email or not password:
        return error_response(AUTH_MISSING_FIELDS, 400)
    
    if User.query.filter_by(email=email).first():
        return error_response(AUTH_EMAIL_ALREADY_EXISTS, 409)
    
    # Check if userid is provided and already exists
    if userid:
        if User.query.filter_by(userid=userid).first():
            return error_response(AUTH_USERID_ALREADY_EXISTS, 409)
    
    # Check if phone number is provided and already exists
    if phone_number:
        if User.query.filter_by(phone_number=phone_number).first():
            return error_response(AUTH_PHONE_ALREADY_EXISTS, 409)

    user = User(email=email, userid=userid, phone_number=phone_number)
    user.set_password(password)
    
    # Check if email verification is enabled
    verify_emails = current_app.config.get('VERIFY_EMAILS', True)
    user.is_verified = not verify_emails  # If verification disabled, set as verified
    
    # Debug logging
    current_app.logger.info(f"DEBUG: Password hash before add: length={len(user.password_hash)}, dollars={user.password_hash.count('$')}")
    current_app.logger.info(f"DEBUG: Hash preview: {user.password_hash[:50]}...")
    
    db.session.add(user)
    
    current_app.logger.info(f"DEBUG: Password hash after add: length={len(user.password_hash)}, dollars={user.password_hash.count('$')}")
    
    db.session.commit()
    
    current_app.logger.info(f"DEBUG: Password hash after commit: length={len(user.password_hash)}, dollars={user.password_hash.count('$')}")
    
    # Only send verification email if verification is enabled
    if verify_emails:
        send_verification_email(user.email)
        return success_response(SUCCESS_EMAIL_VERIFICATION_SENT, {"email": email}, 201)
    else:
        return success_response(SUCCESS_USER_REGISTERED, {"email": email}, 201)

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return error_response(AUTH_MISSING_FIELDS, 400)
    
    user = User.query.filter_by(email=email).first()
    
    if not user:
        current_app.logger.warning(f"Login attempt for non-existent user: {email}")
        return error_response(AUTH_INVALID_CREDENTIALS, 401)
    
    # Log user details for debugging
    current_app.logger.info(f"Login attempt for user: {email} (ID: {user.id}, verified: {user.is_verified})")
    current_app.logger.info(f"Password hash info: length={len(user.password_hash)}, starts_with={user.password_hash[:20]}...")
    
    # Check password
    password_valid = user.check_password(password)
    current_app.logger.info(f"Password check result: {password_valid}")
    
    if not password_valid:
        current_app.logger.warning(f"Invalid password for user: {email}")
        return error_response(AUTH_INVALID_CREDENTIALS, 401)
    
    # Only check verification status if email verification is enabled
    verify_emails = current_app.config.get('VERIFY_EMAILS', True)
    if verify_emails and not user.is_verified:
        current_app.logger.info(f"Unverified user attempted login: {email}")
        return error_response(AUTH_EMAIL_NOT_VERIFIED, 403, {"email": email})
        
    # Create both access and refresh tokens
    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))
    current_app.logger.info(f"✅ Successful login for user: {email} (ID: {user.id})")
    
    return success_response(SUCCESS_LOGIN, {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user_id": user.id,
        "email": user.email,
        "userid": user.userid
    }, 200)

@auth_bp.route('/verify-email', methods=['GET'])
def verify_email():
    token = request.args.get('token')
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    
    try:
        email = serializer.loads(token, salt='email-verification-salt', max_age=3600)
    except (SignatureExpired, BadTimeSignature):
        return jsonify({"error": "Verification link is invalid or has expired."}), 400
        
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "User not found."}), 404
        
    user.is_verified = True
    db.session.commit()
    
    # Return a simple HTML success page for now
    # In production, redirect to your mobile app deep link or website
    success_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Email Verified - Dots</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                margin: 0;
                background: #C1FF72;
            }}
            .container {{
                background: white;
                padding: 3rem;
                border-radius: 16px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                text-align: center;
                max-width: 500px;
            }}
            .checkmark {{
                width: 80px;
                height: 80px;
                border-radius: 50%;
                display: block;
                margin: 0 auto 2rem;
                background: #4CAF50;
                position: relative;
            }}
            .checkmark:after {{
                content: '✓';
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                color: white;
                font-size: 50px;
                font-weight: bold;
            }}
            h1 {{
                color: #333;
                margin-bottom: 1rem;
                font-size: 2rem;
            }}
            p {{
                color: #666;
                font-size: 1.1rem;
                line-height: 1.6;
                margin-bottom: 2rem;
            }}
            .email {{
                background: #f5f5f5;
                padding: 0.5rem 1rem;
                border-radius: 8px;
                color: #1a1a1a;
                font-weight: 600;
                display: inline-block;
                margin: 1rem 0;
            }}
            .next-steps {{
                background: #f9f9f9;
                padding: 1.5rem;
                border-radius: 8px;
                margin-top: 2rem;
                text-align: left;
            }}
            .next-steps h3 {{
                color: #333;
                margin-top: 0;
                font-size: 1.2rem;
            }}
            .next-steps ul {{
                color: #666;
                line-height: 2;
                padding-left: 1.5rem;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="checkmark"></div>
            <h1>Email Verified Successfully! 🎉</h1>
            <p>Your email address has been verified:</p>
            <div class="email">{email}</div>
            <div class="next-steps">
                <h3>Next Steps:</h3>
                <ul>
                    <li>You can now close this window</li>
                    <li>Return to the Dots App!</li>
                    <li>Your account is ready to use!</li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Create proper response with HTML content type
    response = make_response(success_html, 200)
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    return response

@auth_bp.route('/resend-verification', methods=['POST'])
def resend_verification():
    data = request.get_json()
    user = User.query.filter_by(email=data.get('email')).first()
    if user and not user.is_verified:
        send_verification_email(user.email)
        return jsonify({"message": "Verification email resent."}), 200
    return jsonify({"error": "Invalid request"}), 400

@auth_bp.route('/verify-test-user', methods=['POST'])
def verify_test_user():
    """Manually verify a test user (for testing purposes only)"""
    data = request.get_json()
    email = data.get('email')
    secret = data.get('secret')
    
    # Secret read from environment variable to prevent abuse
    expected_secret = os.environ.get('VERIFICATION_SECRET')
    if not expected_secret or secret != expected_secret:
        return jsonify({"error": "Invalid secret"}), 403
    
    if not email:
        return jsonify({"error": "Email is required"}), 400
    
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    if user.is_verified:
        return jsonify({"message": "User already verified"}), 200
    
    user.is_verified = True
    db.session.commit()
    
    current_app.logger.info(f"Test user manually verified: {email}")
    return jsonify({"message": "User verified successfully", "email": email}), 200

@auth_bp.route('/debug-user', methods=['POST'])
def debug_user():
    """Debug endpoint to check user details (for troubleshooting)"""
    data = request.get_json()
    email = data.get('email')
    secret = data.get('secret')
    
    # Secret read from environment variable to prevent abuse
    expected_secret = os.environ.get('VERIFICATION_SECRET')
    if not expected_secret or secret != expected_secret:
        return jsonify({"error": "Invalid secret"}), 403
    
    if not email:
        return jsonify({"error": "Email is required"}), 400
    
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "User not found in database"}), 404
    
    return jsonify({
        "user_id": user.id,
        "email": user.email,
        "userid": user.userid,
        "is_verified": user.is_verified,
        "password_hash_length": len(user.password_hash),
        "password_hash_preview": user.password_hash[:30] + "...",
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "phone_number": user.phone_number,
        "has_profile_picture": bool(user.profile_picture)
    }), 200

@auth_bp.route('/update-password', methods=['PUT'])
def update_password():
    """Update user password (requires JWT authentication)"""
    from functools import wraps
    
    # Apply JWT decorator manually since we can't use it on the function definition
    @jwt_required()
    def _update_password_impl():
        current_user_id = int(get_jwt_identity())
        data = request.get_json()
        
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        if not current_password or not new_password:
            return jsonify({"error": "current_password and new_password are required"}), 400
        
        if len(new_password) < 6:
            return jsonify({"error": "New password must be at least 6 characters"}), 400
        
        user = User.query.get(current_user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Verify current password
        current_app.logger.info(f"Password update attempt for user ID: {current_user_id}")
        current_app.logger.info(f"Current password hash length: {len(user.password_hash)}")
        
        if not user.check_password(current_password):
            current_app.logger.warning(f"Current password check failed for user ID: {current_user_id}")
            return jsonify({"error": "Current password is incorrect"}), 401
        
        # Update password
        current_app.logger.info(f"Updating password for user ID: {current_user_id}")
        old_hash = user.password_hash
        user.set_password(new_password)
        new_hash = user.password_hash
        
        current_app.logger.info(f"Old hash: {old_hash[:30]}...")
        current_app.logger.info(f"New hash: {new_hash[:30]}...")
        current_app.logger.info(f"New hash length: {len(new_hash)}")
        
        db.session.commit()
        current_app.logger.info(f"✅ Password updated successfully for user ID: {current_user_id}")
        
        return jsonify({"message": "Password updated successfully"}), 200
    
    return _update_password_impl()

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """
    Refresh an expired access token using a refresh token.
    
    The client must send the refresh_token in the Authorization header:
    Authorization: Bearer <refresh_token>
    
    Returns a new access_token (refresh_token remains the same).
    """
    current_user_id = get_jwt_identity()
    
    # Verify user still exists
    user = User.query.get(int(current_user_id))
    if not user:
        current_app.logger.warning(f"Refresh attempted for non-existent user ID: {current_user_id}")
        return jsonify({"error": "User not found"}), 404
    
    # Create new access token
    new_access_token = create_access_token(identity=current_user_id)
    current_app.logger.info(f"✅ Token refreshed for user ID: {current_user_id}")
    
    return jsonify({
        "access_token": new_access_token,
        "user_id": user.id,
        "email": user.email,
        "userid": user.userid
    }), 200

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """
    Get current user information and validate token.
    
    Use this endpoint to:
    - Check if a token is still valid
    - Get current user details
    - Verify authentication status
    
    Returns user information if token is valid, 401 if expired/invalid.
    """
    current_user_id = int(get_jwt_identity())
    
    user = User.query.get(current_user_id)
    if not user:
        current_app.logger.warning(f"Token valid but user not found: {current_user_id}")
        return jsonify({"error": "User not found"}), 404
    
    return jsonify({
        "user_id": user.id,
        "email": user.email,
        "userid": user.userid,
        "phone_number": user.phone_number,
        "is_verified": user.is_verified,
        "profile_picture": user.profile_picture,
        "created_at": user.created_at.isoformat() if user.created_at else None
    }), 200

