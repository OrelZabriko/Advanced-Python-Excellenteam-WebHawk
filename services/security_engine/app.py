from flask import Flask, request, jsonify
from services.security_service import SecurityService

app = Flask(__name__)


@app.route("/analyze", methods=["POST"])
def analyze():
    payload = request.get_json()
    if payload is None:
        return jsonify({"error": "Invalid JSON body"}), 400

    if not all(k in payload for k in ("endpoint", "method", "ip")):
        return jsonify({"error": "Missing required fields: endpoint, method, ip"}), 400

    result = SecurityService.analyze_request(payload)
    return jsonify(result), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)