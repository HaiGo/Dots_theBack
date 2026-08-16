# Dots Backend 📸

![Dots Backend](https://img.shields.io/badge/Status-Active-brightgreen.svg)
![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.0+-lightgrey.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13+-blue.svg)

> **Frontend Project Integration:** This backend project works in tandem with our fully developed frontend application. You can find the frontend repository here:
> 👉 **[Frontend - Dots theFront](https://github.com/HaiGo/Dots_theFront)**
> 
> **Hardware Client:** This backend also integrates with our physical hardware booth software running on a Raspberry Pi:
> 👉 **[Hardware - Dots Client](https://github.com/HaiGo/Dots_theBooth)**

---

## 🎯 Motivation

This project started as a freelance endeavor during my IT Master's studies at the École de Technologie Supérieure (ÉTS) in Montreal. Through online platforms (Fiverr and LinkedIn), I connected with an excited and eager entrepreneur from Japan, he calls himself Kai Ghribi, who had a crazy but brilliant idea: to build a smart photobooth hardware/software solution for local businesses, such as restaurants and retail stores.

**The Original Idea:**
Install smart photobooths in stores. Customers can scan a QR code to control the booth from their phone, take pictures, have the store's custom stamp applied to their photos, and receive the memories via email.

**The Pivot to a Social Network:**
We realized that simply emailing photos was too limiting. Why ask users for their email just to send a picture? In Japan, the photobooth ("purikura") culture is highly developed, but we saw a gap in the market for a dedicated social platform, especially with the limited presence of alternatives like Snapchat. 

We expanded the vision to create a full-fledged **social network** built around these photobooths. Users can not only capture memories but also share them, chat with friends, and interact with the businesses they visited. This creates a more convenient and engaging experience that encourages users to return to those stores frequently, driving business growth while providing an unforgettable user experience.

---

## 🚀 Objectives

The primary objective of this backend is to provide a robust, real-time, and highly scalable API that orchestrates interactions between:
1. **The Raspberry Pi Hardware:** Installed inside the physical photobooth, responsible for triggering the camera and uploading assets.
2. **The Mobile Application:** Used by customers to scan QR codes, trigger the camera remotely, view galleries, and interact socially.
3. **The Web Interface/Dashboard:** For store owners and administrators.

---

## 🏗️ Architecture & Technology Stack

This backend is designed to be **cloud-agnostic**. It can be deployed on any Platform as a Service (PaaS) like Railway, Heroku, or Render, as well as any Infrastructure as a Service (IaaS) provider like AWS EC2, DigitalOcean Droplets, or Google Cloud Platform.

- **Core Framework**: Python / Flask (Application Factory Pattern)
- **Database**: PostgreSQL (via Flask-SQLAlchemy & Flask-Migrate)
- **Real-Time Messaging**: Redis Pub/Sub (for instant photo triggering)
- **Object Storage**: MinIO (S3-compatible storage for photos)
- **Authentication**: JWT (JSON Web Tokens) via Flask-JWT-Extended
- **Email Delivery**: SendGrid API (via Flask-Mail)

---

## ✨ Key Functionalities

- **Advanced User Authentication**: Secure JWT-based login, registration, and password reset flows with email verification via SendGrid.
- **QR Code Session Linking**: Real-time linking of a physical Pi device session to a specific user's mobile app via Redis.
- **Remote Hardware Control**: Low-latency photo triggering from the mobile app to the Pi device using Redis Pub/Sub.
- **Cloud Media Storage**: Direct integration with MinIO for secure, scalable photo uploads and public gallery generation.
- **Social Features**: Friend management, photo sharing, profile customization, and granular location privacy settings.
- **Cloud-Agnostic Design**: Fully driven by environment variables, making it trivial to deploy anywhere.

---

## 🔌 Main API Endpoints

Below is a high-level overview of the primary API endpoints. **For detailed request/response schemas and implementation details, please refer to the [Frontend Repository]**.

### Authentication (`/auth`)
- `POST /auth/register`: Create a new user account.
- `POST /auth/login`: Authenticate and receive JWT access/refresh tokens.
- `POST /auth/forgot-password`: Initiate a password reset flow.
- `GET /auth/verify-email`: Verify a user's email address.

### Mobile App Core (`/mobile`)
- `POST /mobile/start-session`: Link a user to a physical booth session via QR code.
- `POST /mobile/trigger-photo`: Command the Pi to capture a photo in real-time.
- `GET /mobile/gallery`: Retrieve the authenticated user's photo gallery.

### Raspberry Pi Hardware (`/pi`)
- `POST /pi/heartbeat`: Register the Pi device's active status.
- `GET /pi/get-session-qr`: Generate a new temporary session key.
- `GET /pi/listen-for-trigger`: Long-polling endpoint waiting for mobile triggers.
- `POST /pi/upload-photo`: Securely upload the captured photo to MinIO.

### Social Features (`/social`)
- `GET /social/profile`: Retrieve user profile data.
- `POST /social/add-friend`: Send a friend request/add a friend.
- `PUT /social/location-sharing-settings`: Update location privacy preferences.

---

## 🛠️ Setup & Installation

To run this backend locally or deploy it to a cloud provider, follow these steps:

### 1. Prerequisites
Ensure you have the following installed or available via a cloud provider:
- Python 3.9+
- PostgreSQL
- Redis
- MinIO (or AWS S3)
- SendGrid Account

### 2. Environment Configuration
The application relies strictly on environment variables. A template is provided in the repository.

1. Copy the example configuration:
   ```bash
   cp .env.example .env
   ```
2. Open `.env` and fill in the values:
   - `DATABASE_URL`: Your PostgreSQL connection string.
   - `REDIS_URL`: Your Redis connection string.
   - `SECRET_KEY` & `JWT_SECRET_KEY`: Cryptographically secure random strings.
   - `MINIO_*`: Your MinIO endpoint and root credentials.
   - `SENDGRID_API_KEY`: Your SendGrid API key for emails.
   - `VERIFICATION_SECRET`: A secret string used internally for certain validation flows.

### 3. Local Development
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
flask db upgrade

# Start the development server
python run.py
```

### 4. Deployment
Because the app is stateless and uses environment variables, you can deploy it easily using Docker, or directly via PaaS platforms by simply linking the GitHub repository and providing the environment variables in the platform's dashboard.

---

*Developed with passion and excitement to put the “vibe-coded” slogan to the test, while hoping to bring people together.* ✨

These are the only human-written words in this whole project, and I’m using it to say: this is a fully vibe-coded project, in its entirety, including the two other parts of it. It’s not recommended for any kind of production use as it is, negligible, if not to say zero, security precautions were taken during its vibe coding. But please, feel free to enjoy "vibe-improving" it while WE CONNECT TOGATHER!