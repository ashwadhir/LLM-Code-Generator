from flask import Flask, request, jsonify, abort
import logging
import os
import google.generativeai as genai
from github import Github

# --- Configure logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# --- Get secrets from environment variables ---
MY_SECRET = os.environ.get('MY_APP_SECRET')
# Set the Gemini API key from the secret you just added
genai.configure(
    api_key=os.environ.get("GEMINI_API_KEY"),
    transport='rest' # <-- Add this line
)
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')

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
        model = genai.GenerativeModel("models/gemini-2.5-flash")
        response = model.generate_content(prompt)
        generated_code = response.text
        logging.info("Successfully received code from Google Gemini API.")
        return generated_code
    except Exception as e:
        logging.error(f"Error calling Google Gemini API: {e}")
        return None

def deploy_to_github(repo_name, html_content):
    """Creates a GitHub repo, pushes content, and returns the repo URLs."""
    try:
        logging.info(f"Connecting to GitHub...")
        g = Github(GITHUB_TOKEN)
        user = g.get_user()

        logging.info(f"Creating new repository named: {repo_name}")
        repo = user.create_repo(repo_name, private=False)

        logging.info("Pushing index.html to the new repository...")
        repo.create_file(
            "index.html",
            "Initial commit: Add generated HTML",
            html_content,
            branch="main"
        )
        
        # NOTE: GitHub Pages enabling via API is complex and often requires a delay.
        # For this project, creating a public repo with index.html is often sufficient,
        # as Pages can be enabled manually or might enable automatically.
        
        repo_url = repo.html_url
        pages_url = f"https://{user.login}.github.io/{repo_name}/"
        commit_sha = repo.get_branch("main").commit.sha

        logging.info(f"Successfully created repo: {repo_url}")
        logging.info(f"GitHub Pages URL will be: {pages_url}")
        
        return repo_url, pages_url, commit_sha
    except Exception as e:
        logging.error(f"Error during GitHub deployment: {e}")
        return None, None, None
    
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
    
    # --- 2. Deploy to GitHub ---
    # Use the 'task' field from the request for a unique repo name
    task_id = request_data.get('task', 'llm-generated-app')
    repo_name = f"{task_id}-{request_data.get('round', 1)}"

    repo_url, pages_url, commit_sha = deploy_to_github(repo_name, generated_html)

    if not repo_url:
        abort(500, "Internal Server Error: Failed to deploy to GitHub.")

    # --- TODO: Final step is to POST these details to the evaluation_url ---
    logging.info(f"Final details: repo_url={repo_url}, pages_url={pages_url}, commit_sha={commit_sha}")
    
    return jsonify({
        "status": "ok", 
        "message": "Code generated and deployed to GitHub successfully.",
        "repo_url": repo_url,
        "pages_url": pages_url
    }), 200