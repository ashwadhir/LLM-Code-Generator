from flask import Flask, request, jsonify, abort
import logging
import os
import google.generativeai as genai

# --- Configure logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# --- Get secrets from environment variables ---
MY_SECRET = os.environ.get('MY_APP_SECRET')
# Set the Gemini API key from the secret you just added
genai.api_key = os.environ.get('GEMINI_API_KEY')

app = Flask(__name__)

def generate_code_with_llm(brief, attachments):
    """Generates a single HTML file using the Gemini API."""

    prompt = f"""
    Based on the following brief, generate a single, complete HTML file (`index.html`).
    The HTML file must include all necessary CSS and JavaScript in <style> and <script> tags.
    Do not use any external files. The entire web application must be contained in this one file.

    Brief: "{brief}"

    Attachments: {attachments}

    Generate only the HTML code, starting with <!DOCTYPE html> and nothing else.
    """

    try:
        logging.info("Sending request to Google Gemini API...")
        model = genai.GenerativeModel('gemini-1.0-pro')
        response = model.generate_content(prompt)
        generated_code = response.text
        logging.info("Successfully received code from Google Gemini API.")
        return generated_code
    except Exception as e:
        logging.error(f"Error calling Google Gemini API: {e}")
        return None

@app.route('/', methods=['POST'])
def handle_request():
    """Handles the incoming project request."""
    request_data = request.get_json()
    # ... (secret verification code remains the same) ...
    if not MY_SECRET or request_data.get('secret') != MY_SECRET:
        logging.error("Secret verification failed.")
        abort(403, "Forbidden: Invalid secret")

    logging.info("Secret verified successfully.")
    
    brief = request_data.get('brief')
    attachments = request_data.get('attachments', [])
    
    if not brief:
        abort(400, "Bad Request: No brief provided.")
    
    # --- 1. Generate Code using LLM ---
    generated_html = generate_code_with_llm(brief, attachments)
    
    if not generated_html:
        abort(500, "Internal Server Error: Failed to generate code.")
        
    # For now, just log the generated code to confirm it works
    logging.info("--- Generated HTML Code ---")
    logging.info(generated_html[:500] + "...") # Log the first 500 chars
    logging.info("--------------------------")
    
    # --- TODO: Add GitHub deployment logic here ---

    return jsonify({"status": "ok", "message": "Code generated successfully."}), 200