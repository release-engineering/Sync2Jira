from copy import deepcopy
import unittest
import unittest.mock as mock
from unittest.mock import MagicMock

import sync2jira.upstream_issue as u

PATH = "sync2jira.upstream_issue."


class TestUpstreamIssue(unittest.TestCase):
    """
    This class tests the upstream_issue.py file under sync2jira
    """

    def setUp(self):
        self.mock_config = {
            "sync2jira": {
                "map": {
                    "github": {"org/repo": {"sync": ["issue"]}},
                },
                "jira": {
                    # Nothing, really..
                },
                "filters": {
                    "github": {
                        "org/repo": {"filter1": "filter1", "labels": ["custom_tag"]}
                    },
                },
                "github_token": "mock_token",
            },
        }

        # Mock GitHub Comment
        self.mock_github_comment = MagicMock()
        self.mock_github_comment.user.name = "mock_username"
        self.mock_github_comment.body = "mock_body"
        self.mock_github_comment.id = "mock_id"
        self.mock_github_comment.created_at = "mock_created_at"

        # Mock GitHub Message
        self.mock_github_message_body = {
            "repository": {"owner": {"login": "org"}, "name": "repo"},
            "issue": {
                "filter1": "filter1",
                "labels": [{"name": "custom_tag"}],
                "comments": ["some_comments!"],
                "number": "mock_number",
                "user": {"login": "mock_login"},
                "assignees": [{"login": "mock_login"}],
                "milestone": {"title": "mock_milestone"},
            },
        }

        # Mock GitHub issue
        self.mock_github_issue = MagicMock()
        self.mock_github_issue.get_comments.return_value = [self.mock_github_comment]

        # Mock GitHub Issue Raw
        self.mock_github_issue_raw = {
            "comments": ["some comment"],
            "number": "1234",
            "user": {"login": "mock_login"},
            "assignees": [{"login": "mock_assignee_login"}],
            "labels": [{"name": "some_label"}],
            "milestone": {"title": "mock_milestone"},
        }

        # Mock GitHub Reporter
        self.mock_github_person = MagicMock()
        self.mock_github_person.name = "mock_name"

        # Mock GitHub Repo
        self.mock_github_repo = MagicMock()
        self.mock_github_repo.get_issue.return_value = self.mock_github_issue

        # Mock GitHub Client
        self.mock_github_client = MagicMock()
        self.mock_github_client.get_repo.return_value = self.mock_github_repo
        self.mock_github_client.get_user.return_value = self.mock_github_person

    @mock.patch("sync2jira.intermediary.Issue.from_github")
    @mock.patch(PATH + "requests.post")
    @mock.patch(PATH + "Github")
    @mock.patch(PATH + "get_all_github_data")
    def test_github_issues(
        self,
        mock_get_all_github_data,
        mock_github,
        mock_requests_post,
        mock_issue_from_github,
    ):
        """
        This function tests 'github_issues' function
        """
        # Set up return values
        mock_github.return_value = self.mock_github_client
        mock_get_all_github_data.return_value = [self.mock_github_issue_raw]
        mock_issue_from_github.return_value = "Successful Call!"
        mock_requests_post.return_value.status_code = 200
        self.mock_config["sync2jira"]["map"]["github"]["org/repo"][
            "github_project_number"
        ] = 1

        # Call the function
        response = list(u.github_issues(upstream="org/repo", config=self.mock_config))

        # Assert that calls were made correctly
        try:
            mock_get_all_github_data.assert_called_with(
                "https://api.github.com/repos/org/repo/issues?labels=custom_tag&filter1=filter1",
                {"Authorization": "token mock_token"},
            )
        except AssertionError:
            mock_get_all_github_data.assert_called_with(
                "https://api.github.com/repos/org/repo/issues?filter1=filter1&labels=custom_tag",
                {"Authorization": "token mock_token"},
            )
        self.mock_github_client.get_user.assert_any_call("mock_login")
        self.mock_github_client.get_user.assert_any_call("mock_assignee_login")
        mock_issue_from_github.assert_called_with(
            "org/repo",
            {
                "labels": ["some_label"],
                "number": "1234",
                "comments": [
                    {
                        "body": "mock_body",
                        "name": unittest.mock.ANY,
                        "author": "mock_username",
                        "changed": None,
                        "date_created": "mock_created_at",
                        "id": "mock_id",
                    }
                ],
                "assignees": [
                    {"login": "mock_assignee_login", "fullname": "mock_name"}
                ],
                "user": {"login": "mock_login", "fullname": "mock_name"},
                "milestone": "mock_milestone",
            },
            self.mock_config,
        )
        self.mock_github_client.get_repo.assert_called_with("org/repo")
        self.mock_github_repo.get_issue.assert_called_with(number="1234")
        self.mock_github_issue.get_comments.assert_any_call()
        self.assertEqual(response[0], "Successful Call!")

    @mock.patch("sync2jira.intermediary.Issue.from_github")
    @mock.patch(PATH + "requests.post")
    @mock.patch(PATH + "Github")
    @mock.patch(PATH + "get_all_github_data")
    def test_github_issues_with_storypoints(
        self,
        mock_get_all_github_data,
        mock_github,
        mock_requests_post,
        mock_issue_from_github,
    ):
        """
        This function tests 'github_issues' function with story points
        """
        self.mock_config["sync2jira"]["map"]["github"]["org/repo"][
            "github_project_number"
        ] = 1
        self.mock_config["sync2jira"]["map"]["github"]["org/repo"]["issue_updates"] = [
            "github_project_fields"
        ]
        self.mock_config["sync2jira"]["map"]["github"]["org/repo"][
            "github_project_fields"
        ] = {
            "storypoints": {"gh_field": "Estimate"},
        }
        # Set up return values
        mock_github.return_value = self.mock_github_client
        mock_get_all_github_data.return_value = [self.mock_github_issue_raw]
        mock_issue_from_github.return_value = "Successful Call!"
        mock_requests_post.return_value.status_code = 200

        mock_requests_post.return_value.json.return_value = {
            "data": {
                "repository": {
                    "issue": {
                        "projectItems": {
                            "nodes": [
                                {
                                    "project": {"title": "Project 1", "number": 1},
                                    "fieldValues": {
                                        "nodes": [
                                            {
                                                "fieldName": {"name": "Estimate"},
                                                "number": 2.0,
                                            }
                                        ]
                                    },
                                },
                                {
                                    "project": {"title": "Project 2", "number": 2},
                                    "fieldValues": {"nodes": []},
                                },
                            ]
                        }
                    }
                }
            }
        }

        # Call the function
        response = list(u.github_issues(upstream="org/repo", config=self.mock_config))

        # Assert that calls were made correctly
        try:
            mock_get_all_github_data.assert_called_with(
                "https://api.github.com/repos/org/repo/issues?labels=custom_tag&filter1=filter1",
                {"Authorization": "token mock_token"},
            )
        except AssertionError:
            mock_get_all_github_data.assert_called_with(
                "https://api.github.com/repos/org/repo/issues?filter1=filter1&labels=custom_tag",
                {"Authorization": "token mock_token"},
            )
        self.mock_github_client.get_user.assert_any_call("mock_login")
        self.mock_github_client.get_user.assert_any_call("mock_assignee_login")
        mock_issue_from_github.assert_called_with(
            "org/repo",
            {
                "labels": ["some_label"],
                "number": "1234",
                "comments": [
                    {
                        "body": "mock_body",
                        "name": unittest.mock.ANY,
                        "author": "mock_username",
                        "changed": None,
                        "date_created": "mock_created_at",
                        "id": "mock_id",
                    }
                ],
                "assignees": [
                    {"login": "mock_assignee_login", "fullname": "mock_name"}
                ],
                "user": {"login": "mock_login", "fullname": "mock_name"},
                "milestone": "mock_milestone",
                "storypoints": 2,
                "priority": None,
            },
            self.mock_config,
        )
        self.mock_github_client.get_repo.assert_called_with("org/repo")
        self.mock_github_repo.get_issue.assert_called_with(number="1234")
        self.mock_github_issue.get_comments.assert_any_call()
        self.assertEqual(response[0], "Successful Call!")

    @mock.patch("sync2jira.intermediary.Issue.from_github")
    @mock.patch(PATH + "requests.post")
    @mock.patch(PATH + "Github")
    @mock.patch(PATH + "get_all_github_data")
    def test_github_issues_with_priority(
        self,
        mock_get_all_github_data,
        mock_github,
        mock_requests_post,
        mock_issue_from_github,
    ):
        """
        This function tests 'github_issues' function with priority
        """
        self.mock_config["sync2jira"]["map"]["github"]["org/repo"][
            "github_project_number"
        ] = 1
        self.mock_config["sync2jira"]["map"]["github"]["org/repo"]["issue_updates"] = [
            "github_project_fields"
        ]
        self.mock_config["sync2jira"]["map"]["github"]["org/repo"][
            "github_project_fields"
        ] = {
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
        # Set up return values
        mock_github.return_value = self.mock_github_client
        mock_get_all_github_data.return_value = [self.mock_github_issue_raw]
        mock_issue_from_github.return_value = "Successful Call!"
        mock_requests_post.return_value.status_code = 200
        self.mock_config["sync2jira"]["map"]["github"]["org/repo"][
            "github_project_number"
        ] = 1

        mock_requests_post.return_value.json.return_value = {
            "data": {
                "repository": {
                    "issue": {
                        "projectItems": {
                            "nodes": [
                                {
                                    "project": {"title": "Project 1", "number": 1},
                                    "fieldValues": {
                                        "nodes": [
                                            {
                                                "fieldName": {"name": "Priority"},
                                                "name": "P1",
                                            }
                                        ]
                                    },
                                },
                                {
                                    "project": {"title": "Project 2", "number": 2},
                                    "fieldValues": {"nodes": []},
                                },
                            ]
                        }
                    }
                }
            }
        }

        # Call the function
        response = list(u.github_issues(upstream="org/repo", config=self.mock_config))

        # Assert that calls were made correctly
        try:
            mock_get_all_github_data.assert_called_with(
                "https://api.github.com/repos/org/repo/issues?labels=custom_tag&filter1=filter1",
                {"Authorization": "token mock_token"},
            )
        except AssertionError:
            mock_get_all_github_data.assert_called_with(
                "https://api.github.com/repos/org/repo/issues?filter1=filter1&labels=custom_tag",
                {"Authorization": "token mock_token"},
            )
        self.mock_github_client.get_user.assert_any_call("mock_login")
        self.mock_github_client.get_user.assert_any_call("mock_assignee_login")
        mock_issue_from_github.assert_called_with(
            "org/repo",
            {
                "labels": ["some_label"],
                "number": "1234",
                "comments": [
                    {
                        "body": "mock_body",
                        "name": unittest.mock.ANY,
                        "author": "mock_username",
                        "changed": None,
                        "date_created": "mock_created_at",
                        "id": "mock_id",
                    }
                ],
                "assignees": [
                    {"login": "mock_assignee_login", "fullname": "mock_name"}
                ],
                "user": {"login": "mock_login", "fullname": "mock_name"},
                "milestone": "mock_milestone",
                "storypoints": None,
                "priority": "P1",
            },
            self.mock_config,
        )
        self.mock_github_client.get_repo.assert_called_with("org/repo")
        self.mock_github_repo.get_issue.assert_called_with(number="1234")
        self.mock_github_issue.get_comments.assert_any_call()
        self.assertEqual(response[0], "Successful Call!")

    @mock.patch("sync2jira.intermediary.Issue.from_github")
    @mock.patch(PATH + "requests.post")
    @mock.patch(PATH + "Github")
    @mock.patch(PATH + "get_all_github_data")
    def test_github_issues_no_token(
        self,
        mock_get_all_github_data,
        mock_github,
        mock_requests_post,
        mock_issue_from_github,
    ):
        """
        This function tests 'github_issues' function where we have no GitHub token
        and no comments
        """
        # Set up return values
        self.mock_config["sync2jira"]["github_token"] = None
        self.mock_github_issue_raw["comments"] = 0
        mock_github.return_value = self.mock_github_client
        mock_get_all_github_data.return_value = [self.mock_github_issue_raw]
        mock_issue_from_github.return_value = "Successful Call!"
        mock_requests_post.return_value.status_code = 200
        self.mock_config["sync2jira"]["map"]["github"]["org/repo"][
            "github_project_number"
        ] = 1

        # Call the function
        response = list(u.github_issues(upstream="org/repo", config=self.mock_config))

        # Assert that calls were made correctly
        try:
            mock_get_all_github_data.assert_called_with(
                "https://api.github.com/repos/org/repo/issues?labels=custom_tag&filter1=filter1",
                {},
            )
        except AssertionError:
            mock_get_all_github_data.assert_called_with(
                "https://api.github.com/repos/org/repo/issues?filter1=filter1&labels=custom_tag",
                {},
            )
        self.mock_github_client.get_user.assert_any_call("mock_login")
        self.mock_github_client.get_user.assert_any_call("mock_assignee_login")
        mock_issue_from_github.assert_called_with(
            "org/repo",
            {
                "labels": ["some_label"],
                "number": "1234",
                "comments": [],
                "assignees": [
                    {"login": "mock_assignee_login", "fullname": "mock_name"}
                ],
                "user": {"login": "mock_login", "fullname": "mock_name"},
                "milestone": "mock_milestone",
            },
            self.mock_config,
        )
        self.assertEqual(response[0], "Successful Call!")
        self.mock_github_client.get_repo.assert_not_called()
        self.mock_github_repo.get_issue.assert_not_called()
        self.mock_github_issue.get_comments.assert_not_called()

    @mock.patch("sync2jira.intermediary.Issue.from_github")
    @mock.patch(PATH + "Github")
    @mock.patch(PATH + "get_all_github_data")
    def test_filter_multiple_labels(
        self, mock_get_all_github_data, mock_github, mock_issue_from_github
    ):
        """
        This function tests 'github_issues' function with a filter including multiple labels
        """
        # Set up return values
        self.mock_config["sync2jira"]["filters"]["github"]["org/repo"]["labels"].extend(
            ["another_tag", "and_another"]
        )
        mock_github.return_value = self.mock_github_client
        mock_issue_from_github.return_value = "Successful Call!"
        # We mutate the issue object so we need to pass a copy here
        mock_get_all_github_data.return_value = [deepcopy(self.mock_github_issue_raw)]

        # Call the function
        list(u.github_issues(upstream="org/repo", config=self.mock_config))

        # Assert that the labels filter is correct
        self.assertIn(
            "labels=custom_tag%2Canother_tag%2Cand_another",
            mock_get_all_github_data.call_args[0][0],
        )
        # Assert the config value was not mutated
        self.assertEqual(
            self.mock_config["sync2jira"]["filters"]["github"]["org/repo"]["labels"],
            ["custom_tag", "another_tag", "and_another"],
        )

        # Restore the return value to the original object
        mock_get_all_github_data.return_value = [deepcopy(self.mock_github_issue_raw)]

        # Call the function again to ensure consistency for subsequent calls
        list(u.github_issues(upstream="org/repo", config=self.mock_config))

        # Assert that the labels filter is correct
        self.assertIn(
            "labels=custom_tag%2Canother_tag%2Cand_another",
            mock_get_all_github_data.call_args[0][0],
        )
        # Assert the config value was not mutated
        self.assertEqual(
            self.mock_config["sync2jira"]["filters"]["github"]["org/repo"]["labels"],
            ["custom_tag", "another_tag", "and_another"],
        )

    @mock.patch(PATH + "Github")
    @mock.patch("sync2jira.intermediary.Issue.from_github")
    def test_handle_github_message_not_in_mapped(
        self, mock_issue_from_github, mock_github
    ):
        """
        This function tests 'handle_github_message' where upstream is not in mapped repos
        """
        # Set up return values
        self.mock_github_message_body["repository"]["owner"]["login"] = "bad_owner"

        # Call the function
        response = u.handle_github_message(
            body=self.mock_github_message_body, config=self.mock_config
        )

        # Assert that all calls were made correctly
        mock_issue_from_github.assert_not_called()
        mock_github.assert_not_called()
        self.assertEqual(None, response)

    @mock.patch(PATH + "Github")
    @mock.patch("sync2jira.intermediary.Issue.from_github")
    def test_handle_github_message_pull_request(
        self, mock_issue_from_github, mock_github
    ):
        """
        This function tests 'handle_github_message' the issue is a pull request comment
        """
        # Set up return values
        self.mock_github_message_body["issue"] = {"pull_request": "test"}

        # Call the function
        response = u.handle_github_message(
            body=self.mock_github_message_body, config=self.mock_config
        )

        # Assert that all calls were made correctly
        mock_issue_from_github.assert_not_called()
        mock_github.assert_not_called()
        self.assertEqual(None, response)

    @mock.patch("sync2jira.intermediary.Issue.from_github")
    def test_handle_github_message_bad_filter(self, mock_issue_from_github):
        """
        This function tests 'handle_github_message' where comparing the actual vs. filter does not equate
        """
        # Set up return values
        self.mock_github_message_body["issue"]["filter1"] = "filter2"

        # Call function
        response = u.handle_github_message(
            body=self.mock_github_message_body, config=self.mock_config
        )
        # Assert that calls were made correctly
        mock_issue_from_github.assert_not_called()
        self.assertEqual(None, response)

    @mock.patch("sync2jira.intermediary.Issue.from_github")
    def test_handle_github_message_bad_label(self, mock_issue_from_github):
        """
        This function tests 'handle_github_message' where comparing the actual vs. filter does not equate
        """
        # Set up return values
        self.mock_github_message_body["issue"]["labels"] = [{"name": "bad_label"}]

        # Call function
        response = u.handle_github_message(
            body=self.mock_github_message_body, config=self.mock_config
        )
        # Assert that calls were made correctly
        mock_issue_from_github.assert_not_called()
        self.assertEqual(None, response)

    @mock.patch(PATH + "Github")
    @mock.patch("sync2jira.intermediary.Issue.from_github")
    def test_handle_github_message_no_comments(
        self, mock_issue_from_github, mock_github
    ):
        """
        This function tests 'handle_github_message' where we have no comments
        """
        # Set up return values
        mock_issue_from_github.return_value = "Successful Call!"
        mock_github.return_value = self.mock_github_client
        self.mock_github_message_body["issue"]["comments"] = 0

        # Call function
        response = u.handle_github_message(
            body=self.mock_github_message_body, config=self.mock_config
        )
        # Assert that calls were made correctly
        mock_issue_from_github.assert_called_with(
            "org/repo",
            {
                "labels": ["custom_tag"],
                "number": "mock_number",
                "comments": [],
                "assignees": [{"login": "mock_login", "fullname": "mock_name"}],
                "filter1": "filter1",
                "user": {"login": "mock_login", "fullname": "mock_name"},
                "milestone": "mock_milestone",
            },
            self.mock_config,
        )
        mock_github.assert_called_with("mock_token", retry=5)
        self.assertEqual("Successful Call!", response)
        self.mock_github_client.get_repo.assert_not_called()
        self.mock_github_repo.get_issue.assert_not_called()
        self.mock_github_issue.get_comments.assert_not_called()
        self.mock_github_client.get_user.assert_called_with("mock_login")

    @mock.patch(PATH + "Github")
    @mock.patch("sync2jira.intermediary.Issue.from_github")
    def test_handle_github_message_successful(
        self, mock_issue_from_github, mock_github
    ):
        """
        This function tests 'handle_github_message' where everything goes smoothly!
        """
        # Set up return values
        mock_issue_from_github.return_value = "Successful Call!"
        mock_github.return_value = self.mock_github_client

        # Call function
        response = u.handle_github_message(
            body=self.mock_github_message_body, config=self.mock_config
        )

        # Assert that calls were made correctly
        mock_issue_from_github.assert_called_with(
            "org/repo",
            {
                "labels": ["custom_tag"],
                "number": "mock_number",
                "comments": [
                    {
                        "body": "mock_body",
                        "name": unittest.mock.ANY,
                        "author": "mock_username",
                        "changed": None,
                        "date_created": "mock_created_at",
                        "id": "mock_id",
                    }
                ],
                "assignees": [{"login": "mock_login", "fullname": "mock_name"}],
                "filter1": "filter1",
                "user": {"login": "mock_login", "fullname": "mock_name"},
                "milestone": "mock_milestone",
            },
            self.mock_config,
        )
        mock_github.assert_called_with("mock_token", retry=5)
        self.assertEqual("Successful Call!", response)
        self.mock_github_client.get_repo.assert_called_with("org/repo")
        self.mock_github_repo.get_issue.assert_called_with(number="mock_number")
        self.mock_github_issue.get_comments.assert_any_call()
        self.mock_github_client.get_user.assert_called_with("mock_login")

    @mock.patch(PATH + "api_call_get")
    @mock.patch(PATH + "_github_link_field_to_dict")
    def test_get_all_github_data(
        self, mock_github_link_field_to_dict, mock_api_call_get
    ):
        """
        This tests the '_get_all_github_data' function
        """
        # Set up return values
        get_return = MagicMock()
        get_return.json.return_value = [{"comments_url": "mock_comments_url"}]
        get_return.headers = {"link": "mock_link"}
        mock_api_call_get.return_value = get_return

        # Call the function
        response = list(u.get_all_github_data(url="mock_url", headers="mock_headers"))

        # Assert everything was called correctly
        mock_api_call_get.assert_any_call("mock_url", headers="mock_headers")
        mock_api_call_get.assert_any_call("mock_comments_url", headers="mock_headers")
        mock_github_link_field_to_dict.assert_called_with("mock_link")
        self.assertEqual("mock_comments_url", response[0]["comments_url"])

    @mock.patch(PATH + "requests")
    def test_api_call_get_error(self, mock_requests):
        """
        Tests the 'api_call_get' function where we raise an IOError
        """
        # Set up return values
        get_return = MagicMock()
        get_return.__bool__ = mock.Mock(return_value=False)
        get_return.__nonzero__ = get_return.__bool__
        get_return.json.side_effect = Exception()
        get_return.text.return_value = {"issues": [{"assignee": "mock_assignee"}]}
        mock_requests.get.return_value = get_return

        # Call the function
        with self.assertRaises(IOError):
            u.api_call_get(url="mock_url", headers="mock_headers")

        # Assert everything was called correctly
        mock_requests.get.assert_called_with("mock_url", headers="mock_headers")

    @mock.patch(PATH + "requests")
    def test_api_call_get(self, mock_requests):
        """
        Tests the 'api_call_get' function where everything goes smoothly!
        """
        # Set up return values
        get_return = MagicMock()
        get_return.__bool__ = mock.Mock(return_value=True)
        get_return.__nonzero__ = get_return.__bool__
        mock_requests.get.return_value = get_return

        # Call the function

        response = u.api_call_get(url="mock_url", headers="mock_headers")

    def test_get_current_project_node(self):
        """This function tests '_get_current_project_node' in a matrix of cases.

        It tests issues with zero, one, and two associated projects when the
        call is made with no configured project, with a project which matches
        none of the associated projects, and with a project which matches one.
        """
        nodes = [
            {"project": {"number": 1, "url": "url1", "title": "title1"}},
            {"project": {"number": 2, "url": "url2", "title": "title2"}},
        ]
        projects = [None, 2, 5]

        for project in projects:
            for node_count in range(len(nodes) + 1):
                gh_issue = {"projectItems": {"nodes": nodes[:node_count]}}
                result = u._get_current_project_node(
                    "org/repo", project, "mock_number", gh_issue
                )
                expected_result = (
                    None
                    if node_count == 0
                    else (
                        (nodes[0] if project is None else None)
                        if node_count == 1
                        else nodes[1] if project == 2 else None
                    )
                )
                self.assertEqual(result, expected_result)

    @mock.patch(PATH + "requests.post")
    def test_add_project_values_early_exit(self, mock_requests_post):
        """
        Test 'add_project_values' early exit when github_project_fields is None/empty
        or when github_project_fields is not in issue_updates.
        """
        # Set up base config
        upstream_config = {
            "issue_updates": ["comments", "title"],
            "github_project_number": 1,
        }
        self.mock_config["sync2jira"]["map"]["github"]["org/repo"] = upstream_config

        mock_issue = {
            "number": 1234,
            "storypoints": None,
            "priority": None,
        }

        scenarios = (
            # Test case 1: github_project_fields is None
            (None, ["github_project_fields"]),
            # Test case 2: github_project_fields is empty dict
            ({}, ["github_project_fields"]),
            # Test case 3: "github_project_fields" not in issue_updates
            ({"storypoints": {"gh_field": "Estimate"}}, []),
        )
        for gpf, iu in scenarios:
            upstream_config["github_project_fields"] = gpf
            upstream_config["issue_updates"] = ["comments", "title"] + iu
            result = u.add_project_values(
                issue=mock_issue,
                upstream="org/repo",
                headers={},
                config=self.mock_config,
            )
            # Assert requests.post was not called (early exit occurred)
            mock_requests_post.assert_not_called()
            self.assertIsNone(result)
            # Reset mock
            mock_requests_post.reset_mock()

    def test_passes_github_filters(self):
        """
        Test passes_github_filters for labels, milestone, and other fields.
        Tests all filtering conditions in one test case.
        """
        upstream = "org/repo"
        self.mock_config["sync2jira"]["filters"]["github"][upstream] = {
            "filter1": "filter1",
            "labels": ["custom_tag"],
            "milestone": 1
        }

        # Test 1: Bad label - should return False
        item = {
            "labels": [{"name": "bad_label"}],
            "milestone": {"number": 1},
            "filter1": "filter1",
        }
        self.assertFalse(
            u.passes_github_filters(item, self.mock_config, upstream, item_type="issue")
        )

        # Test 2: Bad milestone - should return False
        item = {
            "labels": [{"name": "custom_tag"}],
            "milestone": {"number": 456},
            "filter1": "filter1",
        }
        self.assertFalse(
            u.passes_github_filters(item, self.mock_config, upstream, item_type="issue")
        )

        # Test 3: Bad other field (filter1) - should return False
        item = {
            "labels": [{"name": "custom_tag"}],
            "milestone": {"number": 1},
            "filter1": "filter2",
        }
        self.assertFalse(
            u.passes_github_filters(item, self.mock_config, upstream, item_type="issue")
        )

        # Test 4: All filters pass - should return True
        item = {
            "labels": [{"name": "custom_tag"}],
            "milestone": {"number": 1},
            "filter1": "filter1",
        }
        self.assertTrue(
            u.passes_github_filters(item, self.mock_config, upstream, item_type="issue")
        )

        # Test 5: Config specifies only labels; item has matching label (wrong milestone/filter1 ignored) → True
        self.mock_config["sync2jira"]["filters"]["github"][upstream] = {"labels": ["custom_tag"]}
        item = {
            "labels": [{"name": "custom_tag"}],
            "milestone": {"number": 999},
            "filter1": "wrong",
        }
        self.assertTrue(
            u.passes_github_filters(item, self.mock_config, upstream, item_type="issue")
        )

        # Test 6: Config specifies only milestone; item has matching milestone (wrong label/filter1 ignored) → True
        self.mock_config["sync2jira"]["filters"]["github"][upstream] = {"milestone": 1}
        item = {
            "labels": [{"name": "bad_label"}],
            "milestone": {"number": 1},
            "filter1": "wrong",
        }
        self.assertTrue(
            u.passes_github_filters(item, self.mock_config, upstream, item_type="issue")
        )
        
        # Test 7: Config specifies only filter1; item has matching filter1 (wrong label/milestone ignored) → True
        self.mock_config["sync2jira"]["filters"]["github"][upstream] = {"filter1": "filter1"}
        item = {
            "labels": [{"name": "bad_label"}],
            "milestone": {"number": 999},
            "filter1": "filter1",
        }
        self.assertTrue(
            u.passes_github_filters(item, self.mock_config, upstream, item_type="issue")
        )