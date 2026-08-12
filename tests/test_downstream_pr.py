import unittest
import unittest.mock as mock
from unittest.mock import MagicMock

import sync2jira.downstream_issue as d_issue
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
                        "basic_auth": ("email", "mock_token"),
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
        mock_user.accountId = "mock-atlassian-account-id"
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
            "mock_existing", self.mock_pr, self.mock_client, self.mock_config
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
            "mock_existing", self.mock_pr, mock_client, self.mock_config
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

    @mock.patch(PATH + "d_issue.update_jira_issue")
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
        mock_shared_update,
    ):
        """
        This function tests 'update_jira_issue'
        """
        # Set up return values
        mock_format_comment.return_value = "mock_formatted_comment"
        mock_comment_exists.return_value = False
        mock_issue_link_exists.return_value = False

        # Call the function
        d.update_jira_issue(
            "mock_existing", self.mock_pr, self.mock_client, self.mock_config
        )

        # Assert PR-specific steps were called
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
        # Assert shared update pipeline was called
        mock_shared_update.assert_called_with(
            "mock_existing",
            self.mock_pr,
            self.mock_client,
            self.mock_config,
            "pr_updates",
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

    @mock.patch(PATH + "d_issue.update_jira_issue")
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
        mock_shared_update,
    ):
        """
        This function tests 'update_jira_issue' where the comment already exists
        """
        # Set up return values
        mock_format_comment.return_value = "mock_formatted_comment"
        mock_comment_exists.return_value = True
        mock_issue_link_exists.return_value = True

        # Call the function
        d.update_jira_issue(
            "mock_existing", self.mock_pr, self.mock_client, self.mock_config
        )

        # Assert PR-specific steps were called
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
        # Assert shared update pipeline was still called
        mock_shared_update.assert_called_with(
            "mock_existing",
            self.mock_pr,
            self.mock_client,
            self.mock_config,
            "pr_updates",
        )

    def test_comment_exists_false(self):
        """
        Single-page case: comment not found → returns False.
        """
        mock_comment = MagicMock()
        mock_comment.body = "not_mock_new_comment"
        self.mock_client.comments.return_value = [
            mock_comment
        ]  # 1 item < 100 → last page

        response = d.comment_exists(
            self.mock_client, "mock_existing", "mock_new_comment"
        )

        self.mock_client.comments.assert_called_once_with(
            "mock_existing", start_at=0, max_results=100
        )
        self.assertFalse(response)

    def test_comment_exists_true(self):
        """
        Single-page case: comment found → returns True.
        """
        mock_comment = MagicMock()
        mock_comment.body = "mock_new_comment"
        other_comment = MagicMock()
        other_comment.body = "something else"
        self.mock_client.comments.return_value = [other_comment] * 99 + [
            mock_comment
        ]  # 1 item passes other items

        response = d.comment_exists(
            self.mock_client, "mock_existing", "mock_new_comment"
        )

        self.assertTrue(response)
        # Only one page was fetched despite it being full — early exit worked.
        self.mock_client.comments.assert_called_once_with(
            "mock_existing", start_at=0, max_results=100
        )

    def test_comment_exists_false_zero_batch(self):
        """
        Zero-items edge case: Jira has exactly 100 comments so the
        paginator fetches a second page which returns empty.  The target
        comment is not present anywhere so the function returns False.
        """
        unrelated = MagicMock()
        unrelated.body = "some other comment"

        self.mock_client.comments.side_effect = [
            [unrelated] * 100,  # page 1: full → triggers page 2
            [],  # page 2: empty → last page
        ]

        response = d.comment_exists(self.mock_client, "mock_existing", "target comment")

        self.assertFalse(response)
        self.assertEqual(self.mock_client.comments.call_count, 2)
        self.mock_client.comments.assert_any_call(
            "mock_existing", start_at=0, max_results=100
        )
        self.mock_client.comments.assert_any_call(
            "mock_existing", start_at=100, max_results=100
        )

    def test_comment_exists_multi_page(self):
        """
        Multi-page case: comment sits on page 2. Verifies start_at
        advances and function returns True as soon as the match is found.
        """
        unrelated = MagicMock()
        unrelated.body = "other comment"
        target = MagicMock()
        target.body = "mock_new_comment"

        self.mock_client.comments.side_effect = [
            [unrelated] * 100,  # page 1: full, no match
            [target],  # page 2: match found → return True
        ]

        response = d.comment_exists(
            self.mock_client, "mock_existing", "mock_new_comment"
        )

        self.assertTrue(response)
        self.assertEqual(self.mock_client.comments.call_count, 2)
        self.mock_client.comments.assert_any_call(
            "mock_existing", start_at=0, max_results=100
        )
        self.mock_client.comments.assert_any_call(
            "mock_existing", start_at=100, max_results=100
        )

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
        self.mock_client.search_users.assert_called_with(query="mock_reporter")
        self.assertEqual(
            response,
            "[~accountId:mock-atlassian-account-id] mentioned this issue in merge request [mock_title| mock_url].",
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
        self.mock_client.search_users.assert_called_with(query="mock_reporter")
        self.assertEqual(
            response,
            "mock_reporter mentioned this issue in merge request [mock_title| mock_url].",
        )

    @mock.patch(PATH + "d_issue")
    def test_update_pr_transition(self, mock_d_issue):
        """
        This function tests '_update_pr_transition'
        """
        # Set up return values
        mock_client = MagicMock()
        self.mock_existing.fields.issuetype.name = "Bug"

        # Call the function
        d._update_pr_transition(
            mock_client, self.mock_existing, self.mock_pr, "merge_transition"
        )

        # Assert everything was called correctly
        mock_d_issue.change_status.assert_called_with(
            mock_client, self.mock_existing, "CUSTOM_TRANSITION1", self.mock_pr
        )

    def test_matches_transition_filters(self):
        """Table-driven test for _matches_transition_filters as a separate unit."""
        scenarios = (
            (
                "no filters — passes",
                {"merge_transition": "MODIFIED"},
                "main",
                "Bug",
                True,
            ),
            (
                "branch matches glob",
                {"merge_transition": "MODIFIED", "branches": ["release-*"]},
                "release-0.9",
                "Bug",
                True,
            ),
            (
                "branch does not match glob",
                {"merge_transition": "MODIFIED", "branches": ["release-*"]},
                "main",
                "Bug",
                False,
            ),
            (
                "issue type matches",
                {"merge_transition": "MODIFIED", "issue_types": ["Bug"]},
                "main",
                "Bug",
                True,
            ),
            (
                "issue type does not match",
                {"merge_transition": "MODIFIED", "issue_types": ["Bug"]},
                "main",
                "Story",
                False,
            ),
            (
                "both filters match",
                {
                    "merge_transition": "MODIFIED",
                    "branches": ["release-*"],
                    "issue_types": ["Bug"],
                },
                "release-0.9",
                "Bug",
                True,
            ),
            (
                "branch matches but issue type does not",
                {
                    "merge_transition": "MODIFIED",
                    "branches": ["release-*"],
                    "issue_types": ["Bug"],
                },
                "release-0.9",
                "Story",
                False,
            ),
            (
                "issue type matches but branch does not",
                {
                    "merge_transition": "MODIFIED",
                    "branches": ["release-*"],
                    "issue_types": ["Bug"],
                },
                "main",
                "Bug",
                False,
            ),
            (
                "base_branch is None with branch filter",
                {"merge_transition": "MODIFIED", "branches": ["release-*"]},
                None,
                "Bug",
                False,
            ),
        )

        for name, entry, base_branch, jira_type, expected in scenarios:
            with self.subTest(name):
                self.mock_pr.base_branch = base_branch
                self.mock_existing.fields.issuetype.name = jira_type

                result = d._matches_transition_filters(
                    entry, self.mock_pr, self.mock_existing
                )
                self.assertEqual(result, expected)

    @mock.patch(PATH + "d_issue")
    def test_update_transition_selects_first_matching_entry(self, mock_d_issue):
        """Test that _update_pr_transition iterates entries and selects the first match."""
        mock_client = MagicMock()
        self.mock_existing.fields.issuetype.name = "Story"
        self.mock_pr.base_branch = "main"
        self.mock_pr.downstream = {
            "pr_updates": [
                {
                    "merge_transition": "MODIFIED",
                    "branches": ["release-*"],
                    "issue_types": ["Bug"],
                },
                {
                    "merge_transition": "Dev Complete",
                    "issue_types": ["Story", "Task"],
                },
            ]
        }

        d._update_pr_transition(
            mock_client, self.mock_existing, self.mock_pr, "merge_transition"
        )

        mock_d_issue.change_status.assert_called_with(
            mock_client, self.mock_existing, "Dev Complete", self.mock_pr
        )

    @mock.patch(PATH + "d_issue")
    def test_update_transition_no_matching_entry(self, mock_d_issue):
        """Test that no transition fires when no entries match."""
        mock_client = MagicMock()
        self.mock_existing.fields.issuetype.name = "Story"
        self.mock_pr.base_branch = "main"
        self.mock_pr.downstream = {
            "pr_updates": [
                {
                    "merge_transition": "MODIFIED",
                    "branches": ["release-*"],
                },
            ]
        }

        d._update_pr_transition(
            mock_client, self.mock_existing, self.mock_pr, "merge_transition"
        )

        mock_d_issue.change_status.assert_not_called()

    @mock.patch(PATH + "d_issue")
    def test_update_transition_skips_entry_without_transition_type(self, mock_d_issue):
        """Test that entries without the requested transition type are skipped."""
        mock_client = MagicMock()
        self.mock_existing.fields.issuetype.name = "Bug"
        self.mock_pr.downstream = {
            "pr_updates": [
                {"link_transition": "IN PROGRESS"},
                {"merge_transition": "MODIFIED"},
            ]
        }

        d._update_pr_transition(
            mock_client, self.mock_existing, self.mock_pr, "merge_transition"
        )

        mock_d_issue.change_status.assert_called_with(
            mock_client, self.mock_existing, "MODIFIED", self.mock_pr
        )

    @mock.patch(PATH + "d_issue")
    def test_update_transition_no_pr_updates(self, mock_d_issue):
        """Test that _update_pr_transition returns silently when pr_updates is absent."""
        mock_client = MagicMock()
        self.mock_pr.downstream = {}

        d._update_pr_transition(
            mock_client, self.mock_existing, self.mock_pr, "merge_transition"
        )

        mock_d_issue.change_status.assert_not_called()

    @mock.patch(PATH + "d_issue")
    def test_update_transition_empty_pr_updates(self, mock_d_issue):
        """Test that _update_pr_transition returns silently when pr_updates is empty."""
        mock_client = MagicMock()
        self.mock_pr.downstream = {"pr_updates": []}

        d._update_pr_transition(
            mock_client, self.mock_existing, self.mock_pr, "merge_transition"
        )

        mock_d_issue.change_status.assert_not_called()

    @mock.patch(PATH + "d_issue.change_status")
    @mock.patch(PATH + "d_issue.update_jira_issue", wraps=d_issue.update_jira_issue)
    @mock.patch(PATH + "comment_exists", return_value=True)
    @mock.patch(PATH + "format_comment", return_value="mock_comment")
    @mock.patch(PATH + "d_issue.attach_link")
    @mock.patch(PATH + "issue_link_exists", return_value=True)
    def test_update_jira_issue_transition_noop_when_status_none(
        self,
        mock_issue_link_exists,
        mock_attach_link,
        mock_format_comment,
        mock_comment_exists,
        mock_shared_update,
        mock_change_status,
    ):
        """github.pull_request path: PR has status=None, so _update_transition
        is a no-op even when {'transition': 'Closed'} is in pr_updates.
        """
        self.mock_pr.status = None
        self.mock_pr.downstream = {
            "pr_updates": [{"transition": "Closed"}],
        }

        d.update_jira_issue(
            self.mock_existing, self.mock_pr, self.mock_client, self.mock_config
        )

        mock_change_status.assert_not_called()

    @mock.patch(PATH + "d_issue.change_status")
    @mock.patch(PATH + "comment_exists", return_value=True)
    @mock.patch(PATH + "format_comment", return_value="mock_comment")
    @mock.patch(PATH + "d_issue.attach_link")
    @mock.patch(PATH + "issue_link_exists", return_value=True)
    def test_update_jira_issue_merged_pr_no_duplicate_transition(
        self,
        mock_issue_link_exists,
        mock_attach_link,
        mock_format_comment,
        mock_comment_exists,
        mock_change_status,
    ):
        """github.issues path: merged PR with status='Closed'.

        merge_transition fires first (via _update_pr_transitions), then
        _update_transition finds Jira already in target state and skips.
        change_status is called once (for merge_transition) not twice.
        """
        self.mock_pr.suffix = "merged"
        self.mock_pr.status = "Closed"
        self.mock_pr.downstream = {
            "pr_updates": [
                {"merge_transition": "Closed"},
                {"transition": "Closed"},
            ],
        }
        self.mock_existing.fields.status.name = "Closed"

        d.update_jira_issue(
            self.mock_existing, self.mock_pr, self.mock_client, self.mock_config
        )

        mock_change_status.assert_called_once_with(
            self.mock_client, self.mock_existing, "Closed", self.mock_pr
        )

    @mock.patch(PATH + "d_issue.change_status")
    @mock.patch(PATH + "comment_exists", return_value=True)
    @mock.patch(PATH + "format_comment", return_value="mock_comment")
    @mock.patch(PATH + "d_issue.attach_link")
    @mock.patch(PATH + "issue_link_exists", return_value=True)
    def test_update_jira_issue_closed_without_merge_transitions(
        self,
        mock_issue_link_exists,
        mock_attach_link,
        mock_format_comment,
        mock_comment_exists,
        mock_change_status,
    ):
        """github.issues path: PR closed without merge, status='Closed'.

        merge_transition skips (suffix is 'closed', not 'merged').
        _update_transition sees status=='Closed' and fires, transitioning
        the Jira issue — covering a case merge_transition cannot handle.
        """
        self.mock_pr.suffix = "closed"
        self.mock_pr.status = "Closed"
        self.mock_pr.url = "mock_url"
        self.mock_pr.downstream = {
            "pr_updates": [
                {"merge_transition": "Closed"},
                {"transition": "Closed"},
            ],
        }
        self.mock_existing.fields.status.name = "Open"

        d.update_jira_issue(
            self.mock_existing, self.mock_pr, self.mock_client, self.mock_config
        )

        mock_change_status.assert_called_once_with(
            self.mock_client, self.mock_existing, "Closed", self.mock_pr
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
    def test_update_jira_with_no_key_create_enabled_no_issue(
        self,
        mock_d_issue,
        mock_matcher,
        mock_update_jira_issue,
        mock_create_jira_issue_from_pr,
    ):
        """Test 'update_jira' when no JIRA key is found, issue creation is
        enabled, and the issue is not found.
        """
        # Set up return values
        mock_d_issue.check_jira_status.return_value = True
        mock_matcher.return_value = self.mock_pr.jira_key = None
        self.mock_pr.downstream = {"create_pr_issue": True}
        mock_d_issue.get_existing_jira_issue.return_value = None

        # Call the function
        d.update_jira(self.mock_client, self.mock_config, self.mock_pr)

        # Assert everything was called correctly
        mock_update_jira_issue.assert_not_called()
        mock_create_jira_issue_from_pr.assert_called()

    @mock.patch(PATH + "_create_jira_issue_from_pr")
    @mock.patch(PATH + "update_jira_issue")
    @mock.patch(PATH + "matcher")
    @mock.patch(PATH + "d_issue")
    def test_update_jira_with_no_key_create_enabled_issue_exists(
        self,
        mock_d_issue,
        mock_matcher,
        mock_update_jira_issue,
        mock_create_jira_issue_from_pr,
    ):
        """Test 'update_jira' when no JIRA key is found, issue creation is
        enabled, and the issue exists.
        """
        # Set up return values
        mock_d_issue.check_jira_status.return_value = True
        mock_matcher.return_value = self.mock_pr.jira_key = None
        self.mock_pr.downstream = {"create_pr_issue": True}
        mock_d_issue.get_existing_jira_issue.return_value = self.mock_existing

        # Call the function
        d.update_jira(self.mock_client, self.mock_config, self.mock_pr)

        # Assert everything was called correctly
        mock_update_jira_issue.assert_called()
        mock_create_jira_issue_from_pr.assert_not_called()

    @mock.patch(PATH + "_create_jira_issue_from_pr")
    @mock.patch(PATH + "update_jira_issue")
    @mock.patch(PATH + "matcher")
    @mock.patch(PATH + "d_issue")
    def test_update_jira_with_no_key_create_disabled(
        self,
        mock_d_issue,
        mock_matcher,
        mock_update_jira_issue,
        mock_create_jira_issue_from_pr,
    ):
        """Test 'update_jira' when no JIRA key is found and issue creation is disabled."""
        # Set up return values
        mock_d_issue.check_jira_status.return_value = True
        mock_matcher.return_value = self.mock_pr.jira_key = None
        self.mock_pr.downstream = {"create_pr_issue": False}

        # Call the function
        d.update_jira(self.mock_client, self.mock_config, self.mock_pr)

        # Assert everything was (not) called correctly
        mock_update_jira_issue.assert_not_called()
        mock_create_jira_issue_from_pr.assert_not_called()

    @mock.patch(PATH + "_create_jira_issue_from_pr")
    @mock.patch(PATH + "update_jira_issue")
    @mock.patch(PATH + "matcher")
    @mock.patch(PATH + "d_issue")
    def test_update_jira_with_no_key_create_unspecified(
        self,
        mock_d_issue,
        mock_matcher,
        mock_update_jira_issue,
        mock_create_jira_issue_from_pr,
    ):
        """Test 'update_jira' when no JIRA key is found and issue creation is unspecified."""
        # Set up return values
        mock_d_issue.check_jira_status.return_value = True
        mock_matcher.return_value = self.mock_pr.jira_key = None

        # Call the function
        d.update_jira(self.mock_client, self.mock_config, self.mock_pr)

        # Assert everything was (not) called correctly
        mock_update_jira_issue.assert_not_called()
        mock_create_jira_issue_from_pr.assert_not_called()

    @mock.patch(PATH + "_create_jira_issue_from_pr")
    @mock.patch(PATH + "update_jira_issue")
    @mock.patch(PATH + "matcher")
    @mock.patch(PATH + "d_issue")
    def test_update_jira_with_key_found_and_unique_issue(
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
    def test_update_jira_with_key_found_and_no_issue(
        self,
        mock_d_issue,
        mock_matcher,
        mock_update_jira_issue,
        mock_create_jira_issue_from_pr,
    ):
        """Test 'update_jira' when JIRA key is found and the issue is not found."""
        # Set up return values
        mock_d_issue.check_jira_status.return_value = True
        mock_matcher.return_value = self.mock_pr.jira_key
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
    def test_update_jira_with_key_found_and_multiple_issues(
        self,
        mock_d_issue,
        mock_matcher,
        mock_update_jira_issue,
        mock_create_jira_issue_from_pr,
    ):
        """Test 'update_jira' when JIRA key is found and the search returns multiple issues."""
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
        self.mock_pr.tags = ["bug", "enhancement"]
        self.mock_pr.fixVersion = ["v1.0"]
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
        self.assertEqual(kwargs["tags"], self.mock_pr.tags)
        self.assertEqual(kwargs["fixVersion"], self.mock_pr.fixVersion)
        self.assertEqual(kwargs["status"], self.mock_pr.status)
        self.assertEqual(kwargs["id_"], self.mock_pr.id)

        self.assertEqual(kwargs["reporter"], self.mock_pr.reporter)

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
