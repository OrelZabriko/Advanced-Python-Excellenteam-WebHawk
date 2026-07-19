from flask import Flask
from services.backend_registry.routes.backend_routes import backend_bp


def create_app():
    app = Flask(__name__)
    app.register_blueprint(backend_bp)
    return app


if __name__ == "__main__":
    from services.shared.config import Config
    app = create_app()
    app.run(host="0.0.0.0", port=Config.PORT, debug=True)