from flask import Flask, request, jsonify, abort
import logging
import os # Required to read secrets

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# Get your secret from the Hugging Face Space settings
MY_SECRET = os.environ.get('MY_APP_SECRET')

app = Flask(__name__)

@app.route('/', methods=['POST'])
def handle_request():
    """Handles the incoming project request."""
    request_data = request.get_json()
    if not request_data:
        abort(400, "Bad Request: No JSON data received.")

    # --- Verify the Secret ---
    if not MY_SECRET or request_data.get('secret') != MY_SECRET:
        logging.error("Secret verification failed.")
        abort(403, "Forbidden: Invalid secret")

    logging.info("Secret verified successfully.")

    if 'brief' in request_data:
        logging.info(f"Received brief: {request_data['brief']}")

    # --- TODO: Add LLM and GitHub logic here ---

    return jsonify({"status": "ok", "message": "Request received and authenticated."}), 200