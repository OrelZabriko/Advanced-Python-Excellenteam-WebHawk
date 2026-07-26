from flask import Flask
from middleware.routes.proxy_routes import proxy_bp
from services.shared.error_handlers import register_error_handlers


def create_app():
    app = Flask(__name__)
    app.register_blueprint(proxy_bp)
    register_error_handlers(app)
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8080, debug=True)