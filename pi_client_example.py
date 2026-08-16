#!/usr/bin/env python3
"""
Raspberry Pi Client - Continuous Operation
This script runs on the Raspberry Pi device and:
1. Continuously generates QR codes for user linking
2. Listens for trigger commands from mobile app
3. Captures and uploads photos when triggered
"""

import requests
import time
import io
import os
import tempfile
from PIL import Image
import qrcode
from datetime import datetime

# ============ CONFIGURATION ============
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8080")  # Set via environment variable or .env file
PI_DEVICE_KEY = "test-pi-key-123"  # Get this from manage_pi_devices.py
QR_DISPLAY_TIME = 60  # Seconds before generating new QR code
HEARTBEAT_INTERVAL = 30  # Send heartbeat every 30 seconds
# =======================================

class PiBoothClient:
    def __init__(self, api_url, device_key):
        self.api_url = api_url.rstrip('/')
        self.device_key = device_key
        self.headers = {
            'X-Pi-Device-Key': device_key
        }
        self.current_session_key = None
        self.last_heartbeat = 0
        
    def send_heartbeat(self):
        """Send heartbeat to server to update last_seen timestamp"""
        try:
            response = requests.post(
                f"{self.api_url}/pi/heartbeat",
                headers=self.headers,
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                print(f"💚 Heartbeat OK - Device: {data.get('device_name')}")
                return True
            else:
                print(f"❌ Heartbeat failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Heartbeat error: {e}")
            return False
    
    def get_new_session_qr(self):
        """Request new session key and generate QR code"""
        try:
            response = requests.get(
                f"{self.api_url}/pi/get-session-qr",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.current_session_key = data['session_key']
                print(f"\n📱 New Session Created: {self.current_session_key}")
                
                # Generate QR code linking URL for mobile app
                # Mobile app should scan this and call /mobile/start-session
                qr_data = f"dots://link?session={self.current_session_key}"
                
                # Generate and display QR code
                self.display_qr_code(qr_data)
                return True
            else:
                print(f"❌ Failed to get session: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Session request error: {e}")
            return False
    
    def display_qr_code(self, data):
        """Generate and display QR code"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save QR code image to temp directory (cross-platform)
        try:
            temp_dir = tempfile.gettempdir()
            qr_path = os.path.join(temp_dir, "current_qr.png")
            img.save(qr_path)
            print(f"💾 QR code saved to: {qr_path}")
        except Exception as e:
            print(f"⚠️  Warning: Could not save QR image: {e}")
        
        # Print QR code to console (for testing)
        qr.print_ascii(invert=True)
        print(f"\n🔗 Scan this QR code to link your mobile app")
        print(f"📄 Session Key: {self.current_session_key}")
        print(f"⏰ Valid for {QR_DISPLAY_TIME} seconds\n")
    
    def listen_for_trigger(self):
        """Long-poll for trigger command (30 second timeout)"""
        try:
            response = requests.get(
                f"{self.api_url}/pi/listen-for-trigger",
                headers=self.headers,
                timeout=35  # Slightly longer than server timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('action') == 'trigger':
                    print("📸 TRIGGER RECEIVED!")
                    return True
            elif response.status_code == 204:
                # Timeout - no trigger received
                return False
            else:
                print(f"⚠️  Listen error: {response.status_code}")
                
        except requests.exceptions.Timeout:
            # Expected timeout after 30 seconds
            pass
        except Exception as e:
            print(f"❌ Listen error: {e}")
            time.sleep(1)
        
        return False
    
    def capture_photo(self):
        """Capture photo using Pi camera"""
        try:
            # TODO: Replace with actual camera capture
            # Example using picamera2:
            # from picamera2 import Picamera2
            # picam2 = Picamera2()
            # picam2.start()
            # image = picam2.capture_array()
            # picam2.stop()
            
            # For testing: Use photo from simulator folder
            print("📷 Capturing photo...")
            
            photo_path = "simulator/downloaded_photo.jpg"
            
            # Check if file exists
            if os.path.exists(photo_path):
                print(f"   Using photo from: {photo_path}")
                with open(photo_path, 'rb') as f:
                    img_byte_arr = io.BytesIO(f.read())
                    img_byte_arr.seek(0)
                    return img_byte_arr
            else:
                # Fallback: Create a dummy image if photo doesn't exist
                print(f"⚠️  Photo not found at {photo_path}, creating dummy image")
                img = Image.new('RGB', (640, 480), color='red')
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='JPEG')
                img_byte_arr.seek(0)
                return img_byte_arr
            
        except Exception as e:
            print(f"❌ Camera error: {e}")
            return None
    
    def upload_photo(self, photo_data):
        """Upload captured photo to backend"""
        try:
            files = {
                'image': ('photo.jpg', photo_data, 'image/jpeg')
            }
            data = {
                'session_key': self.current_session_key
            }
            
            print("⬆️  Uploading photo...")
            response = requests.post(
                f"{self.api_url}/pi/upload-photo",
                headers=self.headers,
                files=files,
                data=data,
                timeout=30
            )
            
            if response.status_code == 201:
                result = response.json()
                print(f"✅ Photo uploaded successfully!")
                print(f"   Object: {result.get('object_name')}")
                return True
            else:
                print(f"❌ Upload failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Upload error: {e}")
            return False
    
    def run_continuous(self):
        """Main continuous operation loop"""
        print("="*60)
        print("🚀 Dots Client Starting...")
        print(f"📡 Backend: {self.api_url}")
        print("="*60)
        
        # Initial heartbeat
        self.send_heartbeat()
        self.last_heartbeat = time.time()
        
        # Get initial QR code
        self.get_new_session_qr()
        qr_generated_at = time.time()
        
        print("\n🔄 Entering continuous operation mode...")
        print("   Press Ctrl+C to stop\n")
        
        try:
            while True:
                # Check if we need to refresh QR code
                if time.time() - qr_generated_at > QR_DISPLAY_TIME:
                    print("\n🔄 Refreshing QR code...")
                    self.get_new_session_qr()
                    qr_generated_at = time.time()
                
                # Send heartbeat if needed
                if time.time() - self.last_heartbeat > HEARTBEAT_INTERVAL:
                    self.send_heartbeat()
                    self.last_heartbeat = time.time()
                
                # Listen for trigger (blocks for ~30 seconds)
                if self.listen_for_trigger():
                    # Trigger received! Capture and upload photo
                    photo = self.capture_photo()
                    if photo:
                        self.upload_photo(photo)
                        print("\n✨ Photo capture complete!")
                        print("   Ready for next trigger...\n")
                    
                    # After photo, refresh QR code for next user
                    time.sleep(2)
                    self.get_new_session_qr()
                    qr_generated_at = time.time()
                
        except KeyboardInterrupt:
            print("\n\n👋 Shutting down gracefully...")
            print("Goodbye!")

def main():
    # Create client instance
    client = PiBoothClient(API_BASE_URL, PI_DEVICE_KEY)
    
    # Run continuous operation
    client.run_continuous()

if __name__ == "__main__":
    main()

