from flask import Flask, request, jsonify, abort
import logging
import os
import google.generativeai as genai
from github import Github, GithubException
import requests
import time
import json

# --- Configure logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# --- Get secrets from environment variables ---
MY_SECRET = os.environ.get('MY_APP_SECRET')
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"), transport='rest')
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')

app = Flask(__name__)

def generate_code_with_llm(brief, attachments, checks):
    """Generates a single HTML file using a robust, universal prompt."""
    checks_string = "\n".join([f"- `{check}`" for check in checks])
    attachments_string = "No attachments provided."
    if attachments:
        attachments_string = "\n".join([f"- Name: {att['name']}, URL: {att['url']}" for att in attachments])

    # This is the "Golden Prompt" with universal rules
    prompt = f"""
    You are an expert, meticulous, and safety-conscious full-stack web developer.
    Your task is to generate a complete, single-file web application (`index.html`).

    **BRIEF:**
    {brief}

    **ATTACHMENTS:**
    {attachments_string}

    **ACCEPTANCE CRITERIA (The generated code MUST pass these checks):**
    {checks_string}

    ---
    **CRITICAL UNIVERSAL RULES FOR ALL JAVASCRIPT CODE:**

    1.  **Execution Timing:** ALL your custom JavaScript logic MUST be wrapped in a `DOMContentLoaded` event listener. Any code that processes an image MUST be placed inside an `image.onload` callback to prevent race conditions.
        *Example:*
        `document.addEventListener('DOMContentLoaded', () => {{ /* your code here */ }});`
        `myImage.onload = () => {{ /* process the image here */ }};`

    2.  **API Error Handling:** ALL `fetch()` calls or other network requests MUST be wrapped in a `try...catch` block. If an error occurs, you MUST display a user-friendly error message on the page.

    3.  **DOM Safety:** Before you interact with any DOM element, you MUST verify that it exists.
        *Example:* `const myElement = document.querySelector('#my-id'); if (myElement) {{ myElement.textContent = '...'; }}`

    4.  **User Feedback:** For any action that takes time (like an API call), provide a loading state to the user (e.g., "Loading...", "Solving...", etc.).

    5.  **Accessibility:** Use appropriate ARIA attributes where necessary (e.g., `aria-live="polite"` for status messages).

    6.  **Final Output:** Generate ONLY the complete HTML code, starting with `<!DOCTYPE html>`. Do not add any explanations.
    ---
    """
    try:
        logging.info("Sending robust Round 1 request to Google Gemini API...")
        model = genai.GenerativeModel("models/gemini-2.5-flash")
        response = model.generate_content(prompt)
        return response.text.strip().replace("```html", "").replace("```", "")
    except Exception as e:
        logging.error(f"Error calling Google Gemini API for Round 1: {e}")
        return None

def enable_github_pages(repo_name, owner):
    """Explicitly enables GitHub Pages for a repository via the REST API."""
    url = f"https://api.github.com/repos/{owner}/{repo_name}/pages"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    payload = {
        "source": {
            "branch": "main",
            "path": "/"
        }
    }
    try:
        logging.info(f"Attempting to enable GitHub Pages for {repo_name}...")
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 201: # 201 Created is the success code for this action
            logging.info("GitHub Pages enabled successfully.")
            return True
        else:
            logging.error(f"Failed to enable GitHub Pages. Status: {response.status_code}, Response: {response.text}")
            return False
    except Exception as e:
        logging.error(f"An exception occurred while enabling GitHub Pages: {e}")
        return False

def deploy_to_github(repo_name, html_content, brief):
    """Creates a GitHub repo, pushes files, and enables Pages."""
    try:
        g = Github(GITHUB_TOKEN)
        user = g.get_user()
        user_name = user.name if user.name else user.login
        # Check if repo exists and delete it for clean testing
        try:
            old_repo = user.get_repo(repo_name)
            logging.warning(f"Repository {repo_name} already exists. Deleting it for a clean run.")
            old_repo.delete()
            time.sleep(2) # Give GitHub a moment to process the deletion
        except GithubException:
            pass # Repo doesn't exist, which is good

        logging.info(f"Creating new repository: {repo_name}")
        repo = user.create_repo(repo_name, private=False)

        # ... (file creation logic for index.html, README, LICENSE is the same)
        repo.create_file("index.html", "feat: Add generated HTML", html_content, branch="main")
        readme_content = f"# {repo_name}\n\n## Summary\nThis web application was auto-generated by an LLM based on the following brief:\n> {brief}\n\n## License\nThis project is licensed under the MIT License."
        repo.create_file("README.md", "docs: Add README", readme_content.strip(), branch="main")
        mit_license_text = f"MIT License\n\nCopyright (c) 2025 {user_name}\n\n..." # Abbreviated
        repo.create_file("LICENSE", "docs: Add MIT License", mit_license_text.strip(), branch="main")

        # --- ENABLE PAGES (CRITICAL FIX) ---
        enable_github_pages(repo.name, user.login)
        
        commit_sha = repo.get_branch("main").commit.sha
        return repo.html_url, f"https://{user.login}.github.io/{repo_name}/", commit_sha
    except Exception as e:
        logging.error(f"Error during initial GitHub deployment: {e}")
        return None, None, None
    
def modify_code_with_llm(brief, checks, old_html, old_readme):
    """Modifies existing code using the same robust, universal rules."""
    checks_string = "\n".join([f"- `{check}`" for check in checks])
    prompt = f"""
    You are an expert web developer modifying an existing project. Your task is to modify the current files based on the new brief, while STRICTLY adhering to all universal coding rules.

    **NEW BRIEF:** "{brief}"

    **NEW ACCEPTANCE CRITERIA:**
    {checks_string}

    ---
    **CRITICAL UNIVERSAL RULES (You MUST maintain these in your modifications):**
    1.  **Execution Timing:** Ensure all new logic is inside `DOMContentLoaded` or `onload` listeners.
    2.  **API Error Handling:** All new `fetch()` calls must have `try...catch` blocks.
    3.  **DOM Safety:** All new DOM interactions must check for the element's existence first.
    4.  **User Feedback:** Add loading/status indicators for new asynchronous actions.
    5.  **Accessibility:** Add ARIA attributes for new interactive elements or status messages.
    ---

    **Current `index.html` to modify:**
    ```html
    {old_html}
    ```
    **Current `README.md` to modify:**
    ```markdown
    {old_readme}
    ```
    ---
    **Instructions:**
    Return the complete, updated content for `index.html`, then the separator `<<FILE_SEPARATOR>>`, then the complete, updated content for `README.md`.
    """
    try:
        logging.info("Sending robust Round 2 request to Google Gemini API...")
        model = genai.GenerativeModel("models/gemini-2.5-flash")
        response = model.generate_content(prompt)
        parts = response.text.split("<<FILE_SEPARATOR>>")
        if len(parts) == 2:
            return parts[0].strip().replace("```html", "").replace("```", ""), parts[1].strip().replace("```markdown", "").replace("```", "")
        else:
            return None, None
    except Exception as e:
        logging.error(f"Error calling or parsing LLM response for Round 2: {e}")
        return None, None
    
def update_github_repo(repo_name, brief, checks):
    """Finds a repo, gets an LLM to modify its content, and pushes the updates."""
    try:
        logging.info(f"Connecting to GitHub to update repo: {repo_name}")
        g = Github(GITHUB_TOKEN)
        user = g.get_user()
        repo = user.get_repo(repo_name)

        html_file = repo.get_contents("index.html")
        readme_file = repo.get_contents("README.md")
        old_html = html_file.decoded_content.decode("utf-8")
        old_readme = readme_file.decoded_content.decode("utf-8")

        new_html, new_readme = modify_code_with_llm(brief, checks, old_html, old_readme)
        
        # Check if the LLM call was successful
        if new_html is None or new_readme is None:
            raise Exception("LLM failed to return valid modified files.")

        # --- CRITICAL FIX: Update files sequentially ---
        logging.info("Pushing updated index.html...")
        repo.update_file(
            path="index.html",
            message="feat: Update application based on round 2 brief",
            content=new_html,
            sha=html_file.sha,
            branch="main"
        )
        
        # Give GitHub a moment to process the first update
        time.sleep(2) 
        
        logging.info("Pushing updated README.md...")
        # Get the LATEST version of the readme file before updating
        latest_readme_file = repo.get_contents("README.md")
        update_result = repo.update_file(
            path="README.md",
            message="docs: Update README for round 2 changes",
            content=new_readme,
            sha=latest_readme_file.sha, # Use the latest SHA
            branch="main"
        )
        
        new_commit_sha = update_result['commit'].sha
        logging.info(f"Successfully updated repo. New commit SHA: {new_commit_sha}")

        return repo.html_url, f"https://{user.login}.github.io/{repo_name}/", new_commit_sha

    except Exception as e:
        logging.error(f"Error during GitHub repository update: {e}")
        return None, None, None
    
def notify_evaluation_server(url, payload):
    """Sends the final results to the evaluation server with retries."""
    retries = 5
    delay = 1
    for i in range(retries):
        try:
            response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'}, timeout=10)
            if response.status_code == 200:
                logging.info("Successfully notified evaluation server.")
                return True
            logging.warning(f"Notification failed with status {response.status_code}. Retrying...")
        except requests.exceptions.RequestException as e:
            logging.error(f"Error sending notification: {e}. Retrying...")
        time.sleep(delay)
        delay *= 2
    logging.error("Failed to notify evaluation server after all retries.")
    return False

# --- Round Handlers ---

def handle_round_1(data):
    """Handles the logic for creating a new application."""
    brief = data.get('brief')
    attachments = data.get('attachments', [])
    checks = data.get('checks', [])
    repo_name = data.get('task')

    if not all([brief, repo_name]):
        abort(400, "Bad Request: Missing 'brief' or 'task' for Round 1.")

    generated_html = generate_code_with_llm(brief, attachments, checks)
    if not generated_html:
        abort(500, "Internal Server Error: Failed to generate code.")
    
    repo_url, pages_url, commit_sha = deploy_to_github(repo_name, generated_html, brief)
    if not repo_url:
        abort(500, "Internal Server Error: Failed to deploy to GitHub.")

    return repo_url, pages_url, commit_sha

def handle_round_2(data):
    """Handles the logic for modifying an existing application."""
    brief = data.get('brief')
    checks = data.get('checks', [])
    repo_name = data.get('task')

    if not all([brief, repo_name]):
        abort(400, "Bad Request: Missing 'brief' or 'task' for Round 2.")

    repo_url, pages_url, commit_sha = update_github_repo(repo_name, brief, checks)
    if not repo_url:
        abort(500, "Internal Server Error: Failed to update GitHub repo.")
    
    return repo_url, pages_url, commit_sha
    
@app.route('/', methods=['POST'])
def handle_request():
    """Main endpoint to handle all project requests."""
    request_data = request.get_json()
    if not request_data:
        abort(400, "Bad Request: No JSON data received.")

    if not MY_SECRET or request_data.get('secret') != MY_SECRET:
        logging.error("Secret verification failed.")
        abort(403, "Forbidden: Invalid secret")
    logging.info("Secret verified successfully.")

    round_num = request_data.get('round', 1)
    if round_num > 1:
        repo_url, pages_url, commit_sha = handle_round_2(request_data)
    else:
        repo_url, pages_url, commit_sha = handle_round_1(request_data)
        
    evaluation_url = request_data.get('evaluation_url')
    if not evaluation_url:
        abort(400, "Bad Request: evaluation_url is missing.")

    final_payload = {
        "email": request_data.get('email'),
        "task": request_data.get('task'),
        "round": round_num,
        "nonce": request_data.get('nonce'),
        "repo_url": repo_url,
        "commit_sha": commit_sha,
        "pages_url": pages_url
    }
    
    notify_evaluation_server(evaluation_url, final_payload)

    return jsonify({"status": "ok", "message": "Process complete. Evaluation server notified."}), 200