from flask import Flask
from flask_cors import CORS   # 🔹 Add this
from config import Config
from api.auth import bp as auth_bp
from api.upload import bp as up_bp
from api.notes import bp as notes_bp
from api.health import bp as health_bp   

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # 🔹 Enable CORS (frontend at localhost:3000 allowed)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    app.register_blueprint(auth_bp)
    app.register_blueprint(up_bp)
    app.register_blueprint(notes_bp)
    app.register_blueprint(health_bp)    
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=Config.PORT)
