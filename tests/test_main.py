import unittest
import unittest.mock as mock
from unittest.mock import MagicMock, patch

import requests

import sync2jira.jira_auth as jira_auth_module
from sync2jira.jira_auth import (
    build_jira_client_kwargs,
    invalidate_oauth2_cache_for_config,
)
import sync2jira.main as m

PATH = "sync2jira.main."


class MockMessage(object):
    def __init__(self, msg_id, body, topic):
        self.id = msg_id
        self.body = body
        self.topic = topic


class TestMain(unittest.TestCase):
    """
    This class tests the main.py file under sync2jira
    """

    def setUp(self):
        """
        Set up the testing environment
        """
        # Mock Config dict
        self.mock_config = {
            "sync2jira": {
                "jira": {"mock_jira_instance": {"mock_jira": "mock_jira"}},
                "testing": {},
                "legacy_matching": False,
                "map": {"github": {"key_github": {"sync": ["issue", "pullrequest"]}}},
                "initialize": True,
                "listen": True,
                "develop": False,
            },
        }

        # Mock Fedmsg Message
        self.mock_message_body = {"issue": "mock_issue"}
        self.old_style_mock_message = MockMessage(
            msg_id="mock_id",
            body=self.mock_message_body,
            topic=None,
        )
        self.new_style_mock_message = MockMessage(
            msg_id="mock_id",
            body={"body": self.mock_message_body},
            topic=None,
        )

    def _check_for_exception(self, loader, target, exc=ValueError):
        try:
            m.load_config(loader)
            assert False, "Exception expected."
        except exc as e:
            self.assertIn(target, repr(e))

    def test_config_validate_empty(self):
        loader = lambda: {}
        self._check_for_exception(loader, "No sync2jira section")

    def test_config_validate_missing_map(self):
        loader = lambda: {"sync2jira": {}}
        self._check_for_exception(loader, "No sync2jira.map section")

    def test_config_validate_misspelled_mappings(self):
        loader = lambda: {"sync2jira": {"map": {"githob": {}}}, "jira": {}}
        self._check_for_exception(loader, 'Specified handlers: "githob", must')

    def test_config_validate_missing_jira(self):
        loader = lambda: {"sync2jira": {"map": {"github": {}}}}
        self._check_for_exception(loader, "No sync2jira.jira section")

    def test_config_validate_all_good(self):
        loader = lambda: {"sync2jira": {"map": {"github": {}}, "jira": {}}}
        m.load_config(loader)  # Should succeed without an exception.

    @mock.patch(PATH + "report_failure")
    @mock.patch(PATH + "INITIALIZE", 1)
    @mock.patch(PATH + "initialize_issues")
    @mock.patch(PATH + "initialize_pr")
    @mock.patch(PATH + "load_config")
    @mock.patch(PATH + "listen")
    def test_main_initialize(
        self,
        mock_listen,
        mock_load_config,
        mock_initialize_pr,
        mock_initialize_issues,
        mock_report_failure,
    ):
        """
        This tests the 'main' function
        """
        # Set up return values
        mock_load_config.return_value = self.mock_config

        # Call the function
        m.main()

        # Assert everything was called correctly
        mock_load_config.assert_called_once()
        mock_listen.assert_called_with(self.mock_config)
        mock_listen.assert_called_with(self.mock_config)
        mock_initialize_issues.assert_called_with(self.mock_config)
        mock_initialize_pr.assert_called_with(self.mock_config)
        mock_report_failure.assert_not_called()

    @mock.patch(PATH + "report_failure")
    @mock.patch(PATH + "INITIALIZE", 0)
    @mock.patch(PATH + "initialize_issues")
    @mock.patch(PATH + "initialize_pr")
    @mock.patch(PATH + "load_config")
    @mock.patch(PATH + "listen")
    def test_main_no_initialize(
        self,
        mock_listen,
        mock_load_config,
        mock_initialize_pr,
        mock_initialize_issues,
        mock_report_failure,
    ):
        """
        This tests the 'main' function
        """
        # Set up return values
        mock_load_config.return_value = self.mock_config

        # Call the function
        m.main()

        # Assert everything was called correctly
        mock_load_config.assert_called_once()
        mock_listen.assert_called_with(self.mock_config)
        mock_listen.assert_called_with(self.mock_config)
        mock_initialize_issues.assert_not_called()
        mock_initialize_pr.assert_not_called()
        mock_report_failure.assert_not_called()

    @mock.patch(PATH + "u_issue")
    @mock.patch(PATH + "d_issue")
    def test_initialize(self, mock_d, mock_u):
        """
        This tests 'initialize' function where everything goes smoothly!
        """
        # Set up return values
        mock_u.github_issues.return_value = ["mock_issue_github"]

        # Call the function
        m.initialize_issues(self.mock_config)

        # Assert everything was called correctly
        mock_u.github_issues.assert_called_with("key_github", self.mock_config)
        mock_d.sync_with_jira.assert_any_call("mock_issue_github", self.mock_config)

    @mock.patch(PATH + "u_issue")
    @mock.patch(PATH + "d_issue")
    def test_initialize_repo_name_github(self, mock_d, mock_u):
        """
        This tests 'initialize' function where we want to sync an individual repo for GitHub
        """
        # Set up return values
        mock_u.github_issues.return_value = ["mock_issue_github"]

        # Call the function
        m.initialize_issues(self.mock_config, repo_name="key_github")

        # Assert everything was called correctly
        mock_u.github_issues.assert_called_with("key_github", self.mock_config)
        mock_d.sync_with_jira.assert_called_with("mock_issue_github", self.mock_config)

    @mock.patch(PATH + "u_issue")
    @mock.patch(PATH + "d_issue")
    def test_initialize_errors(self, mock_d, mock_u):
        """
        This tests 'initialize' function where syncing with JIRA throws an exception
        """
        # Set up return values
        mock_u.github_issues.return_value = ["mock_issue_github"]
        mock_d.sync_with_jira.side_effect = Exception()

        # Call the function
        with self.assertRaises(Exception):
            m.initialize_issues(self.mock_config)

        # Assert everything was called correctly
        mock_u.github_issues.assert_called_with("key_github", self.mock_config)
        mock_d.sync_with_jira.assert_any_call("mock_issue_github", self.mock_config)

    @mock.patch(PATH + "u_issue")
    @mock.patch(PATH + "d_issue")
    @mock.patch(PATH + "sleep")
    @mock.patch(PATH + "report_failure")
    def test_initialize_api_limit(
        self, mock_report_failure, mock_sleep, mock_d, mock_u
    ):
        """
        This tests 'initialize' where we get an GitHub API limit error.
        """
        # Set up return values
        mock_error = MagicMock(side_effect=Exception("API rate limit exceeded"))
        mock_u.github_issues.side_effect = mock_error

        # Call the function
        m.initialize_issues(self.mock_config, testing=True)

        # Assert everything was called correctly
        mock_u.github_issues.assert_called_with("key_github", self.mock_config)
        mock_d.sync_with_jira.assert_not_called()
        mock_sleep.assert_called_with(3600)
        mock_report_failure.assert_not_called()

    @mock.patch(PATH + "u_issue")
    @mock.patch(PATH + "d_issue")
    @mock.patch(PATH + "sleep")
    @mock.patch(PATH + "report_failure")
    def test_initialize_github_error(
        self, mock_report_failure, mock_sleep, mock_d, mock_u
    ):
        """
        This tests 'initialize' where we get a GitHub API (not limit) error.
        """
        # Set up return values
        mock_error = MagicMock(side_effect=Exception("Random Error"))
        mock_u.github_issues.side_effect = mock_error

        # Call the function
        with self.assertRaises(Exception):
            m.initialize_issues(self.mock_config, testing=True)

        # Assert everything was called correctly
        mock_u.github_issues.assert_called_with("key_github", self.mock_config)
        mock_d.sync_with_jira.assert_not_called()
        mock_sleep.assert_not_called()
        mock_report_failure.assert_called_with(self.mock_config)

    @mock.patch(PATH + "handle_msg")
    @mock.patch(PATH + "load_config")
    def test_listen_no_handlers(self, mock_load_config, mock_handle_msg):
        """
        Test 'listen' function where suffix is not in handlers
        """
        # Set up return values
        mock_load_config.return_value = self.mock_config

        # Call the function
        self.old_style_mock_message.topic = "d.d.d.github.issue.no_handlers_match_this"
        m.callback(self.old_style_mock_message)

        # Assert everything was called correctly
        mock_handle_msg.assert_not_called()

    @mock.patch.dict(
        PATH + "issue_handlers", {"github.issue.comment": lambda msg, c: "dummy_issue"}
    )
    @mock.patch(PATH + "handle_msg")
    @mock.patch(PATH + "load_config")
    def test_listen(self, mock_load_config, mock_handle_msg):
        """
        Test 'listen' function where everything goes smoothly
        """
        # Set up return values
        mock_load_config.return_value = self.mock_config

        # Call the function once with the old style
        self.old_style_mock_message.topic = "d.d.d.github.issue.comment"
        m.callback(self.old_style_mock_message)

        # ... and again with the new style
        self.new_style_mock_message.topic = "d.d.d.github.issue.comment"
        m.callback(self.new_style_mock_message)

        # Assert everything was called correctly
        # It should be called twice, once for the old style message and once for the new.
        mock_handle_msg.assert_has_calls(
            [
                mock.call(
                    self.mock_message_body, "github.issue.comment", self.mock_config
                ),
                mock.call(
                    self.mock_message_body, "github.issue.comment", self.mock_config
                ),
            ]
        )

    @mock.patch(PATH + "send_mail")
    @mock.patch(PATH + "jinja2")
    def test_report_failure(self, mock_jinja2, mock_send_mail):
        """
        Tests 'report_failure' function
        """
        # Set up return values
        mock_template_loader = MagicMock()
        mock_template_env = MagicMock()
        mock_template = MagicMock()
        mock_template.render.return_value = "mock_html"
        mock_template_env.get_template.return_value = mock_template
        mock_jinja2.FileSystemLoader.return_value = mock_template_loader
        mock_jinja2.Environment.return_value = mock_template_env

        # Call the function
        m.report_failure({"sync2jira": {"mailing-list": "mock_email"}})

        # Assert everything was called correctly
        mock_send_mail.assert_called_with(
            cc=None,
            recipients=["mock_email"],
            subject="Sync2Jira Has Failed!",
            text="mock_html",
        )

    @mock.patch(PATH + "u_issue")
    @mock.patch(PATH + "d_issue")
    def test_handle_msg_no_handlers(self, mock_d, mock_u):
        """
        Tests 'handle_msg' function where there are no handlers
        """
        # Call the function
        m.handle_msg(
            body=self.mock_message_body, suffix="no_handler", config=self.mock_config
        )

        # Assert everything was called correctly
        mock_d.sync_with_jira.assert_not_called()
        mock_u.handle_github_message.assert_not_called()

    @mock.patch.dict(
        PATH + "issue_handlers", {"github.issue.comment": lambda msg, c: None}
    )
    @mock.patch(PATH + "u_issue")
    @mock.patch(PATH + "d_issue")
    def test_handle_msg_no_issue(self, mock_d, mock_u):
        """
        Tests 'handle_msg' function where there is no issue
        """
        # Call the function
        m.handle_msg(
            body=self.mock_message_body,
            suffix="github.issue.comment",
            config=self.mock_config,
        )

        # Assert everything was called correctly
        mock_d.sync_with_jira.assert_not_called()
        mock_u.handle_github_message.assert_not_called()

    @mock.patch.dict(
        PATH + "issue_handlers", {"github.issue.comment": lambda msg, c: "dummy_issue"}
    )
    @mock.patch(PATH + "u_issue")
    @mock.patch(PATH + "d_issue")
    def test_handle_msg(self, mock_d, mock_u):
        """
        Tests 'handle_msg' function
        """
        # Set up return values
        mock_u.handle_github_message.return_value = "dummy_issue"

        # Call the function
        m.handle_msg(
            body=self.mock_message_body,
            suffix="github.issue.comment",
            config=self.mock_config,
        )

        # Assert everything was called correctly
        mock_d.sync_with_jira.assert_called_with("dummy_issue", self.mock_config)


class TestJiraAuth(unittest.TestCase):
    """Tests for Jira auth: PAT and OAuth2 (build_jira_client_kwargs)."""

    def setUp(self):
        """Clear OAuth2 token cache so tests don't reuse tokens from other tests."""
        jira_auth_module._oauth2_token_cache.clear()

    def test_jira_auth_pat_with_basic_auth(self):
        """PAT with basic_auth succeeds."""
        config = {
            "options": {"server": "https://jira.example.com", "verify": True},
            "basic_auth": ("user", "pass"),
        }
        kwargs = build_jira_client_kwargs(config)
        self.assertEqual(kwargs["basic_auth"], ("user", "pass"))
        self.assertEqual(kwargs["options"], config["options"])

    def test_jira_auth_pat_missing_basic_auth(self):
        """PAT without basic_auth raises ValueError."""
        config = {
            "options": {"server": "https://jira.example.com"},
        }
        with self.assertRaises(ValueError) as ctx:
            build_jira_client_kwargs(config)
        self.assertIn("basic_auth", str(ctx.exception))

    @patch("sync2jira.jira_auth.requests.post")
    def test_jira_auth_oauth2_cache(self, mock_post):
        """OAuth2 second call reuses cached token (no second request)."""
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "access_token": "cached_token",
                "expires_in": 3600,
            },
            raise_for_status=MagicMock(),
        )
        config = {
            "options": {"server": "https://site.atlassian.net"},
            "auth_method": "oauth2",
            "oauth2": {"client_id": "cid", "client_secret": "csecret"},
        }
        kwargs1 = build_jira_client_kwargs(config)
        kwargs2 = build_jira_client_kwargs(config)
        self.assertEqual(kwargs1["token_auth"], "cached_token")
        self.assertEqual(kwargs2["token_auth"], "cached_token")
        mock_post.assert_called_once()

    @patch("sync2jira.jira_auth.time.time")
    @patch("sync2jira.jira_auth.requests.post")
    def test_jira_auth_oauth2_refresh(self, mock_post, mock_time):
        """OAuth2 expired token triggers new token fetch; second token is used."""
        mock_time.return_value = 1000.0

        # Return different tokens per call so we can verify the second call's result is used
        def make_response(access_token, expires_in=60):
            return MagicMock(
                status_code=200,
                json=lambda t=access_token, e=expires_in: {
                    "access_token": t,
                    "expires_in": e,
                },
                raise_for_status=MagicMock(),
            )

        mock_post.side_effect = [
            make_response("first_token"),
            make_response("refreshed_token"),
        ]
        config = {
            "options": {"server": "https://site.atlassian.net"},
            "auth_method": "oauth2",
            "oauth2": {"client_id": "cid", "client_secret": "csecret"},
        }
        # First call populates cache (expires at 1000 + 60 = 1060)
        build_jira_client_kwargs(config)
        # Advance time past expiry (e.g. 2000)
        mock_time.return_value = 2000.0
        kwargs = build_jira_client_kwargs(config)
        self.assertEqual(kwargs["token_auth"], "refreshed_token")
        self.assertEqual(mock_post.call_count, 2)

    def test_jira_auth_oauth2_missing_credentials(self):
        """OAuth2 missing client_id or client_secret raises ValueError."""
        base = {
            "options": {"server": "https://site.atlassian.net"},
            "auth_method": "oauth2",
        }
        for oauth2_cfg in [
            {},
            {"client_id": "cid"},
            {"client_secret": "csecret"},
        ]:
            config = base | {"oauth2": oauth2_cfg}
            with self.assertRaises(ValueError) as ctx:
                build_jira_client_kwargs(config)
            self.assertIn("client_id and oauth2.client_secret", str(ctx.exception))

    @patch("sync2jira.jira_auth.requests.post")
    def test_jira_auth_oauth2_request_failure(self, mock_post):
        """OAuth2 token request failure propagates requests.RequestException."""
        mock_post.side_effect = requests.RequestException("network error")
        config = {
            "options": {"server": "https://site.atlassian.net"},
            "auth_method": "oauth2",
            "oauth2": {"client_id": "cid", "client_secret": "csecret"},
        }
        with self.assertRaises(requests.RequestException) as ctx:
            build_jira_client_kwargs(config)
        self.assertIn("network error", str(ctx.exception))

    @patch("sync2jira.jira_auth.requests.post")
    def test_jira_auth_invalidate_oauth2_clears_cache(self, mock_post):
        """invalidate_oauth2_cache_for_config clears OAuth2 cache; next build fetches new token."""

        def make_response(access_token):
            return MagicMock(
                status_code=200,
                json=lambda t=access_token: {"access_token": t, "expires_in": 3600},
                raise_for_status=MagicMock(),
            )

        mock_post.side_effect = [
            make_response("cached_token"),
            make_response("new_token_after_invalidate"),
        ]
        config = {
            "options": {"server": "https://site.atlassian.net"},
            "auth_method": "oauth2",
            "oauth2": {"client_id": "cid", "client_secret": "csecret"},
        }
        kwargs1 = build_jira_client_kwargs(config)
        self.assertEqual(kwargs1["token_auth"], "cached_token")
        kwargs2 = build_jira_client_kwargs(config)
        self.assertEqual(kwargs2["token_auth"], "cached_token")
        invalidate_oauth2_cache_for_config(config)
        kwargs3 = build_jira_client_kwargs(config)
        self.assertEqual(kwargs3["token_auth"], "new_token_after_invalidate")
        self.assertEqual(mock_post.call_count, 2)
