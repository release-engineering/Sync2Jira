import unittest
import unittest.mock as mock

import sync2jira.intermediary as i

PATH = "sync2jira.intermediary."


class TestIntermediary(unittest.TestCase):
    """
    This class tests the downstream_issue.py file under sync2jira
    """

    def setUp(self):
        self.mock_config = {
            "sync2jira": {
                "pagure_url": "dummy_pagure_url",
                "map": {
                    "pagure": {"pagure": {"mock_downstream": "mock_key"}},
                    "github": {"github": {"mock_downstream": "mock_key"}},
                },
            }
        }
        self.mock_pagure_issue = {
            "comments": [
                {
                    "date_created": "1234",
                    "user": {"name": "mock_name"},
                    "comment": "mock_body",
                    "id": "1234",
                }
            ],
            "title": "mock_title",
            "id": 1234,
            "tags": "mock_tags",
            "milestone": "mock_milestone",
            "priority": "mock_priority",
            "content": "mock_content",
            "user": "mock_reporter",
            "assignee": "mock_assignee",
            "status": "mock_status",
            "date_created": "mock_date",
        }

        self.mock_github_issue = {
            "comments": [
                {
                    "author": "mock_author",
                    "name": "mock_name",
                    "body": "mock_body",
                    "id": "mock_id",
                    "date_created": "mock_date",
                }
            ],
            "title": "mock_title",
            "html_url": "mock_url",
            "id": 1234,
            "labels": "mock_tags",
            "milestone": "mock_milestone",
            "priority": "mock_priority",
            "body": "mock_content",
            "user": "mock_reporter",
            "assignees": "mock_assignee",
            "state": "open",
            "date_created": "mock_date",
            "number": "1",
            "storypoints": "mock_storypoints",
        }

        self.mock_github_pr = {
            "comments": [
                {
                    "author": "mock_author",
                    "name": "mock_name",
                    "body": "mock_body",
                    "id": "mock_id",
                    "date_created": "mock_date",
                }
            ],
            "title": "mock_title",
            "html_url": "mock_url",
            "id": 1234,
            "labels": "mock_tags",
            "milestone": "mock_milestone",
            "priority": "mock_priority",
            "body": "mock_content",
            "user": {"fullname": "mock_reporter"},
            "assignee": "mock_assignee",
            "state": "open",
            "date_created": "mock_date",
            "number": 1234,
        }

        self.mock_pagure_pr = {
            "comments": [
                {
                    "date_created": "1234",
                    "user": {"name": "mock_name"},
                    "comment": "mock_body",
                    "id": "1234",
                }
            ],
            "title": "mock_title",
            "id": 1234,
            "tags": "mock_tags",
            "milestone": "mock_milestone",
            "priority": "mock_priority",
            "content": "mock_content",
            "user": {"fullname": "mock_reporter"},
            "assignee": "mock_assignee",
            "status": "mock_status",
            "date_created": "mock_date",
            "project": {"name": "mock_project_name"},
            "initial_comment": "mock_content_initial",
        }

    def checkResponseFields(self, response):
        self.assertEqual(response.source, "github")
        self.assertEqual(response.title, "[github] mock_title")
        self.assertEqual(response.url, "mock_url")
        self.assertEqual(response.upstream, "github")
        self.assertEqual(
            response.comments,
            [
                {
                    "body": "mock_body",
                    "name": "mock_name",
                    "author": "mock_author",
                    "changed": None,
                    "date_created": "mock_date",
                    "id": "mock_id",
                }
            ],
        )
        self.assertEqual(response.content, "mock_content")
        self.assertEqual(response.reporter, "mock_reporter")
        self.assertEqual(response.assignee, "mock_assignee")
        self.assertEqual(response.id, "1234")

    @mock.patch(PATH + "datetime")
    def test_from_pagure(self, mock_datetime):
        """
        This tests the 'from_pagure' function under the Issue class
        """
        # Set up return values
        mock_datetime.fromtimestamp.return_value = "mock_date"

        # Call the function
        response = i.Issue.from_pagure(
            upstream="pagure", issue=self.mock_pagure_issue, config=self.mock_config
        )

        # Assert that we made the calls correctly
        self.assertEqual(response.source, "pagure")
        self.assertEqual(response.title, "[pagure] mock_title")
        self.assertEqual(response.url, "dummy_pagure_url/pagure/issue/1234")
        self.assertEqual(response.upstream, "pagure")
        self.assertEqual(
            response.comments,
            [
                {
                    "body": "mock_body",
                    "name": "mock_name",
                    "author": "mock_name",
                    "changed": None,
                    "date_created": "mock_date",
                    "id": "1234",
                }
            ],
        )
        self.assertEqual(response.tags, "mock_tags")
        self.assertEqual(response.fixVersion, ["mock_milestone"])
        self.assertEqual(response.priority, "mock_priority")
        self.assertEqual(response.content, "mock_content")
        self.assertEqual(response.reporter, "mock_reporter")
        self.assertEqual(response.assignee, "mock_assignee")
        self.assertEqual(response.status, "mock_status")
        self.assertEqual(response.id, "1234")
        self.assertEqual(response.downstream, {"mock_downstream": "mock_key"})

    def test_from_github_open(self):
        """
        This tests the 'from_github' function under the Issue class where the state is open
        """
        # Call the function
        response = i.Issue.from_github(
            upstream="github", issue=self.mock_github_issue, config=self.mock_config
        )

        # Assert that we made the calls correctly
        self.checkResponseFields(response)

        self.assertEqual(response.fixVersion, ["mock_milestone"])
        self.assertEqual(response.priority, "mock_priority")
        self.assertEqual(response.status, "Open")
        self.assertEqual(response.downstream, {"mock_downstream": "mock_key"})
        self.assertEqual(response.storypoints, "mock_storypoints")

    def test_from_github_open_without_priority(self):
        """
        This tests the 'from_github' function under the Issue class
        where the state is open but the priority is not initialized.
        """
        mock_github_issue = {
            "comments": [
                {
                    "author": "mock_author",
                    "name": "mock_name",
                    "body": "mock_body",
                    "id": "mock_id",
                    "date_created": "mock_date",
                }
            ],
            "title": "mock_title",
            "html_url": "mock_url",
            "id": 1234,
            "labels": "mock_tags",
            "milestone": "mock_milestone",
            "body": "mock_content",
            "user": "mock_reporter",
            "assignees": "mock_assignee",
            "state": "open",
            "date_created": "mock_date",
            "number": "1",
            "storypoints": "mock_storypoints",
        }

        # Call the function
        response = i.Issue.from_github(
            upstream="github", issue=mock_github_issue, config=self.mock_config
        )

        # Assert that we made the calls correctly
        self.checkResponseFields(response)

        self.assertEqual(response.priority, None)
        self.assertEqual(response.status, "Open")

    def test_from_github_closed(self):
        """
        This tests the 'from_github' function under the Issue class where the state is closed
        """
        # Set up return values
        self.mock_github_issue["state"] = "closed"

        # Call the function
        response = i.Issue.from_github(
            upstream="github", issue=self.mock_github_issue, config=self.mock_config
        )

        # Assert that we made the calls correctly
        self.checkResponseFields(response)

        self.assertEqual(response.tags, "mock_tags")
        self.assertEqual(response.fixVersion, ["mock_milestone"])
        self.assertEqual(response.priority, "mock_priority")
        self.assertEqual(response.status, "Closed")
        self.assertEqual(response.downstream, {"mock_downstream": "mock_key"})
        self.assertEqual(response.storypoints, "mock_storypoints")

    def test_mapping_github(self):
        """
        This tests the mapping feature from GitHub
        """
        # Set up return values
        self.mock_config["sync2jira"]["map"]["github"]["github"] = {
            "mock_downstream": "mock_key",
            "mapping": [{"fixVersion": "Test XXX"}],
        }
        self.mock_github_issue["state"] = "closed"

        # Call the function
        response = i.Issue.from_github(
            upstream="github", issue=self.mock_github_issue, config=self.mock_config
        )

        # Assert that we made the calls correctly
        self.checkResponseFields(response)

        self.assertEqual(response.tags, "mock_tags")
        self.assertEqual(response.fixVersion, ["Test mock_milestone"])
        self.assertEqual(response.priority, "mock_priority")
        self.assertEqual(response.status, "Closed")
        self.assertEqual(
            response.downstream,
            {"mock_downstream": "mock_key", "mapping": [{"fixVersion": "Test XXX"}]},
        )
        self.assertEqual(response.storypoints, "mock_storypoints")

    @mock.patch(PATH + "datetime")
    def test_mapping_pagure(self, mock_datetime):
        """
        This tests the mapping feature from pagure
        """
        # Set up return values
        mock_datetime.fromtimestamp.return_value = "mock_date"
        self.mock_config["sync2jira"]["map"]["pagure"]["pagure"] = {
            "mock_downstream": "mock_key",
            "mapping": [{"fixVersion": "Test XXX"}],
        }

        # Call the function
        response = i.Issue.from_pagure(
            upstream="pagure", issue=self.mock_pagure_issue, config=self.mock_config
        )

        # Assert that we made the calls correctly
        self.assertEqual(response.source, "pagure")
        self.assertEqual(response.title, "[pagure] mock_title")
        self.assertEqual(response.url, "dummy_pagure_url/pagure/issue/1234")
        self.assertEqual(response.upstream, "pagure")
        self.assertEqual(
            response.comments,
            [
                {
                    "body": "mock_body",
                    "name": "mock_name",
                    "author": "mock_name",
                    "changed": None,
                    "date_created": "mock_date",
                    "id": "1234",
                }
            ],
        )
        self.assertEqual(response.tags, "mock_tags")
        self.assertEqual(response.fixVersion, ["Test mock_milestone"])
        self.assertEqual(response.priority, "mock_priority")
        self.assertEqual(response.content, "mock_content")
        self.assertEqual(response.reporter, "mock_reporter")
        self.assertEqual(response.assignee, "mock_assignee")
        self.assertEqual(response.status, "mock_status")
        self.assertEqual(response.id, "1234")
        self.assertEqual(
            response.downstream,
            {"mock_downstream": "mock_key", "mapping": [{"fixVersion": "Test XXX"}]},
        )

    @mock.patch(PATH + "matcher")
    def test_from_github_pr_reopen(self, mock_matcher):
        """
        This tests the message from GitHub for a PR
        """
        # Set up return values
        mock_matcher.return_value = "JIRA-1234"

        # Call the function
        response = i.PR.from_github(
            upstream="github",
            pr=self.mock_github_pr,
            suffix="reopened",
            config=self.mock_config,
        )

        # Assert that we made the calls correctly
        self.checkResponseFields(response)

        self.assertEqual(response.suffix, "reopened")
        self.assertEqual(response.status, None)
        self.assertEqual(response.downstream, {"mock_downstream": "mock_key"})
        self.assertEqual(response.jira_key, "JIRA-1234")
        self.mock_github_pr["comments"][0]["changed"] = None
        mock_matcher.assert_called_with(
            self.mock_github_pr["body"], self.mock_github_pr["comments"]
        )

    @mock.patch(PATH + "datetime")
    @mock.patch(PATH + "matcher")
    def test_from_pagure_pr_reopen(self, mock_matcher, mock_datetime):
        """
        This tests the from Pagure for a PR
        """
        # Set up return values
        mock_matcher.return_value = "JIRA-1234"
        mock_datetime.fromtimestamp.return_value = "1234"

        # Call the function
        response = i.PR.from_pagure(
            upstream="pagure",
            pr=self.mock_pagure_pr,
            suffix="reopened",
            config=self.mock_config,
        )

        # Assert that we made the calls correctly
        formatted_comments = [
            {
                "author": "mock_name",
                "body": "mock_body",
                "name": "mock_name",
                "id": "1234",
                "date_created": "1234",
                "changed": None,
            }
        ]
        self.assertEqual(response.source, "pagure")
        self.assertEqual(response.title, "[pagure] mock_title")
        self.assertEqual(
            response.url, "https://pagure.io/mock_project_name/pull-request/1234"
        )
        self.assertEqual(response.upstream, "pagure")
        self.assertEqual(response.comments, formatted_comments)
        self.assertEqual(response.priority, None)
        self.assertEqual(response.content, "mock_content_initial")
        self.assertEqual(response.reporter, "mock_reporter")
        self.assertEqual(response.assignee, "mock_assignee")
        self.assertEqual(response.status, "mock_status")
        self.assertEqual(response.id, "1234")
        self.assertEqual(response.suffix, "reopened")
        self.assertEqual(response.downstream, {"mock_downstream": "mock_key"})
        self.assertEqual(response.jira_key, "JIRA-1234")
        self.mock_pagure_pr["comments"][0]["changed"] = None
        mock_datetime.fromtimestamp.assert_called_with(float(1234))
        mock_matcher.assert_called_with(
            self.mock_pagure_pr["initial_comment"], formatted_comments
        )

    def test_matcher(self):
        """This tests the matcher function"""
        # Found in content, no comments
        expected = "XYZ-5678"
        content = f"Relates to JIRA: {expected}"
        comments = []
        actual = i.matcher(content, comments)
        self.assertEqual(expected, actual)

        # Found in comment, no content
        expected = "XYZ-5678"
        content = None
        comments = [{"body": f"Relates to JIRA: {expected}"}]
        actual = i.matcher(content, comments)
        self.assertEqual(expected, actual)

        # Found in content, not spanning comments
        expected = "XYZ-5678"
        content = f"Relates to JIRA: {expected}"
        comments = [
            {"body": "ABC-1234"},
            {"body": "JIRA:"},
            {"body": "to"},
            {"body": "Relates"},
        ]
        actual = i.matcher(content, comments)
        self.assertEqual(expected, actual)

        # Found in comment, not contents
        expected = "XYZ-5678"
        content = "Nothing here"
        comments = [
            {"body": "Relates"},
            {"body": f"Relates to JIRA: {expected}"},
            {"body": "stuff"},
        ]
        actual = i.matcher(content, comments)
        self.assertEqual(expected, actual)

        # Overridden in comment
        expected = "XYZ-5678"
        content = "Relates to JIRA: ABC-1234"
        comments = [
            {"body": "Relates"},
            {"body": f"Relates to JIRA: {expected}"},
            {"body": "stuff"},
        ]
        actual = i.matcher(content, comments)
        self.assertEqual(expected, actual)

        # Overridden twice in comments
        expected = "XYZ-5678"
        content = "Relates to JIRA: ABC-1234"
        comments = [
            {"body": "Relates to JIRA: ABC-1235"},
            {"body": f"Relates to JIRA: {expected}"},
            {"body": "stuff"},
        ]
        actual = i.matcher(content, comments)
        self.assertEqual(expected, actual)

        # Funky spacing
        expected = "XYZ-5678"
        content = f"Relates  to  JIRA:   {expected}"
        comments = []
        actual = i.matcher(content, comments)
        self.assertEqual(expected, actual)

        # Funkier spacing
        expected = "XYZ-5678"
        content = f"Relates to JIRA:{expected}"
        comments = []
        actual = i.matcher(content, comments)
        self.assertEqual(expected, actual)

        # Negative case
        content = "No JIRAs here..."
        comments = [{"body": "... nor here"}]
        expected = None
        actual = i.matcher(content, comments)
        self.assertEqual(expected, actual)

    # TODO: Add new tests from PR
