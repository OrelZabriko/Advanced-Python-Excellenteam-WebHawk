from flask import Flask
from services.users.routes.auth_routes import auth_bp
from services.shared.error_handlers import register_error_handlers


def create_app():
    app = Flask(__name__)
    app.register_blueprint(auth_bp)
    register_error_handlers(app)
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8080, debug=True)