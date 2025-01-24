import unittest
import unittest.mock as mock
from unittest.mock import MagicMock

import sync2jira.main as m

PATH = "sync2jira.main."


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
        self.old_style_mock_message = {
            "msg_id": "mock_id",
            "msg": self.mock_message_body,
        }
        self.new_style_mock_message = {
            "msg_id": "mock_id",
            "body": {"body": self.mock_message_body},
        }

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

    @mock.patch(PATH + "u_issue")
    @mock.patch(PATH + "d_issue")
    @mock.patch(PATH + "load_config")
    def test_close_duplicates(self, mock_load_config, mock_d, mock_u):
        """
        This tests the 'close_duplicates' function where everything goes smoothly
        """
        # Set up return values
        mock_load_config.return_value = self.mock_config
        mock_u.github_issues.return_value = ["mock_issue_github"]

        # Call the function
        m.close_duplicates()

        # Assert everything was called correctly
        mock_load_config.assert_called_once()
        mock_u.github_issues.assert_called_with("key_github", self.mock_config)
        mock_d.close_duplicates.assert_any_call("mock_issue_github", self.mock_config)

    @mock.patch(PATH + "u_issue")
    @mock.patch(PATH + "d_issue")
    @mock.patch(PATH + "load_config")
    def test_close_duplicates_errors(self, mock_load_config, mock_d, mock_u):
        """
        This tests the 'close_duplicates' function where closing duplicates raises an exception
        """
        # Set up return values
        mock_load_config.return_value = self.mock_config
        mock_u.github_issues.return_value = ["mock_issue"]
        mock_d.close_duplicates.side_effect = Exception()

        # Call the function
        with self.assertRaises(Exception):
            m.close_duplicates()

        # Assert everything was called correctly
        mock_load_config.assert_called_once()
        mock_u.github_issues.assert_called_once()
        mock_d.close_duplicates.assert_called_with("mock_issue", self.mock_config)

    @mock.patch(PATH + "load_config")
    @mock.patch(PATH + "u_issue")
    def test_list_managed(self, mock_u, mock_load_config):
        """
        This tests the 'list_managed' function
        """
        # Set up return values
        mock_load_config.return_value = self.mock_config

        # Call the function
        m.list_managed()

        # Assert everything was called correctly
        mock_load_config.assert_called_once()
        mock_u.github_issues.assert_called_with("key_github", self.mock_config)

    @mock.patch(PATH + "initialize_recent")
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
        mock_initialize_recent,
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
        mock_initialize_recent.assert_not_called()

    @mock.patch(PATH + "initialize_recent")
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
        mock_initialize_recent,
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
        mock_initialize_recent.assert_called_with(self.mock_config)

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
    @mock.patch(PATH + "fedmsg")
    def test_listen_no_handlers(self, mock_fedmsg, mock_handle_msg):
        """
        Test 'listen' function where suffix is not in handlers
        """
        # Set up return values
        mock_fedmsg.tail_messages.return_value = [
            ("dummy", "dummy", "mock_topic", self.old_style_mock_message)
        ]

        # Call the function
        m.listen(self.mock_config)

        # Assert everything was called correctly
        mock_handle_msg.assert_not_called()

    @mock.patch(PATH + "handle_msg")
    @mock.patch(PATH + "issue_handlers")
    @mock.patch(PATH + "fedmsg")
    def test_listen_no_issue(self, mock_fedmsg, mock_handlers_issue, mock_handle_msg):
        """
        Test 'listen' function where the handler returns none
        """
        # Set up return values
        mock_handlers_issue["github.issue.comment"].return_value = None
        mock_fedmsg.tail_messages.return_value = [
            ("dummy", "dummy", "d.d.d.github.issue.drop", self.old_style_mock_message)
        ]

        # Call the function
        m.listen(self.mock_config)

        # Assert everything was called correctly
        mock_handle_msg.assert_not_called()

    @mock.patch(PATH + "handle_msg")
    @mock.patch(PATH + "issue_handlers")
    @mock.patch(PATH + "fedmsg")
    def test_listen(self, mock_fedmsg, mock_handlers_issue, mock_handle_msg):
        """
        Test 'listen' function where everything goes smoothly
        """
        # Set up return values
        mock_handlers_issue["github.issue.comment"].return_value = "dummy_issue"
        mock_fedmsg.tail_messages.return_value = [
            (
                "dummy",
                "dummy",
                "d.d.d.github.issue.comment",
                self.old_style_mock_message,
            ),
            (
                "dummy",
                "dummy",
                "d.d.d.github.issue.comment",
                self.new_style_mock_message,
            ),
        ]

        # Call the function
        m.listen(self.mock_config)

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

    @mock.patch(PATH + "handle_msg")
    @mock.patch(PATH + "query")
    def test_initialize_recent(self, mock_query, mock_handle_msg):
        """
        Tests 'initialize_recent' function
        """
        # Set up return values
        mock_query.return_value = [
            {"topic": "m.m.m.github.issue.comment", "msg": "mock_msg"}
        ]

        # Call the function
        m.initialize_recent(self.mock_config)

        # Assert everything was called correctly
        mock_handle_msg.assert_called_with(
            "mock_msg", "github.issue.comment", self.mock_config
        )

    @mock.patch(PATH + "handle_msg")
    @mock.patch(PATH + "query")
    def test_initialize_recent_no_handler(self, mock_query, mock_handle_msg):
        """
        Tests 'initialize_recent' function where the topic is not for a valid handler
        """
        # Set up return values
        mock_query.return_value = [{"topic": "m.m.m.bad.topic", "msg": "mock_msg"}]

        # Call the function
        m.initialize_recent(self.mock_config)

        # Assert everything was called correctly
        mock_handle_msg.assert_not_called()

    @mock.patch(PATH + "get")
    def test_query(self, mock_get):
        """
        Tests 'query' function
        """
        # Set up return values
        mock_get.return_value = {"raw_messages": ["test_msg"], "count": 1, "total": 1}
        # Call the function
        response = list(m.query())

        # Assert everything was called correctly
        mock_get.assert_called_once()
        self.assertEqual(mock_get.call_args.kwargs["params"]["order"], "asc")
        self.assertEqual(response, ["test_msg"])

    @mock.patch(PATH + "HTTPKerberosAuth")
    @mock.patch(PATH + "requests")
    def test_get(self, mock_requests, mock_kerberos_auth):
        """
        Tests 'get' function
        """
        # Set up return values
        mock_response = MagicMock()
        mock_response.json.return_value = "mock_return_value"
        mock_requests.get.return_value = mock_response

        # Call the function
        response = m.get("mock_params")

        # Assert everything was called correctly
        self.assertEqual(response, "mock_return_value")
        mock_requests.get.assert_called_with(
            auth=mock_kerberos_auth(),
            headers={"Accept": "application/json"},
            params="mock_params",
            url=m.DATAGREPPER_URL,
        )
