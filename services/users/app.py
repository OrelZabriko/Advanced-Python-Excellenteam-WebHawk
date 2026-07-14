from flask import Flask
from services.users.routes.auth_routes import auth_bp


def create_app():
    app = Flask(__name__)
    app.register_blueprint(auth_bp)
    return app


if __name__ == "__main__":
    from services.shared.config import Config
    app = create_app()
    app.run(host="0.0.0.0", port=Config.PORT, debug=True)