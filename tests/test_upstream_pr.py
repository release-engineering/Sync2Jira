import unittest
import unittest.mock as mock
from unittest.mock import MagicMock

import sync2jira.upstream_pr as u


PATH = 'sync2jira.upstream_pr.'


class TestUpstreamPR(unittest.TestCase):
    """
    This class tests the upstream_pr.py file under sync2jira
    """
    def setUp(self):
        self.mock_config = {
            'sync2jira': {
                'map': {
                    'github': {
                        'org/repo': {'sync': ['pullrequest']},
                    },
                },
                'jira': {
                    # Nothing, really..
                },
                'filters': {
                    'github':
                        {'org/repo': {'filter1': 'filter1', 'labels': 'custom_tag'}},
                },
                'github_token': 'mock_token'
            },
        }

        # Mock Github Comment
        self.mock_github_comment = MagicMock()
        self.mock_github_comment.user.name = 'mock_username'
        self.mock_github_comment.body = 'mock_body'
        self.mock_github_comment.id = 'mock_id'
        self.mock_github_comment.created_at = 'mock_created_at'

        # Mock Github Message
        self.mock_github_message = {
            'msg': {
                'repository': {
                    'owner': {
                        'login': 'org'
                    },
                    'name': 'repo'
                },
                'pull_request': {
                    'filter1': 'filter1',
                    'labels': [{'name': 'custom_tag'}],
                    'comments': ['some_comments!'],
                    'number': 'mock_number',
                    'user': {
                        'login': 'mock_login'
                    },
                    'assignees': [{'login': 'mock_login'}],
                    'milestone': {
                        'title': 'mock_milestone'
                    }
                },
            }
        }

        # Mock GitHub issue
        self.mock_github_pr = MagicMock()
        self.mock_github_pr.get_issue_comments.return_value = [self.mock_github_comment]

        # Mock Github Issue Raw
        self.mock_github_issue_raw = {
            'comments': ['some comment'],
            'number': '1234',
            'user': {
                'login': 'mock_login'
            },
            'assignees': [{'login': 'mock_assignee_login'}],
            'labels': [{'name': 'some_label'}],
            'milestone': {
                'title': 'mock_milestone'
            }
        }

        # Mock GitHub Reporter
        self.mock_github_person = MagicMock()
        self.mock_github_person.name = 'mock_name'

        # Mock GitHub Repo
        self.mock_github_repo = MagicMock()
        self.mock_github_repo.get_pull.return_value = self.mock_github_pr
        self.mock_github_repo.get_issue.return_value = self.mock_github_pr

        # Mock GitHub Client
        self.mock_github_client = MagicMock()
        self.mock_github_client.get_repo.return_value = self.mock_github_repo
        self.mock_github_client.get_user.return_value = self.mock_github_person

    @mock.patch(PATH + 'Github')
    @mock.patch('sync2jira.intermediary.PR.from_github')
    def test_handle_github_message(self,
                                   mock_pr_from_github,
                                   mock_github):
        """
        This function tests 'handle_github_message'
        """
        # Set up return values
        mock_pr_from_github.return_value = "Successful Call!"
        mock_github.return_value = self.mock_github_client

        # Call function
        response = u.handle_github_message(
            msg=self.mock_github_message,
            config=self.mock_config,
            suffix='mock_suffix'
        )

        # Assert that calls were made correctly
        mock_pr_from_github.assert_called_with(
            'org/repo',
            {'filter1': 'filter1', 'labels': ['custom_tag'],
             'comments': [{'author': 'mock_username',
                           'name': unittest.mock.ANY,
                           'body': 'mock_body', 'id': 'mock_id',
                           'date_created': 'mock_created_at',
                           'changed': None}], 'number': 'mock_number',
             'user': {'login': 'mock_login', 'fullname': 'mock_name'},
             'assignees': [{'fullname': 'mock_name'}],
             'milestone': 'mock_milestone'}, 'mock_suffix', self.mock_config)
        mock_github.assert_called_with('mock_token')
        self.assertEqual('Successful Call!', response)
        self.mock_github_client.get_repo.assert_called_with('org/repo')
        self.mock_github_repo.get_pull.assert_called_with(number='mock_number')
        self.mock_github_pr.get_issue_comments.assert_any_call()
        self.mock_github_client.get_user.assert_called_with('mock_login')

    @mock.patch(PATH + 'Github')
    @mock.patch('sync2jira.intermediary.Issue.from_github')
    def test_handle_github_message_not_in_mapped(self,
                                                 mock_issue_from_github,
                                                 mock_github):
        """
        This function tests 'handle_github_message' where upstream is not in mapped repos
        """
        # Set up return values
        self.mock_github_message['msg']['repository']['owner']['login'] = 'bad_owner'

        # Call the function
        response = u.handle_github_message(
            msg=self.mock_github_message,
            config=self.mock_config,
            suffix='mock_suffix'
        )

        # Assert that all calls were made correctly
        mock_issue_from_github.assert_not_called()
        mock_github.assert_not_called()
        self.assertEqual(None, response)

    @mock.patch('sync2jira.intermediary.PR.from_github')
    @mock.patch(PATH + 'Github')
    @mock.patch(PATH + 'u_issue.get_all_github_data')
    def test_github_issues(self,
                           mock_get_all_github_data,
                           mock_github,
                           mock_pr_from_github):
        """
        This function tests 'github_issues' function
        """
        # Set up return values
        mock_github.return_value = self.mock_github_client
        mock_get_all_github_data.return_value = [self.mock_github_issue_raw]
        mock_pr_from_github.return_value = 'Successful Call!'

        # Call the function
        response = list(u.github_prs(
            upstream='org/repo',
            config=self.mock_config
        ))

        # Assert that calls were made correctly
        mock_get_all_github_data.assert_called_with(
            'https://api.github.com/repos/org/repo/pulls?filter1=filter1&labels=custom_tag',
            {'Authorization': 'token mock_token'}
        )
        self.mock_github_client.get_user.assert_any_call('mock_login')
        self.mock_github_client.get_user.assert_any_call('mock_assignee_login')
        mock_pr_from_github.assert_called_with(
            'org/repo',
            {'comments':
                [{'author': 'mock_username', 'name': unittest.mock.ANY,
                    'body': 'mock_body', 'id': 'mock_id',
                    'date_created': 'mock_created_at', 'changed': None}],
             'number': '1234', 'user':
                {'login': 'mock_login', 'fullname': 'mock_name'},
             'assignees': [{'fullname': 'mock_name'}],
             'labels': ['some_label'], 'milestone': 'mock_milestone'},
            'open',
            self.mock_config
        )
        self.mock_github_client.get_repo.assert_called_with('org/repo')
        self.mock_github_repo.get_pull.assert_called_with(number='1234')
        self.mock_github_pr.get_issue_comments.assert_any_call()
        self.assertEqual(response[0], 'Successful Call!')
