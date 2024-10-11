import unittest
import unittest.mock as mock

import sync2jira.intermediary as i

PATH = 'sync2jira.intermediary.'


class TestIntermediary(unittest.TestCase):
    """
    This class tests the downstream_issue.py file under sync2jira
    """
    def setUp(self):
        self.mock_config = {
            'sync2jira': {
                'map': {
                    'github': {
                        'github': {'mock_downstream': 'mock_key'}
                    }
                }
            }
        }

        self.mock_github_issue = {
            'comments': [{
                'author': 'mock_author',
                'name': 'mock_name',
                'body': 'mock_body',
                'id': 'mock_id',
                'date_created': 'mock_date'
            }],
            'title': 'mock_title',
            'html_url': 'mock_url',
            'id': 1234,
            'labels': 'mock_tags',
            'milestone': 'mock_milestone',
            'priority': 'mock_priority',
            'storypoints': '1.0',
            'body': 'mock_content',
            'user': 'mock_reporter',
            'assignees': 'mock_assignee',
            'state': 'open',
            'date_created': 'mock_date',
            'number': '1',
            'storypoints': 'mock_storypoints',
        }

        self.mock_github_pr = {
            'comments': [{
                'author': 'mock_author',
                'name': 'mock_name',
                'body': 'mock_body',
                'id': 'mock_id',
                'date_created': 'mock_date'
            }],
            'title': 'mock_title',
            'html_url': 'mock_url',
            'id': 1234,
            'labels': 'mock_tags',
            'milestone': 'mock_milestone',
            'priority': 'mock_priority',
            'body': 'mock_content',
            'user': {'fullname': 'mock_reporter'},
            'assignee': 'mock_assignee',
            'state': 'open',
            'date_created': 'mock_date',
            'number': 1234,
        }

    def checkResponseFields(self, response):
        self.assertEqual(response.source, 'github')
        self.assertEqual(response.title, '[github] mock_title')
        self.assertEqual(response.url, 'mock_url')
        self.assertEqual(response.upstream, 'github')
        self.assertEqual(response.comments, [{'body': 'mock_body', 'name': 'mock_name', 'author': 'mock_author',
                                              'changed': None, 'date_created': 'mock_date', 'id': 'mock_id'}])
        self.assertEqual(response.content, 'mock_content')
        self.assertEqual(response.reporter, 'mock_reporter')
        self.assertEqual(response.assignee, 'mock_assignee')
        self.assertEqual(response.id, '1234')

    def test_from_github_open(self):
        """
        This tests the 'from_github' function under the Issue class where the state is open
        """
        # Call the function
        response = i.Issue.from_github(
            upstream='github',
            issue=self.mock_github_issue,
            config=self.mock_config
        )

        # Assert that we made the calls correctly
        self.checkResponseFields(response)

        self.assertEqual(response.fixVersion, ['mock_milestone'])
        self.assertEqual(response.priority, 'mock_priority')
        self.assertEqual(response.content, 'mock_content')
        self.assertEqual(response.reporter, 'mock_reporter')
        self.assertEqual(response.assignee, 'mock_assignee')
        self.assertEqual(response.status, 'Open')
        self.assertEqual(response.downstream, {'mock_downstream': 'mock_key'})
        self.assertEqual(response.storypoints, 'mock_storypoints')

    def test_from_github_closed(self):
        """
        This tests the 'from_github' function under the Issue class where the state is closed
        """
        # Set up return values
        self.mock_github_issue['state'] = 'closed'

        # Call the function
        response = i.Issue.from_github(
            upstream='github',
            issue=self.mock_github_issue,
            config=self.mock_config
        )

        # Assert that we made the calls correctly
        self.checkResponseFields(response)

        self.assertEqual(response.tags, 'mock_tags')
        self.assertEqual(response.fixVersion, ['mock_milestone'])
        self.assertEqual(response.priority, 'mock_priority')
        self.assertEqual(response.content, 'mock_content')
        self.assertEqual(response.reporter, 'mock_reporter')
        self.assertEqual(response.assignee, 'mock_assignee')
        self.assertEqual(response.status, 'Closed')
        self.assertEqual(response.downstream, {'mock_downstream': 'mock_key'})
        self.assertEqual(response.storypoints, 'mock_storypoints')

    def test_mapping_github(self):
        """
        This tests the mapping feature from GitHub
        """
        # Set up return values
        self.mock_config['sync2jira']['map']['github']['github'] = {
            'mock_downstream': 'mock_key',
            'mapping': [{'fixVersion': 'Test XXX'}]
        }
        self.mock_github_issue['state'] = 'closed'

        # Call the function
        response = i.Issue.from_github(
            upstream='github',
            issue=self.mock_github_issue,
            config=self.mock_config
        )

        # Assert that we made the calls correctly
        self.checkResponseFields(response)

        self.assertEqual(response.tags, 'mock_tags')
        self.assertEqual(response.fixVersion, ['Test mock_milestone'])
        self.assertEqual(response.priority, 'mock_priority')
        self.assertEqual(response.content, 'mock_content')
        self.assertEqual(response.reporter, 'mock_reporter')
        self.assertEqual(response.assignee, 'mock_assignee')
        self.assertEqual(response.status, 'Closed')
        self.assertEqual(response.downstream, {
            'mock_downstream': 'mock_key',
            'mapping': [{'fixVersion': 'Test XXX'}]})
        self.assertEqual(response.storypoints, 'mock_storypoints')

    @mock.patch(PATH + 'matcher')
    def test_from_github_pr_reopen(self,
                                   mock_matcher):
        """
        This tests the message from GitHub for a PR
        """
        # Set up return values
        mock_matcher.return_value = "JIRA-1234"

        # Call the function
        response = i.PR.from_github(
            upstream='github',
            pr=self.mock_github_pr,
            suffix='reopened',
            config=self.mock_config
        )

        # Assert that we made the calls correctly
        self.checkResponseFields(response)

        self.assertEqual(response.suffix, 'reopened')
        self.assertEqual(response.status, None)
        self.assertEqual(response.downstream, {'mock_downstream': 'mock_key'})
        self.assertEqual(response.jira_key, "JIRA-1234")
        self.mock_github_pr['comments'][0]['changed'] = None
        mock_matcher.assert_called_with(self.mock_github_pr['body'], self.mock_github_pr['comments'])

    def test_matcher(self):
        """ This tests the matcher function """
        # Positive case
        content = "Relates to JIRA: XYZ-5678"
        comments = [{"body": "Relates to JIRA: ABC-1234"}]
        expected = True
        actual = bool(i.matcher(content, comments))
        assert expected == actual

        # Negative case
        content = "No JIRAs here..."
        comments = [{"body": "... nor here"}]
        expected = False
        actual = bool(i.matcher(content, comments))
        assert expected == actual

    # TODO: Add new tests from PR
