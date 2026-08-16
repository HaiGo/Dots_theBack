"""
Standardized API response codes and messages for frontend
"""

# Authentication Error Codes
AUTH_INVALID_CREDENTIALS = {
    "code": "AUTH_INVALID_CREDENTIALS",
    "message": "Invalid email or password"
}

AUTH_EMAIL_NOT_VERIFIED = {
    "code": "AUTH_EMAIL_NOT_VERIFIED",
    "message": "Email not verified. Please check your inbox."
}

AUTH_USER_NOT_FOUND = {
    "code": "AUTH_USER_NOT_FOUND",
    "message": "User not found"
}

AUTH_EMAIL_ALREADY_EXISTS = {
    "code": "AUTH_EMAIL_ALREADY_EXISTS",
    "message": "Email already registered"
}

AUTH_USERID_ALREADY_EXISTS = {
    "code": "AUTH_USERID_ALREADY_EXISTS",
    "message": "Username already taken"
}

AUTH_PHONE_ALREADY_EXISTS = {
    "code": "AUTH_PHONE_ALREADY_EXISTS",
    "message": "Phone number already registered"
}

AUTH_MISSING_FIELDS = {
    "code": "AUTH_MISSING_FIELDS",
    "message": "Required fields are missing"
}

AUTH_PASSWORD_TOO_SHORT = {
    "code": "AUTH_PASSWORD_TOO_SHORT",
    "message": "Password must be at least 6 characters"
}

AUTH_CURRENT_PASSWORD_INCORRECT = {
    "code": "AUTH_CURRENT_PASSWORD_INCORRECT",
    "message": "Current password is incorrect"
}

AUTH_TOKEN_INVALID = {
    "code": "AUTH_TOKEN_INVALID",
    "message": "Invalid or expired token"
}

AUTH_PASSWORD_RESET_CODE_INVALID = {
    "code": "AUTH_PASSWORD_RESET_CODE_INVALID",
    "message": "Invalid reset code. Please check the code or request a new one."
}

AUTH_PASSWORD_RESET_CODE_EXPIRED = {
    "code": "AUTH_PASSWORD_RESET_CODE_EXPIRED",
    "message": "Reset code has expired. Please request a new one."
}

# Profile Error Codes
PROFILE_PICTURE_INVALID_FORMAT = {
    "code": "PROFILE_PICTURE_INVALID_FORMAT",
    "message": "Invalid image format. Allowed: png, jpg, jpeg, gif, webp"
}

PROFILE_PICTURE_UPLOAD_FAILED = {
    "code": "PROFILE_PICTURE_UPLOAD_FAILED",
    "message": "Failed to upload profile picture"
}

PROFILE_PICTURE_MISSING = {
    "code": "PROFILE_PICTURE_MISSING",
    "message": "No image file provided"
}

# Social Error Codes
SOCIAL_USER_NOT_FOUND = {
    "code": "SOCIAL_USER_NOT_FOUND",
    "message": "User not found"
}

SOCIAL_FRIEND_NOT_FOUND = {
    "code": "SOCIAL_FRIEND_NOT_FOUND",
    "message": "Friend not found"
}

SOCIAL_FRIENDSHIP_EXISTS = {
    "code": "SOCIAL_FRIENDSHIP_EXISTS",
    "message": "You are already friends"
}

SOCIAL_CANNOT_ADD_SELF = {
    "code": "SOCIAL_CANNOT_ADD_SELF",
    "message": "Cannot add yourself as a friend"
}

SOCIAL_MUST_BE_FRIENDS = {
    "code": "SOCIAL_MUST_BE_FRIENDS",
    "message": "You must be friends to share location"
}

# Location Error Codes
LOCATION_INVALID_COORDINATES = {
    "code": "LOCATION_INVALID_COORDINATES",
    "message": "Invalid coordinates. Latitude: -90 to 90, Longitude: -180 to 180"
}

LOCATION_MISSING_FIELDS = {
    "code": "LOCATION_MISSING_FIELDS",
    "message": "Latitude and longitude are required"
}

LOCATION_PERMISSION_EXISTS = {
    "code": "LOCATION_PERMISSION_EXISTS",
    "message": "Location sharing permission already exists"
}

# Validation Error Codes
VALIDATION_INVALID_INPUT = {
    "code": "VALIDATION_INVALID_INPUT",
    "message": "Invalid input data"
}

VALIDATION_PHONE_LIST_REQUIRED = {
    "code": "VALIDATION_PHONE_LIST_REQUIRED",
    "message": "Phone numbers list is required"
}

VALIDATION_PHONE_LIST_TOO_LARGE = {
    "code": "VALIDATION_PHONE_LIST_TOO_LARGE",
    "message": "Maximum 500 phone numbers allowed"
}

# Success Codes
SUCCESS_USER_REGISTERED = {
    "code": "SUCCESS_USER_REGISTERED",
    "message": "User registered successfully"
}

SUCCESS_EMAIL_VERIFICATION_SENT = {
    "code": "SUCCESS_EMAIL_VERIFICATION_SENT",
    "message": "Verification email sent. Please check your inbox."
}

SUCCESS_LOGIN = {
    "code": "SUCCESS_LOGIN",
    "message": "Login successful"
}

SUCCESS_PASSWORD_UPDATED = {
    "code": "SUCCESS_PASSWORD_UPDATED",
    "message": "Password updated successfully"
}

SUCCESS_PROFILE_UPDATED = {
    "code": "SUCCESS_PROFILE_UPDATED",
    "message": "Profile updated successfully"
}

SUCCESS_PROFILE_PICTURE_UPLOADED = {
    "code": "SUCCESS_PROFILE_PICTURE_UPLOADED",
    "message": "Profile picture uploaded successfully"
}

SUCCESS_FRIEND_ADDED = {
    "code": "SUCCESS_FRIEND_ADDED",
    "message": "Friend added successfully"
}

SUCCESS_FRIEND_REMOVED = {
    "code": "SUCCESS_FRIEND_REMOVED",
    "message": "Friend removed successfully"
}

SUCCESS_LOCATION_UPDATED = {
    "code": "SUCCESS_LOCATION_UPDATED",
    "message": "Location updated successfully"
}

SUCCESS_LOCATION_SETTINGS_UPDATED = {
    "code": "SUCCESS_LOCATION_SETTINGS_UPDATED",
    "message": "Location sharing settings updated"
}

SUCCESS_PASSWORD_RESET_EMAIL_SENT = {
    "code": "SUCCESS_PASSWORD_RESET_EMAIL_SENT",
    "message": "Password reset email sent. Please check your inbox."
}

SUCCESS_PASSWORD_RESET = {
    "code": "SUCCESS_PASSWORD_RESET",
    "message": "Password reset successfully. You can now login with your new password."
}


def error_response(error_dict, status_code=400, extra_data=None):
    """Create standardized error response"""
    response = {
        "success": False,
        "error": {
            "code": error_dict["code"],
            "message": error_dict["message"]
        }
    }
    if extra_data:
        response["error"].update(extra_data)
    return response, status_code


def success_response(success_dict, data=None, status_code=200):
    """Create standardized success response"""
    response = {
        "success": True,
        "code": success_dict["code"],
        "message": success_dict["message"]
    }
    if data:
        response["data"] = data
    return response, status_code

