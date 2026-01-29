import unittest
import unittest.mock as mock
from unittest.mock import MagicMock

import sync2jira.downstream_pr as d

PATH = "sync2jira.downstream_pr."


class TestDownstreamPR(unittest.TestCase):
    """
    This class tests the downstream_pr.py file under sync2jira
    """

    def setUp(self):
        """
        Setting up the testing environment
        """
        self.mock_pr = MagicMock()
        self.mock_pr.jira_key = "JIRA-1234"
        self.mock_pr.suffix = "mock_suffix"
        self.mock_pr.title = "mock_title"
        self.mock_pr.url = "mock_url"
        self.mock_pr.reporter = "mock_reporter"
        self.mock_pr.downstream = {
            "pr_updates": [
                {"merge_transition": "CUSTOM_TRANSITION1"},
                {"link_transition": "CUSTOM_TRANSITION2"},
            ]
        }
        self.mock_config = {
            "sync2jira": {
                "default_jira_instance": "another_jira_instance",
                "jira_username": "mock_user",
                "jira": {
                    "mock_jira_instance": {"mock_jira": "mock_jira"},
                    "another_jira_instance": {
                        "token_auth": "mock_token",
                        "options": {"server": "mock_server"},
                    },
                },
                "testing": False,
                "legacy_matching": False,
                "admins": [{"mock_admin": "mock_email"}],
                "develop": False,
            },
        }

        self.mock_client = MagicMock()
        mock_user = MagicMock()
        mock_user.displayName = "mock_reporter"
        mock_user.key = "mock_key"
        self.mock_client.search_users.return_value = [mock_user]
        self.mock_client.search_issues.return_value = ["mock_existing"]

        self.mock_existing = MagicMock()

    @mock.patch(PATH + "update_jira_issue")
    @mock.patch(PATH + "d_issue")
    def test_sync_with_jira_link(self, mock_d_issue, mock_update_jira_issue):
        """
        This function tests 'sync_with_jira'
        """
        # Set up return values
        mock_d_issue.get_jira_client.return_value = self.mock_client

        # Call the function
        d.sync_with_jira(self.mock_pr, self.mock_config)

        # Assert everything was called correctly
        mock_update_jira_issue.assert_called_with(
            "mock_existing", self.mock_pr, self.mock_client
        )
        self.mock_client.search_issues.assert_called_with("Key = JIRA-1234")
        mock_d_issue.get_jira_client.assert_called_with(self.mock_pr, self.mock_config)

    @mock.patch(PATH + "update_jira_issue")
    @mock.patch(PATH + "d_issue")
    def test_sync_with_jira_merged(self, mock_d_issue, mock_update_jira_issue):
        """
        This function tests 'sync_with_jira'
        """
        # Set up return values
        mock_client = MagicMock()
        mock_client.search_issues.return_value = ["mock_existing"]
        mock_d_issue.get_jira_client.return_value = mock_client
        self.mock_pr.suffix = "merged"

        # Call the function
        d.sync_with_jira(self.mock_pr, self.mock_config)

        # Assert everything was called correctly
        mock_update_jira_issue.assert_called_with(
            "mock_existing", self.mock_pr, mock_client
        )
        mock_client.search_issues.assert_called_with("Key = JIRA-1234")
        mock_d_issue.get_jira_client.assert_called_with(self.mock_pr, self.mock_config)

    @mock.patch(PATH + "update_jira_issue")
    @mock.patch(PATH + "d_issue")
    def test_sync_with_jira_no_match(self, mock_d_issue, mock_update_jira_issue):
        """
        This function tests 'sync_with_jira' when the PR contains no matched issue.
        """
        # Set up return values
        mock_d_issue.get_jira_client.return_value = self.mock_client
        self.mock_pr.jira_key = None

        # Call the function
        d.sync_with_jira(self.mock_pr, self.mock_config)

        # Assert everything was called correctly
        mock_d_issue.get_jira_client.assert_called_with(self.mock_pr, self.mock_config)
        self.mock_client.search_issues.assert_not_called()
        mock_update_jira_issue.assert_not_called()

    @mock.patch(PATH + "update_jira_issue")
    @mock.patch(PATH + "d_issue")
    def test_sync_with_jira_no_issues_found(self, mock_d_issue, mock_update_jira_issue):
        """
        This function tests 'sync_with_jira' where no issues are found
        """
        # Set up return values
        self.mock_client.search_issues.return_value = []
        mock_d_issue.get_jira_client.return_value = self.mock_client

        # Call the function
        d.sync_with_jira(self.mock_pr, self.mock_config)

        # Assert everything was called correctly
        mock_update_jira_issue.assert_not_called()
        self.mock_client.search_issues.assert_called_with("Key = JIRA-1234")
        mock_d_issue.get_jira_client.assert_called_with(self.mock_pr, self.mock_config)

    @mock.patch(PATH + "update_jira_issue")
    @mock.patch(PATH + "d_issue")
    def test_sync_with_jira_testing(self, mock_d_issue, mock_update_jira_issue):
        """
        This function tests 'sync_with_jira' where no issues are found
        """
        # Set up return values
        mock_client = MagicMock()
        mock_client.search_issues.return_value = []
        self.mock_config["sync2jira"]["testing"] = True
        mock_d_issue.get_jira_client.return_value = mock_client

        # Call the function
        d.sync_with_jira(self.mock_pr, self.mock_config)

        # Assert everything was called correctly
        mock_update_jira_issue.assert_not_called()
        mock_client.search_issues.assert_not_called()
        mock_d_issue.get_jira_client.assert_not_called()

    @mock.patch(PATH + "comment_exists")
    @mock.patch(PATH + "format_comment")
    @mock.patch(PATH + "d_issue.attach_link")
    @mock.patch(PATH + "issue_link_exists")
    def test_update_jira_issue_link(
        self,
        mock_issue_link_exists,
        mock_attach_link,
        mock_format_comment,
        mock_comment_exists,
    ):
        """
        This function tests 'update_jira_issue'
        """
        # Set up return values
        mock_format_comment.return_value = "mock_formatted_comment"
        mock_comment_exists.return_value = False
        mock_issue_link_exists.return_value = False

        # Call the function
        d.update_jira_issue("mock_existing", self.mock_pr, self.mock_client)

        # Assert everything was called correctly
        self.mock_client.add_comment.assert_called_with(
            "mock_existing", "mock_formatted_comment"
        )
        mock_format_comment.assert_called_with(
            self.mock_pr, self.mock_pr.suffix, self.mock_client
        )
        mock_comment_exists.assert_called_with(
            self.mock_client, "mock_existing", "mock_formatted_comment"
        )
        mock_attach_link.assert_called_with(
            self.mock_client,
            "mock_existing",
            {"url": "mock_url", "title": "[PR] mock_title"},
        )

    def test_issue_link_exists_false(self):
        """
        This function tests 'issue_link_exists' where it does not exist
        """
        # Set up return values
        mock_issue_link = MagicMock()
        mock_issue_link.object.url = "bad_url"
        self.mock_client.remote_links.return_value = [mock_issue_link]

        # Call the function
        ret = d.issue_link_exists(self.mock_client, self.mock_existing, self.mock_pr)

        # Assert everything was called correctly
        self.mock_client.remote_links.assert_called_with(self.mock_existing)
        self.assertEqual(ret, False)

    def test_issue_link_exists_true(self):
        """
        This function tests 'issue_link_exists' where it does exist
        """
        # Set up return values
        mock_issue_link = MagicMock()
        mock_issue_link.object.url = self.mock_pr.url
        self.mock_client.remote_links.return_value = [mock_issue_link]

        # Call the function
        ret = d.issue_link_exists(self.mock_client, self.mock_existing, self.mock_pr)

        # Assert everything was called correctly
        self.mock_client.remote_links.assert_called_with(self.mock_existing)
        self.assertEqual(ret, True)

    @mock.patch(PATH + "format_comment")
    @mock.patch(PATH + "comment_exists")
    @mock.patch(PATH + "d_issue.attach_link")
    @mock.patch(PATH + "issue_link_exists")
    def test_update_jira_issue_exists(
        self,
        mock_issue_link_exists,
        mock_attach_link,
        mock_comment_exists,
        mock_format_comment,
    ):
        """
        This function tests 'update_jira_issue' where the comment already exists
        """
        # Set up return values
        mock_format_comment.return_value = "mock_formatted_comment"
        mock_comment_exists.return_value = True
        mock_issue_link_exists.return_value = True

        # Call the function
        d.update_jira_issue("mock_existing", self.mock_pr, self.mock_client)

        # Assert everything was called correctly
        self.mock_client.add_comment.assert_not_called()
        mock_format_comment.assert_called_with(
            self.mock_pr, self.mock_pr.suffix, self.mock_client
        )
        mock_comment_exists.assert_called_with(
            self.mock_client, "mock_existing", "mock_formatted_comment"
        )
        mock_attach_link.assert_not_called()
        mock_issue_link_exists.assert_called_with(
            self.mock_client, "mock_existing", self.mock_pr
        )

    def test_comment_exists_false(self):
        """
        This function tests 'comment_exists' where the comment does not exists
        """
        # Set up return values
        mock_comment = MagicMock()
        mock_comment.body = "not_mock_new_comment"
        self.mock_client.comments.return_value = [mock_comment]

        # Call the function
        response = d.comment_exists(
            self.mock_client, "mock_existing", "mock_new_comment"
        )

        # Assert Everything was called correctly
        self.mock_client.comments.assert_called_with("mock_existing")
        self.assertEqual(response, False)

    def test_comment_exists_true(self):
        """
        This function tests 'comment_exists' where the comment exists
        """
        # Set up return values
        mock_comment = MagicMock()
        mock_comment.body = "mock_new_comment"
        self.mock_client.comments.return_value = [mock_comment]

        # Call the function
        response = d.comment_exists(
            self.mock_client, "mock_existing", "mock_new_comment"
        )

        # Assert Everything was called correctly
        self.mock_client.comments.assert_called_with("mock_existing")
        self.assertEqual(response, True)

    def test_format_comment_closed(self):
        """
        This function tests 'format_comment' where the PR is closed
        """
        # Call the function
        response = d.format_comment(self.mock_pr, "closed", self.mock_client)

        # Assert Everything was called correctly
        self.assertEqual(response, "Merge request [mock_title| mock_url] was closed.")

    def test_format_comment_reopened(self):
        """
        This function tests 'format_comment' where the PR is reopened
        """
        # Call the function
        response = d.format_comment(self.mock_pr, "reopened", self.mock_client)

        # Assert Everything was called correctly
        self.assertEqual(response, "Merge request [mock_title| mock_url] was reopened.")

    def test_format_comment_merged(self):
        """
        This function tests 'format_comment' where the PR is merged
        """
        # Call the function
        response = d.format_comment(self.mock_pr, "merged", self.mock_client)

        # Assert Everything was called correctly
        self.assertEqual(response, "Merge request [mock_title| mock_url] was merged!")

    def test_format_comment_open(self):
        """
        This function tests 'format_comment' where the PR is open
        """
        # Call the function
        response = d.format_comment(self.mock_pr, "open", self.mock_client)

        # Assert Everything was called correctly
        self.assertEqual(
            response,
            "[~mock_key] mentioned this issue in merge request [mock_title| mock_url].",
        )

    def test_format_comment_open_no_user_found(self):
        """
        This function tests 'format_comment' where the PR is open and search_users returns nothing
        """
        # Set up return values
        self.mock_client.search_users.return_value = []

        # Call the function
        response = d.format_comment(self.mock_pr, "open", self.mock_client)

        # Assert Everything was called correctly
        self.assertEqual(
            response,
            "mock_reporter mentioned this issue in merge request [mock_title| mock_url].",
        )

    @mock.patch(PATH + "d_issue")
    def test_update_transition(self, mock_d_issue):
        """
        This function tests 'update_transition'
        """
        # Set up return values
        mock_client = MagicMock()

        # Call the function
        d.update_transition(
            mock_client, self.mock_existing, self.mock_pr, "merge_transition"
        )

        # Assert everything was called correctly
        mock_d_issue.change_status.assert_called_with(
            mock_client, self.mock_existing, "CUSTOM_TRANSITION1", self.mock_pr
        )

    @mock.patch(PATH + "update_jira")
    @mock.patch(PATH + "d_issue")
    def test_sync_with_jira_create_pr_issue_enabled(
        self, mock_d_issue, mock_update_jira
    ):
        """
        Test 'sync_with_jira' when create_pr_issue is enabled and no JIRA key is found.
        """
        # Set up return values
        self.mock_pr.jira_key = None
        self.mock_pr.match = None
        self.mock_pr.downstream = {"create_pr_issue": True}
        mock_client = MagicMock()
        mock_d_issue.get_jira_client.return_value = mock_client

        # Call the function
        d.sync_with_jira(self.mock_pr, self.mock_config)

        # Assert update_jira was called
        mock_update_jira.assert_called_with(mock_client, self.mock_config, self.mock_pr)

    @mock.patch(PATH + "update_jira")
    @mock.patch(PATH + "d_issue")
    def test_sync_with_jira_create_pr_issue_disabled(
        self, mock_d_issue, mock_update_jira
    ):
        """
        Test 'sync_with_jira' when create_pr_issue is disabled and no JIRA key is found.
        Should skip and return early.
        """
        # Set up return values
        self.mock_pr.jira_key = None
        self.mock_pr.match = None
        self.mock_pr.downstream = {"create_pr_issue": False}

        # Call the function
        d.sync_with_jira(self.mock_pr, self.mock_config)

        # Assert everything was called correctly
        mock_update_jira.assert_not_called()

    @mock.patch(PATH + "d_issue")
    def test_update_jira_service_unavailable(self, mock_d_issue):
        """Test 'update_jira' when in development mode and the Jira service is unavailable."""

        # Set up return values
        self.mock_config["sync2jira"]["develop"] = False
        mock_d_issue.check_jira_status.return_value = False

        # Call the function
        with self.assertRaises(RuntimeError):
            d.update_jira(self.mock_client, self.mock_config, self.mock_pr)

    @mock.patch(PATH + "_create_jira_issue_from_pr")
    @mock.patch(PATH + "update_jira_issue")
    @mock.patch(PATH + "matcher")
    @mock.patch(PATH + "d_issue")
    def test_update_jira_create_pr_issue_disabled_no_key(
        self,
        mock_d_issue,
        mock_matcher,
        mock_update_jira_issue,
        mock_create_jira_issue_from_pr,
    ):
        """Test 'update_jira' when create_pr_issue is disabled and no JIRA key is found."""
        # Set up return values
        mock_d_issue.check_jira_status.return_value = True
        mock_matcher.return_value = self.mock_pr.jira_key = None
        self.mock_pr.downstream = {"create_pr_issue": False}

        # Call the function
        d.update_jira(self.mock_client, self.mock_config, self.mock_pr)

        # Assert everything was called correctly:  should exit without calling subroutines
        self.mock_client.search_issues.assert_not_called()
        mock_update_jira_issue.assert_not_called()
        mock_create_jira_issue_from_pr.assert_not_called()

    @mock.patch(PATH + "_create_jira_issue_from_pr")
    @mock.patch(PATH + "update_jira_issue")
    @mock.patch(PATH + "matcher")
    @mock.patch(PATH + "d_issue")
    def test_update_jira_with_key_found(
        self,
        mock_d_issue,
        mock_matcher,
        mock_update_jira_issue,
        mock_create_jira_issue_from_pr,
    ):
        """Test 'update_jira' when JIRA key is found and the issue is found."""
        # Set up return values
        mock_d_issue.check_jira_status.return_value = True
        mock_matcher.return_value = self.mock_pr.jira_key

        # Call the function
        d.update_jira(self.mock_client, self.mock_config, self.mock_pr)

        # Assert everything was called correctly
        mock_update_jira_issue.assert_called()
        mock_create_jira_issue_from_pr.assert_not_called()

    @mock.patch(PATH + "_create_jira_issue_from_pr")
    @mock.patch(PATH + "update_jira_issue")
    @mock.patch(PATH + "matcher")
    @mock.patch(PATH + "d_issue")
    def test_update_jira_with_key_not_found_no_create(
        self,
        mock_d_issue,
        mock_matcher,
        mock_update_jira_issue,
        mock_create_jira_issue_from_pr,
    ):
        """Test 'update_jira' when JIRA key is found, the issue is not found,
        and issue creation is not enabled.
        """
        # Set up return values
        mock_d_issue.check_jira_status.return_value = True
        mock_matcher.return_value = self.mock_pr.jira_key
        self.mock_pr.downstream = {"create_pr_issue": False}
        self.mock_client.search_issues.return_value = []

        # Call the function
        d.update_jira(self.mock_client, self.mock_config, self.mock_pr)

        # Assert everything was (not) called correctly
        mock_update_jira_issue.assert_not_called()
        mock_create_jira_issue_from_pr.assert_not_called()

    @mock.patch(PATH + "_create_jira_issue_from_pr")
    @mock.patch(PATH + "update_jira_issue")
    @mock.patch(PATH + "matcher")
    @mock.patch(PATH + "d_issue")
    def test_update_jira_with_key_not_found_create(
        self,
        mock_d_issue,
        mock_matcher,
        mock_update_jira_issue,
        mock_create_jira_issue_from_pr,
    ):
        """Test 'update_jira' when JIRA key is found, the issue is not found,
        and issue creation is enabled.
        """
        # Set up return values
        mock_d_issue.check_jira_status.return_value = True
        mock_matcher.return_value = self.mock_pr.jira_key
        self.mock_client.search_issues.return_value = []
        self.mock_pr.downstream = {"create_pr_issue": True}

        # Call the function
        d.update_jira(self.mock_client, self.mock_config, self.mock_pr)

        # Assert everything was called correctly
        mock_update_jira_issue.assert_not_called()
        mock_create_jira_issue_from_pr.assert_called()

    @mock.patch(PATH + "_create_jira_issue_from_pr")
    @mock.patch(PATH + "update_jira_issue")
    @mock.patch(PATH + "matcher")
    @mock.patch(PATH + "d_issue")
    def test_update_jira_multiple_issues(
        self,
        mock_d_issue,
        mock_matcher,
        mock_update_jira_issue,
        mock_create_jira_issue_from_pr,
    ):
        """Test 'update_jira' when the search returns multiple issues."""
        # Set up return values
        mock_d_issue.check_jira_status.return_value = True
        mock_matcher.return_value = self.mock_pr.jira_key
        self.mock_client.search_issues.return_value = ["MOCK-123", "MOCK-456"]

        # Call the function
        d.update_jira(self.mock_client, self.mock_config, self.mock_pr)

        # Assert everything was called correctly:  should exit without calling subroutines
        mock_update_jira_issue.assert_not_called()
        mock_create_jira_issue_from_pr.assert_not_called()

    def _setup_pr_for_issue_creation(self, **overrides):
        """
        Helper to set up mock_pr with common attributes for _create_jira_issue_from_pr tests.
        Override specific attributes via kwargs.
        """
        # Set defaults from setUp
        self.mock_pr._title = "Test PR Title"
        self.mock_pr.url = "https://github.com/test/repo/pull/1"
        self.mock_pr.upstream = "test/repo"
        self.mock_pr.comments = []
        self.mock_pr.priority = None
        self.mock_pr.content = "PR description"
        self.mock_pr.reporter = "testuser"
        self.mock_pr.assignee = []
        self.mock_pr.status = None
        self.mock_pr.id = "1"
        self.mock_pr.downstream = {"project": "TEST", "type": "Task"}
        # Apply any overrides
        for key, value in overrides.items():
            setattr(self.mock_pr, key, value)

    def _assert_issue_created_with_pr_fields(self, mock_issue_class, **field_overrides):
        """
        Helper to assert Issue was created with correct fields from self.mock_pr.
        Only checks fields that differ from defaults or are specified in field_overrides.
        """
        call_args = mock_issue_class.call_args
        self.assertIsNotNone(call_args, "Issue class should have been called")
        kwargs = call_args[1]

        # Common assertions using self.mock_pr fields
        self.assertEqual(kwargs["source"], self.mock_pr.source)
        self.assertEqual(kwargs["title"], self.mock_pr._title)
        self.assertEqual(kwargs["url"], self.mock_pr.url)
        self.assertEqual(kwargs["upstream"], self.mock_pr.upstream)
        self.assertEqual(kwargs["status"], self.mock_pr.status)
        self.assertEqual(kwargs["id_"], self.mock_pr.id)

        # Handle reporter conversion
        if isinstance(self.mock_pr.reporter, dict):
            self.assertEqual(kwargs["reporter"], self.mock_pr.reporter)
        else:
            self.assertEqual(
                kwargs["reporter"], {"fullname": str(self.mock_pr.reporter)}
            )

        # Apply field-specific overrides
        for key, expected_value in field_overrides.items():
            self.assertEqual(kwargs[key], expected_value)

    @mock.patch(PATH + "d_issue._create_jira_issue")
    @mock.patch(PATH + "Issue")
    def test_create_jira_issue_from_pr(self, mock_issue_class, mock_create_jira_issue):
        """
        Test '_create_jira_issue_from_pr' converts PR to Issue-like object and creates JIRA issue.
        """
        # Set up return values
        mock_client = MagicMock()
        mock_created_issue = MagicMock()
        mock_create_jira_issue.return_value = mock_created_issue

        # Set up PR object
        self._setup_pr_for_issue_creation()

        # Call the function
        result = d._create_jira_issue_from_pr(
            mock_client, self.mock_pr, self.mock_config
        )

        # Assert Issue was created with correct parameters
        self._assert_issue_created_with_pr_fields(mock_issue_class)

        # Assert _create_jira_issue was called and result returned
        self.assertEqual(result, mock_created_issue)

    @mock.patch(PATH + "d_issue._create_jira_issue")
    @mock.patch(PATH + "Issue")
    def test_create_jira_issue_from_pr_no_content(
        self, mock_issue_class, mock_create_jira_issue
    ):
        """
        Test '_create_jira_issue_from_pr' when PR has no content (uses fallback).
        """
        # Set up return values
        mock_client = MagicMock()
        mock_created_issue = MagicMock()
        mock_create_jira_issue.return_value = mock_created_issue

        self._setup_pr_for_issue_creation(content=None)

        # Call the function
        d._create_jira_issue_from_pr(mock_client, self.mock_pr, self.mock_config)

        self._assert_issue_created_with_pr_fields(
            mock_issue_class, content=f"PR: {self.mock_pr.url}"
        )

    @mock.patch(PATH + "d_issue._create_jira_issue")
    @mock.patch(PATH + "Issue")
    def test_create_jira_issue_from_pr_reporter_dict(
        self, mock_issue_class, mock_create_jira_issue
    ):
        """
        Test '_create_jira_issue_from_pr' when reporter is already a dict (not a string).
        """
        # Set up return values
        mock_client = MagicMock()
        mock_created_issue = MagicMock()
        mock_create_jira_issue.return_value = mock_created_issue

        # Set up PR object with dict reporter
        self._setup_pr_for_issue_creation(
            reporter={"fullname": "testuser", "email": "test@example.com"}
        )

        # Call the function
        d._create_jira_issue_from_pr(mock_client, self.mock_pr, self.mock_config)

        # Assert Issue was created with dict reporter (not wrapped)
        self._assert_issue_created_with_pr_fields(mock_issue_class)
