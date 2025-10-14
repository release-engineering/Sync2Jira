from datetime import datetime, timezone
from typing import Any, Optional
import unittest
import unittest.mock as mock
from unittest.mock import MagicMock

from jira import JIRAError
import jira.client

import sync2jira.downstream_issue as d
from sync2jira.downstream_issue import remove_diacritics
from sync2jira.intermediary import Issue

PATH = "sync2jira.downstream_issue."


class TestDownstreamIssue(unittest.TestCase):
    """
    This class tests the downstream_issue.py file under sync2jira
    """

    def setUp(self):
        """
        Setting up the testing environment
        """
        # Mock Config dict
        self.mock_config = {
            "sync2jira": {
                "default_jira_instance": "another_jira_instance",
                "jira_username": "mock_user",
                "default_jira_fields": {"storypoints": "customfield_12310243"},
                "jira": {
                    "mock_jira_instance": {"mock_jira": "mock_jira"},
                    "another_jira_instance": {
                        "token_auth": "mock_token",
                        "options": {"server": "mock_server"},
                    },
                },
                "testing": {},
                "legacy_matching": False,
                "admins": [{"mock_admin": "mock_email"}],
                "develop": False,
            },
        }

        # Mock sync2jira.intermediary.Issue
        self.mock_issue = MagicMock()
        self.mock_issue.assignee = [
            {"fullname": "mock_user", "login": "mock_user_login"}
        ]
        self.mock_issue.downstream = {
            "project": "mock_project",
            "custom_fields": {"somecustumfield": "somecustumvalue"},
            "qa-contact": "dummy@dummy.com",
            "epic-link": "DUMMY-1234",
            "EXD-Service": {"guild": "EXD-Project", "value": "EXD-Value"},
            "issue_updates": [
                "comments",
                {"tags": {"overwrite": False}},
                {"fixVersion": {"overwrite": False}},
                {"assignee": {"overwrite": True}},
                "description",
                "title",
                {"transition": "CUSTOM TRANSITION"},
                {"on_close": {"apply_labels": ["closed-upstream"]}},
            ],
            "owner": "mock_owner",
        }
        self.mock_issue.content = "mock_content"
        self.mock_issue.reporter = {"fullname": "mock_user"}
        self.mock_issue.url = "mock_url"
        self.mock_issue.title = "mock_title"
        self.mock_issue.comments = "mock_comments"
        self.mock_issue.tags = ["tag1", "tag2"]
        self.mock_issue.fixVersion = ["fixVersion3", "fixVersion4"]
        self.mock_issue.fixVersion = ["fixVersion3", "fixVersion4"]
        self.mock_issue.assignee = [
            {"fullname": "mock_assignee", "login": "mock_assignee_login"}
        ]
        self.mock_issue.status = "Open"
        self.mock_issue.id = "1234"
        self.mock_issue.storypoints = 2
        self.mock_issue.priority = "P1"
        self.mock_issue.issue_type = None

        # Mock issue updates
        self.mock_updates = [
            "comments",
            {"tags": {"overwrite": False}},
            {"fixVersion": {"overwrite": False}},
            {"assignee": {"overwrite": True}},
            "description",
            "title",
            {"transition": "CUSTOM TRANSITION"},
            {"on_close": {"apply_labels": ["closed-upstream"]}},
        ]

        # Mock Jira transition
        self.mock_transition = [{"name": "custom_closed_status", "id": 1234}]

        # Mock jira.resources.Issue
        self.mock_downstream = MagicMock()
        self.mock_downstream.id = 1234
        self.mock_downstream.fields.labels = ["tag3", "tag4"]
        self.mock_downstream.key = "downstream_issue_key"
        mock_version1 = MagicMock()
        mock_version1.name = "fixVersion3"
        mock_version2 = MagicMock()
        mock_version2.name = "fixVersion4"
        self.mock_downstream.fields.fixVersions = [mock_version1, mock_version2]
        self.mock_downstream.update.return_value = True
        self.mock_downstream.fields.description = "This is an existing description"

        # Mock datetime.today()
        self.mock_today = MagicMock()
        self.mock_today.strftime.return_value = "mock_today"

    @mock.patch("jira.client.JIRA")
    def test_get_jira_client_not_issue(self, mock_client):
        """
        This tests 'get_jira_client' function where the passed in
        argument is not an Issue instance
        """
        # Call the function
        with self.assertRaises(Exception):
            d.get_jira_client(issue="string", config=self.mock_config)

        # Assert everything was called correctly
        mock_client.assert_not_called()

    @mock.patch("jira.client.JIRA")
    def test_get_jira_client_not_instance(self, mock_client):
        """
        This tests 'get_jira_client' function there is no JIRA instance
        """
        # Set up return values
        self.mock_issue.downstream = {}

        # Call the function
        with self.assertRaises(Exception):
            d.get_jira_client(issue=self.mock_issue, config=self.mock_config)

        # Assert everything was called correctly
        mock_client.assert_not_called()

    @mock.patch("jira.client.JIRA")
    def test_get_jira_client(self, mock_client):
        """
        This tests 'get_jira_client' function where everything goes smoothly
        """
        # Set up return values
        mock_issue = MagicMock(spec=Issue)
        mock_issue.downstream = {"jira_instance": "mock_jira_instance"}
        mock_client.return_value = "Successful call!"

        # Call the function

        response = d.get_jira_client(issue=mock_issue, config=self.mock_config)

        # Assert everything was called correctly
        mock_client.assert_called_with(mock_jira="mock_jira")
        self.assertEqual("Successful call!", response)

    @mock.patch("jira.client.JIRA")
    def test_get_existing_legacy(self, client):
        """
        This tests '_get_existing_jira_issue_legacy' function
        """

        class MockIssue(object):
            downstream = {"key": "value"}
            url = "wat"

        issue = MockIssue()
        # Ensure that we get results back from the jira client.
        target1 = "target1"
        client.return_value.search_issues = mock.MagicMock(return_value=[target1])
        result = d._get_existing_jira_issue_legacy(jira.client.JIRA(), issue)
        assert result == target1

        client.return_value.search_issues.assert_called_once_with(
            "'External issue URL'='wat' AND 'key'='value' AND "
            "(resolution is null OR resolution = Duplicate)",
        )

    @mock.patch("jira.client.JIRA")
    def test_get_existing_newstyle(self, client):
        config = self.mock_config

        issue = MagicMock()
        issue.downstream = {"key": "value"}
        issue.title = "A title, a title..."
        issue.url = "http://threebean.org"
        mock_results_of_query = MagicMock()
        mock_results_of_query.fields.summary = "A title, a title..."

        client.return_value.search_issues.return_value = [mock_results_of_query]
        result = d._get_existing_jira_issue(jira.client.JIRA(), issue, config)
        # Ensure that we get the mock_result_of_query as a result
        self.assertEqual(result, mock_results_of_query)

        client.return_value.search_issues.assert_called_once_with(
            'issueFunction in linkedIssuesOfRemote("Upstream issue") and '
            'issueFunction in linkedIssuesOfRemote("http://threebean.org")'
        )

    @mock.patch("jira.client.JIRA")
    def test_upgrade_oldstyle_jira_issue(self, client):
        config = self.mock_config

        class MockIssue(object):
            downstream = {"key": "value"}
            title = "A title, a title..."
            url = "http://threebean.org"

        downstream = mock.MagicMock()
        issue = MockIssue()
        client_obj = mock.MagicMock()
        client.return_value = client_obj
        d._upgrade_jira_issue(jira.client.JIRA(), downstream, issue, config)

        remote = {
            "url": "http://threebean.org",
            "title": "Upstream issue",
        }
        client_obj.add_remote_link.assert_called_once_with(downstream.id, remote)

    @mock.patch("Rover_Lookup.github_username_to_emails")
    @mock.patch("jira.client.JIRA")
    def test_assign_user(self, mock_client, mock_rover_lookup):
        """
        Test `assign_user()` when the downstream user matches the upstream user.
        """
        # Set up return values
        mock_user = MagicMock()
        mock_user.displayName = "mock_assignee"
        mock_user.key = "mock_user_key"
        mock_client.search_assignable_users_for_issues.return_value = [mock_user]
        mock_client.assign_issue.return_value = True
        mock_rover_lookup.return_value = ["mock_user@redhat.com"]

        # Call the assign user function
        d.assign_user(
            issue=self.mock_issue, downstream=self.mock_downstream, client=mock_client
        )

        # Assert that all calls mocked were called properly
        self.mock_downstream.update.assert_called_with(
            {"assignee": {"name": mock_user.name}}
        )
        mock_client.search_assignable_users_for_issues.assert_called_with(
            query="mock_user@redhat.com", issueKey=self.mock_downstream.key
        )

    @mock.patch("Rover_Lookup.github_username_to_emails")
    @mock.patch("jira.client.JIRA")
    def test_assign_user_diacritics(self, mock_client, mock_rover_lookup):
        """
        Test `assign_user()` when the downstream user matches the upstream user
        only when the diacritic characters are replaced.
        """
        # Set up return values
        mock_user = MagicMock()
        mock_user.displayName = "mock_assignee"
        mock_user.key = "mock_user_key"
        mock_client.search_assignable_users_for_issues.return_value = [mock_user]
        mock_client.assign_issue.return_value = True
        mock_rover_lookup.return_value = ["mock_user@redhat.com"]
        self.mock_issue.assignee = [
            {"fullname": "ḿòćḱ_ášśìǵńèé", "login": "mock_user_diacritics"}
        ]
        # Call the assign user function
        d.assign_user(
            issue=self.mock_issue, downstream=self.mock_downstream, client=mock_client
        )

        # Assert that all calls mocked were called properly
        self.mock_downstream.update.assert_called_with(
            {"assignee": {"name": mock_user.name}}
        )
        mock_client.search_assignable_users_for_issues.assert_called_with(
            query="mock_user@redhat.com", issueKey=self.mock_downstream.key
        )

    @mock.patch("Rover_Lookup.github_username_to_emails")
    @mock.patch("jira.client.JIRA")
    def test_assign_user_multiple(self, mock_client, mock_rover_lookup):
        """
        Test `assign_user()` when the upstream assignee field contains a list
        in which most entries aren't useful.
        """
        # Set up return values
        mock_user = MagicMock()
        mock_user.displayName = "mock_assignee"
        mock_user.name = "mock_assignee_name"
        mock_user.emailAddress = "mock_user@redhat.com"
        mock_user.key = "mock_user_key"
        mock_user2 = MagicMock()
        mock_user2.displayName = "mock_assignee2"
        mock_user2.name = "mock_assignee2_name"
        mock_user2.emailAddress = "wrong_mock_user@redhat.com"
        mock_user2.key = "mock_user2_key"
        mock_client.search_assignable_users_for_issues.return_value = [
            mock_user,
            mock_user2,
        ]
        mock_client.assign_issue.return_value = True
        self.mock_issue.assignee = [
            {"fullname": None, "login": "login1"},
            {"fullname": "", "login": "login2"},
            {"fullname": "not_a_match", "login": "login3"},
            {"fullname": "ḿòćḱ_ášśìǵńèé", "login": "login4"},
            # Should not match this next -- should match the previous.
            {"fullname": "mock_assignee2", "login": "login5"},
        ]
        rlu = {
            "login1": [],
            "login2": [],
            "login3": ["not_a_match@redhat.com"],
            "login4": [mock_user.emailAddress],
            "login5": [mock_user2.emailAddress],
        }
        mock_rover_lookup.side_effect = lambda un: rlu.get(
            un, AssertionError("Test bug!  Missing assignee login")
        )

        # Call the assign user function
        d.assign_user(
            issue=self.mock_issue, downstream=self.mock_downstream, client=mock_client
        )

        # Assert that all calls mocked were called properly
        self.mock_downstream.update.assert_called_with(
            {"assignee": {"name": mock_user.name}}
        )
        mock_client.search_assignable_users_for_issues.assert_called_with(
            query="mock_user@redhat.com", issueKey=self.mock_downstream.key
        )

    @mock.patch("Rover_Lookup.github_username_to_emails")
    @mock.patch("jira.client.JIRA")
    def test_assign_user_with_owner_no_upstream(self, mock_client, mock_rover_lookup):
        """
        Test `assign_user()` to show that, when no downstream user is
        available, the issue is assigned to the configured owner.
        """
        # Set up return values
        mock_user = MagicMock()
        mock_user.displayName = "mock_assignee"
        mock_user.key = "mock_user_key"
        mock_client.search_assignable_users_for_issues.return_value = []
        mock_client.assign_issue.return_value = True
        mock_rover_lookup.return_value = []

        # Call the assign user function
        d.assign_user(
            issue=self.mock_issue, downstream=self.mock_downstream, client=mock_client
        )

        # Assert that all calls mocked were called properly
        mock_client.assign_issue.assert_called_with(1234, "mock_owner")
        mock_client.search_assignable_users_for_issues.assert_not_called()

    @mock.patch("Rover_Lookup.github_username_to_emails")
    @mock.patch("jira.client.JIRA")
    def test_assign_user_with_owner_no_match(self, mock_client, mock_rover_lookup):
        """
        Test `assign_user()` to show that, when no downstream user is
        available, the issue is assigned to the configured owner.
        """
        # Set up return values
        mock_user = MagicMock()
        mock_user.displayName = "mock_assignee"
        mock_user.key = "mock_user_key"
        mock_client.search_assignable_users_for_issues.return_value = []
        mock_client.assign_issue.return_value = True
        mock_rover_lookup.return_value = ["no_match@redhat.com"]

        # Call the assign user function
        d.assign_user(
            issue=self.mock_issue, downstream=self.mock_downstream, client=mock_client
        )

        # Assert that all calls mocked were called properly
        mock_client.assign_issue.assert_called_with(1234, "mock_owner")
        mock_client.search_assignable_users_for_issues.assert_called_with(
            query="no_match@redhat.com", issueKey=self.mock_downstream.key
        )

    @mock.patch("Rover_Lookup.github_username_to_emails")
    @mock.patch("jira.client.JIRA")
    def test_assign_user_without_owner(self, mock_client, mock_rover_lookup):
        """
        Test `assign_user()` when no downstream user is available and there is
        no configured owner for the project.
        """
        # Set up return values
        mock_user = MagicMock()
        mock_user.displayName = "mock_assignee"
        mock_user.key = "mock_user_key"
        mock_client.search_assignable_users_for_issues.return_value = []
        mock_client.assign_issue.return_value = True
        mock_rover_lookup.return_value = []
        self.mock_issue.downstream.pop("owner")

        # Call the assign user function
        d.assign_user(
            issue=self.mock_issue, downstream=self.mock_downstream, client=mock_client
        )

        # Assert that all calls mocked were called properly
        mock_client.assign_issue.assert_not_called()
        mock_client.search_assignable_users_for_issues.assert_not_called()

    @mock.patch(PATH + "match_user")
    @mock.patch("jira.client.JIRA")
    def test_assign_user_none(self, mock_client, mock_match_user):
        """
        Test `assign_user()` when no upstream user is available and there is
        no configured owner for the project.
        """
        # Set up return values
        self.mock_issue.assignee = []
        self.mock_issue.downstream.pop("owner")

        # Call the assign user function
        d.assign_user(
            issue=self.mock_issue, downstream=self.mock_downstream, client=mock_client
        )

        # Assert that all calls mocked were called properly
        mock_match_user.assert_not_called()
        mock_client.search_assignable_users_for_issues.assert_not_called()
        self.mock_downstream.update.assert_not_called()
        mock_client.assign_issue.assert_not_called()

    @mock.patch("jira.client.JIRA")
    def test_assign_user_remove_all(self, mock_client):
        """
        Test 'assign_user' function when the `remove_all` flag is True
        """
        # Call the assign user function
        d.assign_user(
            issue=self.mock_issue,
            downstream=self.mock_downstream,
            client=mock_client,
            remove_all=True,
        )

        # Assert that all calls mocked were called properly
        self.mock_downstream.update.assert_called_with(assignee={"name": ""})
        mock_client.assign_issue.assert_not_called()
        mock_client.search_assignable_users_for_issues.assert_not_called()

    def common_test_create_jira_issue(
        self, mock_attach_link, mock_client, mock_update_jira_issue
    ):
        """Common code for testing _create_jira_issue"""

        # Set up return values
        mock_client.create_issue.return_value = self.mock_downstream
        mock_client.fields.return_value = [
            {"name": "Epic Link", "id": "customfield_1"},
            {"name": "QA Contact", "id": "customfield_2"},
            {"name": "EXD-Service", "id": "customfield_3"},
        ]

        # Call the function
        response = d._create_jira_issue(
            client=mock_client, issue=self.mock_issue, config=self.mock_config
        )

        # Assert everything was called correctly
        mock_client.create_issue.assert_called_with(
            issuetype={"name": "Bug"},
            project={"key": "mock_project"},
            somecustumfield="somecustumvalue",
            description=(
                "[1234] Upstream Reporter: mock_user\n"
                "Upstream issue status: Open\n"
                "Upstream description: {quote}mock_content{quote}"
            ),
            summary="mock_title",
        )
        mock_attach_link.assert_called_with(
            mock_client,
            self.mock_downstream,
            {"url": "mock_url", "title": "Upstream issue"},
        )
        mock_update_jira_issue.assert_called_with(
            self.mock_downstream, self.mock_issue, mock_client, self.mock_config
        )
        self.mock_downstream.update.assert_any_call({"customfield_1": "DUMMY-1234"})
        self.mock_downstream.update.assert_any_call(
            {"customfield_2": "dummy@dummy.com"}
        )
        self.mock_downstream.update.assert_any_call(
            {"customfield_3": {"value": "EXD-Project", "child": {"value": "EXD-Value"}}}
        )
        self.assertEqual(response, self.mock_downstream)

    @mock.patch(PATH + "_update_jira_issue")
    @mock.patch(PATH + "attach_link")
    @mock.patch("jira.client.JIRA")
    def test_create_jira_issue(
        self, mock_client, mock_attach_link, mock_update_jira_issue
    ):
        """
        Tests '_create_jira_issue' function normal success case
        """
        self.common_test_create_jira_issue(
            mock_attach_link, mock_client, mock_update_jira_issue
        )

        mock_client.add_comment.assert_not_called()

    @mock.patch(PATH + "_update_jira_issue")
    @mock.patch(PATH + "attach_link")
    @mock.patch("jira.client.JIRA")
    def test_create_jira_issue_failed_epic_link(
        self, mock_client, mock_attach_link, mock_update_jira_issue
    ):
        """
        Tests '_create_jira_issue' function when we fail while updating the epic link
        """
        # Set up return values
        self.mock_downstream.update.side_effect = [JIRAError, "success", "success"]

        self.common_test_create_jira_issue(
            mock_attach_link, mock_client, mock_update_jira_issue
        )

        mock_client.add_comment.assert_called_with(
            self.mock_downstream, f"Error adding Epic-Link: DUMMY-1234"
        )

    @mock.patch(PATH + "_update_jira_issue")
    @mock.patch(PATH + "attach_link")
    @mock.patch("jira.client.JIRA")
    def test_create_jira_issue_failed_exd_service(
        self, mock_client, mock_attach_link, mock_update_jira_issue
    ):
        """
        Tests '_create_jira_issue' function when we fail while updating the
        EXD-Service field
        """
        # Set up return values
        self.mock_downstream.update.side_effect = ["success", "success", JIRAError]

        self.common_test_create_jira_issue(
            mock_attach_link, mock_client, mock_update_jira_issue
        )

        mock_client.add_comment.assert_called_with(
            self.mock_downstream,
            f"Error adding EXD-Service field.\n"
            f"Project: {self.mock_issue.downstream['EXD-Service']['guild']}\n"
            f"Value: {self.mock_issue.downstream['EXD-Service']['value']}",
        )

    @mock.patch(PATH + "_update_jira_issue")
    @mock.patch(PATH + "attach_link")
    @mock.patch(PATH + "_get_preferred_issue_types")
    @mock.patch("jira.client.JIRA")
    def test_create_jira_issue_multiple_types(
        self,
        mock_client,
        mock_get_preferred_issue_types,
        mock_attach_link,
        mock_update_jira_issue,
    ):
        """
        Tests '_create_jira_issue' function when multiple possible issue types are found
        """
        # Set up return values
        issue_types = ["Bug", "Feature", "Outcome", "Story"]
        mock_get_preferred_issue_types.return_value = issue_types

        self.common_test_create_jira_issue(
            mock_attach_link, mock_client, mock_update_jira_issue
        )

        mock_client.add_comment.assert_called_with(
            self.mock_downstream,
            f"Some labels look like issue types but were not considered:  {issue_types[1:]}",
        )

    @mock.patch(PATH + "_update_jira_issue")
    @mock.patch(PATH + "attach_link")
    @mock.patch("jira.client.JIRA")
    def test_create_jira_issue_no_updates(
        self, mock_client, mock_attach_link, mock_update_jira_issue
    ):
        """
        Tests '_create_jira_issue' function where we have
        no updates
        """
        # Set up return values
        mock_client.create_issue.return_value = self.mock_downstream
        self.mock_issue.downstream["issue_updates"] = []

        # Call the function
        response = d._create_jira_issue(
            client=mock_client, issue=self.mock_issue, config=self.mock_config
        )

        # Assert everything was called correctly
        mock_client.create_issue.assert_called_with(
            issuetype={"name": "Bug"},
            project={"key": "mock_project"},
            somecustumfield="somecustumvalue",
            description="[1234] Upstream Reporter: mock_user\n",
            summary="mock_title",
        )
        mock_attach_link.assert_called_with(
            mock_client,
            self.mock_downstream,
            {"url": "mock_url", "title": "Upstream issue"},
        )
        mock_update_jira_issue.assert_called_with(
            self.mock_downstream, self.mock_issue, mock_client, self.mock_config
        )
        self.assertEqual(response, self.mock_downstream)
        mock_client.add_comment.assert_not_called()

    def test_get_preferred_issue_types(self):
        """
        Tests '_get_preferred_issue_types' function

        Scenarios:
         - configuration has type mappings
            - first mapping matches
            - second mapping matches
            - multiple mappings match
            - no mapping matches
         - configuration has a default type
         - upstream issue has a type
         - "RFE" in issue title
         - None of the above.
        """
        conf = {
            "issue_types": {
                "tag1": "mapped_type_C",  # In reverse-sorted order to test sorting
                "tag2": "mapped_type_B",
                "tag3": "mapped_type_A",
            },
            "type": "S2J_type",
        }
        self.mock_config["sync2jira"]["map"] = {
            "github": {self.mock_issue.upstream: conf}
        }
        self.mock_issue.issue_type = "GH_type"
        self.mock_issue.tags = ["tag1"]
        self.mock_issue.title = "RFE: Mock Issue Title"

        def update_state(
            issue_field: Optional[dict[str, Any]] = None, config: Optional[str] = None
        ):
            if issue_field:
                for k, v in issue_field.items():
                    self.mock_issue.__setattr__(k, v)
            if config:
                del conf[config]

        # List of scenarios:  each entry includes a callable which modifies
        # either the mock issue or the mock configuration prior to invoking the
        # CUT and the resulting value which is expected to be returned; the
        # test iterates over the list, calling each setup function, calling the
        # CUT, and then comparing the result to the expected value.
        scenarios = (
            # The issue label matches the first in the configured type map.
            (lambda: None, ["mapped_type_C"]),
            # The issue label matches the second in the configured type map.
            (
                lambda: update_state(issue_field={"tags": ["tag2"]}),
                ["mapped_type_B"],
            ),
            # The issue label has multiple matches in the configured type map.
            (
                lambda: update_state(issue_field={"tags": ["tag2", "tag1"]}),
                ["mapped_type_B", "mapped_type_C"],
            ),
            # The issue label has no matches in the configured type map.
            (lambda: update_state(issue_field={"tags": ["fred"]}), ["S2J_type"]),
            # There is no type map, but the configuration specifies a default type.
            (lambda: update_state(config="issue_types"), ["S2J_type"]),
            # No type in the configuration, but the upstream issue has a type.
            (lambda: update_state(config="type"), ["GH_type"]),
            # No type from config or upstream, but there is "RFE" in issue title.
            (lambda: update_state(issue_field={"issue_type": None}), ["Story"]),
            # Default fallback
            (
                lambda: update_state(issue_field={"title": "Plain Issue Title"}),
                ["Bug"],
            ),
        )

        for scenario, (setup_action, expected) in enumerate(scenarios):
            setup_action()
            actual = d._get_preferred_issue_types(self.mock_config, self.mock_issue)
            self.assertEqual(actual, expected, f"In scenario {scenario}")

    @mock.patch(PATH + "get_jira_client")
    @mock.patch(PATH + "_get_existing_jira_issue")
    @mock.patch(PATH + "_update_jira_issue")
    @mock.patch(PATH + "_create_jira_issue")
    @mock.patch("jira.client.JIRA")
    @mock.patch(PATH + "_get_existing_jira_issue_legacy")
    @mock.patch(PATH + "check_jira_status")
    def test_sync_with_jira_matching(
        self,
        mock_check_jira_status,
        mock_existing_jira_issue_legacy,
        mock_client,
        mock_create_jira_issue,
        mock_update_jira_issue,
        mock_existing_jira_issue,
        mock_get_jira_client,
    ):
        """
        Tests 'sync_with_jira' function where we do find a matching issue
        This assumes we're not using the legacy matching anymore
        """
        # Set up return values
        mock_get_jira_client.return_value = mock_client
        mock_existing_jira_issue.return_value = self.mock_downstream
        mock_check_jira_status.return_value = True

        # Call the function
        d.sync_with_jira(issue=self.mock_issue, config=self.mock_config)

        # Assert all calls were made correctly
        mock_get_jira_client.assert_called_with(self.mock_issue, self.mock_config)
        mock_update_jira_issue.assert_called_with(
            self.mock_downstream, self.mock_issue, mock_client, self.mock_config
        )
        mock_create_jira_issue.assert_not_called()
        mock_existing_jira_issue_legacy.assert_not_called()

    @mock.patch(PATH + "get_jira_client")
    @mock.patch(PATH + "_get_existing_jira_issue")
    @mock.patch(PATH + "_update_jira_issue")
    @mock.patch(PATH + "_create_jira_issue")
    @mock.patch("jira.client.JIRA")
    @mock.patch(PATH + "_get_existing_jira_issue_legacy")
    @mock.patch(PATH + "check_jira_status")
    def test_sync_with_jira_down(
        self,
        mock_check_jira_status,
        mock_existing_jira_issue_legacy,
        mock_client,
        mock_create_jira_issue,
        mock_update_jira_issue,
        mock_existing_jira_issue,
        mock_get_jira_client,
    ):
        """
        Tests 'sync_with_jira' function where the JIRA scriptrunner is down
        """
        # Set up return values
        mock_get_jira_client.return_value = mock_client
        mock_existing_jira_issue.return_value = self.mock_downstream
        mock_check_jira_status.return_value = False

        # Call the function
        with self.assertRaises(RuntimeError):
            d.sync_with_jira(issue=self.mock_issue, config=self.mock_config)

        # Assert all calls were made correctly
        mock_get_jira_client.assert_called_with(self.mock_issue, self.mock_config)
        mock_update_jira_issue.assert_not_called()
        mock_create_jira_issue.assert_not_called()
        mock_existing_jira_issue_legacy.assert_not_called()

    @mock.patch(PATH + "get_jira_client")
    @mock.patch(PATH + "_get_existing_jira_issue")
    @mock.patch(PATH + "_update_jira_issue")
    @mock.patch(PATH + "_create_jira_issue")
    @mock.patch("jira.client.JIRA")
    @mock.patch(PATH + "_get_existing_jira_issue_legacy")
    @mock.patch(PATH + "check_jira_status")
    def test_sync_with_jira_no_matching(
        self,
        mock_check_jira_status,
        mock_existing_jira_issue_legacy,
        mock_client,
        mock_create_jira_issue,
        mock_update_jira_issue,
        mock_existing_jira_issue,
        mock_get_jira_client,
    ):
        """
        Tests 'sync_with_jira' function where we do NOT find a matching issue
        This assumes we're not using the legacy matching anymore
        """
        # Set up return values
        mock_get_jira_client.return_value = mock_client
        mock_existing_jira_issue.return_value = None
        mock_check_jira_status.return_value = True

        # Call the function
        d.sync_with_jira(issue=self.mock_issue, config=self.mock_config)

        # Assert all calls were made correctly
        mock_get_jira_client.assert_called_with(self.mock_issue, self.mock_config)
        mock_update_jira_issue.assert_not_called()
        mock_create_jira_issue.assert_called_with(
            mock_client, self.mock_issue, self.mock_config
        )
        mock_existing_jira_issue_legacy.assert_not_called()

    @mock.patch(PATH + "_update_title")
    @mock.patch(PATH + "_update_description")
    @mock.patch(PATH + "_update_comments")
    @mock.patch(PATH + "_update_tags")
    @mock.patch(PATH + "_update_fixVersion")
    @mock.patch(PATH + "_update_transition")
    @mock.patch(PATH + "_update_assignee")
    @mock.patch(PATH + "_update_on_close")
    @mock.patch("jira.client.JIRA")
    def test_update_jira_issue(
        self,
        mock_client,
        mock_update_on_close,
        mock_update_assignee,
        mock_update_transition,
        mock_update_fixVersion,
        mock_update_tags,
        mock_update_comments,
        mock_update_description,
        mock_update_title,
    ):
        """
        This tests '_update_jira_issue' function
        """
        # Call the function
        d._update_jira_issue(
            existing=self.mock_downstream,
            issue=self.mock_issue,
            client=mock_client,
            config=self.mock_config,
        )

        # Assert all calls were made correctly
        mock_update_comments.assert_called_with(
            mock_client, self.mock_downstream, self.mock_issue
        )
        mock_update_tags.assert_called_with(
            self.mock_updates, self.mock_downstream, self.mock_issue
        )
        mock_update_fixVersion.assert_called_with(
            self.mock_updates,
            self.mock_downstream,
            self.mock_issue,
            mock_client,
        )
        mock_update_description.assert_called_with(
            self.mock_downstream, self.mock_issue
        )
        mock_update_title.assert_called_with(self.mock_issue, self.mock_downstream)
        mock_update_transition.assert_called_with(
            mock_client, self.mock_downstream, self.mock_issue
        )
        mock_update_on_close.assert_called_once()

    @mock.patch("jira.client.JIRA")
    def test_update_transition_JIRAError(self, mock_client):
        """
        This function tests the '_update_transition' function where Upstream issue status
        s not in existing.fields.description and transitioning the issue throws an error
        """
        # Set up return values
        self.mock_issue.status = "Closed"
        self.mock_downstream.fields.description = ""
        mock_client.transitions.return_value = [
            {"name": "CUSTOM TRANSITION", "id": "1234"}
        ]
        mock_client.transition_issue.side_effect = JIRAError

        # Call the function
        d._update_transition(
            client=mock_client, existing=self.mock_downstream, issue=self.mock_issue
        )

        # Assert all calls were made correctly
        mock_client.transitions.assert_called_with(self.mock_downstream)
        mock_client.transition_issue.assert_called_with(self.mock_downstream, 1234)

    @mock.patch("jira.client.JIRA")
    def test_update_transition_not_found(self, mock_client):
        """
        This function tests the '_update_transition' function when the Upstream
        issue status is not in the existing.fields.description value and we
        can't find the appropriate closed status
        """
        # Set up return values
        self.mock_issue.status = "Closed"
        self.mock_issue.downstream["transition"] = "bad_transition"
        self.mock_downstream.fields.description = ""
        mock_client.transitions.return_value = [
            {"name": "CUSTOM TRANSITION", "id": "1234"}
        ]

        # Call the function
        d._update_transition(
            client=mock_client, existing=self.mock_downstream, issue=self.mock_issue
        )

        # Assert all calls were made correctly
        mock_client.transitions.assert_called_with(self.mock_downstream)
        mock_client.transition_issue.assert_called_with(self.mock_downstream, 1234)

    @mock.patch("jira.client.JIRA")
    def test_update_transition_successful(self, mock_client):
        """
        This function tests the '_update_transition' function where everything goes smoothly!
        """
        # Set up return values
        self.mock_issue.status = "Closed"
        self.mock_downstream.fields.description = "[test] Upstream issue status: Open"
        mock_client.transitions.return_value = [
            {"name": "CUSTOM TRANSITION", "id": "1234"}
        ]

        # Call the function
        d._update_transition(
            client=mock_client, existing=self.mock_downstream, issue=self.mock_issue
        )

        # Assert all calls were made correctly
        mock_client.transitions.assert_called_with(self.mock_downstream)
        mock_client.transition_issue.assert_called_with(self.mock_downstream, 1234)

    @mock.patch(PATH + "_comment_format")
    @mock.patch(PATH + "_comment_matching")
    @mock.patch("jira.client.JIRA")
    def test_update_comments(
        self, mock_client, mock_comment_matching, mock_comment_format
    ):
        """
        This function tests the 'update_comments' function
        """
        # Set up return values
        mock_client.comments.return_value = "mock_comments"
        mock_comment_matching.return_value = ["mock_comments_d"]
        mock_comment_format.return_value = "mock_comment_body"

        # Call the function
        d._update_comments(
            client=mock_client, existing=self.mock_downstream, issue=self.mock_issue
        )

        # Assert all calls were made correctly
        mock_client.comments.assert_called_with(self.mock_downstream)
        mock_comment_matching.assert_called_with(
            self.mock_issue.comments, "mock_comments"
        )
        mock_comment_format.assert_called_with("mock_comments_d")
        mock_client.add_comment.assert_called_with(
            self.mock_downstream, "mock_comment_body"
        )

    def test_update_fixVersion_JIRAError(self):
        """
        This function tests the 'update_fixVersion' function where updating the downstream
        issue throws an error
        """
        # Set up return values
        self.mock_downstream.update.side_effect = JIRAError
        self.mock_downstream.fields.fixVersions = []
        mock_client = MagicMock()

        # Call the function
        d._update_fixVersion(
            updates=self.mock_updates,
            existing=self.mock_downstream,
            issue=self.mock_issue,
            client=mock_client,
        )
        # Assert all calls were made correctly
        self.mock_downstream.update.assert_called_with(
            {"fixVersions": [{"name": "fixVersion3"}, {"name": "fixVersion4"}]}
        )
        mock_client.add_comment(
            self.mock_downstream,
            f"Error updating fixVersion: {self.mock_issue.fixVersion}",
        )

    def test_update_fixVersion_no_api_call(self):
        """
        This function tests the 'update_fixVersion' function existing labels are the same
        and thus no API call should be made
        """
        # Set up return values
        self.mock_downstream.update.side_effect = JIRAError
        mock_client = MagicMock()

        # Call the function
        d._update_fixVersion(
            updates=self.mock_updates,
            existing=self.mock_downstream,
            issue=self.mock_issue,
            client=mock_client,
        )
        # Assert all calls were made correctly
        self.mock_downstream.update.assert_not_called()
        mock_client.add_comment.assert_not_called()

    def test_update_fixVersion_successful(self):
        """
        This function tests the 'update_fixVersion' function where everything goes smoothly!
        """
        # Set up return values
        self.mock_downstream.fields.fixVersions = []
        mock_client = MagicMock()

        # Call the function
        d._update_fixVersion(
            updates=self.mock_updates,
            existing=self.mock_downstream,
            issue=self.mock_issue,
            client=mock_client,
        )
        # Assert all calls were made correctly
        self.mock_downstream.update.assert_called_with(
            {"fixVersions": [{"name": "fixVersion3"}, {"name": "fixVersion4"}]}
        )
        mock_client.add_comment.assert_not_called()

    @mock.patch(PATH + "assign_user")
    @mock.patch("jira.client.JIRA")
    def test_update_assignee_all(self, mock_client, mock_assign_user):
        """
        This function tests the `_update_assignee()` function in a variety of scenarios.
        """

        # The values of expected_results mean:
        #  - None:  _update_assignee() was not called
        #  - True:  _update_assignee() was called with `remove_all` set to `True`
        #  - False:  _update_assignee() was called with `remove_all` set to `False`
        expected_results = iter(
            (
                # - overwrite = True
                #    - downstream assignee exists
                None,  # upstream assignee exists and assignments are equal: not called
                None,  # upstream assignee exists and assignments differ only in diacritics: not called
                False,  # upstream assignee exists and assignments are different: called with remove_all=False
                True,  # upstream assignee has a fullname of None: called with remove_all=True
                True,  # upstream assignee does not exist: called with remove_all=True
                True,  # upstream assignee is an empty list: called with remove_all=True
                #    - downstream assignee does not exist
                False,  # upstream assignee exists: called with remove_all=False
                False,  # upstream assignee exists: called with remove_all=False
                False,  # upstream assignee exists: called with remove_all=False
                False,  # upstream assignee has a fullname of None: called with remove_all=False
                False,  # upstream assignee does not exist: called with remove_all=False
                False,  # upstream assignee is an empty list: called with remove_all=False
                # - overwrite = False
                #    - downstream assignee exists:
                None,  # upstream assignee exists and assignments are equal: not called
                None,  # upstream assignee exists and assignments differ only in diacritics: not called
                None,  # upstream assignee exists and assignments are different: not called
                None,  # upstream assignee has a fullname of None: not called
                None,  # upstream assignee does not exist: not called
                None,  # upstream assignee is an empty list: not called
                #    - downstream assignee does not exist
                False,  # upstream assignee exists: called with remove_all=False
                False,  # upstream assignee exists: called with remove_all=False
                False,  # upstream assignee exists: called with remove_all=False
                False,  # upstream assignee has a fullname of None: called with remove_all=False
                False,  # upstream assignee does not exist: called with remove_all=False
                False,  # upstream assignee is an empty list: called with remove_all=False
            )
        )
        match = "Erik"
        for overwrite in (True, False):
            for ds in (match, None):
                if ds is None:
                    delattr(self.mock_downstream.fields.assignee, "displayName")
                else:
                    setattr(self.mock_downstream.fields.assignee, "displayName", match)

                for us in (
                    [{"fullname": match}],
                    [{"fullname": "Èŕìḱ"}],
                    [{"fullname": "Bob"}],
                    [{"fullname": None}],
                    None,
                    [],
                ):
                    self.mock_issue.assignee = us

                    d._update_assignee(
                        client=mock_client,
                        existing=self.mock_downstream,
                        issue=self.mock_issue,
                        overwrite=overwrite,
                    )

                    # Check that the call was made correctly
                    expected_result = next(expected_results)
                    if expected_result is None:
                        mock_assign_user.assert_not_called()
                    else:
                        mock_assign_user.assert_called_with(
                            mock_client,
                            self.mock_issue,
                            self.mock_downstream,
                            remove_all=expected_result,
                        )
                    mock_assign_user.reset_mock()

    @mock.patch(PATH + "verify_tags")
    @mock.patch(PATH + "_label_matching")
    def test_update_tags(self, mock_label_matching, mock_verify_tags):
        """
        This function tests the '_update_tags' function
        """
        # Set up return values
        mock_label_matching.return_value = "mock_updated_labels"
        mock_verify_tags.return_value = ["mock_verified_tags"]

        # Call the function
        d._update_tags(
            updates=self.mock_updates,
            existing=self.mock_downstream,
            issue=self.mock_issue,
        )

        # Assert all calls were made correctly
        mock_label_matching.assert_called_with(
            self.mock_issue.tags, self.mock_downstream.fields.labels
        )
        mock_verify_tags.assert_called_with("mock_updated_labels")
        self.mock_downstream.update.assert_called_with(
            {"labels": ["mock_verified_tags"]}
        )

    @mock.patch(PATH + "verify_tags")
    @mock.patch(PATH + "_label_matching")
    def test_update_tags_no_api_call(self, mock_label_matching, mock_verify_tags):
        """
        This function tests the '_update_tags' function where the existing tags are the same
        as the new ones
        """
        # Set up return values
        mock_label_matching.return_value = "mock_updated_labels"
        mock_verify_tags.return_value = ["tag3", "tag4"]

        # Call the function
        d._update_tags(
            updates=self.mock_updates,
            existing=self.mock_downstream,
            issue=self.mock_issue,
        )

        # Assert all calls were made correctly
        mock_label_matching.assert_called_with(
            self.mock_issue.tags, self.mock_downstream.fields.labels
        )
        mock_verify_tags.assert_called_with("mock_updated_labels")
        self.mock_downstream.update.assert_not_called()

    def test_update_description_update(self):
        """
        This function tests '_update_description' where we just have to update the contents of the description
        """
        # Set up return values
        self.mock_downstream.fields.description = "[1234] Upstream Reporter: mock_user\nUpstream issue status: Open\nUpstream description: {quote} test {quote}"

        # Call the function
        d._update_description(existing=self.mock_downstream, issue=self.mock_issue)

        # Assert all calls were made correctly
        self.mock_downstream.update.assert_called_with(
            {
                "description": "[1234] Upstream Reporter: mock_user\nUpstream issue status: Open\nUpstream description: {quote}mock_content{quote}"
            }
        )

    def test_update_description_add_field(self):
        """
        This function tests '_update_description' where we just have to add a description field
        """
        # Set up return values
        self.mock_downstream.fields.description = (
            "[123] Upstream Reporter: mock_user\n"
            "Upstream description: {quote} test {quote}"
        )

        # Call the function
        d._update_description(existing=self.mock_downstream, issue=self.mock_issue)

        # Assert all calls were made correctly
        self.mock_downstream.update.assert_called_with(
            {
                "description": "[1234] Upstream Reporter: mock_user\n"
                "Upstream issue status: Open\n"
                "Upstream description: {quote}mock_content{quote}"
            }
        )

    def test_update_description_add_reporter(self):
        """
        This function tests '_update_description' where we have to add a description and upstream reporter field
        """
        # Set up return values
        self.mock_downstream.fields.description = "[123] Upstream issue status: Open\n"
        self.mock_issue.status = "Open"
        self.mock_issue.id = "123"
        self.mock_issue.reporter = {"fullname": "mock_user"}

        # Call the function
        d._update_description(existing=self.mock_downstream, issue=self.mock_issue)
        # Assert all calls were made correctly
        self.mock_downstream.update.assert_called_with(
            {
                "description": "[123] Upstream Reporter: mock_user\n"
                "Upstream issue status: Open\n"
                "Upstream description: {quote}mock_content{quote}"
            }
        )

    def test_update_description_add_reporter_no_status(self):
        """
        This function tests '_update_description' where we have to add reporter and description without status
        """
        # Set up return values
        self.mock_downstream.fields.description = ""
        self.mock_issue.downstream["issue_updates"] = [
            u
            for u in self.mock_issue.downstream["issue_updates"]
            if "transition" not in u
        ]

        # Call the function
        d._update_description(existing=self.mock_downstream, issue=self.mock_issue)

        # Assert all calls were made correctly
        self.mock_downstream.update.assert_called_with(
            {
                "description": "[1234] Upstream Reporter: mock_user\n"
                "Upstream description: {quote}mock_content{quote}"
            }
        )

    @mock.patch(PATH + "datetime")
    def test_update_description_add_description(self, mock_datetime):
        """
        This function tests '_update_description' where we have a reporter and status already
        """
        # Set up return values
        self.mock_downstream.fields.description = (
            "[123] Upstream issue status: Open\n" "[123] Upstream Reporter: mock_user\n"
        )
        self.mock_issue.status = "Open"
        self.mock_issue.id = "123"
        self.mock_issue.reporter = {"fullname": "mock_user"}
        mock_datetime.today.return_value = self.mock_today

        # Call the function
        d._update_description(existing=self.mock_downstream, issue=self.mock_issue)

        # Assert all calls were made correctly
        self.mock_downstream.update.assert_called_with(
            {
                "description": "[123] Upstream Reporter: mock_user\n"
                "Upstream issue status: Open\n"
                "Upstream description: {quote}mock_content{quote}"
            }
        )

    def test_verify_tags(self):
        """
        This function tests 'verify_tags' function
        """
        # Call the function
        response = d.verify_tags(tags=["this is a tag"])

        # Assert everything was called correctly
        self.assertEqual(response, ["this_is_a_tag"])

    @mock.patch(PATH + "find_username")
    @mock.patch(PATH + "check_comments_for_duplicate")
    @mock.patch("jira.client.JIRA")
    def test_matching_jira_issue_query(
        self,
        mock_client,
        mock_check_comments_for_duplicates,
        mock_find_username,
    ):
        """
        This tests '_matching_jira_query' function
        """
        # Set up return values
        mock_downstream_issue = MagicMock()
        self.mock_issue.upstream_title = "mock_upstream_title"
        mock_downstream_issue.fields.description = self.mock_issue.id
        bad_downstream_issue = MagicMock()
        bad_downstream_issue.fields.description = "bad"
        bad_downstream_issue.fields.summary = "bad"
        mock_client.search_issues.return_value = [
            mock_downstream_issue,
            bad_downstream_issue,
        ]
        mock_check_comments_for_duplicates.return_value = True
        mock_find_username.return_value = "mock_username"

        # Call the function
        response = d._matching_jira_issue_query(
            client=mock_client, issue=self.mock_issue, config=self.mock_config
        )

        # Assert everything was called correctly
        self.assertEqual(response, [mock_downstream_issue])
        mock_client.search_issues.assert_called_with(
            'issueFunction in linkedIssuesOfRemote("Upstream issue")'
            ' and issueFunction in linkedIssuesOfRemote("mock_url")'
        )
        mock_check_comments_for_duplicates.assert_called_with(
            mock_client, mock_downstream_issue, "mock_username"
        )
        mock_find_username.assert_called_with(self.mock_issue, self.mock_config)

    def test_find_username(self):
        """
        Tests 'find_username' function
        """
        # Call the function
        response = d.find_username(self.mock_issue, self.mock_config)

        # Assert everything was called correctly
        self.assertEqual(response, "mock_user")

    @mock.patch("jira.client.JIRA")
    def test_check_comments_for_duplicates(self, mock_client):
        """
        Tests 'check_comments_for_duplicates' function
        """
        # Set up return values
        mock_comment = MagicMock()
        mock_comment.body = "Marking as duplicate of TEST-1234"
        mock_comment.author.name = "mock_user"
        mock_client.comments.return_value = [mock_comment]
        mock_client.issue.return_value = "Successful Call!"

        # Call the function
        response = d.check_comments_for_duplicate(
            client=mock_client, result=self.mock_downstream, username="mock_user"
        )

        # Assert everything was called correctly
        self.assertEqual(response, "Successful Call!")
        mock_client.comments.assert_called_with(self.mock_downstream)
        mock_client.issue.assert_called_with("TEST-1234")

    @mock.patch(PATH + "_comment_format")
    @mock.patch(PATH + "_comment_format_legacy")
    def test_find_comment_in_jira_legacy(
        self, mock_comment_format_legacy, mock_comment_format
    ):
        """
        This function tests '_find_comment_in_jira' where we find a legacy comment
        """
        # Set up return values
        mock_comment_format.return_value = "mock_comment_body"
        mock_comment_format_legacy.return_value = "mock_legacy_comment_body"
        mock_jira_comment = MagicMock()
        mock_jira_comment.raw = {"body": "mock_legacy_comment_body"}
        mock_comment = {
            "id": "12345",
            "date_created": datetime(2019, 8, 8, tzinfo=timezone.utc),
        }

        # Call the function
        response = d._find_comment_in_jira(mock_comment, [mock_jira_comment])

        # Assert everything was called correctly
        mock_comment_format_legacy.assert_called_with(mock_comment)
        mock_comment_format.assert_called_with(mock_comment)
        self.assertEqual(response, mock_jira_comment)

    @mock.patch(PATH + "_comment_format")
    @mock.patch(PATH + "_comment_format_legacy")
    def test_find_comment_in_jira_id(
        self, mock_comment_format_legacy, mock_comment_format
    ):
        """
        This function tests '_find_comment_in_jira' where we match an ID
        """
        # Set up return values
        mock_comment_format.return_value = "mock_comment_body"
        mock_comment_format_legacy.return_value = "mock_legacy_comment_body"
        mock_jira_comment = MagicMock()
        mock_jira_comment.raw = {"body": "12345"}
        mock_comment = {
            "id": "12345",
            "date_created": datetime(2019, 8, 8, tzinfo=timezone.utc),
        }

        # Call the function
        response = d._find_comment_in_jira(mock_comment, [mock_jira_comment])

        # Assert everything was called correctly
        mock_comment_format_legacy.assert_called_with(mock_comment)
        mock_comment_format.assert_called_with(mock_comment)
        self.assertEqual(response, mock_jira_comment)

    @mock.patch(PATH + "_comment_format")
    @mock.patch(PATH + "_comment_format_legacy")
    def test_find_comment_in_jira_old_comment(
        self, mock_comment_format_legacy, mock_comment_format
    ):
        """
        This function tests '_find_comment_in_jira' when we find an old comment
        """
        # Set up return values
        mock_comment_format.return_value = "mock_comment_body"
        mock_comment_format_legacy.return_value = "mock_legacy_comment_body"
        mock_jira_comment = MagicMock()
        mock_jira_comment.raw = {"body": "old_comment"}
        mock_comment = {
            "id": "12345",
            "date_created": datetime(2019, 1, 1, tzinfo=timezone.utc),
        }

        # Call the function
        response = d._find_comment_in_jira(mock_comment, [mock_jira_comment])

        # Assert everything was called correctly
        mock_comment_format_legacy.assert_called_with(mock_comment)
        mock_comment_format.assert_called_with(mock_comment)
        self.assertEqual(response, mock_jira_comment)

    @mock.patch(PATH + "_comment_format")
    @mock.patch(PATH + "_comment_format_legacy")
    def test_find_comment_in_jira_none(
        self, mock_comment_format_legacy, mock_comment_format
    ):
        """
        This function tests '_find_comment_in_jira' where we return None
        """
        # Set up return values
        mock_comment_format.return_value = "mock_comment_body"
        mock_comment_format_legacy.return_value = "mock_legacy_comment_body"
        mock_comment = {
            "id": "12345",
            "date_created": datetime(2019, 1, 1, tzinfo=timezone.utc),
        }

        # Call the function
        response = d._find_comment_in_jira(mock_comment, [])

        # Assert everything was called correctly
        mock_comment_format_legacy.assert_called_with(mock_comment)
        mock_comment_format.assert_called_with(mock_comment)
        self.assertEqual(response, None)

    def test_check_jira_status_false(self):
        """
        This function tests 'check_jira_status' where we return false
        """
        # Set up return values
        mock_jira_client = MagicMock()
        mock_jira_client.search_issues.return_value = []

        # Call the function
        response = d.check_jira_status(mock_jira_client)

        # Assert everything was called correctly
        self.assertEqual(response, False)
        mock_jira_client.search_issues.assert_called_with(
            "issueFunction in linkedIssuesOfRemote('*')"
        )

    def test_check_jira_status_true(self):
        """
        This function tests 'check_jira_status' where we return false
        """
        # Set up return values
        mock_jira_client = MagicMock()
        mock_jira_client.search_issues.return_value = ["some", "values"]

        # Call the function
        response = d.check_jira_status(mock_jira_client)

        # Assert everything was called correctly
        self.assertEqual(response, True)
        mock_jira_client.search_issues.assert_called_with(
            "issueFunction in linkedIssuesOfRemote('*')"
        )

    def test_update_on_close_update(self):
        """
        This function tests '_update_on_close' where there is an
        "apply_labels" configuration, and labels need to be updated.
        """
        # Set up return values
        self.mock_downstream.fields.description = ""
        self.mock_issue.status = "Closed"
        updates = [{"on_close": {"apply_labels": ["closed-upstream"]}}]

        # Call the function
        d._update_on_close(self.mock_downstream, self.mock_issue, updates)

        # Assert everything was called correctly
        self.mock_downstream.update.assert_called_with(
            {"labels": ["closed-upstream", "tag3", "tag4"]}
        )

    def test_update_on_close_no_change(self):
        """
        This function tests '_update_on_close' where there is an
        "apply_labels" configuration but there is no update required.
        """
        # Set up return values
        self.mock_issue.status = "Closed"
        updates = [{"on_close": {"apply_labels": ["tag4"]}}]

        # Call the function
        d._update_on_close(self.mock_downstream, self.mock_issue, updates)

        # Assert everything was called correctly
        self.mock_downstream.update.assert_not_called()

    def test_update_on_close_no_action(self):
        """
        This function tests '_update_on_close' where there is no
        "apply_labels" configuration.
        """
        # Set up return values
        self.mock_issue.status = "Closed"
        updates = [{"on_close": {"some_other_action": None}}]

        # Call the function
        d._update_on_close(self.mock_downstream, self.mock_issue, updates)

        # Assert everything was called correctly
        self.mock_downstream.update.assert_not_called()

    def test_update_on_close_no_config(self):
        """
        This function tests '_update_on_close' where there is no
        configuration for close events.
        """
        # Set up return values
        self.mock_issue.status = "Closed"
        updates = ["description"]

        # Call the function
        d._update_on_close(self.mock_downstream, self.mock_issue, updates)

        # Assert everything was called correctly
        self.mock_downstream.update.assert_not_called()

    @mock.patch("jira.client.JIRA")
    def test_update_github_project_fields_storypoints(self, mock_client):
        """
        This function tests `_update_github_project_fields`
        with story points value.
        """
        github_project_fields = {"storypoints": {"gh_field": "Estimate"}}
        d._update_github_project_fields(
            mock_client,
            self.mock_downstream,
            self.mock_issue,
            github_project_fields,
            self.mock_config,
        )
        self.mock_downstream.update.assert_called_with({"customfield_12310243": 2})

    @mock.patch("jira.client.JIRA")
    def test_update_github_project_fields_storypoints_bad(self, mock_client):
        """This function tests `_update_github_project_fields` with
        a bad (non-numeric) story points value.
        """
        github_project_fields = {"storypoints": {"gh_field": "Estimate"}}
        for bad_sp in [None, "", "bad_value"]:
            self.mock_issue.storypoints = bad_sp
            d._update_github_project_fields(
                mock_client,
                self.mock_downstream,
                self.mock_issue,
                github_project_fields,
                self.mock_config,
            )
            self.mock_downstream.update.assert_not_called()
            mock_client.add_comment.assert_not_called()

    @mock.patch("jira.client.JIRA")
    def test_update_github_project_fields_priority(self, mock_client):
        """
        This function tests `_update_github_project_fields`
        with priority value.
        """
        github_project_fields = {
            "priority": {
                "gh_field": "Priority",
                "options": {
                    "P0": "Blocker",
                    "P1": "Critical",
                    "P2": "Major",
                    "P3": "Minor",
                    "P4": "Optional",
                    "P5": "Trivial",
                },
            }
        }
        d._update_github_project_fields(
            mock_client,
            self.mock_downstream,
            self.mock_issue,
            github_project_fields,
            self.mock_config,
        )
        self.mock_downstream.update.assert_called_with(
            {"priority": {"name": "Critical"}}
        )

    @mock.patch("jira.client.JIRA")
    def test_update_github_project_fields_priority_bad(self, mock_client):
        """This function tests `_update_github_project_fields` with
        a bad priority value.
        """
        github_project_fields = {
            "priority": {
                "gh_field": "Priority",
                "options": {
                    "P0": "Blocker",
                    "P1": "Critical",
                    "P2": "Major",
                    "P3": "Minor",
                    "P4": "Optional",
                    "P5": "Trivial",
                },
            }
        }
        for bad_pv in [None, "", "bad_value"]:
            self.mock_issue.priority = bad_pv
            d._update_github_project_fields(
                mock_client,
                self.mock_downstream,
                self.mock_issue,
                github_project_fields,
                self.mock_config,
            )
            self.mock_downstream.update.assert_not_called()
            mock_client.add_comment.assert_not_called()

    def test_remove_diacritics(self):
        scenarios = [
            ("Èŕìḱ", "Erik"),
            ("Erik", "Erik"),
            ("", ""),
            (None, ""),
        ]

        for text, expected in scenarios:
            actual = remove_diacritics(text)
            self.assertEqual(actual, expected)
