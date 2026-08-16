from app import minio_client
from flask import current_app
import uuid
import json
from minio.error import S3Error

def initialize_minio_bucket():
    """
    Initialize Minio bucket at application startup.
    Creates the bucket if it doesn't exist and sets up permissions.
    Returns True if successful, False otherwise.
    """
    if not minio_client:
        current_app.logger.error("Minio client not initialized!")
        return False
    
    bucket_name = current_app.config['MINIO_BUCKET_NAME']
    current_app.logger.info(f"Initializing Minio bucket: {bucket_name}")
    
    try:
        # Try to check if bucket exists
        try:
            exists = minio_client.bucket_exists(bucket_name)
            if exists:
                current_app.logger.info(f"✓ Bucket '{bucket_name}' already exists")
                return True
            else:
                current_app.logger.info(f"Bucket '{bucket_name}' does not exist, creating...")
        except S3Error as check_error:
            current_app.logger.warning(f"Could not check bucket existence: {check_error}")
            current_app.logger.info(f"Attempting to create bucket anyway...")
        
        # Try to create bucket
        try:
            minio_client.make_bucket(bucket_name)
            current_app.logger.info(f"✓ Bucket '{bucket_name}' created successfully!")
        except S3Error as create_error:
            if create_error.code in ['BucketAlreadyOwnedByYou', 'BucketAlreadyExists']:
                current_app.logger.info(f"✓ Bucket '{bucket_name}' already exists")
            else:
                current_app.logger.error(f"✗ Failed to create bucket: {create_error}")
                current_app.logger.error(f"   Error code: {create_error.code}")
                current_app.logger.error(f"   Error message: {create_error.message}")
                current_app.logger.warning("")
                current_app.logger.warning("=" * 80)
                current_app.logger.warning("MINIO BUCKET CREATION FAILED")
                current_app.logger.warning("=" * 80)
                current_app.logger.warning("Your Minio credentials don't have permission to create buckets.")
                current_app.logger.warning("")
                current_app.logger.warning("MANUAL FIX REQUIRED:")
                current_app.logger.warning(f"1. Go to your Railway Minio console")
                current_app.logger.warning(f"2. Log in with your credentials")
                current_app.logger.warning(f"3. Create a bucket named: {bucket_name}")
                current_app.logger.warning(f"4. Set the bucket to 'public' or allow read access")
                current_app.logger.warning(f"5. Restart this Flask server")
                current_app.logger.warning("=" * 80)
                current_app.logger.warning("")
                return False
        
        # Try to set bucket policy (optional - don't fail if this doesn't work)
        try:
            policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"AWS": ["*"]},
                        "Action": ["s3:GetObject"],
                        "Resource": [f"arn:aws:s3:::{bucket_name}/*"]
                    }
                ]
            }
            minio_client.set_bucket_policy(bucket_name, json.dumps(policy))
            current_app.logger.info(f"✓ Public read policy set for bucket '{bucket_name}'")
        except S3Error as policy_error:
            current_app.logger.warning(f"Could not set bucket policy (this is optional): {policy_error}")
        
        return True
        
    except Exception as e:
        current_app.logger.error(f"Unexpected error during Minio initialization: {e}")
        return False

def upload_photo_to_minio(file_stream, file_length, user_id):
    """Uploads a photo to Minio and returns the object name."""
    bucket_name = current_app.config['MINIO_BUCKET_NAME']
    
    # Bucket should already exist from initialization
    # If not, log an error but try to upload anyway

    # Create a unique object name
    object_name = f"user_{user_id}/{uuid.uuid4()}.jpg"
    
    try:
        minio_client.put_object(
            bucket_name,
            object_name,
            file_stream,
            file_length,
            content_type='image/jpeg'
        )
        return object_name
    except S3Error as e:
        current_app.logger.error(f"Minio upload error: {e}")
        return None

def get_public_photo_url(object_name):
    """Gets the full public URL for a Minio object."""
    if not object_name:
        return None
    # This uses the public-facing endpoint from Railway vars
    public_endpoint = current_app.config['MINIO_PUBLIC_ENDPOINT']
    bucket_name = current_app.config['MINIO_BUCKET_NAME']
    return f"{public_endpoint}/{bucket_name}/{object_name}"

def delete_photo_from_minio(object_name):
    """Deletes a photo from Minio."""
    if not object_name:
        return True
    
    bucket_name = current_app.config['MINIO_BUCKET_NAME']
    
    try:
        minio_client.remove_object(bucket_name, object_name)
        current_app.logger.info(f"Deleted object from Minio: {object_name}")
        return True
    except S3Error as e:
        current_app.logger.error(f"Minio delete error: {e}")
        return False
    except Exception as e:
        current_app.logger.error(f"Unexpected error deleting from Minio: {e}")
        return False

