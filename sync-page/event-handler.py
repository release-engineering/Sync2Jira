# Build-In Modules
import logging
import os

# 3rd Party Modules
from flask import Flask, redirect, render_template, request

# Local Modules
from sync2jira.main import initialize_issues, initialize_pr, load_config

# Global Variables
app = Flask(__name__, static_url_path="/assets", static_folder="assets")
BASE_URL = os.environ['BASE_URL']
REDIRECT_URL = os.environ['REDIRECT_URL']
config = load_config()

# Set up our logging
FORMAT = "[%(asctime)s] %(levelname)s: %(message)s"
logging.basicConfig(format=FORMAT, level=logging.INFO)
logging.basicConfig(format=FORMAT, level=logging.DEBUG)
logging.basicConfig(format=FORMAT, level=logging.WARNING)
log = logging.getLogger('sync2jira-sync-page')


@app.route('/handle-event', methods=['POST'])
def handle_event():
    """
    Handler for when a user wants to sync a repo
    """
    response = request.form
    synced_repos = []
    for repo_name, switch in response.items():
        if switch == "on":
            # Sync repo_name
            log.info(f"Starting sync for repo: {repo_name}")
            initialize_issues(config, repo_name=repo_name)
            initialize_pr(config, repo_name=repo_name)
            synced_repos.append(repo_name)
    if synced_repos:
        return render_template('sync-page-success.jinja',
                               synced_repos=synced_repos,
                               url=f"https://{REDIRECT_URL}")
    else:
        return render_template('sync-page-failure.jinja',
                               url=f"https://{REDIRECT_URL}")


@app.route('/', methods=['GET'])
def index():
    """
    Return relevant redirect
    """
    return redirect("/github")


@app.route('/github', methods=['GET'])
def github():
    """
    Github Sync Page
    """
    # Build and return our updated HTML page
    return render_template('sync-page-github.jinja',
                           github=config['sync2jira']['map']['github'],
                           url=f"https://{REDIRECT_URL}")


if __name__ == '__main__':
    app.run(host=BASE_URL)
