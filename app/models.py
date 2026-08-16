from app import db
from werkzeug.security import generate_password_hash, check_password_hash
import datetime

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    userid = db.Column(db.String(64), index=True, unique=True, nullable=True)  # Unique user identifier
    phone_number = db.Column(db.String(20), index=True, nullable=True)  # Phone number for contact finding
    password_hash = db.Column(db.String(256))  # Increased to 256 for scrypt hashes
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # Profile
    profile_picture = db.Column(db.String(256), nullable=True)  # MinIO object name
    
    # Location tracking
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    last_location_update = db.Column(db.DateTime, nullable=True)
    share_location_globally = db.Column(db.Boolean, default=True, nullable=False)  # Global location sharing toggle
    
    # Relationships
    photos = db.relationship('Photo', backref='user', lazy=True)
    
    # Friends relationships
    friends = db.relationship(
        'User',
        secondary='friendship',
        primaryjoin='User.id==Friendship.user_id',
        secondaryjoin='User.id==Friendship.friend_id',
        backref=db.backref('friend_of', lazy='dynamic'),
        lazy='dynamic'
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self, include_location=False, requesting_user_id=None):
        """Convert user to dictionary for API responses
        
        Args:
            include_location: Whether to attempt including location data
            requesting_user_id: ID of user requesting this data (for privacy checks)
        """
        from app.services.minio_service import get_public_photo_url
        
        user_dict = {
            'id': self.id,
            'email': self.email,
            'userid': self.userid,
            'phone_number': self.phone_number,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'profile_picture_url': get_public_photo_url(self.profile_picture) if self.profile_picture else None
        }
        
        if include_location:
            # Check if location can be shared
            can_share_location = self._can_share_location_with(requesting_user_id) if requesting_user_id else True
            
            if can_share_location:
                user_dict.update({
                    'latitude': self.latitude,
                    'longitude': self.longitude,
                    'last_location_update': self.last_location_update.isoformat() if self.last_location_update else None
                })
            else:
                user_dict.update({
                    'latitude': None,
                    'longitude': None,
                    'last_location_update': None
                })
        
        return user_dict
    
    def _can_share_location_with(self, requesting_user_id):
        """Check if location can be shared with requesting user"""
        if not requesting_user_id or requesting_user_id == self.id:
            return True  # Always share with self
        
        # If sharing globally, share with all friends
        if self.share_location_globally:
            return True
        
        # Check if user has selective permission
        permission = LocationSharingPermission.query.filter_by(
            user_id=self.id,
            friend_id=requesting_user_id
        ).first()
        
        return permission is not None

class Friendship(db.Model):
    __tablename__ = 'friendship'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    friend_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # Ensure unique friendship pairs and prevent self-friendship
    __table_args__ = (
        db.UniqueConstraint('user_id', 'friend_id', name='unique_friendship'),
        db.CheckConstraint('user_id != friend_id', name='no_self_friendship'),
    )

class LocationSharingPermission(db.Model):
    """Allows users to selectively share location with specific friends when global sharing is off"""
    __tablename__ = 'location_sharing_permission'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # User sharing their location
    friend_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Friend who can see location
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # Ensure unique permissions and prevent self-permission
    __table_args__ = (
        db.UniqueConstraint('user_id', 'friend_id', name='unique_location_permission'),
        db.CheckConstraint('user_id != friend_id', name='no_self_location_permission'),
    )

class PiDevice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # This key is pre-provisioned on the Pi and used for auth
    device_key = db.Column(db.String(128), index=True, unique=True, nullable=False)
    name = db.Column(db.String(64))
    last_seen = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class PasswordResetCode(db.Model):
    """Store one-time password reset codes"""
    __tablename__ = 'password_reset_code'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), index=True, nullable=False)
    reset_code = db.Column(db.String(6), nullable=False)  # 6-digit code
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    used = db.Column(db.Boolean, default=False, nullable=False)
    
    def is_expired(self):
        """Check if code is expired (15 minutes)"""
        expiry_time = self.created_at + datetime.timedelta(minutes=15)
        return datetime.datetime.utcnow() > expiry_time
    
    def is_valid(self):
        """Check if code is valid (not used and not expired)"""
        return not self.used and not self.is_expired()

class Photo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # The object name in Minio, e.g., "user_1/abc123xyz.jpg"
    minio_object_name = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

