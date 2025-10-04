from flask import Flask, request, jsonify

# Initialize the Flask application
app = Flask(__name__)

# Define your unique usercode
# TODO: Replace "YOUR_UNIQUE_CODE_HERE" with the one you'll submit
USER_CODE = "YOUR_UNIQUE_CODE_HERE"

@app.route('/', methods=['POST'])
def handle_request():
    """
    This is the main endpoint that receives the project request.
    """
    # Get the JSON data from the request
    request_data = request.get_json()

    # For now, just print the brief to the console to confirm we received it
    if request_data and 'brief' in request_data:
        print(f"Received brief: {request_data['brief']}")
    else:
        print("Received a request with no brief.")

    # --- TODO: ADD YOUR LOGIC HERE ---
    # 1. Verify the signature.
    # 2. Call the LLM to generate code.
    # 3. Use the GitHub API to create a repo and push the code.
    # 4. POST the results back to the evaluation_url.
    # -----------------------------------

    # Immediately send back the required response
    return jsonify({"usercode": USER_CODE}), 200

if __name__ == '__main__':
    # Run the app. The host '0.0.0.0' makes it accessible on your network.
    # The port is set to 7860, a common port for Hugging Face apps.
    app.run(host='0.0.0.0', port=7860)