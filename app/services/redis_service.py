from app import redis_client
from flask import current_app
import shortuuid
import json

def create_pi_session(pi_device_id):
    """
    Creates a new, short-lived session key for a Pi.
    Stores a JSON object in Redis with session data.
    """
    session_key = shortuuid.uuid()[:8].upper()  # e.g., "A8D3F1B9"
    session_data = {
        "pi_device_id": pi_device_id,
        "user_id": None,
        "status": "pending"
    }
    timeout = current_app.config['SESSION_TIMEOUT_SECONDS']
    
    redis_client.setex(
        f"session:{session_key}", 
        timeout, 
        json.dumps(session_data)
    )
    return session_key

def get_session_data(session_key):
    """Retrieves session data from Redis."""
    data = redis_client.get(f"session:{session_key}")
    return json.loads(data) if data else None

def link_user_to_session(session_key, user_id):
    """Links a mobile user to an existing session."""
    data = get_session_data(session_key)
    if not data:
        return False, "Session expired or invalid"
    
    data['user_id'] = user_id
    data['status'] = 'linked'
    timeout = redis_client.ttl(f"session:{session_key}")  # Get remaining time
    
    redis_client.setex(
        f"session:{session_key}",
        timeout,
        json.dumps(data)
    )
    return True, "Session linked"

def publish_trigger(pi_device_id):
    """Publishes a trigger message to the Pi's channel."""
    channel = f"pi_trigger:{pi_device_id}"
    redis_client.publish(channel, "trigger_photo")

def subscribe_to_triggers(pi_device_id, timeout=30):
    """Subscribes to a Pi's trigger channel (for long-polling)."""
    import time
    
    pubsub = redis_client.pubsub()
    channel = f"pi_trigger:{pi_device_id}"
    pubsub.subscribe(channel)
    
    # Skip the subscription confirmation message
    pubsub.get_message()
    
    # Wait for actual message with timeout using polling
    start_time = time.time()
    while (time.time() - start_time) < timeout:
        message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
        if message and message['type'] == 'message':
            # Cleanup
            pubsub.unsubscribe()
            pubsub.close()
            return message['data']  # Returns "trigger_photo"
        time.sleep(0.1)  # Small sleep to prevent tight loop
    
    # Cleanup on timeout
    pubsub.unsubscribe()
    pubsub.close()
    
    return None  # Timeout occurred

