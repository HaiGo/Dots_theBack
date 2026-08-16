from flask import current_app
from itsdangerous import URLSafeTimedSerializer
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content

def send_verification_email(user_email):
    """Generates and sends a verification email using SendGrid API."""
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    token = serializer.dumps(user_email, salt='email-verification-salt')
    
    # Generate the verification link using CURRENT_DOMAIN from config
    # This ensures the link works in both local and production environments
    domain = current_app.config['CURRENT_DOMAIN']
    
    # Add http:// prefix if not present (for localhost)
    if not domain.startswith('http://') and not domain.startswith('https://'):
        # Use http for localhost, https for production domains
        protocol = 'http://' if 'localhost' in domain or '127.0.0.1' in domain else 'https://'
        domain = protocol + domain
    
    verify_url = f"{domain}/auth/verify-email?token={token}"
    
    subject = "Verify your email for Dots"
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .container {{
                background: #ffffff;
                border-radius: 8px;
                padding: 40px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}
            .header {{
                text-align: center;
                margin-bottom: 30px;
            }}
            .header h1 {{
                color: #C1FF72;
                margin: 0;
                font-size: 28px;
            }}
            .content {{
                margin-bottom: 30px;
            }}
            .button {{
                display: inline-block;
                padding: 14px 32px;
                background: #C1FF72;
                color: #1a1a1a !important;
                text-decoration: none;
                border-radius: 6px;
                font-weight: 600;
                text-align: center;
                margin: 20px 0;
            }}
            .button:hover {{
                opacity: 0.9;
            }}
            .footer {{
                text-align: center;
                color: #999;
                font-size: 12px;
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #eee;
            }}
            .link {{
                color: #C1FF72;
                word-break: break-all;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📸 Dots</h1>
            </div>
            <div class="content">
                <h2>Welcome to Dots!</h2>
                <p>Thank you for signing up. To complete your registration, please verify your email address by clicking the button below:</p>
                <div style="text-align: center;">
                    <a href="{verify_url}" class="button">Verify Email Address</a>
                </div>
                <p style="color: #666; font-size: 14px;">Or copy and paste this link into your browser:</p>
                <p class="link" style="font-size: 12px;">{verify_url}</p>
                <p style="color: #999; font-size: 13px; margin-top: 30px;">⏰ This link will expire in 1 hour.</p>
            </div>
            <div class="footer">
                <p>If you did not sign up for Dots, please ignore this email.</p>
                <p>This is an automated message, please do not reply.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Create SendGrid message
    message = Mail(
        from_email=Email(current_app.config['MAIL_DEFAULT_SENDER']),
        to_emails=To(user_email),
        subject=subject,
        html_content=Content("text/html", html_body)
    )
    
    try:
        # Send email using SendGrid API
        sg = SendGridAPIClient(current_app.config['SENDGRID_API_KEY'])
        response = sg.send(message)
        
        current_app.logger.info(f"✅ Verification email sent to {user_email} (Status: {response.status_code})")
        return True
    except Exception as e:
        current_app.logger.error(f"❌ Failed to send email to {user_email}: {str(e)}")
        # Re-raise the exception so the caller knows it failed
        raise


def send_password_reset_email(user_email, reset_code):
    """Generates and sends a password reset email with a 6-digit code using SendGrid API."""
    
    subject = "Reset your Dots password"
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .container {{
                background: #ffffff;
                border-radius: 8px;
                padding: 40px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}
            .header {{
                text-align: center;
                margin-bottom: 30px;
            }}
            .header h1 {{
                color: #C1FF72;
                margin: 0;
                font-size: 28px;
            }}
            .content {{
                margin-bottom: 30px;
            }}
            .code-box {{
                background: #C1FF72;
                color: #1a1a1a;
                font-size: 36px;
                font-weight: bold;
                letter-spacing: 8px;
                padding: 20px;
                border-radius: 8px;
                text-align: center;
                margin: 30px 0;
                font-family: 'Courier New', monospace;
            }}
            .footer {{
                text-align: center;
                color: #999;
                font-size: 12px;
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #eee;
            }}
            .warning {{
                background: #fff3cd;
                border-left: 4px solid #ffc107;
                padding: 12px;
                margin: 20px 0;
                border-radius: 4px;
            }}
            .expiry {{
                background: #f0f0f0;
                padding: 10px;
                border-radius: 4px;
                text-align: center;
                color: #666;
                font-size: 14px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔐 Dots</h1>
            </div>
            <div class="content">
                <h2>Password Reset Code</h2>
                <p>We received a request to reset your password. Use the code below to reset your password in the app:</p>
                
                <div class="code-box">
                    {reset_code}
                </div>
                
                <div class="expiry">
                    ⏰ This code will expire in 15 minutes
                </div>
                
                <p style="color: #666; font-size: 14px; margin-top: 20px;">
                    <strong>How to use this code:</strong>
                </p>
                <ol style="color: #666; font-size: 14px;">
                    <li>Open the Dots app</li>
                    <li>Go to the password reset screen</li>
                    <li>Enter this code and your new password</li>
                </ol>
                
                <div class="warning">
                    <strong>⚠️ Security Notice:</strong>
                    <p style="margin: 5px 0 0 0; font-size: 13px;">If you didn't request this password reset, please ignore this email. Your password will remain unchanged. Never share this code with anyone.</p>
                </div>
            </div>
            <div class="footer">
                <p>This is an automated message, please do not reply.</p>
                <p>Need help? Contact our support team.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Create SendGrid message
    message = Mail(
        from_email=Email(current_app.config['MAIL_DEFAULT_SENDER']),
        to_emails=To(user_email),
        subject=subject,
        html_content=Content("text/html", html_body)
    )
    
    try:
        # Send email using SendGrid API
        sg = SendGridAPIClient(current_app.config['SENDGRID_API_KEY'])
        response = sg.send(message)
        
        current_app.logger.info(f"✅ Password reset email sent to {user_email} (Status: {response.status_code})")
        return True
    except Exception as e:
        current_app.logger.error(f"❌ Failed to send password reset email to {user_email}: {str(e)}")
        # Re-raise the exception so the caller knows it failed
        raise