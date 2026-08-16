import os
import platform
from app import create_app, db
from app.models import User, PiDevice, Photo


if platform.system() == "Windows":
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=".env.local", override=True)
    print("Loaded .env file (Windows detected)")

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'PiDevice': PiDevice, 'Photo': Photo}

if __name__ == '__main__':
    # Gunicorn will run this 'app' object
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

