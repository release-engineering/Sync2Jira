import os
import pathlib
import sys
import time
import unittest
from unittest import mock

# Set required env vars before the module is imported
os.environ.setdefault("BASE_URL", "localhost")
os.environ.setdefault("REDIRECT_URL", "example.com")

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "sync-page"))

with mock.patch(
    "sync2jira.main.load_config", return_value={"sync2jira": {"map": {"github": {}}}}
):
    import event_handler as eh

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
        eh._jobs.clear()
        eh._jobs_repo.clear()
        self.client = eh.app.test_client()

    @mock.patch(PATH + "_cleanup_expired_jobs")
    @mock.patch(PATH + "render_template", return_value="")
    def test_no_repos_selected_returns_failure_page(self, mock_render, _mock_cleanup):
        resp = self.client.post("/handle-event", data={})
        self.assertEqual(resp.status_code, 400)
        mock_render.assert_called_once_with("sync-page-failure.jinja", url=mock.ANY)

    @mock.patch(PATH + "_cleanup_expired_jobs")
    @mock.patch(PATH + "render_template", return_value="")
    def test_all_repos_off_returns_failure_page(self, mock_render, _mock_cleanup):
        resp = self.client.post("/handle-event", data={"org/repo": "off"})
        self.assertEqual(resp.status_code, 400)
        mock_render.assert_called_once_with("sync-page-failure.jinja", url=mock.ANY)

    @mock.patch(PATH + "_cleanup_expired_jobs")
    @mock.patch(PATH + "render_template", return_value="")
    def test_already_syncing_same_repo_returns_failure_with_error(
        self, mock_render, _mock_cleanup
    ):
        # repo-b overlaps; repo-a is new; repo-c is an unrelated concurrent sync
        with eh._jobs_repo_lock:
            eh._jobs_repo.update(["org/repo-b", "org/repo-c"])

        resp = self.client.post(
            "/handle-event", data={"org/repo-a": "on", "org/repo-b": "on"}
        )

        self.assertEqual(resp.status_code, 409)
        _, kwargs = mock_render.call_args
        self.assertIn("org/repo-b", kwargs["error"])  # the conflicting repo is named
        self.assertNotIn(
            "org/repo-a", kwargs["error"]
        )  # the non-conflicting repo is not

    @mock.patch(PATH + "_cleanup_expired_jobs")
    @mock.patch("threading.Thread")
    @mock.patch(PATH + "render_template", return_value="")
    def test_valid_repos_creates_job_and_starts_thread(
        self, mock_render, mock_thread, _mock_cleanup
    ):
        resp = self.client.post("/handle-event", data={"org/repo": "on"})

        self.assertEqual(resp.status_code, 200)
        mock_render.assert_called_once_with(
            "sync-page-in-progress.jinja",
            job_id=mock.ANY,
            synced_repos=["org/repo"],
            url=mock.ANY,
        )

        # Job created in in_progress state
        with eh._jobs_lock:
            self.assertEqual(len(eh._jobs), 1)
            job = next(iter(eh._jobs.values()))
        self.assertEqual(job["status"], "in_progress")
        self.assertEqual(job["repos"], ["org/repo"])

        # Repo locked for the duration of the sync
        with eh._jobs_repo_lock:
            self.assertIn("org/repo", eh._jobs_repo)

        # Background thread created and started with correct arguments
        mock_thread.assert_called_once_with(
            target=eh._run_sync, args=(mock.ANY, ["org/repo"]), daemon=True
        )
        mock_thread.return_value.start.assert_called_once()


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
    def test_success(self, _mock_pr, _mock_issues):
        repos = ["org/repo-a", "org/repo-b"]
        eh._jobs["j1"] = _make_job("in_progress", repos=repos)
        with eh._jobs_repo_lock:
            # Simulate a concurrent sync holding an unrelated repo
            eh._jobs_repo.update(repos + ["org/other-sync"])
        before = time.monotonic()

        eh._run_sync("j1", repos)

        self.assertEqual(eh._jobs["j1"]["status"], "completed")
        self.assertIsNone(eh._jobs["j1"]["error"])
        self.assertIsInstance(eh._jobs["j1"]["finished_at"], float)
        self.assertGreaterEqual(eh._jobs["j1"]["finished_at"], before)
        with eh._jobs_repo_lock:
            self.assertNotIn("org/repo-a", eh._jobs_repo)  # job's repos released
            self.assertNotIn("org/repo-b", eh._jobs_repo)
            self.assertIn("org/other-sync", eh._jobs_repo)  # unrelated sync untouched

    @mock.patch(
        PATH + "initialize_issues", side_effect=RuntimeError("connection refused")
    )
    @mock.patch(PATH + "initialize_pr")
    def test_failure_via_initialize_issues(self, _mock_pr, _mock_issues):
        repos = ["org/repo"]
        eh._jobs["j1"] = _make_job("in_progress", repos=repos)
        with eh._jobs_repo_lock:
            eh._jobs_repo.update(repos + ["org/other-sync"])

        eh._run_sync("j1", repos)

        self.assertEqual(eh._jobs["j1"]["status"], "failed")
        self.assertEqual(eh._jobs["j1"]["error"], "connection refused")
        self.assertIsNotNone(eh._jobs["j1"]["finished_at"])
        with eh._jobs_repo_lock:
            self.assertNotIn("org/repo", eh._jobs_repo)
            self.assertIn("org/other-sync", eh._jobs_repo)

    @mock.patch(PATH + "initialize_issues")
    @mock.patch(PATH + "initialize_pr", side_effect=RuntimeError("pr fetch failed"))
    def test_failure_via_initialize_pr(self, _mock_pr, _mock_issues):
        repos = ["org/repo"]
        eh._jobs["j1"] = _make_job("in_progress", repos=repos)
        with eh._jobs_repo_lock:
            eh._jobs_repo.update(repos + ["org/other-sync"])

        eh._run_sync("j1", repos)

        self.assertEqual(eh._jobs["j1"]["status"], "failed")
        self.assertEqual(eh._jobs["j1"]["error"], "pr fetch failed")
        self.assertIsNotNone(eh._jobs["j1"]["finished_at"])
        with eh._jobs_repo_lock:
            self.assertNotIn("org/repo", eh._jobs_repo)
            self.assertIn("org/other-sync", eh._jobs_repo)


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


class TestSyncPage(unittest.TestCase):
    """Tests for the sync page endpoints."""

    def setUp(self):
        self.client = eh.app.test_client()

    @mock.patch(PATH + "render_template", return_value="")
    def test_github_sync_page(self, mock_render):
        # no config
        resp = self.client.get("/github")
        self.assertEqual(resp.status_code, 200)
        mock_render.assert_called_once_with(
            "sync-page-github.jinja", github={}, url=mock.ANY
        )

    @mock.patch(PATH + "render_template", return_value="")
    def test_github_sync_page_with_config(self, mock_render):
        # with config
        with mock.patch(
            PATH + "config", {"sync2jira": {"map": {"github": {"org/repo": "on"}}}}
        ):
            resp = self.client.get("/github")
            self.assertEqual(resp.status_code, 200)
            mock_render.assert_called_once_with(
                "sync-page-github.jinja", github={"org/repo": "on"}, url=mock.ANY
            )

    def test_sync_page_redirects_to_github(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.location, "/github")
