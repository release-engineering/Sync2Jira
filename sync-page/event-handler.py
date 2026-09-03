# Build-In Modules
import logging
import os
import threading
import time
import uuid

# 3rd Party Modules
from flask import Flask, jsonify, redirect, render_template, request

# Local Modules
from sync2jira.main import initialize_issues, initialize_pr, load_config

# Global Variables
app = Flask(__name__, static_url_path="/assets", static_folder="assets")
BASE_URL = os.environ["BASE_URL"]
REDIRECT_URL = os.environ["REDIRECT_URL"]
config = load_config()

# In-memory job tracker: {job_id: {"status": str, "repos": list, "error": str|None, "finished_at": float}}
_jobs: dict = {}
_jobs_repo = set()
_jobs_repo_lock = threading.Lock()
_jobs_lock = threading.Lock()

JOB_TTL_SECONDS = 600  # retain terminal jobs for 10 minutes then discard

# Set up our logging
FORMAT = "[%(asctime)s] %(levelname)s: %(message)s"
logging.basicConfig(format=FORMAT, level=logging.INFO)
logging.basicConfig(format=FORMAT, level=logging.DEBUG)
logging.basicConfig(format=FORMAT, level=logging.WARNING)
log = logging.getLogger("sync2jira-sync-page")


def _cleanup_expired_jobs():
    """Daemon thread: remove terminal jobs older than JOB_TTL_SECONDS."""
    while True:
        time.sleep(120)  # check every 2 minutes
        cutoff = time.monotonic() - JOB_TTL_SECONDS
        with _jobs_lock:
            if not _jobs:
                continue
            expired = [
                jid
                for jid, job in _jobs.items()
                if job["status"] in ("completed", "failed")
                and job["finished_at"] < cutoff
            ]
            for jid in expired:
                _jobs.pop(jid)
                log.debug("Expired sync job %s from memory", jid)


threading.Thread(target=_cleanup_expired_jobs, daemon=True, name="job-cleanup").start()


def _run_sync(job_id: str, repos: list):
    """Run initialize_issues and initialize_pr for each repo in a background thread."""
    try:
        for repo_name in repos:
            log.info(f"[job:{job_id}] Syncing repo: {repo_name}")
            initialize_issues(config, repo_name=repo_name)
            initialize_pr(config, repo_name=repo_name)
            log.info(f"[job:{job_id}] Finished repo: {repo_name}")
        with _jobs_lock:
            _jobs[job_id]["status"] = "completed"
            _jobs[job_id]["finished_at"] = time.monotonic()
    except Exception as e:
        log.exception(f"[job:{job_id}] Sync failed")
        with _jobs_lock:
            _jobs[job_id]["status"] = "failed"
            _jobs[job_id]["error"] = str(e)
            _jobs[job_id]["finished_at"] = time.monotonic()
    finally:
        # Release the repo lock only after sync completes (success or failure)
        with _jobs_repo_lock:
            _jobs_repo.difference_update(repos)


@app.route("/handle-event", methods=["POST"])
def handle_event():
    """
    Handler for when a user wants to sync a repo.
    Kicks off sync in a background thread and immediately returns an
    in-progress page so the gateway never times out.
    """
    response = request.form
    repos_to_sync = [repo for repo, switch in response.items() if switch == "on"]

    if not repos_to_sync:
        return render_template("sync-page-failure.jinja", url=f"https://{REDIRECT_URL}")

    with _jobs_repo_lock:
        already_syncing = set(repos_to_sync) & _jobs_repo
        if already_syncing:
            return render_template(
                "sync-page-failure.jinja",
                url=f"https://{REDIRECT_URL}",
                error=f"Already syncing: {', '.join(already_syncing)}",
            )
        _jobs_repo.update(repos_to_sync)

    job_id = str(uuid.uuid4())
    with _jobs_lock:
        _jobs[job_id] = {
            "status": "in_progress",
            "repos": repos_to_sync,
            "error": None,
            "finished_at": None,
        }

    thread = threading.Thread(
        target=_run_sync, args=(job_id, repos_to_sync), daemon=True
    )
    thread.start()

    log.info(f"Started background sync job {job_id} for repos: {repos_to_sync}")
    return render_template(
        "sync-page-in-progress.jinja",
        job_id=job_id,
        synced_repos=repos_to_sync,
        url=f"https://{REDIRECT_URL}",
    )


@app.route("/status/<job_id>", methods=["GET"])
def job_status(job_id: str):
    """Return JSON status for a background sync job.
    Jobs are retained until JOB_TTL_SECONDS after completion, then expired by the cleanup thread.
    """
    with _jobs_lock:
        job = _jobs.get(job_id)
    if job is None:
        return jsonify({"status": "not_found"}), 404
    return jsonify({k: v for k, v in job.items() if k != "finished_at"})


@app.route("/", methods=["GET"])
def index():
    """
    Return relevant redirect
    """
    return redirect("/github")


@app.route("/github", methods=["GET"])
def github():
    """
    Github Sync Page
    """
    # Build and return our updated HTML page
    return render_template(
        "sync-page-github.jinja",
        github=config["sync2jira"]["map"]["github"],
        url=f"https://{REDIRECT_URL}",
    )


if __name__ == "__main__":
    app.run(host=BASE_URL)
