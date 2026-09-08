# Build-In Modules
import importlib.util
import os
import pathlib
import sys
import threading
import time
import unittest
from unittest import mock

# Set required env vars before the module is imported
os.environ.setdefault("BASE_URL", "localhost")
os.environ.setdefault("REDIRECT_URL", "example.com")

_MODULE_PATH = str(
    pathlib.Path(__file__).parent.parent / "sync-page" / "event-handler.py"
)

# Load the event-handler module with load_config mocked so no real config file is needed.
with mock.patch(
    "sync2jira.main.load_config", return_value={"sync2jira": {"map": {"github": {}}}}
):
    spec = importlib.util.spec_from_file_location("event_handler", _MODULE_PATH)
    eh = importlib.util.module_from_spec(spec)
    sys.modules["event_handler"] = eh
    spec.loader.exec_module(eh)  # type: ignore[union-attr]

PATH = "event_handler."


def _make_job(status="in_progress", repos=None, finished_at=None, error=None):
    """Helper to build a job dict matching the shape used by _run_sync."""
    return {
        "status": status,
        "repos": repos if repos is not None else ["org/repo"],
        "error": error,
        "finished_at": finished_at,
    }


class TestHandleEvent(unittest.TestCase):
    """Tests for the /handle-event POST endpoint."""

    def setUp(self):
        self.mock_config = {
            "sync2jira": {"testing": False, "map": {"github": {"org/repo": {}}}}
        }
        eh._jobs.clear()
        eh._jobs_repo.clear()
        self.client = eh.app.test_client()

    def test_no_repos_selected_returns_failure_page(self):
        resp = self.client.post("/handle-event", data={})
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Failed", resp.data)

    def test_all_repos_off_returns_failure_page(self):
        resp = self.client.post("/handle-event", data={"org/repo": "off"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Failed", resp.data)

    def test_already_syncing_same_repo_returns_failure_with_error(self):
        with eh._jobs_repo_lock:
            eh._jobs_repo.add("org/repo")
        resp = self.client.post("/handle-event", data={"org/repo": "on"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Already syncing", resp.data)

    @mock.patch(PATH + "initialize_issues")
    @mock.patch(PATH + "initialize_pr")
    def test_valid_repos_returns_in_progress_page(self, _mock_pr, _mock_issues):
        resp = self.client.post("/handle-event", data={"org/repo": "on"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Sync in Progress", resp.data)

    @mock.patch(PATH + "initialize_issues")
    @mock.patch(PATH + "initialize_pr")
    def test_valid_repos_creates_in_progress_job(self, _mock_pr, _mock_issues):
        # Block the sync thread until we have checked the in_progress state
        sync_started = threading.Event()
        _mock_issues.side_effect = lambda *a, **kw: sync_started.wait()

        self.client.post("/handle-event", data={"org/repo": "on"})

        with eh._jobs_lock:
            self.assertEqual(len(eh._jobs), 1)
            job = next(iter(eh._jobs.values()))
        self.assertEqual(job["status"], "in_progress")
        self.assertEqual(job["repos"], ["org/repo"])

        sync_started.set()  # let the thread finish cleanly

    @mock.patch(PATH + "initialize_issues")
    @mock.patch(PATH + "initialize_pr")
    def test_valid_repos_added_to_jobs_repo_set(self, _mock_pr, _mock_issues):
        sync_started = threading.Event()
        _mock_issues.side_effect = lambda *a, **kw: sync_started.wait()

        self.client.post("/handle-event", data={"org/repo": "on"})

        with eh._jobs_repo_lock:
            self.assertIn("org/repo", eh._jobs_repo)

        sync_started.set()


class TestJobStatus(unittest.TestCase):
    """Tests for the /status/<job_id> GET endpoint."""

    def setUp(self):
        eh._jobs.clear()
        self.client = eh.app.test_client()

    def test_unknown_job_returns_404(self):
        resp = self.client.get("/status/nonexistent")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.get_json()["status"], "not_found")

    def test_in_progress_job_returns_status(self):
        eh._jobs["j1"] = _make_job("in_progress")
        resp = self.client.get("/status/j1")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["status"], "in_progress")

    def test_in_progress_job_not_removed_after_read(self):
        eh._jobs["j1"] = _make_job("in_progress")
        self.client.get("/status/j1")
        with eh._jobs_lock:
            self.assertIn("j1", eh._jobs)

    def test_completed_job_returns_status(self):
        eh._jobs["j1"] = _make_job("completed", finished_at=time.monotonic())
        resp = self.client.get("/status/j1")
        self.assertEqual(resp.get_json()["status"], "completed")

    def test_completed_job_readable_on_second_poll(self):
        eh._jobs["j1"] = _make_job("completed", finished_at=time.monotonic())
        self.client.get("/status/j1")
        resp = self.client.get("/status/j1")
        self.assertEqual(resp.get_json()["status"], "completed")

    def test_failed_job_returns_error_message(self):
        eh._jobs["j1"] = _make_job(
            "failed", finished_at=time.monotonic(), error="connection refused"
        )
        resp = self.client.get("/status/j1")
        data = resp.get_json()
        self.assertEqual(data["status"], "failed")
        self.assertEqual(data["error"], "connection refused")

    def test_finished_at_not_exposed_in_response(self):
        eh._jobs["j1"] = _make_job("completed", finished_at=time.monotonic())
        resp = self.client.get("/status/j1")
        self.assertNotIn("finished_at", resp.get_json())


class TestRunSync(unittest.TestCase):
    """Tests for _run_sync — called directly to avoid threading complexity."""

    def setUp(self):
        eh._jobs.clear()
        eh._jobs_repo.clear()

    @mock.patch(PATH + "initialize_issues")
    @mock.patch(PATH + "initialize_pr")
    def test_success_sets_completed_status(self, _mock_pr, _mock_issues):
        eh._jobs["j1"] = _make_job("in_progress")
        eh._jobs_repo.add("org/repo")
        eh._run_sync("j1", ["org/repo"])
        self.assertEqual(eh._jobs["j1"]["status"], "completed")
        self.assertIsNone(eh._jobs["j1"]["error"])

    @mock.patch(PATH + "initialize_issues")
    @mock.patch(PATH + "initialize_pr")
    def test_success_records_finished_at(self, _mock_pr, _mock_issues):
        eh._jobs["j1"] = _make_job("in_progress")
        eh._jobs_repo.add("org/repo")
        before = time.monotonic()
        eh._run_sync("j1", ["org/repo"])
        self.assertIsNotNone(eh._jobs["j1"]["finished_at"])
        self.assertGreaterEqual(eh._jobs["j1"]["finished_at"], before)

    @mock.patch(PATH + "initialize_issues")
    @mock.patch(PATH + "initialize_pr")
    def test_success_releases_repos(self, _mock_pr, _mock_issues):
        eh._jobs["j1"] = _make_job("in_progress")
        eh._jobs_repo.add("org/repo")
        eh._run_sync("j1", ["org/repo"])
        with eh._jobs_repo_lock:
            self.assertNotIn("org/repo", eh._jobs_repo)

    @mock.patch(PATH + "initialize_issues", side_effect=RuntimeError("timeout"))
    @mock.patch(PATH + "initialize_pr")
    def test_failure_sets_failed_status_with_error(self, _mock_pr, _mock_issues):
        eh._jobs["j1"] = _make_job("in_progress")
        eh._jobs_repo.add("org/repo")
        eh._run_sync("j1", ["org/repo"])
        self.assertEqual(eh._jobs["j1"]["status"], "failed")
        self.assertEqual(eh._jobs["j1"]["error"], "timeout")

    @mock.patch(PATH + "initialize_issues", side_effect=RuntimeError("boom"))
    @mock.patch(PATH + "initialize_pr")
    def test_failure_records_finished_at(self, _mock_pr, _mock_issues):
        eh._jobs["j1"] = _make_job("in_progress")
        eh._jobs_repo.add("org/repo")
        eh._run_sync("j1", ["org/repo"])
        self.assertIsNotNone(eh._jobs["j1"]["finished_at"])

    @mock.patch(PATH + "initialize_issues", side_effect=RuntimeError("err"))
    @mock.patch(PATH + "initialize_pr")
    def test_failure_still_releases_repos(self, _mock_pr, _mock_issues):
        eh._jobs["j1"] = _make_job("in_progress")
        eh._jobs_repo.add("org/repo")
        eh._run_sync("j1", ["org/repo"])
        with eh._jobs_repo_lock:
            self.assertNotIn("org/repo", eh._jobs_repo)

    @mock.patch(PATH + "initialize_issues")
    @mock.patch(PATH + "initialize_pr")
    def test_multiple_repos_all_released_on_success(self, _mock_pr, _mock_issues):
        repos = ["org/repo-a", "org/repo-b"]
        eh._jobs["j1"] = _make_job("in_progress", repos=repos)
        with eh._jobs_repo_lock:
            eh._jobs_repo.update(repos)
        eh._run_sync("j1", repos)
        with eh._jobs_repo_lock:
            for r in repos:
                self.assertNotIn(r, eh._jobs_repo)

    @mock.patch(PATH + "initialize_issues", side_effect=RuntimeError("err"))
    @mock.patch(PATH + "initialize_pr")
    def test_multiple_repos_all_released_on_failure(self, _mock_pr, _mock_issues):
        repos = ["org/repo-a", "org/repo-b"]
        eh._jobs["j1"] = _make_job("in_progress", repos=repos)
        with eh._jobs_repo_lock:
            eh._jobs_repo.update(repos)
        eh._run_sync("j1", repos)
        with eh._jobs_repo_lock:
            for r in repos:
                self.assertNotIn(r, eh._jobs_repo)


class TestCleanupExpiredJobs(unittest.TestCase):
    """Tests for _cleanup_expired_jobs — the TTL-based expiry logic."""

    def setUp(self):
        eh._jobs.clear()

    def test_expired_completed_job_is_removed(self):
        eh._jobs["old"] = _make_job(
            "completed", finished_at=time.monotonic() - eh.JOB_TTL_SECONDS - 1
        )
        eh._cleanup_expired_jobs()
        self.assertNotIn("old", eh._jobs)

    def test_expired_failed_job_is_removed(self):
        eh._jobs["old"] = _make_job(
            "failed", finished_at=time.monotonic() - eh.JOB_TTL_SECONDS - 1
        )
        eh._cleanup_expired_jobs()
        self.assertNotIn("old", eh._jobs)

    def test_fresh_terminal_job_is_retained(self):
        eh._jobs["new"] = _make_job("completed", finished_at=time.monotonic())
        eh._cleanup_expired_jobs()
        self.assertIn("new", eh._jobs)

    def test_in_progress_job_never_expired(self):
        eh._jobs["running"] = _make_job("in_progress")
        eh._cleanup_expired_jobs()
        self.assertIn("running", eh._jobs)

    def test_only_expired_jobs_removed(self):
        eh._jobs["old"] = _make_job(
            "completed", finished_at=time.monotonic() - eh.JOB_TTL_SECONDS - 1
        )
        eh._jobs["new"] = _make_job("completed", finished_at=time.monotonic())
        eh._jobs["running"] = _make_job("in_progress")
        eh._cleanup_expired_jobs()
        self.assertNotIn("old", eh._jobs)
        self.assertIn("new", eh._jobs)
        self.assertIn("running", eh._jobs)

    def test_empty_jobs_dict_does_not_raise(self):
        eh._cleanup_expired_jobs()  # should not raise

    def test_job_ttl_constant_is_positive(self):
        self.assertIsInstance(eh.JOB_TTL_SECONDS, int)
        self.assertGreater(eh.JOB_TTL_SECONDS, 0)
