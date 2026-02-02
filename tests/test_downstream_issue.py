from datetime import timedelta
import os
from typing import Any, Optional
import unittest
import unittest.mock as mock
from unittest.mock import MagicMock

from jira import JIRAError
import jira.client
from jira.client import Issue as JIssue
from jira.client import ResultList

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
            "custom_fields": {"somecustomfield": "somecustomvalue"},
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
            d.get_jira_client(issue="string", config=self.mock_config)  # type: ignore

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
        mock_jira_instance = MagicMock()
        mock_jira_instance.session.return_value = None
        mock_client.return_value = mock_jira_instance

        # Call the function

        response = d.get_jira_client(issue=mock_issue, config=self.mock_config)

        # Assert everything was called correctly
        mock_client.assert_called_with(mock_jira="mock_jira")
        mock_jira_instance.session.assert_called_once()
        self.assertEqual(mock_jira_instance, response)

    @mock.patch("jira.client.JIRA")
    def test_get_jira_client_auth_failure(self, mock_client):
        """
        This tests 'get_jira_client' function where JIRA authentication fails
        """
        # Set up return values
        mock_issue = MagicMock(spec=Issue)
        mock_issue.downstream = {"jira_instance": "mock_jira_instance"}
        mock_jira_instance = MagicMock()
        mock_jira_instance.session.side_effect = JIRAError("Authentication failed")
        mock_client.return_value = mock_jira_instance

        # Call the function and expect it to raise JIRAError
        with self.assertRaises(JIRAError):
            d.get_jira_client(issue=mock_issue, config=self.mock_config)

        # Assert the client was created but failed authentication
        mock_client.assert_called_with(mock_jira="mock_jira")
        mock_jira_instance.session.assert_called_once()

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

    @mock.patch(PATH + "_filter_downstream_issues")
    @mock.patch(PATH + "_get_existing_jira_issue_query")
    @mock.patch("jira.client.JIRA")
    def test_get_existing_newstyle(self, mock_client, mock_get_query, mock_filter):
        """
        This tests 'get_existing_jira_issue' function.
        """
        mock_issue_1: JIssue = MagicMock(spec=JIssue, name="mock_issue_1")
        mock_issue_1.key = "MOCK-1"
        mock_issue_1.fields = MagicMock()
        mock_issue_1.fields.updated = "2025-11-30T00:00:10.0+0000"
        mock_issue_2: JIssue = MagicMock(spec=JIssue, name="mock_issue_2")
        mock_issue_2.key = "MOCK-2"
        mock_issue_2.fields = MagicMock()
        mock_issue_2.fields.updated = "2025-11-30T00:02:00.0+0000"
        mock_issue_3: JIssue = MagicMock(spec=JIssue, name="mock_issue_3")
        mock_issue_3.key = "MOCK-3"
        mock_issue_3.fields = MagicMock()
        mock_issue_3.fields.updated = "2025-11-30T00:00:00.0+0000"

        scenarios = (
            {
                "scenario": "_get_existing_jira_issue_query returns None",
                "jira_results": None,
                "search_issues": None,
                "filter_results": None,
                "expected": None,
            },
            {
                "scenario": "Jira search returns one item",
                "jira_results": "mock issue key query string",
                "search_issues": ResultList[JIssue]((mock_issue_1,)),
                "filter_results": None,
                "expected": mock_issue_1,
            },
            {
                "scenario": "_filter_downstream_issues returns one item",
                "jira_results": "mock issue key query string",
                "search_issues": ResultList[JIssue](
                    (mock_issue_1, mock_issue_2, mock_issue_3)
                ),
                "filter_results": ResultList[JIssue]((mock_issue_3,)),
                "expected": mock_issue_3,
            },
            {
                "scenario": "_filter_downstream_issues returns multiple items",
                "jira_results": "mock issue key query string",
                "search_issues": ResultList[JIssue](
                    (mock_issue_1, mock_issue_2, mock_issue_3)
                ),
                "filter_results": ResultList[JIssue](
                    (mock_issue_1, mock_issue_2, mock_issue_3)
                ),
                "expected": mock_issue_2,  # Most-recently updated
            },
        )

        for x in scenarios:
            d.jira_cache = d.UrlCache()  # Clear the cache
            mock_get_query.return_value = x["jira_results"]
            mock_client.search_issues.return_value = x["search_issues"]
            mock_filter.return_value = x["filter_results"]
            result = d.get_existing_jira_issue(
                client=mock_client, issue=self.mock_issue, config=self.mock_config
            )
            self.assertEqual(result, x["expected"])
            if x["expected"]:
                self.assertEqual(d.jira_cache[self.mock_issue.url], x["expected"].key)

    @mock.patch(PATH + "execute_snowflake_query")
    def test_get_existing_jira_issue_query(self, mock_snowflake):
        scenarios = (
            {
                "jira_cache": {self.mock_issue.url: "issue_key"},
                "snowflake": (),
                "expected": "key in (issue_key)",
            },
            {
                "jira_cache": {},
                "snowflake": (),
                "expected": None,
            },
            {
                "jira_cache": {},
                "snowflake": (("issue_key",),),
                "expected": "key in (issue_key)",
            },
            {
                "jira_cache": {},
                "snowflake": (
                    ("issue_key_1",),
                    ("issue_key_2",),
                    ("issue_key_3",),
                ),
                "expected": "key in (issue_key_1,issue_key_2,issue_key_3)",
            },
        )

        for x in scenarios:
            d.jira_cache = x["jira_cache"]
            mock_snowflake.return_value = x["snowflake"]
            result = d._get_existing_jira_issue_query(self.mock_issue)
            self.assertEqual(result, x["expected"])

    @mock.patch(PATH + "find_username")
    @mock.patch(PATH + "check_comments_for_duplicate")
    @mock.patch("jira.client.JIRA")
    def test_filter_downstream_issues(
        self,
        mock_client,
        mock_check_comments_for_duplicate,
        _mock_find_username,
    ):
        self.mock_issue.upstream_title = "issue upstream title"

        # These issues will be included by the filter, each for a different reason.
        issue_included_1 = MagicMock(spec=JIssue, name="issue_included_1")
        issue_included_1.fields = MagicMock()
        issue_included_1.fields.description = (
            f"contains {self.mock_issue.id} in description"
        )
        issue_included_1.fields.summary = "but doesn't match either title or regex"
        issue_included_2 = MagicMock(spec=JIssue, name="issue_included_2")
        issue_included_2.fields = MagicMock()
        issue_included_2.fields.description = "missing issue ID"
        issue_included_2.fields.summary = self.mock_issue.title  # Summary matches title
        issue_included_3 = MagicMock(spec=JIssue, name="issue_included_3")
        issue_included_3.fields = MagicMock()
        issue_included_3.fields.description = "missing issue ID"
        issue_included_3.fields.summary = (
            f"[mock] {self.mock_issue.upstream_title} regex match"
        )

        # These issues will be excluded by the filter.
        issue_excluded_1 = MagicMock(spec=JIssue, name="issue_excluded_1")
        issue_excluded_1.fields = MagicMock()
        issue_excluded_1.fields.description = "missing issue ID"
        issue_excluded_1.fields.summary = f"doesn't match either title or regex"
        issue_excluded_2 = MagicMock(spec=JIssue, name="issue_excluded_2")
        issue_excluded_2.fields = MagicMock()
        issue_excluded_2.fields.description = "also missing issue ID"
        issue_excluded_2.fields.summary = f"also doesn't match either title or regex"
        issue_excluded_3 = MagicMock(spec=JIssue, name="issue_excluded_3")
        issue_excluded_3.fields = MagicMock()
        issue_excluded_3.fields.description = "missing issue ID, also"
        issue_excluded_3.fields.summary = f"doesn't match either title or regex either"

        scenarios = (
            {
                "scenario": "Empty input",
                "results_in": ResultList[JIssue](),
                "check_comments_rv": None,
                "expected": ResultList[JIssue](),
            },
            {
                "scenario": "Single input gets filtered out but returned in lieu of empty output",
                "results_in": ResultList[JIssue]((issue_excluded_1,)),
                "check_comments_rv": None,
                "expected": ResultList[JIssue]((issue_excluded_1,)),
            },
            {
                "scenario": "Single input gets selected but is not a duplicate",
                "results_in": ResultList[JIssue]((issue_included_1,)),
                "check_comments_rv": None,
                "expected": ResultList[JIssue]((issue_included_1,)),
            },
            {
                "scenario": "Single input gets selected but is a duplicate",
                "results_in": ResultList[JIssue]((issue_included_1,)),
                "check_comments_rv": issue_excluded_1,
                "expected": ResultList[JIssue]((issue_excluded_1,)),
            },
            {
                "scenario": "Multiple input gets filtered out but returned in lieu of empty output",
                "results_in": ResultList[JIssue](
                    (issue_excluded_1, issue_excluded_2, issue_excluded_3)
                ),
                "check_comments_rv": None,
                "expected": ResultList[JIssue](
                    (issue_excluded_1, issue_excluded_2, issue_excluded_3)
                ),
            },
            {
                "scenario": "Multiple input get selected with no duplicates",
                "results_in": ResultList[JIssue](
                    (issue_included_1, issue_included_2, issue_included_3)
                ),
                "check_comments_rv": None,
                "expected": ResultList[JIssue](
                    (issue_included_1, issue_included_2, issue_included_3)
                ),
            },
            {
                "scenario": "Multiple input get selected with all duplicates",
                "results_in": ResultList[JIssue](
                    (issue_included_1, issue_included_2, issue_included_3)
                ),
                "check_comments_rv": issue_excluded_1,
                "expected": ResultList[JIssue](
                    (issue_excluded_1, issue_excluded_1, issue_excluded_1)
                ),
            },
        )

        for x in scenarios:
            mock_check_comments_for_duplicate.return_value = x["check_comments_rv"]
            result = d._filter_downstream_issues(
                x["results_in"], self.mock_issue, mock_client, self.mock_config
            )
            self.assertListEqual(result, x["expected"])

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
        mock_client.search_users.return_value = [mock_user]
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
        mock_client.search_users.assert_called_with(user="mock_user@redhat.com")

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
        mock_client.search_users.return_value = [mock_user]
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
        mock_client.search_users.assert_called_with(user="mock_user@redhat.com")

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
        mock_client.search_users.return_value = [
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
        mock_client.search_users.assert_called_with(user="mock_user@redhat.com")

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
        mock_client.search_users.return_value = []
        mock_client.assign_issue.return_value = True
        mock_rover_lookup.return_value = []

        # Call the assign user function
        d.assign_user(
            issue=self.mock_issue, downstream=self.mock_downstream, client=mock_client
        )

        # Assert that all calls mocked were called properly
        mock_client.assign_issue.assert_called_with(1234, "mock_owner")
        mock_client.search_users.assert_not_called()

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
        mock_client.search_users.return_value = []
        mock_client.assign_issue.return_value = True
        mock_rover_lookup.return_value = ["no_match@redhat.com"]

        # Call the assign user function
        d.assign_user(
            issue=self.mock_issue, downstream=self.mock_downstream, client=mock_client
        )

        # Assert that all calls mocked were called properly
        mock_client.assign_issue.assert_called_with(1234, "mock_owner")
        mock_client.search_users.assert_called_with(user="no_match@redhat.com")

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
        mock_client.search_users.return_value = []
        mock_client.assign_issue.return_value = True
        mock_rover_lookup.return_value = []
        self.mock_issue.downstream.pop("owner")

        # Call the assign user function
        d.assign_user(
            issue=self.mock_issue, downstream=self.mock_downstream, client=mock_client
        )

        # Assert that all calls mocked were called properly
        mock_client.assign_issue.assert_not_called()
        mock_client.search_users.assert_not_called()

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
        mock_client.search_users.assert_not_called()
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
        mock_client.search_users.assert_not_called()

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
            {"name": "somecustomfield", "id": "customfield_4"},
        ]

        # Call the function
        response = d._create_jira_issue(
            client=mock_client, issue=self.mock_issue, config=self.mock_config
        )

        # Assert everything was called correctly
        mock_client.create_issue.assert_called_with(
            issuetype={"name": "Bug"},
            project={"key": "mock_project"},
            customfield_4="somecustomvalue",
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
        mock_client.fields.return_value = [
            {"name": "Epic Link", "id": "customfield_1"},
            {"name": "QA Contact", "id": "customfield_2"},
            {"name": "EXD-Service", "id": "customfield_3"},
            {"name": "somecustomfield", "id": "customfield_4"},
        ]
        self.mock_issue.downstream["issue_updates"] = []

        # Call the function
        response = d._create_jira_issue(
            client=mock_client, issue=self.mock_issue, config=self.mock_config
        )

        # Assert everything was called correctly
        mock_client.create_issue.assert_called_with(
            issuetype={"name": "Bug"},
            project={"key": "mock_project"},
            customfield_4="somecustomvalue",
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
    @mock.patch(PATH + "get_existing_jira_issue")
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
    @mock.patch(PATH + "get_existing_jira_issue")
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
    @mock.patch(PATH + "get_existing_jira_issue")
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
    def test_update_jira_issue_closed(
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
        This tests '_update_jira_issue' function when the issue is closed
        """

        self.mock_issue.status = "Closed"

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
        mock_update_assignee.assert_called_once()
        mock_update_description.assert_called_with(
            self.mock_downstream, self.mock_issue
        )
        mock_update_title.assert_called_with(self.mock_issue, self.mock_downstream)
        mock_update_transition.assert_called_with(
            mock_client, self.mock_downstream, self.mock_issue
        )
        mock_update_on_close.assert_called_once()

    @mock.patch(PATH + "_update_title")
    @mock.patch(PATH + "_update_description")
    @mock.patch(PATH + "_update_comments")
    @mock.patch(PATH + "_update_tags")
    @mock.patch(PATH + "_update_fixVersion")
    @mock.patch(PATH + "_update_transition")
    @mock.patch(PATH + "_update_assignee")
    @mock.patch(PATH + "_update_on_close")
    @mock.patch("jira.client.JIRA")
    def test_update_jira_issue_open(
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
        This tests '_update_jira_issue' function when the issue is not closed
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
        mock_update_assignee.assert_called_once()
        mock_update_description.assert_called_with(
            self.mock_downstream, self.mock_issue
        )
        mock_update_title.assert_called_with(self.mock_issue, self.mock_downstream)
        mock_update_transition.assert_called_with(
            mock_client, self.mock_downstream, self.mock_issue
        )
        mock_update_on_close.assert_not_called()

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
                #    - downstream assignee is set
                #       - upstream assignee exists and assignments are equal: not called
                (11, None),
                #       - upstream assignee exists and assignments differ only in diacritics: not called
                (12, None),
                #       - upstream assignee exists and assignments are different: called with remove_all=False
                (13, False),
                #       - upstream assignee has a fullname of None: called with remove_all=True
                (14, True),
                #       - upstream assignee does not exist: called with remove_all=True
                (15, True),
                #       - upstream assignee is an empty list: called with remove_all=True
                (16, True),
                #    - downstream assignee is owner
                #       - upstream assignee exists and assignments are different: called with remove_all=False
                (21, False),
                #       - upstream assignee exists and assignments are different: called with remove_all=False
                (22, False),
                #       - upstream assignee exists and assignments are different: called with remove_all=False
                (23, False),
                #       - upstream assignee has a fullname of None: not called (already assigned to owner)
                (24, None),
                #       - upstream assignee does not exist: not called (already assigned to owner)
                (25, None),
                #       - upstream assignee is an empty list: not called (already assigned to owner)
                (26, None),
                #    - downstream assignee does not exist
                #       - upstream assignee exists: called with remove_all=False
                (31, False),
                #       - upstream assignee exists: called with remove_all=False
                (32, False),
                #       - upstream assignee exists: called with remove_all=False
                (33, False),
                #       - upstream assignee has a fullname of None: called with remove_all=False
                (34, False),
                #       - upstream assignee does not exist: called with remove_all=False
                (35, False),
                #       - upstream assignee is an empty list: called with remove_all=False
                (36, False),
                # - overwrite = False
                #    - downstream assignee is set:
                #       - upstream assignee exists and assignments are equal: not called
                (41, None),
                #       - upstream assignee exists and assignments differ only in diacritics: not called
                (42, None),
                #       - upstream assignee exists and assignments are different: not called
                (43, None),
                #       - upstream assignee has a fullname of None: not called
                (44, None),
                #       - upstream assignee does not exist: not called
                (45, None),
                #       - upstream assignee is an empty list: not called
                (46, None),
                #    - downstream assignee is owner
                #       - upstream assignee exists and assignments are different: not called
                (51, None),
                #       - upstream assignee exists and assignments are different: not called
                (52, None),
                #       - upstream assignee exists and assignments are different: not called
                (53, None),
                #       - upstream assignee has a fullname of None: not called
                (54, None),
                #       - upstream assignee does not exist: not called
                (55, None),
                #       - upstream assignee is an empty list: not called
                (56, None),
                #    - downstream assignee does not exist
                #       - upstream assignee exists: called with remove_all=False
                (61, False),
                #       - upstream assignee exists: called with remove_all=False
                (62, False),
                #       - upstream assignee exists: called with remove_all=False
                (63, False),
                #       - upstream assignee has a fullname of None: called with remove_all=False
                (64, False),
                #       - upstream assignee does not exist: called with remove_all=False
                (65, False),
                #       - upstream assignee is an empty list: called with remove_all=False
                (66, False),
            )
        )
        match = "Erik"
        owner = self.mock_issue.downstream["owner"]
        for overwrite in (True, False):
            for ds in (match, owner, None):
                if ds is None:
                    delattr(self.mock_downstream.fields.assignee, "displayName")
                    delattr(self.mock_downstream.fields.assignee, "name")
                else:
                    setattr(self.mock_downstream.fields.assignee, "displayName", ds)
                    setattr(self.mock_downstream.fields.assignee, "name", ds)

                for us in (
                    [{"fullname": match}],
                    [{"fullname": "Èŕìḱ"}],
                    [{"fullname": "Bob"}],
                    [{"fullname": None}],
                    None,
                    [],
                ):
                    self.mock_issue.assignee = us
                    scenario, expected_result = next(expected_results)

                    d._update_assignee(
                        client=mock_client,
                        existing=self.mock_downstream,
                        issue=self.mock_issue,
                        overwrite=overwrite,
                    )

                    # Check that the call was made correctly
                    try:
                        if expected_result is None:
                            mock_assign_user.assert_not_called()
                        else:
                            mock_assign_user.assert_called_with(
                                mock_client,
                                self.mock_issue,
                                self.mock_downstream,
                                remove_all=expected_result,
                            )
                    except AssertionError as e:
                        raise AssertionError(f"Failed scenario {scenario}: {e}")
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
        mock_comment = {
            "id": "12345",
            "date_created": d.UPDATE_DATE,
        }
        mock_jira_comment_nm1 = MagicMock()
        mock_jira_comment_nm1.raw = {"body": "mock_legacy_comment_body_non-match-1"}
        mock_jira_comment_match = MagicMock()
        mock_jira_comment_match.raw = {"body": "mock_legacy_comment_body"}
        mock_jira_comment_nm2 = MagicMock()
        mock_jira_comment_nm2.raw = {"body": "mock_legacy_comment_body_non-match-2"}

        # Call the function
        response = d._find_comment_in_jira(
            mock_comment,
            [mock_jira_comment_nm1, mock_jira_comment_match, mock_jira_comment_nm2],
        )
        self.assertEqual(response, mock_jira_comment_match)

    @mock.patch(PATH + "_comment_format")
    @mock.patch(PATH + "_comment_format_legacy")
    def test_find_comment_in_jira_id_update(
        self, mock_comment_format_legacy, mock_comment_format
    ):
        """
        This function tests '_find_comment_in_jira' where we match an ID
        """
        # Set up return values
        mock_comment_format.return_value = "mock_comment_body"
        mock_comment_format_legacy.return_value = "mock_legacy_comment_body"
        mock_comment = {
            "id": "12345",
            "date_created": d.UPDATE_DATE,
        }
        mock_jira_comment_nm1 = MagicMock()
        mock_jira_comment_nm1.raw = {"body": "1234_X"}
        mock_jira_comment_match = MagicMock()
        mock_jira_comment_match.raw = {"body": "12345"}
        mock_jira_comment_nm2 = MagicMock()
        mock_jira_comment_nm2.raw = {"body": "1234_Y"}

        # Call the function
        response = d._find_comment_in_jira(
            mock_comment,
            [mock_jira_comment_nm1, mock_jira_comment_match, mock_jira_comment_nm2],
        )
        self.assertEqual(response, mock_jira_comment_match)

        # Assert everything was (not) called correctly
        mock_jira_comment_nm1.update.assert_not_called()
        mock_jira_comment_match.update.assert_called_with(
            body=mock_comment_format.return_value
        )
        mock_jira_comment_nm2.update.assert_not_called()

    @mock.patch(PATH + "_comment_format")
    @mock.patch(PATH + "_comment_format_legacy")
    def test_find_comment_in_jira_id_no_update(
        self, mock_comment_format_legacy, mock_comment_format
    ):
        """
        This function tests '_find_comment_in_jira' where we match an ID
        """
        # Set up return values
        mock_comment_format.return_value = "mock_comment_body_12345"
        mock_comment_format_legacy.return_value = "mock_legacy_comment_body"
        mock_comment = {
            "id": "12345",
            "date_created": d.UPDATE_DATE,
        }
        mock_jira_comment_nm1 = MagicMock()
        mock_jira_comment_nm1.raw = {"body": "1234_X"}
        mock_jira_comment_match = MagicMock()
        mock_jira_comment_match.raw = {"body": "mock_comment_body_12345"}
        mock_jira_comment_nm2 = MagicMock()
        mock_jira_comment_nm2.raw = {"body": "1234_Y"}

        # Call the function
        response = d._find_comment_in_jira(
            mock_comment,
            [mock_jira_comment_nm1, mock_jira_comment_match, mock_jira_comment_nm2],
        )
        self.assertEqual(response, mock_jira_comment_match)

        # Assert everything was (not) called correctly
        mock_jira_comment_nm1.update.assert_not_called()
        mock_jira_comment_match.update.assert_not_called()
        mock_jira_comment_nm2.update.assert_not_called()

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
            "date_created": d.UPDATE_DATE - timedelta(days=1),
        }

        # Call the function
        response = d._find_comment_in_jira(mock_comment, [mock_jira_comment])
        self.assertEqual(response, mock_comment)

        # Assert everything was (not) called correctly
        mock_comment_format_legacy.assert_not_called()
        mock_comment_format.assert_not_called()

    @mock.patch(PATH + "_comment_format")
    @mock.patch(PATH + "_comment_format_legacy")
    def test_find_comment_in_jira_no_match(
        self, mock_comment_format_legacy, mock_comment_format
    ):
        """
        This function tests '_find_comment_in_jira' where none match
        """
        # Set up return values
        mock_comment_format.return_value = "mock_comment_body"
        mock_comment_format_legacy.return_value = "mock_legacy_comment_body"
        mock_comment = {
            "id": "12345",
            "date_created": d.UPDATE_DATE,
        }
        mock_jira_comment_1 = MagicMock()
        mock_jira_comment_1.raw = {"body": "comment 1"}
        mock_jira_comment_2 = MagicMock()
        mock_jira_comment_2.raw = {"body": "comment 2"}
        mock_jira_comment_3 = MagicMock()
        mock_jira_comment_3.raw = {"body": "comment 3"}

        # Call the function
        response = d._find_comment_in_jira(
            mock_comment,
            [mock_jira_comment_1, mock_jira_comment_2, mock_jira_comment_3],
        )
        self.assertEqual(response, None)

    @mock.patch(PATH + "_comment_format")
    @mock.patch(PATH + "_comment_format_legacy")
    def test_find_comment_in_jira_empty_list(
        self, mock_comment_format_legacy, mock_comment_format
    ):
        """
        This function tests '_find_comment_in_jira' where we pass in an empty list of comments
        """
        # Set up return values
        mock_comment_format.return_value = "mock_comment_body"
        mock_comment_format_legacy.return_value = "mock_legacy_comment_body"
        mock_comment = {
            "id": "12345",
            "date_created": d.UPDATE_DATE,
        }

        # Call the function
        response = d._find_comment_in_jira(mock_comment, [])
        self.assertEqual(response, None)

    def test_check_jira_status_false(self):
        """
        This function tests 'check_jira_status' where we return false
        """
        # Set up mock jira client that raises an exception
        mock_jira_client = MagicMock()
        mock_jira_client.server_info.side_effect = Exception("Connection failed")

        # Call the function
        response = d.check_jira_status(mock_jira_client)

        # Assert everything was called correctly
        self.assertEqual(response, False)

    def test_check_jira_status_true(self):
        """
        This function tests 'check_jira_status' where we return true
        """
        # Set up mock jira client that works normally
        mock_jira_client = MagicMock()
        mock_jira_client.server_info.return_value = {"version": "8.0.0"}

        # Call the function
        response = d.check_jira_status(mock_jira_client)

        # Assert everything was called correctly
        self.assertEqual(response, True)

    def test_update_on_close_update(self):
        """
        This function tests '_update_on_close' where there is an
        "apply_labels" configuration, and labels need to be updated.
        """
        # Set up return values
        self.mock_downstream.fields.description = ""
        updates = [{"on_close": {"apply_labels": ["closed-upstream"]}}]

        # Call the function
        d._update_on_close(self.mock_downstream, updates)

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
        updates = [{"on_close": {"apply_labels": ["tag4"]}}]

        # Call the function
        d._update_on_close(self.mock_downstream, updates)

        # Assert everything was called correctly
        self.mock_downstream.update.assert_not_called()

    def test_update_on_close_no_action(self):
        """
        This function tests '_update_on_close' where there is no
        "apply_labels" configuration.
        """
        # Set up return values
        updates = [{"on_close": {"some_other_action": None}}]

        # Call the function
        d._update_on_close(self.mock_downstream, updates)

        # Assert everything was called correctly
        self.mock_downstream.update.assert_not_called()

    def test_update_on_close_no_config(self):
        """
        This function tests '_update_on_close' where there is no
        configuration for close events.
        """
        # Set up return values
        updates = ["description"]

        # Call the function
        d._update_on_close(self.mock_downstream, updates)

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

    def test_get_field_id_by_name(self):
        """Test _get_field_id_by_name function"""
        # Clear cache first
        d.jira_cache.clear()

        mock_client = MagicMock()
        mock_client.fields.return_value = [
            {"name": "Story Points", "id": "customfield_12345"},
            {"name": "Epic Link", "id": "customfield_67890"},
        ]

        # Test field found - fetches and caches
        result = d._get_field_id_by_name(mock_client, "Story Points")
        self.assertEqual(result, "customfield_12345")
        mock_client.fields.assert_called_once()

        # Test cache - should use cache, not fetch again
        result = d._get_field_id_by_name(mock_client, "Epic Link")
        self.assertEqual(result, "customfield_67890")
        self.assertEqual(mock_client.fields.call_count, 1)

        # Test standard field from cache - should not call fields() again
        result = d._get_field_id_by_name(mock_client, "priority")
        self.assertEqual(result, "priority")
        self.assertEqual(mock_client.fields.call_count, 1)  # Still only called once

        # verify standard fields were seeded in cache
        self.assertEqual(d.field_name_cache.get("priority"), "priority")
        self.assertEqual(d.field_name_cache.get("assignee"), "assignee")
        self.assertEqual(d.field_name_cache.get("summary"), "summary")
        self.assertEqual(d.field_name_cache.get("description"), "description")

        # Test field not found - will fetch again since not in cache
        result = d._get_field_id_by_name(mock_client, "Non Existent Field")
        self.assertIsNone(result)
        self.assertEqual(mock_client.fields.call_count, 2)

    @mock.patch("sync2jira.downstream_issue._get_field_id_by_name")
    def test_resolve_field_identifier(self, mock_get_field_id_by_name):
        """Test _resolve_field_identifier function"""

        mock_client = MagicMock()

        # Test customfield ID - should return as-is
        result = d._resolve_field_identifier(mock_client, "customfield_99999")
        self.assertEqual(result, "customfield_99999")
        mock_get_field_id_by_name.assert_not_called()

        mock_get_field_id_by_name.reset_mock()

        # Test standard field - should return as-is
        mock_get_field_id_by_name.return_value = "priority"
        result = d._resolve_field_identifier(mock_client, "priority")
        self.assertEqual(result, "priority")
        mock_get_field_id_by_name.assert_called_once_with(mock_client, "priority")

        # Test field name - should convert to ID
        mock_get_field_id_by_name.return_value = "customfield_12345"
        result = d._resolve_field_identifier(mock_client, "Story Points")
        self.assertEqual(result, "customfield_12345")
        self.assertEqual(mock_get_field_id_by_name.call_count, 2)
        mock_get_field_id_by_name.assert_any_call(mock_client, "Story Points")

    def test_get_field_id_by_name_exception(self):
        """Test _get_field_id_by_name when client.fields() raises an exception"""
        # Clear cache first
        d.field_name_cache.clear()

        mock_client = MagicMock()
        mock_client.fields.side_effect = Exception("Connection error")

        # Call function
        with self.assertRaises(Exception) as context:
            result = d._get_field_id_by_name(mock_client, "Story Points")

        # Assert
        self.assertEqual(str(context.exception), "Connection error")
        mock_client.fields.assert_called_once()
        expected_cache = {
            "priority": "priority",
            "assignee": "assignee",
            "summary": "summary",
            "description": "description",
        }
        self.assertDictEqual(d.field_name_cache, expected_cache)

    @mock.patch(PATH + "_update_jira_issue")
    @mock.patch(PATH + "attach_link")
    @mock.patch("jira.client.JIRA")
    def test_create_jira_issue_epic_link_field_not_found(
        self, mock_client, mock_attach_link, mock_update_jira_issue
    ):
        """Test _create_jira_issue when Epic Link field cannot be resolved"""
        # Set up return values
        mock_client.create_issue.return_value = self.mock_downstream
        mock_client.fields.return_value = [
            {"name": "QA Contact", "id": "customfield_2"},
            {"name": "EXD-Service", "id": "customfield_3"},
            # Note: Epic Link is NOT in the fields list
        ]

        # Call the function
        response = d._create_jira_issue(
            client=mock_client, issue=self.mock_issue, config=self.mock_config
        )

        # Assert response is the mock downstream issue
        self.assertEqual(response, self.mock_downstream)
        mock_client.create_issue.assert_called_once()

    @mock.patch("jira.client.JIRA")
    def test_update_github_project_fields_storypoints_resolution_failure(
        self, mock_client
    ):
        """Test _update_github_project_fields raises ValueError when storypoints field cannot be resolved"""
        github_project_fields = {"storypoints": {"gh_field": "Estimate"}}
        jira_fields = self.mock_config["sync2jira"]["default_jira_fields"]
        original_storypoints = jira_fields["storypoints"]
        jira_fields["storypoints"] = "Story Points"
        # Set up mock - storypoints field identifier doesn't exist in JIRA
        # Note: The field from default_jira_fields.storypoints doesn't exist
        mock_client.fields.return_value = [{"name": "Priority", "id": "priority"}]

        # Clear cache to force fresh lookup
        d.field_name_cache.clear()

        # Call function - should raise ValueError
        with self.assertRaises(ValueError) as context:
            d._update_github_project_fields(
                mock_client,
                self.mock_downstream,
                self.mock_issue,
                github_project_fields,
                self.mock_config,
            )

        # Assert error message contains diagnostic information
        error_msg = str(context.exception)
        self.assertIn("story points", error_msg.lower())
        self.assertIn("Could not resolve", error_msg)
        # Issue should not be updated
        self.mock_downstream.update.assert_not_called()
        # Restore original config
        self.mock_config["sync2jira"]["default_jira_fields"][
            "storypoints"
        ] = original_storypoints

    @mock.patch(PATH + "_update_jira_issue")
    @mock.patch(PATH + "attach_link")
    @mock.patch(PATH + "change_status")
    @mock.patch("jira.client.JIRA")
    def test_create_jira_issue_with_component_and_labels(
        self, mock_client, mock_change_status, mock_attach_link, mock_update_jira_issue
    ):
        """Test _create_jira_issue with component and labels"""
        # Clear cache first
        d.jira_cache.clear()

        # Set up return values
        mock_client.create_issue.return_value = self.mock_downstream
        mock_client.fields.return_value = [
            {"name": "Epic Link", "id": "customfield_1"},
            {"name": "QA Contact", "id": "customfield_2"},
            {"name": "EXD-Service", "id": "customfield_3"},
        ]

        # Add component and labels to issue
        self.mock_issue.downstream["component"] = "test-component"
        self.mock_issue.downstream["labels"] = ["label1", "label2"]

        # Call the function
        response = d._create_jira_issue(
            client=mock_client, issue=self.mock_issue, config=self.mock_config
        )

        # Assert component and labels are included
        mock_client.create_issue.assert_called_once()
        call_kwargs = mock_client.create_issue.call_args[1]
        self.assertEqual(call_kwargs["components"], [{"name": "test-component"}])
        self.assertEqual(call_kwargs["labels"], ["label1", "label2"])
        self.assertEqual(response, self.mock_downstream)

    @mock.patch(PATH + "_update_jira_issue")
    @mock.patch(PATH + "attach_link")
    @mock.patch(PATH + "change_status")
    @mock.patch("jira.client.JIRA")
    def test_create_jira_issue_with_default_status_and_upstream_id(
        self, mock_client, mock_change_status, mock_attach_link, mock_update_jira_issue
    ):
        """Test _create_jira_issue with default_status and upstream_id comment"""
        # Clear cache first
        d.jira_cache.clear()

        # Set up return values
        mock_client.create_issue.return_value = self.mock_downstream
        mock_client.fields.return_value = [
            {"name": "Epic Link", "id": "customfield_1"},
            {"name": "QA Contact", "id": "customfield_2"},
            {"name": "EXD-Service", "id": "customfield_3"},
        ]

        # Add default_status and upstream_id to issue
        self.mock_issue.downstream["default_status"] = "In Progress"
        self.mock_issue.downstream["issue_updates"].append("upstream_id")
        self.mock_issue.upstream = "github"
        self.mock_issue.upstream_id = "123"

        # Call the function
        response = d._create_jira_issue(
            client=mock_client, issue=self.mock_issue, config=self.mock_config
        )

        # Assert default_status and upstream_id comment are handled
        mock_client.create_issue.assert_called_once()
        mock_change_status.assert_called_once_with(
            mock_client, self.mock_downstream, "In Progress", self.mock_issue
        )
        mock_client.add_comment.assert_called_with(
            self.mock_downstream,
            f"Creating issue for [github-#123|{self.mock_issue.url}]",
        )
        self.assertEqual(response, self.mock_downstream)

    @mock.patch(PATH + "snowflake.connector.connect")
    @mock.patch.dict(
        os.environ,
        {
            "SNOWFLAKE_ACCOUNT": "test_account",
            "SNOWFLAKE_USER": "test_user",
            "SNOWFLAKE_ROLE": "test_role",
            "SNOWFLAKE_PAT": "fake_password",
        },
    )
    def test_execute_snowflake_query_real_connection(self, mock_snowflake_connect):
        """Test execute_snowflake_query function."""
        # Create a mock issue
        mock_issue = MagicMock()
        mock_issue.url = "https://github.com/test/repo/issues/1"
        # Call the function
        result = d.execute_snowflake_query(mock_issue)
        mock_cursor = (
            mock_snowflake_connect.return_value.__enter__.return_value.cursor.return_value
        )
        # Assert the function was called correctly
        mock_snowflake_connect.assert_called_once()
        # Verify password authentication is used
        call_args = mock_snowflake_connect.call_args[1]
        self.assertEqual(call_args["password"], os.getenv("SNOWFLAKE_PAT"))
        self.assertNotIn("authenticator", call_args)
        self.assertNotIn("private_key_file", call_args)
        mock_cursor.fetchall.assert_called_once()
        mock_cursor.close.assert_called_once()
        # Assert the result
        self.assertEqual(result, mock_cursor.fetchall.return_value)

    @mock.patch(PATH + "snowflake.connector.connect")
    @mock.patch.dict(
        os.environ,
        {
            "SNOWFLAKE_ACCOUNT": "test_account",
            "SNOWFLAKE_USER": "test_user",
            "SNOWFLAKE_ROLE": "test_role",
            "SNOWFLAKE_PRIVATE_KEY_FILE": "test_key.pem",
        },
    )
    @mock.patch("os.path.exists")
    def test_execute_snowflake_query_with_jwt_auth(
        self, mock_exists, mock_snowflake_connect
    ):
        """Test execute_snowflake_query with JWT authentication."""
        mock_exists.return_value = True
        # Create a mock issue
        mock_issue = MagicMock()
        mock_issue.url = "https://github.com/test/repo/issues/1"
        # Call the function
        result = d.execute_snowflake_query(mock_issue)
        mock_cursor = (
            mock_snowflake_connect.return_value.__enter__.return_value.cursor.return_value
        )
        # Assert the function was called correctly
        mock_snowflake_connect.assert_called_once()
        # Verify JWT authentication is used
        call_args = mock_snowflake_connect.call_args[1]
        self.assertEqual(call_args["authenticator"], "SNOWFLAKE_JWT")
        self.assertEqual(
            call_args["private_key_file"], os.getenv("SNOWFLAKE_PRIVATE_KEY_FILE")
        )
        self.assertNotIn("password", call_args)
        self.assertNotIn("private_key_file_pwd", call_args)
        mock_cursor.execute.assert_called_once()
        mock_cursor.fetchall.assert_called_once()
        mock_cursor.close.assert_called_once()
        # Assert the result
        self.assertEqual(result, mock_cursor.fetchall.return_value)

    @mock.patch(PATH + "snowflake.connector.connect")
    @mock.patch.dict(
        os.environ,
        {
            "SNOWFLAKE_ACCOUNT": "test_account",
            "SNOWFLAKE_USER": "test_user",
            "SNOWFLAKE_ROLE": "test_role",
            "SNOWFLAKE_PRIVATE_KEY_FILE": "test_key.pem",
            "SNOWFLAKE_PRIVATE_KEY_FILE_PWD": "key_password",
        },
    )
    @mock.patch("os.path.exists")
    def test_execute_snowflake_query_with_jwt_auth_and_password(
        self, mock_exists, mock_snowflake_connect
    ):
        """Test execute_snowflake_query with JWT authentication and key password."""
        mock_exists.return_value = True
        # Create a mock issue
        mock_issue = MagicMock()
        mock_issue.url = "https://github.com/test/repo/issues/1"
        # Call the function
        result = d.execute_snowflake_query(mock_issue)
        mock_cursor = (
            mock_snowflake_connect.return_value.__enter__.return_value.cursor.return_value
        )
        # Assert the function was called correctly
        mock_snowflake_connect.assert_called_once()
        # Verify JWT authentication with password is used
        call_args = mock_snowflake_connect.call_args[1]
        self.assertEqual(call_args["authenticator"], "SNOWFLAKE_JWT")
        self.assertEqual(
            call_args["private_key_file"], os.getenv("SNOWFLAKE_PRIVATE_KEY_FILE")
        )
        self.assertEqual(
            call_args["private_key_file_pwd"],
            os.getenv("SNOWFLAKE_PRIVATE_KEY_FILE_PWD"),
        )
        self.assertNotIn("password", call_args)
        mock_cursor.execute.assert_called_once()
        mock_cursor.fetchall.assert_called_once()
        mock_cursor.close.assert_called_once()
        # Assert the result
        self.assertEqual(result, mock_cursor.fetchall.return_value)

    @mock.patch.dict(os.environ, {}, clear=True)
    def test_execute_snowflake_query_no_credentials(self):
        """Test execute_snowflake_query raises error when no credentials are set."""
        # Create a mock issue
        mock_issue = MagicMock()
        mock_issue.url = "https://github.com/test/repo/issues/1"

        with self.assertRaises(ValueError) as context:
            d.execute_snowflake_query(mock_issue)

        self.assertIn(
            "Either SNOWFLAKE_PRIVATE_KEY_FILE or SNOWFLAKE_PAT must be set",
            str(context.exception),
        )

    def test_UrlCache(self):
        """Test UrlCache class

        Show that, as we add items to the cache, the size of the cache never
        exceeds the maximum, even when it is full; then show that the
        overflow removed items in FIFO order, and that the last-inserted items
        are still in the cache.
        """
        cache = d.UrlCache()
        for i in range(cache.MAX_SIZE * 2):
            self.assertLessEqual(len(cache), cache.MAX_SIZE)
            cache[str(i)] = i
        for i in range(cache.MAX_SIZE):
            self.assertNotIn(str(i), cache)
        for i in range(cache.MAX_SIZE, cache.MAX_SIZE * 2):
            self.assertIn(str(i), cache)

    @mock.patch(PATH + "_update_github_project_fields")
    @mock.patch(PATH + "_update_title")
    @mock.patch(PATH + "_update_description")
    @mock.patch(PATH + "_update_comments")
    @mock.patch(PATH + "_update_tags")
    @mock.patch(PATH + "_update_fixVersion")
    @mock.patch(PATH + "_update_transition")
    @mock.patch(PATH + "_update_assignee")
    @mock.patch(PATH + "_update_on_close")
    @mock.patch("jira.client.JIRA")
    def test_update_jira_issue_github_project_fields_early_exit(
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
        mock_update_github_project_fields,
    ):
        """
        Test '_update_jira_issue' early exit when github_project_fields is not in updates
        or when github_project_fields is empty/None.
        """
        scenarios = (
            # Test case 1: github_project_fields not in updates
            {
                "issue_updates": ["comments", "title"],  # No "github_project_fields"
                "github_project_fields": {"storypoints": {"gh_field": "Estimate"}},
            },
            # Test case 2: github_project_fields is empty dict
            {
                "issue_updates": ["comments", "title", "github_project_fields"],
                "github_project_fields": {},  # Empty dict
            },
            # Test case 3: github_project_fields is None
            {
                "issue_updates": ["comments", "title", "github_project_fields"],
                "github_project_fields": None,
            },
        )

        for s in scenarios:
            self.mock_issue.downstream = s
            d._update_jira_issue(
                existing=self.mock_downstream,
                issue=self.mock_issue,
                client=mock_client,
                config=self.mock_config,
            )
            # Assert _update_github_project_fields was not called
            mock_update_github_project_fields.assert_not_called()
            # Reset mock
            mock_update_github_project_fields.reset_mock()
