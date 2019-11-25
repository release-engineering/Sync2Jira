from nose.tools import eq_
import mock
import unittest

import sync2jira.intermediary as i

PATH = 'sync2jira.intermediary.'

class TestIntermediary(unittest.TestCase):
    """
    This class tests the downstream.py file under sync2jira
    """
    def setUp(self):
        self.mock_config = {
            'sync2jira': {
                'pagure_url': 'dummy_pagure_url',
                'map': {
                    'pagure': {
                        'pagure': {'mock_downstream': 'mock_key'}
                    },
                    'github': {
                        'github': {'mock_downstream': 'mock_key'}
                    }
                }
            }
        }

    @mock.patch(PATH + 'datetime')
    def test_from_pagure(self,
                         mock_datetime):
        """
        This tests the 'from_pagure' function under the Issue class
        """
        # Set up return values
        mock_datetime.fromtimestamp.return_value = 'mock_date'
        mock_issue = {
            'comments': [{
                'date_created': '1234',
                'user': {
                    'name': 'mock_name'
                },
                'comment': 'mock_body',
                'id': '1234',
            }],
            'title': 'mock_title',
            'id': 1234,
            'tags': 'mock_tags',
            'milestone': 'mock_milestone',
            'priority': 'mock_priority',
            'content': 'mock_content',
            'user': 'mock_reporter',
            'assignee': 'mock_assignee',
            'status': 'mock_status',
            'date_created': 'mock_date'
            ''
        }

        # Call the function
        response = i.Issue.from_pagure(
            upstream='pagure',
            issue=mock_issue,
            config=self.mock_config
        )

        # Assert that we made the calls correctly
        self.assertEqual(response.source, 'pagure')
        self.assertEqual(response.title, '[pagure] mock_title')
        self.assertEqual(response.url, 'dummy_pagure_url/pagure/issue/1234')
        self.assertEqual(response.upstream, 'pagure')
        self.assertEqual(response.comments, [{'body': 'mock_body', 'name': 'mock_name',
                                              'author': 'mock_name', 'changed': None,
                                              'date_created': 'mock_date', 'id': '1234'}])
        self.assertEqual(response.tags, 'mock_tags')
        self.assertEqual(response.fixVersion, ['mock_milestone'])
        self.assertEqual(response.priority, 'mock_priority')
        self.assertEqual(response.content, 'mock_content')
        self.assertEqual(response.reporter, 'mock_reporter')
        self.assertEqual(response.assignee, 'mock_assignee')
        self.assertEqual(response.status, 'mock_status')
        self.assertEqual(response.id, 'mock_date')
        self.assertEqual(response.downstream, {'mock_downstream': 'mock_key'})

    def test_from_github_open(self):
        """
        This tests the 'from_github' function under the Issue class where the state is open
        """
        # Set up return values
        mock_issue = {
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
            'user': 'mock_reporter',
            'assignees': 'mock_assignee',
            'state': 'open',
            'date_created': 'mock_date',
            'number': '1',
        }

        # Call the function
        response = i.Issue.from_github(
            upstream='github',
            issue=mock_issue,
            config=self.mock_config
        )

        # Assert that we made the calls correctly
        self.assertEqual(response.source, 'github')
        self.assertEqual(response.title, '[github] mock_title')
        self.assertEqual(response.url, 'mock_url')
        self.assertEqual(response.upstream, 'github')
        self.assertEqual(response.comments, [{'body': 'mock_body', 'name': 'mock_name', 'author': 'mock_author',
                                              'changed': None, 'date_created': 'mock_date', 'id': 'mock_id'}])
        self.assertEqual(response.tags, 'mock_tags')
        self.assertEqual(response.fixVersion, ['mock_milestone'])
        self.assertEqual(response.priority, None)
        self.assertEqual(response.content, 'mock_content')
        self.assertEqual(response.reporter, 'mock_reporter')
        self.assertEqual(response.assignee, 'mock_assignee')
        self.assertEqual(response.status, 'Open')
        self.assertEqual(response.id, '1234')
        self.assertEqual(response.downstream, {'mock_downstream': 'mock_key'})

    def test_from_github_closed(self):
        """
        This tests the 'from_github' function under the Issue class where the state is closed
        """
        # Set up return values
        mock_issue = {
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
            'user': 'mock_reporter',
            'assignees': 'mock_assignee',
            'state': 'closed',
            'date_created': 'mock_date',
            'number': '1',
        }

        # Call the function
        response = i.Issue.from_github(
            upstream='github',
            issue=mock_issue,
            config=self.mock_config
        )

        # Assert that we made the calls correctly
        self.assertEqual(response.source, 'github')
        self.assertEqual(response.title, '[github] mock_title')
        self.assertEqual(response.url, 'mock_url')
        self.assertEqual(response.upstream, 'github')
        self.assertEqual(response.comments, [{'body': 'mock_body', 'name': 'mock_name', 'author': 'mock_author',
                                              'changed': None, 'date_created': 'mock_date', 'id': 'mock_id'}])
        self.assertEqual(response.tags, 'mock_tags')
        self.assertEqual(response.fixVersion, ['mock_milestone'])
        self.assertEqual(response.priority, None)
        self.assertEqual(response.content, 'mock_content')
        self.assertEqual(response.reporter, 'mock_reporter')
        self.assertEqual(response.assignee, 'mock_assignee')
        self.assertEqual(response.status, 'Closed')
        self.assertEqual(response.id, '1234')
        self.assertEqual(response.downstream, {'mock_downstream': 'mock_key'})

    def test_mapping_github(self):
        """
        This tests the mapping feature from github
        """
        # Set up return values
        mock_issue = {
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
            'user': 'mock_reporter',
            'assignees': 'mock_assignee',
            'state': 'closed',
            'date_created': 'mock_date',
            'number': '1',
        }
        self.mock_config['sync2jira']['map']['github']['github'] = {
            'mock_downstream': 'mock_key',
            'mapping': [{'fixVersion': 'Test XXX'}]
        }

        # Call the function
        response = i.Issue.from_github(
            upstream='github',
            issue=mock_issue,
            config=self.mock_config
        )

        # Assert that we made the calls correctly
        self.assertEqual(response.source, 'github')
        self.assertEqual(response.title, '[github] mock_title')
        self.assertEqual(response.url, 'mock_url')
        self.assertEqual(response.upstream, 'github')
        self.assertEqual(response.comments, [{'body': 'mock_body', 'name': 'mock_name', 'author': 'mock_author',
                                              'changed': None, 'date_created': 'mock_date', 'id': 'mock_id'}])
        self.assertEqual(response.tags, 'mock_tags')
        self.assertEqual(response.fixVersion, ['Test mock_milestone'])
        self.assertEqual(response.priority, None)
        self.assertEqual(response.content, 'mock_content')
        self.assertEqual(response.reporter, 'mock_reporter')
        self.assertEqual(response.assignee, 'mock_assignee')
        self.assertEqual(response.status, 'Closed')
        self.assertEqual(response.id, '1234')
        self.assertEqual(response.downstream, {
            'mock_downstream': 'mock_key',
            'mapping': [{'fixVersion': 'Test XXX'}]})

    @mock.patch(PATH + 'datetime')
    def test_mapping_pagure(self,
                            mock_datetime):
        """
        This tests the mapping feature from pagure
        """
        # Set up return values
        mock_datetime.fromtimestamp.return_value = 'mock_date'
        mock_issue = {
            'comments': [{
                'date_created': '1234',
                'user': {
                    'name': 'mock_name'
                },
                'comment': 'mock_body',
                'id': '1234',
            }],
            'title': 'mock_title',
            'id': 1234,
            'tags': 'mock_tags',
            'milestone': 'mock_milestone',
            'priority': 'mock_priority',
            'content': 'mock_content',
            'user': 'mock_reporter',
            'assignee': 'mock_assignee',
            'status': 'mock_status',
            'date_created': 'mock_date'
                            ''
        }
        self.mock_config['sync2jira']['map']['pagure']['pagure'] = {
            'mock_downstream': 'mock_key',
            'mapping': [{'fixVersion': 'Test XXX'}]
        }

        # Call the function
        response = i.Issue.from_pagure(
            upstream='pagure',
            issue=mock_issue,
            config=self.mock_config
        )

        # Assert that we made the calls correctly
        self.assertEqual(response.source, 'pagure')
        self.assertEqual(response.title, '[pagure] mock_title')
        self.assertEqual(response.url, 'dummy_pagure_url/pagure/issue/1234')
        self.assertEqual(response.upstream, 'pagure')
        self.assertEqual(response.comments, [{'body': 'mock_body', 'name': 'mock_name',
                                              'author': 'mock_name', 'changed': None,
                                              'date_created': 'mock_date',
                                              'id': '1234'}])
        self.assertEqual(response.tags, 'mock_tags')
        self.assertEqual(response.fixVersion, ['Test mock_milestone'])
        self.assertEqual(response.priority, 'mock_priority')
        self.assertEqual(response.content, 'mock_content')
        self.assertEqual(response.reporter, 'mock_reporter')
        self.assertEqual(response.assignee, 'mock_assignee')
        self.assertEqual(response.status, 'mock_status')
        self.assertEqual(response.id, 'mock_date')
        self.assertEqual(response.downstream, {
            'mock_downstream': 'mock_key',
            'mapping': [{'fixVersion': 'Test XXX'}]})
