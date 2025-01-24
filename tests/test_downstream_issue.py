from datetime import datetime, timezone
import unittest
import unittest.mock as mock
from unittest.mock import MagicMock

from jira import JIRAError
import jira.client

import sync2jira.downstream_issue as d
from sync2jira.intermediary import Issue

PATH = 'sync2jira.downstream_issue.'


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
            'sync2jira': {
                'default_jira_instance': 'another_jira_instance',
                'jira_username': 'mock_user',
                'default_jira_fields': {'storypoints': 'customfield_12310243'},
                'jira': {
                    'mock_jira_instance': {'mock_jira': 'mock_jira'},
                    'another_jira_instance': {'token_auth': 'mock_token',
                                              'options': {'server': 'mock_server'}}
                },
                'testing': {},
                'legacy_matching': False,
                'admins': [{'mock_admin': 'mock_email'}],
                'develop': False
            },
        }

        # Mock sync2jira.intermediary.Issue
        self.mock_issue = MagicMock()
        self.mock_issue.assignee = [{'fullname': 'mock_user'}]
        self.mock_issue.downstream = {
            'project': 'mock_project',
            'custom_fields': {'somecustumfield': 'somecustumvalue'},
            'qa-contact': 'dummy@dummy.com',
            'epic-link': 'DUMMY-1234',
            'EXD-Service': {'guild': 'EXD-Project', 'value': 'EXD-Value'},
            'issue_updates': [
                'comments',
                {'tags': {'overwrite': False}},
                {'fixVersion': {'overwrite': False}},
                {'assignee': {'overwrite': True}}, 'description', 'title',
                {'transition': 'CUSTOM TRANSITION'},
                {'on_close': {"apply_labels": ["closed-upstream"]}}
            ],
            'owner': 'mock_owner'
        }
        self.mock_issue.content = 'mock_content'
        self.mock_issue.reporter = {'fullname': 'mock_user'}
        self.mock_issue.url = 'mock_url'
        self.mock_issue.title = 'mock_title'
        self.mock_issue.comments = 'mock_comments'
        self.mock_issue.tags = ['tag1', 'tag2']
        self.mock_issue.fixVersion = ['fixVersion3', 'fixVersion4']
        self.mock_issue.fixVersion = ['fixVersion3', 'fixVersion4']
        self.mock_issue.assignee = [{'fullname': 'mock_assignee'}]
        self.mock_issue.status = 'Open'
        self.mock_issue.id = '1234'
        self.mock_issue.storypoints = 2
        self.mock_issue.priority = 'P1'

        # Mock issue updates
        self.mock_updates = [
                'comments',
                {'tags': {'overwrite': False}},
                {'fixVersion': {'overwrite': False}},
                {'assignee': {'overwrite': True}}, 'description', 'title',
                {'transition': 'CUSTOM TRANSITION'},
                {'on_close': {"apply_labels": ["closed-upstream"]}}
            ]

        # Mock Jira transition
        self.mock_transition = [{
            'name': 'custom_closed_status',
            'id': 1234
        }]

        # Mock jira.resources.Issue
        self.mock_downstream = MagicMock()
        self.mock_downstream.id = 1234
        self.mock_downstream.fields.labels = ['tag3', 'tag4']
        mock_version1 = MagicMock()
        mock_version1.name = 'fixVersion3'
        mock_version2 = MagicMock()
        mock_version2.name = 'fixVersion4'
        self.mock_downstream.fields.fixVersions = [mock_version1, mock_version2]
        self.mock_downstream.update.return_value = True
        self.mock_downstream.fields.description = "This is an existing description"

        # Mock datetime.today()
        self.mock_today = MagicMock()
        self.mock_today.strftime.return_value = 'mock_today'

    @mock.patch('jira.client.JIRA')
    def test_get_jira_client_not_issue(self,
                                       mock_client):
        """
        This tests 'get_jira_client' function where the passed in
        argument is not an Issue instance
        """
        # Call the function
        with self.assertRaises(Exception):
            d.get_jira_client(
                issue='string',
                config=self.mock_config
            )

        # Assert everything was called correctly
        mock_client.assert_not_called()

    @mock.patch('jira.client.JIRA')
    def test_get_jira_client_not_instance(self,
                                          mock_client):
        """
        This tests 'get_jira_client' function there is no JIRA instance
        """
        # Set up return values
        self.mock_issue.downstream = {}

        # Call the function
        with self.assertRaises(Exception):
            d.get_jira_client(
                issue=self.mock_issue,
                config=self.mock_config
            )

        # Assert everything was called correctly
        mock_client.assert_not_called()

    @mock.patch('jira.client.JIRA')
    def test_get_jira_client(self,
                             mock_client):
        """
        This tests 'get_jira_client' function where everything goes smoothly
        """
        # Set up return values
        mock_issue = MagicMock(spec=Issue)
        mock_issue.downstream = {'jira_instance': 'mock_jira_instance'}
        mock_client.return_value = 'Successful call!'

        # Call the function

        response = d.get_jira_client(
            issue=mock_issue,
            config=self.mock_config
        )

        # Assert everything was called correctly
        mock_client.assert_called_with(mock_jira='mock_jira')
        self.assertEqual('Successful call!', response)

    @mock.patch('jira.client.JIRA')
    def test_get_existing_legacy(self, client):
        """
        This tests '_get_existing_jira_issue_legacy' function
        """
        class MockIssue(object):
            downstream = {'key': 'value'}
            url = 'wat'
        issue = MockIssue()
        config = self.mock_config
        # Ensure that we get results back from the jira client.
        target1 = "target1"
        client.return_value.search_issues = mock.MagicMock(return_value=[target1])
        result = d._get_existing_jira_issue_legacy(jira.client.JIRA(), issue)
        assert result == target1

        client.return_value.search_issues.assert_called_once_with(
            "'External issue URL'='wat' AND 'key'='value' AND "
            "(resolution is null OR resolution = Duplicate)",
        )

    @mock.patch('jira.client.JIRA')
    def test_get_existing_newstyle(self, client):
        config = self.mock_config

        class MockIssue(object):
            downstream = {'key': 'value'}
            title = 'A title, a title...'
            url = 'http://threebean.org'


        issue = MockIssue()
        mock_results_of_query = MagicMock()
        mock_results_of_query.fields.summary = 'A title, a title...'

        client.return_value.search_issues.return_value = [mock_results_of_query]
        result = d._get_existing_jira_issue(jira.client.JIRA(), issue, config)
        # Ensure that we get the mock_result_of_query as a result
        self.assertEqual(result, mock_results_of_query)

        client.return_value.search_issues.assert_called_once_with(
            'issueFunction in linkedIssuesOfRemote("Upstream issue") and '
            'issueFunction in linkedIssuesOfRemote("http://threebean.org")'
        )

    @mock.patch('jira.client.JIRA')
    def test_upgrade_oldstyle_jira_issue(self, client):
        config = self.mock_config

        class MockIssue(object):
            downstream = {'key': 'value'}
            title = 'A title, a title...'
            url = 'http://threebean.org'

        downstream = mock.MagicMock()
        issue = MockIssue()
        client_obj = mock.MagicMock()
        client.return_value = client_obj
        d._upgrade_jira_issue(jira.client.JIRA(), downstream, issue, config)

        remote = {
            'url': 'http://threebean.org',
            'title': 'Upstream issue',
        }
        client_obj.add_remote_link.assert_called_once_with(downstream.id, remote)


    @mock.patch('jira.client.JIRA')
    def test_assign_user(self, mock_client):
        """
        Test 'assign_user' function where remove_all flag is False
        """
        # Set up return values
        mock_user = MagicMock()
        mock_user.displayName = 'mock_assignee'
        mock_user.key = 'mock_user_key'
        mock_client.search_assignable_users_for_issues.return_value = [mock_user]
        mock_client.assign_issue.return_value = True

        # Call the assign user function
        d.assign_user(
            issue=self.mock_issue,
            downstream=self.mock_downstream,
            client=mock_client
        )

        # Assert that all calls mocked were called properly
        self.mock_downstream.update({'assignee': {'name': 1234}})
        mock_client.search_assignable_users_for_issues.assert_called_with(
            'mock_assignee',
            project='mock_project'
        )

    @mock.patch('jira.client.JIRA')
    def test_assign_user_with_owner(self, mock_client):
        """
        Test 'assign_user' function where remove_all flag is False
        """
        # Set up return values
        mock_user = MagicMock()
        mock_user.displayName = 'mock_assignee'
        mock_user.key = 'mock_user_key'
        mock_client.search_assignable_users_for_issues.return_value = []
        mock_client.assign_issue.return_value = True

        # Call the assign user function
        d.assign_user(
            issue=self.mock_issue,
            downstream=self.mock_downstream,
            client=mock_client
        )

        # Assert that all calls mocked were called properly
        mock_client.assign_issue.assert_called_with(1234, 'mock_owner')
        mock_client.search_assignable_users_for_issues.assert_called_with(
            'mock_assignee',
            project='mock_project'
        )

    @mock.patch('jira.client.JIRA')
    def test_assign_user_without_owner(self, mock_client):
        """
        Test 'assign_user' function where remove_all flag is False
        """
        # Set up return values
        mock_user = MagicMock()
        mock_user.displayName = 'mock_assignee'
        mock_user.key = 'mock_user_key'
        mock_client.search_assignable_users_for_issues.return_value = []
        mock_client.assign_issue.return_value = True
        self.mock_issue.downstream.pop('owner')

        # Call the assign user function
        d.assign_user(
            issue=self.mock_issue,
            downstream=self.mock_downstream,
            client=mock_client
        )

        # Assert that all calls mocked were called properly
        mock_client.assign_issue.assert_not_called()
        mock_client.search_assignable_users_for_issues.assert_called_with(
            'mock_assignee',
            project='mock_project'
        )

    @mock.patch('jira.client.JIRA')
    def test_assign_user_remove_all(self, mock_client):
        """
        Test 'assign_user' function where remove_all flag is True
        """
        # Call the assign user function
        d.assign_user(
            issue=self.mock_issue,
            downstream=self.mock_downstream,
            client=mock_client,
            remove_all=True
        )

        # Assert that all calls mocked were called properly
        self.mock_downstream.update.assert_called_with(assignee={'name': ''})
        mock_client.assign_issue.assert_not_called()
        mock_client.search_assignable_users_for_issues.assert_not_called()

    @mock.patch(PATH + '_update_jira_issue')
    @mock.patch(PATH + 'attach_link')
    @mock.patch('jira.client.JIRA')
    def test_create_jira_issue(self,
                               mock_client,
                               mock_attach_link,
                               mock_update_jira_issue):
        """
        Tests '_create_jira_issue' function
        """
        # Set up return values
        mock_client.create_issue.return_value = self.mock_downstream
        mock_client.fields.return_value = [
            {'name': 'Epic Link', 'id': 'customfield_1'},
            {'name': 'QA Contact', 'id': 'customfield_2'},
            {'name': 'EXD-Service', 'id': 'customfield_3'},
        ]

        # Call the function
        response = d._create_jira_issue(
            client=mock_client,
            issue=self.mock_issue,
            config=self.mock_config
        )

        # Assert everything was called correctly
        mock_client.create_issue.assert_called_with(
            issuetype={'name': 'Bug'},
            project={'key': 'mock_project'},
            somecustumfield='somecustumvalue',
            description='[1234] Upstream Reporter: mock_user\nUpstream issue status: Open\nUpstream description: {quote}mock_content{quote}',
            summary='mock_title'
        )
        mock_attach_link.assert_called_with(
            mock_client,
            self.mock_downstream,
            {
                'url': 'mock_url',
                'title': 'Upstream issue'
            }
        )
        mock_update_jira_issue.assert_called_with(
            self.mock_downstream,
            self.mock_issue,
            mock_client,
            self.mock_config
        )
        self.mock_downstream.update.assert_any_call({'customfield_1': 'DUMMY-1234'})
        self.mock_downstream.update.assert_any_call({'customfield_2': 'dummy@dummy.com'})
        self.mock_downstream.update.assert_any_call(
            {"customfield_3": {"value": "EXD-Project", "child": {"value": "EXD-Value"}}})
        self.assertEqual(response, self.mock_downstream)
        mock_client.add_comment.assert_not_called()

    @mock.patch(PATH + '_update_jira_issue')
    @mock.patch(PATH + 'attach_link')
    @mock.patch('jira.client.JIRA')
    def test_create_jira_issue_failed_epic_link(self,
                                                mock_client,
                                                mock_attach_link,
                                                mock_update_jira_issue):
        """
        Tests '_create_jira_issue' function where we fail updating the epic link
        """
        # Set up return values
        mock_client.create_issue.return_value = self.mock_downstream
        mock_client.fields.return_value = [
            {'name': 'Epic Link', 'id': 'customfield_1'},
            {'name': 'QA Contact', 'id': 'customfield_2'},
            {'name': 'EXD-Service', 'id': 'customfield_3'},
        ]
        self.mock_downstream.update.side_effect = [JIRAError, 'success', 'success']

        # Call the function
        response = d._create_jira_issue(
            client=mock_client,
            issue=self.mock_issue,
            config=self.mock_config
        )

        # Assert everything was called correctly
        mock_client.create_issue.assert_called_with(
            issuetype={'name': 'Bug'},
            project={'key': 'mock_project'},
            somecustumfield='somecustumvalue',
            description='[1234] Upstream Reporter: mock_user\nUpstream issue status: Open\nUpstream description: {quote}mock_content{quote}',
            summary='mock_title'
        )
        mock_attach_link.assert_called_with(
            mock_client,
            self.mock_downstream,
            {
                'url': 'mock_url',
                'title': 'Upstream issue'
            }
        )
        mock_update_jira_issue.assert_called_with(
            self.mock_downstream,
            self.mock_issue,
            mock_client,
            self.mock_config
        )
        self.mock_downstream.update.assert_any_call({'customfield_1': 'DUMMY-1234'})
        self.mock_downstream.update.assert_any_call(
            {'customfield_2': 'dummy@dummy.com'})
        self.mock_downstream.update.assert_any_call(
            {"customfield_3": {"value": "EXD-Project", "child": {"value": "EXD-Value"}}})
        self.assertEqual(response, self.mock_downstream)
        mock_client.add_comment.assert_called_with(self.mock_downstream, f"Error adding Epic-Link: DUMMY-1234")

    @mock.patch(PATH + '_update_jira_issue')
    @mock.patch(PATH + 'attach_link')
    @mock.patch('jira.client.JIRA')
    def test_create_jira_issue_failed_exd_service(self,
                                                  mock_client,
                                                  mock_attach_link,
                                                  mock_update_jira_issue):
        """
        Tests '_create_jira_issue' function where we fail updating the EXD-Service field
        """
        # Set up return values
        mock_client.create_issue.return_value = self.mock_downstream
        mock_client.fields.return_value = [
            {'name': 'Epic Link', 'id': 'customfield_1'},
            {'name': 'QA Contact', 'id': 'customfield_2'},
            {'name': 'EXD-Service', 'id': 'customfield_3'},
        ]
        self.mock_downstream.update.side_effect = ['success', 'success', JIRAError]

        # Call the function
        response = d._create_jira_issue(
            client=mock_client,
            issue=self.mock_issue,
            config=self.mock_config
        )

        # Assert everything was called correctly
        mock_client.create_issue.assert_called_with(
            issuetype={'name': 'Bug'},
            project={'key': 'mock_project'},
            somecustumfield='somecustumvalue',
            description='[1234] Upstream Reporter: mock_user\nUpstream issue status: Open\nUpstream description: {quote}mock_content{quote}',
            summary='mock_title'
        )
        mock_attach_link.assert_called_with(
            mock_client,
            self.mock_downstream,
            {
                'url': 'mock_url',
                'title': 'Upstream issue'
            }
        )
        mock_update_jira_issue.assert_called_with(
            self.mock_downstream,
            self.mock_issue,
            mock_client,
            self.mock_config
        )
        self.mock_downstream.update.assert_any_call({'customfield_1': 'DUMMY-1234'})
        self.mock_downstream.update.assert_any_call(
            {'customfield_2': 'dummy@dummy.com'})
        self.mock_downstream.update.assert_any_call(
            {"customfield_3": {"value": "EXD-Project", "child": {"value": "EXD-Value"}}})
        self.assertEqual(response, self.mock_downstream)
        mock_client.add_comment.assert_called_with(self.mock_downstream,
                                                   f"Error adding EXD-Service field.\n"
                                                   f"Project: {self.mock_issue.downstream['EXD-Service']['guild']}\n"
                                                   f"Value: {self.mock_issue.downstream['EXD-Service']['value']}")

    @mock.patch(PATH + '_update_jira_issue')
    @mock.patch(PATH + 'attach_link')
    @mock.patch('jira.client.JIRA')
    def test_create_jira_issue_no_updates(self,
                                          mock_client,
                                          mock_attach_link,
                                          mock_update_jira_issue):
        """
        Tests '_create_jira_issue' function where we have
        no updates
        """
        # Set up return values
        mock_client.create_issue.return_value = self.mock_downstream
        self.mock_issue.downstream['issue_updates'] = []

        # Call the function
        response = d._create_jira_issue(
            client=mock_client,
            issue=self.mock_issue,
            config=self.mock_config
        )

        # Assert everything was called correctly
        mock_client.create_issue.assert_called_with(
            issuetype={'name': 'Bug'},
            project={'key': 'mock_project'},
            somecustumfield='somecustumvalue',
            description='[1234] Upstream Reporter: mock_user\n',
            summary='mock_title'
        )
        mock_attach_link.assert_called_with(
            mock_client,
            self.mock_downstream,
            {
                'url': 'mock_url',
                'title': 'Upstream issue'
            }
        )
        mock_update_jira_issue.assert_called_with(
            self.mock_downstream,
            self.mock_issue,
            mock_client,
            self.mock_config
        )
        self.assertEqual(response, self.mock_downstream)
        mock_client.add_comment.assert_not_called()


    @mock.patch(PATH + 'get_jira_client')
    @mock.patch(PATH + '_get_existing_jira_issue')
    @mock.patch(PATH + '_update_jira_issue')
    @mock.patch(PATH + '_create_jira_issue')
    @mock.patch('jira.client.JIRA')
    @mock.patch(PATH + '_get_existing_jira_issue_legacy')
    @mock.patch(PATH + 'check_jira_status')
    def test_sync_with_jira_matching(self,
                                     mock_check_jira_status,
                                     mock_existing_jira_issue_legacy,
                                     mock_client,
                                     mock_create_jira_issue,
                                     mock_update_jira_issue,
                                     mock_existing_jira_issue,
                                     mock_get_jira_client):
        """
        Tests 'sync_with_jira' function where we do find a matching issue
        This assumes we're not using the legacy matching anymore
        """
        # Set up return values
        mock_get_jira_client.return_value = mock_client
        mock_existing_jira_issue.return_value = self.mock_downstream
        mock_check_jira_status.return_value = True

        # Call the function
        d.sync_with_jira(
            issue=self.mock_issue,
            config=self.mock_config
        )

        # Assert all calls were made correctly
        mock_get_jira_client.assert_called_with(self.mock_issue, self.mock_config)
        mock_update_jira_issue.assert_called_with(self.mock_downstream, self.mock_issue,
                                                  mock_client, self.mock_config)
        mock_create_jira_issue.assert_not_called()
        mock_existing_jira_issue_legacy.assert_not_called()

    @mock.patch(PATH + 'get_jira_client')
    @mock.patch(PATH + '_get_existing_jira_issue')
    @mock.patch(PATH + '_update_jira_issue')
    @mock.patch(PATH + '_create_jira_issue')
    @mock.patch('jira.client.JIRA')
    @mock.patch(PATH + '_get_existing_jira_issue_legacy')
    @mock.patch(PATH + 'check_jira_status')
    def test_sync_with_jira_down(self,
                                 mock_check_jira_status,
                                 mock_existing_jira_issue_legacy,
                                 mock_client,
                                 mock_create_jira_issue,
                                 mock_update_jira_issue,
                                 mock_existing_jira_issue,
                                 mock_get_jira_client):
        """
        Tests 'sync_with_jira' function where the JIRA scriptrunner is down
        """
        # Set up return values
        mock_get_jira_client.return_value = mock_client
        mock_existing_jira_issue.return_value = self.mock_downstream
        mock_check_jira_status.return_value = False

        # Call the function
        with self.assertRaises(JIRAError):
            d.sync_with_jira(
                issue=self.mock_issue,
                config=self.mock_config
            )

        # Assert all calls were made correctly
        mock_get_jira_client.assert_called_with(self.mock_issue, self.mock_config)
        mock_update_jira_issue.assert_not_called()
        mock_create_jira_issue.assert_not_called()
        mock_existing_jira_issue_legacy.assert_not_called()

    @mock.patch(PATH + 'get_jira_client')
    @mock.patch(PATH + '_get_existing_jira_issue')
    @mock.patch(PATH + '_update_jira_issue')
    @mock.patch(PATH + '_create_jira_issue')
    @mock.patch('jira.client.JIRA')
    @mock.patch(PATH + '_get_existing_jira_issue_legacy')
    @mock.patch(PATH + 'check_jira_status')
    def test_sync_with_jira_no_matching(self,
                                        mock_check_jira_status,
                                        mock_existing_jira_issue_legacy,
                                        mock_client,
                                        mock_create_jira_issue,
                                        mock_update_jira_issue,
                                        mock_existing_jira_issue,
                                        mock_get_jira_client):
        """
        Tests 'sync_with_jira' function where we do NOT find a matching issue
        This assumes we're not using the legacy matching anymore
        """
        # Set up return values
        mock_get_jira_client.return_value = mock_client
        mock_existing_jira_issue.return_value = None
        mock_check_jira_status.return_value = True

        # Call the function
        d.sync_with_jira(
            issue=self.mock_issue,
            config=self.mock_config
        )

        # Assert all calls were made correctly
        mock_get_jira_client.assert_called_with(self.mock_issue, self.mock_config)
        mock_update_jira_issue.assert_not_called()
        mock_create_jira_issue.assert_called_with(mock_client, self.mock_issue, self.mock_config)
        mock_existing_jira_issue_legacy.assert_not_called()

    @mock.patch(PATH + '_update_title')
    @mock.patch(PATH + '_update_description')
    @mock.patch(PATH + '_update_comments')
    @mock.patch(PATH + '_update_tags')
    @mock.patch(PATH + '_update_fixVersion')
    @mock.patch(PATH + '_update_transition')
    @mock.patch(PATH + '_update_assignee')
    @mock.patch(PATH + '_update_on_close')
    @mock.patch('jira.client.JIRA')
    def test_update_jira_issue(self,
                               mock_client,
                               mock_update_on_close,
                               mock_update_assignee,
                               mock_update_transition,
                               mock_update_fixVersion,
                               mock_update_tags,
                               mock_update_comments,
                               mock_update_description,
                               mock_update_title):
        """
        This tests '_update_jira_issue' function
        """
        # Call the function
        d._update_jira_issue(
            existing=self.mock_downstream,
            issue=self.mock_issue,
            client=mock_client,
            config=self.mock_config
        )

        # Assert all calls were made correctly
        mock_update_comments.assert_called_with(
            mock_client,
            self.mock_downstream,
            self.mock_issue
        )
        mock_update_tags.assert_called_with(
            self.mock_updates,
            self.mock_downstream,
            self.mock_issue
        )
        mock_update_fixVersion.assert_called_with(
            self.mock_updates,
            self.mock_downstream,
            self.mock_issue,
            mock_client,
        )
        mock_update_description.assert_called_with(
            self.mock_downstream,
            self.mock_issue
        )
        mock_update_title.assert_called_with(
            self.mock_issue,
            self.mock_downstream
        )
        mock_update_transition.assert_called_with(
            mock_client,
            self.mock_downstream,
            self.mock_issue
        )
        mock_update_on_close.assert_called_once()

    @mock.patch('jira.client.JIRA')
    def test_update_transition_JIRAError(self,
                                         mock_client):
        """
        This function tests the '_update_transition' function where Upstream issue status
        s not in existing.fields.description and transitioning the issue throws an error
        """
        # Set up return values
        self.mock_issue.status = 'Closed'
        self.mock_downstream.fields.description = ''
        mock_client.transitions.return_value = [{'name': 'CUSTOM TRANSITION', 'id': '1234'}]
        mock_client.transition_issue.side_effect = JIRAError

        # Call the function
        d._update_transition(
            client=mock_client,
            existing=self.mock_downstream,
            issue=self.mock_issue
        )

        # Assert all calls were made correctly
        mock_client.transitions.assert_called_with(self.mock_downstream)
        mock_client.transition_issue.assert_called_with(self.mock_downstream, 1234)


    @mock.patch('jira.client.JIRA')
    def test_update_transition_not_found(self,
                                         mock_client):
        """
        This function tests the '_update_transition' function where Upstream issue status
        not in existing.fields.description and we can't find the appropriate closed status
        """
        # Set up return values
        self.mock_issue.status = 'Closed'
        self.mock_issue.downstream['transition'] = 'bad_transition'
        self.mock_downstream.fields.description = ''
        mock_client.transitions.return_value = [{'name': 'CUSTOM TRANSITION', 'id': '1234'}]

        # Call the function
        d._update_transition(
            client=mock_client,
            existing=self.mock_downstream,
            issue=self.mock_issue
        )

        # Assert all calls were made correctly
        mock_client.transitions.assert_called_with(self.mock_downstream)
        mock_client.transition_issue.assert_called_with(self.mock_downstream, 1234)

    @mock.patch('jira.client.JIRA')
    def test_update_transition_successful(self,
                                          mock_client):
        """
        This function tests the '_update_transition' function where everything goes smoothly!
        """
        # Set up return values
        self.mock_issue.status = 'Closed'
        self.mock_downstream.fields.description = '[test] Upstream issue status: Open'
        mock_client.transitions.return_value = [{'name': 'CUSTOM TRANSITION', 'id': '1234'}]

        # Call the function
        d._update_transition(
            client=mock_client,
            existing=self.mock_downstream,
            issue=self.mock_issue
        )

        # Assert all calls were made correctly
        mock_client.transitions.assert_called_with(self.mock_downstream)
        mock_client.transition_issue.assert_called_with(self.mock_downstream, 1234)

    @mock.patch(PATH + '_comment_format')
    @mock.patch(PATH + '_comment_matching')
    @mock.patch('jira.client.JIRA')
    def test_update_comments(self,
                             mock_client,
                             mock_comment_matching,
                             mock_comment_format):
        """
        This function tests the 'update_comments' function
        """
        # Set up return values
        mock_client.comments.return_value = 'mock_comments'
        mock_comment_matching.return_value = ['mock_comments_d']
        mock_comment_format.return_value = 'mock_comment_body'

        # Call the function
        d._update_comments(
            client=mock_client,
            existing=self.mock_downstream,
            issue=self.mock_issue
        )

        # Assert all calls were made correctly
        mock_client.comments.assert_called_with(self.mock_downstream)
        mock_comment_matching.assert_called_with(self.mock_issue.comments, 'mock_comments')
        mock_comment_format.assert_called_with('mock_comments_d')
        mock_client.add_comment.assert_called_with(self.mock_downstream, 'mock_comment_body')

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
            {'fixVersions': [{'name': 'fixVersion3'}, {'name': 'fixVersion4'}]})
        mock_client.add_comment(self.mock_downstream, f"Error updating fixVersion: {self.mock_issue.fixVersion}")


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
            {'fixVersions': [{'name': 'fixVersion3'}, {'name': 'fixVersion4'}]})
        mock_client.add_comment.assert_not_called()

    @mock.patch(PATH + 'assign_user')
    @mock.patch('jira.client.JIRA')
    def test_update_assignee_assignee(self,
                                      mock_client,
                                      mock_assign_user):
        """
        This function tests the 'update_assignee' function where issue.assignee exists
        """
        # Call the function
        d._update_assignee(
            client=mock_client,
            existing=self.mock_downstream,
            issue=self.mock_issue,
            updates=[{'assignee': {'overwrite': True}}]
        )

        # Assert all calls were made correctly
        mock_assign_user.assert_called_with(
            mock_client,
            self.mock_issue,
            self.mock_downstream
        )

    @mock.patch(PATH + 'assign_user')
    @mock.patch('jira.client.JIRA')
    def test_update_assignee_no_assignee(self,
                                         mock_client,
                                         mock_assign_user):
        """
        This function tests the '_update_assignee' function where issue.assignee does not exist
        """
        # Set up return values
        self.mock_issue.assignee = None

        # Call the function
        d._update_assignee(
            client=mock_client,
            existing=self.mock_downstream,
            issue=self.mock_issue,
            updates=[{'assignee': {'overwrite': True}}]
        )

        # Assert all calls were made correctly
        mock_assign_user.assert_called_with(
            mock_client,
            self.mock_issue,
            self.mock_downstream,
            remove_all=True
        )

    @mock.patch(PATH + 'assign_user')
    @mock.patch('jira.client.JIRA')
    def test_update_assignee_no_overwrite(self,
                                          mock_client,
                                          mock_assign_user):
        """
        This function tests the '_update_assignee' function where overwrite is false
        """
        # Set up return values
        self.mock_downstream.fields.assignee = None

        # Call the function
        d._update_assignee(
            client=mock_client,
            existing=self.mock_downstream,
            issue=self.mock_issue,
            updates=[{'assignee': {'overwrite': False}}]
        )

        # Assert all calls were made correctly
        mock_assign_user.assert_called_with(
            mock_client,
            self.mock_issue,
            self.mock_downstream
        )


    @mock.patch(PATH + 'verify_tags')
    @mock.patch(PATH + '_label_matching')
    def test_update_tags(self,
                         mock_label_matching,
                         mock_verify_tags):
        """
        This function tests the '_update_tags' function
        """
        # Set up return values
        mock_label_matching.return_value = 'mock_updated_labels'
        mock_verify_tags.return_value = ['mock_verified_tags']

        # Call the function
        d._update_tags(
            updates=self.mock_updates,
            existing=self.mock_downstream,
            issue=self.mock_issue
        )

        # Assert all calls were made correctly
        mock_label_matching.assert_called_with(
            self.mock_issue.tags,
            self.mock_downstream.fields.labels
        )
        mock_verify_tags.assert_called_with('mock_updated_labels')
        self.mock_downstream.update.assert_called_with({'labels': ['mock_verified_tags']})

    @mock.patch(PATH + 'verify_tags')
    @mock.patch(PATH + '_label_matching')
    def test_update_tags_no_api_call(self,
                                     mock_label_matching,
                                     mock_verify_tags):
        """
        This function tests the '_update_tags' function where the existing tags are the same
        as the new ones
        """
        # Set up return values
        mock_label_matching.return_value = 'mock_updated_labels'
        mock_verify_tags.return_value = ['tag3', 'tag4']

        # Call the function
        d._update_tags(
            updates=self.mock_updates,
            existing=self.mock_downstream,
            issue=self.mock_issue
        )

        # Assert all calls were made correctly
        mock_label_matching.assert_called_with(
            self.mock_issue.tags,
            self.mock_downstream.fields.labels
        )
        mock_verify_tags.assert_called_with('mock_updated_labels')
        self.mock_downstream.update.assert_not_called()

    def test_update_description_update(self):
        """
        This function tests '_update_description' where we just have to update the contents of the description
        """
        # Set up return values
        self.mock_downstream.fields.description = '[1234] Upstream Reporter: mock_user\nUpstream issue status: Open\nUpstream description: {quote} test {quote}'

        # Call the function
        d._update_description(
            existing=self.mock_downstream,
            issue=self.mock_issue
        )

        # Assert all calls were made correctly
        self.mock_downstream.update.assert_called_with(
            {'description': '[1234] Upstream Reporter: mock_user\nUpstream issue status: Open\nUpstream description: {quote}mock_content{quote}'})

    def test_update_description_add_field(self):
        """
        This function tests '_update_description' where we just have to add a description field
        """
        # Set up return values
        self.mock_downstream.fields.description = '[123] Upstream Reporter: mock_user\n' \
                                                  'Upstream description: {quote} test {quote}'

        # Call the function
        d._update_description(
            existing=self.mock_downstream,
            issue=self.mock_issue
        )

        # Assert all calls were made correctly
        self.mock_downstream.update.assert_called_with(
            {'description': '[1234] Upstream Reporter: mock_user\n'
                            'Upstream issue status: Open\n'
                            'Upstream description: {quote}mock_content{quote}'})

    def test_update_description_add_reporter(self):
        """
        This function tests '_update_description' where we have to add a description and upstream reporter field
        """
        # Set up return values
        self.mock_downstream.fields.description = '[123] Upstream issue status: Open\n'
        self.mock_issue.status = 'Open'
        self.mock_issue.id = '123'
        self.mock_issue.reporter = {'fullname': 'mock_user'}

        # Call the function
        d._update_description(
            existing=self.mock_downstream,
            issue=self.mock_issue
        )
        # Assert all calls were made correctly
        self.mock_downstream.update.assert_called_with(
            {'description': '[123] Upstream Reporter: mock_user\n'
                            'Upstream issue status: Open\n'
                            'Upstream description: {quote}mock_content{quote}'})

    def test_update_description_add_reporter_no_status(self):
        """
        This function tests '_update_description' where we have to add reporter and description without status
        """
        # Set up return values
        self.mock_downstream.fields.description = ''
        self.mock_issue.downstream['issue_updates'] = [
            u for u in self.mock_issue.downstream['issue_updates'] if 'transition' not in u]

        # Call the function
        d._update_description(
            existing=self.mock_downstream,
            issue=self.mock_issue
        )

        # Assert all calls were made correctly
        self.mock_downstream.update.assert_called_with(
            {'description': '[1234] Upstream Reporter: mock_user\n'
                            'Upstream description: {quote}mock_content{quote}'})

    @mock.patch(PATH + 'datetime')
    def test_update_description_add_description(self,
                                                mock_datetime):
        """
        This function tests '_update_description' where we have a reporter and status already
        """
        # Set up return values
        self.mock_downstream.fields.description = '[123] Upstream issue status: Open\n' \
                                                  '[123] Upstream Reporter: mock_user\n'
        self.mock_issue.status = 'Open'
        self.mock_issue.id = '123'
        self.mock_issue.reporter = {'fullname': 'mock_user'}
        mock_datetime.today.return_value = self.mock_today

        # Call the function
        d._update_description(
            existing=self.mock_downstream,
            issue=self.mock_issue
        )

        # Assert all calls were made correctly
        self.mock_downstream.update.assert_called_with(
            {'description': '[123] Upstream Reporter: mock_user\n'
                            'Upstream issue status: Open\n'
                            'Upstream description: {quote}mock_content{quote}'})

    def test_verify_tags(self):
        """
        This function tests 'verify_tags' function
        """
        # Call the function
        response = d.verify_tags(
            tags=['this is a tag']
        )

        # Assert everything was called correctly
        self.assertEqual(response, ['this_is_a_tag'])

    @mock.patch(PATH + 'get_jira_client')
    @mock.patch(PATH + '_matching_jira_issue_query')
    @mock.patch(PATH + '_close_as_duplicate')
    @mock.patch('jira.client.JIRA')
    @mock.patch(PATH + 'check_jira_status')
    def test_close_duplicates_no_matching(self,
                                          mock_check_jira_status,
                                          mock_client,
                                          mock_close_as_duplicate,
                                          mock_matching_jira_issue_query,
                                          mock_get_jira_client):
        """
        This tests 'close_duplicates' function where len(results) <= 1
        """
        # Set up return values
        mock_get_jira_client.return_value = mock_client
        mock_matching_jira_issue_query.return_value = ['only_one_response']
        mock_check_jira_status.return_value = True

        # Call the function
        response = d.close_duplicates(
            issue=self.mock_issue,
            config=self.mock_config
        )

        # Assert everything was called correctly
        mock_get_jira_client.assert_called_with(self.mock_issue, self.mock_config)
        mock_matching_jira_issue_query.assert_called_with(
            mock_client,
            self.mock_issue,
            self.mock_config,
            free=True
        )
        mock_close_as_duplicate.assert_not_called()
        self.assertEqual(None, response)

    @mock.patch(PATH + 'get_jira_client')
    @mock.patch(PATH + '_matching_jira_issue_query')
    @mock.patch(PATH + '_close_as_duplicate')
    @mock.patch('jira.client.JIRA')
    @mock.patch(PATH + 'check_jira_status')
    def test_close_duplicates(self,
                              mock_check_jira_status,
                              mock_client,
                              mock_close_as_duplicate,
                              mock_matching_jira_issue_query,
                              mock_get_jira_client):
        """
        This tests 'close_duplicates' function where len(results) > 1
        """
        # Set up return values
        mock_get_jira_client.return_value = mock_client
        mock_item = MagicMock()
        mock_item.fields.created = 1
        mock_matching_jira_issue_query.return_value = [mock_item, mock_item, mock_item]
        mock_check_jira_status.return_value = True

        # Call the function
        response = d.close_duplicates(
            issue=self.mock_issue,
            config=self.mock_config
        )

        # Assert everything was called correctly
        mock_get_jira_client.assert_called_with(self.mock_issue, self.mock_config)
        mock_matching_jira_issue_query.assert_called_with(
            mock_client,
            self.mock_issue,
            self.mock_config,
            free=True
        )
        mock_close_as_duplicate.assert_called_with(
            mock_client,
            mock_item,
            mock_item,
            self.mock_config
        )
        self.assertEqual(None, response)

    @mock.patch('jira.client.JIRA')
    def test_close_as_duplicate_errors(self,
                                       mock_client):
        """
        This tests '_close_as_duplicate' function where client.transition_issue throws an exception
        """
        # Set up return values
        class HTTPExceptionHelper():
            text = "Field 'resolution' cannot be set"

        class HTTPException(Exception):
            response = HTTPExceptionHelper

        mock_duplicate = MagicMock()
        mock_duplicate.permalink.return_value = 'mock_url'
        mock_duplicate.key = 'mock_key'
        mock_keeper = MagicMock()
        mock_keeper.key = 'mock_key'
        mock_keeper.permalink.return_value = 'mock_url'
        mock_client.transitions.return_value = [{'name': 'Dropped', 'id': '1234'}]
        mock_client.comments.return_value = []
        mock_client.transition_issue.side_effect = HTTPException

        # Call the function
        d._close_as_duplicate(
            client=mock_client,
            duplicate=mock_duplicate,
            keeper=mock_keeper,
            config=self.mock_config
        )

        # Assert everything was called correctly
        mock_client.comments.assert_any_call(mock_keeper)
        mock_client.comments.assert_any_call(mock_duplicate)
        mock_client.transitions.assert_called_with(mock_duplicate)
        mock_client.add_comment.assert_any_call(mock_duplicate, 'Marking as duplicate of mock_key')
        mock_client.add_comment.assert_any_call(mock_keeper, 'mock_key is a duplicate.')
        mock_client.transition_issue.assert_any_call(
            mock_duplicate,
            '1234',
            resolution={'name': 'Duplicate'}
        )
        mock_client.transition_issue.assert_any_call(
            mock_duplicate,
            '1234'
        )

    @mock.patch('jira.client.JIRA')
    def test_close_as_duplicate(self,
                                mock_client):
        """
        This tests '_close_as_duplicate' function where everything goes smoothly
        """
        # Set up return values
        mock_duplicate = MagicMock()
        mock_duplicate.permalink.return_value = 'mock_url'
        mock_duplicate.key = 'mock_key'
        mock_keeper = MagicMock()
        mock_keeper.key = 'mock_key'
        mock_keeper.permalink.return_value = 'mock_url'
        mock_client.transitions.return_value = [{'name': 'Dropped', 'id': '1234'}]
        mock_client.comments.return_value = []

        # Call the function
        d._close_as_duplicate(
            client=mock_client,
            duplicate=mock_duplicate,
            keeper=mock_keeper,
            config=self.mock_config
        )

        # Assert everything was called correctly
        mock_client.comments.assert_any_call(mock_keeper)
        mock_client.comments.assert_any_call(mock_duplicate)
        mock_client.transitions.assert_called_with(mock_duplicate)
        mock_client.add_comment.assert_any_call(mock_duplicate, 'Marking as duplicate of mock_key')
        mock_client.add_comment.assert_any_call(mock_keeper, 'mock_key is a duplicate.')
        mock_client.transition_issue.assert_called_with(
            mock_duplicate,
            '1234',
            resolution={'name': 'Duplicate'}
        )

    @mock.patch(PATH + 'alert_user_of_duplicate_issues')
    @mock.patch(PATH + 'find_username')
    @mock.patch(PATH + 'check_comments_for_duplicate')
    @mock.patch('jira.client.JIRA')
    def test_matching_jira_issue_query(self,
                                       mock_client,
                                       mock_check_comments_for_duplicates,
                                       mock_find_username,
                                       mock_alert_user_of_duplicate_issues):
        """
        This tests '_matching_jira_query' function
        """
        # Set up return values
        mock_downstream_issue = MagicMock()
        self.mock_issue.upstream_title = 'mock_upstream_title'
        mock_downstream_issue.fields.description = self.mock_issue.id
        bad_downstream_issue = MagicMock()
        bad_downstream_issue.fields.description = 'bad'
        bad_downstream_issue.fields.summary = 'bad'
        mock_client.search_issues.return_value = [mock_downstream_issue, bad_downstream_issue]
        mock_check_comments_for_duplicates.return_value = True
        mock_find_username.return_value = 'mock_username'
        mock_alert_user_of_duplicate_issues.return_value = True

        # Call the function
        response = d._matching_jira_issue_query(
            client=mock_client,
            issue=self.mock_issue,
            config=self.mock_config
        )

        # Assert everything was called correctly
        self.assertEqual(response, [mock_downstream_issue])
        mock_alert_user_of_duplicate_issues.assert_called_with(
            self.mock_issue,
            [mock_downstream_issue],
            mock_client.search_issues.return_value,
            self.mock_config,
            mock_client
        )
        mock_client.search_issues.assert_called_with(
            'issueFunction in linkedIssuesOfRemote("Upstream issue")'
            ' and issueFunction in linkedIssuesOfRemote("mock_url")')
        mock_check_comments_for_duplicates.assert_called_with(
            mock_client,
            mock_downstream_issue,
            'mock_username'
        )
        mock_find_username.assert_called_with(
            self.mock_issue,
            self.mock_config
        )

    @mock.patch(PATH + 'jinja2')
    @mock.patch(PATH + 'send_mail')
    @mock.patch('jira.client.JIRA')
    def test_alert_user(self,
                        mock_client,
                        mock_mailer,
                        mock_jinja,):
        """
        This tests 'alert_user_of_duplicate_issues' function
        """
        # Set up return values
        mock_downstream_issue = MagicMock()
        mock_downstream_issue.key = 'mock_key'
        bad_downstream_issue = MagicMock()
        bad_downstream_issue.key = 'mock_key'
        bad_downstream_issue.fields.status.name = 'To Do'
        mock_results_of_query = [mock_downstream_issue, bad_downstream_issue]
        mock_search_user_result = MagicMock()
        mock_search_user_result.displayName = 'mock_name'
        mock_search_user_result.emailAddress = 'mock_email'
        mock_client.search_users.return_value = [mock_search_user_result]
        mock_template = MagicMock(name='template')
        mock_template.render.return_value = 'mock_html_text'
        mock_template_env = MagicMock(name='templateEnv')
        mock_template_env.get_template.return_value = mock_template
        mock_jinja.Environment.return_value = mock_template_env

        # Call the function
        d.alert_user_of_duplicate_issues(
            issue=self.mock_issue,
            final_result=[mock_downstream_issue],
            results_of_query=mock_results_of_query,
            config=self.mock_config,
            client=mock_client
        )

        # Assert everything was called correctly
        mock_client.search_users.assert_any_call('mock_owner')
        mock_client.search_users.assert_any_call('mock_admin')
        mock_template.render.assert_called_with(
            admins=[{'name': 'mock_name', 'email': 'mock_email'}],
            duplicate_issues=[{'url': 'mock_server/browse/mock_key', 'title': 'mock_key'}],
            issue=self.mock_issue,
            selected_issue={'url': 'mock_server/browse/mock_key', 'title': 'mock_key'},
            user={'name': 'mock_name', 'email': 'mock_email'})
        mock_mailer().send.asset_called_with('test')

    @mock.patch(PATH + 'jinja2')
    @mock.patch(PATH + 'send_mail')
    @mock.patch('jira.client.JIRA')
    def test_alert_user_multiple_users(self,
                                       mock_client,
                                       mock_mailer,
                                       mock_jinja, ):
        """
        This tests 'alert_user_of_duplicate_issues' function
        where searching returns multiple users
        """
        # Set up return values
        mock_downstream_issue = MagicMock()
        mock_downstream_issue.key = 'mock_key'
        bad_downstream_issue = MagicMock()
        bad_downstream_issue.key = 'mock_key'
        bad_downstream_issue.fields.status.name = 'To Do'
        mock_results_of_query = [mock_downstream_issue, bad_downstream_issue]
        mock_search_user_result1 = MagicMock()
        mock_search_user_result1.displayName = 'bad_name'
        mock_search_user_result1.emailAddress = 'bad_email'
        mock_search_user_result1.key = 'bad_owner'
        mock_search_user_result2 = MagicMock()
        mock_search_user_result2.displayName = 'mock_name'
        mock_search_user_result2.emailAddress = 'mock_email'
        mock_search_user_result2.key = 'mock_owner'
        mock_client.search_users.return_value = [mock_search_user_result1, mock_search_user_result2]
        mock_template = MagicMock(name='template')
        mock_template.render.return_value = 'mock_html_text'
        mock_template_env = MagicMock(name='templateEnv')
        mock_template_env.get_template.return_value = mock_template
        mock_jinja.Environment.return_value = mock_template_env

        # Call the function
        d.alert_user_of_duplicate_issues(
            issue=self.mock_issue,
            final_result=[mock_downstream_issue],
            results_of_query=mock_results_of_query,
            config=self.mock_config,
            client=mock_client
        )

        # Assert everything was called correctly
        mock_client.search_users.assert_any_call('mock_owner')
        mock_client.search_users.assert_any_call('mock_admin')
        mock_template.render.assert_called_with(
            admins=[{'name': 'mock_name', 'email': 'mock_email'}],
            duplicate_issues=[{'url': 'mock_server/browse/mock_key', 'title': 'mock_key'}],
            issue=self.mock_issue,
            selected_issue={'url': 'mock_server/browse/mock_key', 'title': 'mock_key'},
            user={'name': 'mock_name', 'email': 'mock_email'})
        mock_mailer().send.asset_called_with('test')

    def test_find_username(self):
        """
        Tests 'find_username' function
        """
        # Call the function
        response = d.find_username(
            self.mock_issue,
            self.mock_config
        )

        # Assert everything was called correctly
        self.assertEqual(response, 'mock_user')

    @mock.patch('jira.client.JIRA')
    def test_check_comments_for_duplicates(self,
                                           mock_client):
        """
        Tests 'check_comments_for_duplicates' function
        """
        # Set up return values
        mock_comment = MagicMock()
        mock_comment.body = 'Marking as duplicate of TEST-1234'
        mock_comment.author.name = 'mock_user'
        mock_client.comments.return_value = [mock_comment]
        mock_client.issue.return_value = 'Successful Call!'

        # Call the function
        response = d.check_comments_for_duplicate(
            client=mock_client,
            result=self.mock_downstream,
            username='mock_user'
        )

        # Assert everything was called correctly
        self.assertEqual(response, 'Successful Call!')
        mock_client.comments.assert_called_with(self.mock_downstream)
        mock_client.issue.assert_called_with('TEST-1234')

    @mock.patch(PATH + '_comment_format')
    @mock.patch(PATH + '_comment_format_legacy')
    def test_find_comment_in_jira_legacy(self,
                                         mock_comment_format_legacy,
                                         mock_comment_format):
        """
        This function tests '_find_comment_in_jira' where we find a legacy comment
        """
        # Set up return values
        mock_comment_format.return_value = 'mock_comment_body'
        mock_comment_format_legacy.return_value = 'mock_legacy_comment_body'
        mock_jira_comment = MagicMock()
        mock_jira_comment.raw = {'body': 'mock_legacy_comment_body'}
        mock_comment = {
            'id': '12345',
            'date_created': datetime(2019, 8, 8, tzinfo=timezone.utc)
        }

        # Call the function
        response = d._find_comment_in_jira(mock_comment, [mock_jira_comment])

        # Assert everything was called correctly
        mock_comment_format_legacy.assert_called_with(mock_comment)
        mock_comment_format.assert_called_with(mock_comment)
        self.assertEqual(response, mock_jira_comment)

    @mock.patch(PATH + '_comment_format')
    @mock.patch(PATH + '_comment_format_legacy')
    def test_find_comment_in_jira_id(self,
                                     mock_comment_format_legacy,
                                     mock_comment_format):
        """
        This function tests '_find_comment_in_jira' where we match an ID
        """
        # Set up return values
        mock_comment_format.return_value = 'mock_comment_body'
        mock_comment_format_legacy.return_value = 'mock_legacy_comment_body'
        mock_jira_comment = MagicMock()
        mock_jira_comment.raw = {'body': '12345'}
        mock_comment = {
            'id': '12345',
            'date_created': datetime(2019, 8, 8, tzinfo=timezone.utc)
        }

        # Call the function
        response = d._find_comment_in_jira(mock_comment, [mock_jira_comment])

        # Assert everything was called correctly
        mock_comment_format_legacy.assert_called_with(mock_comment)
        mock_comment_format.assert_called_with(mock_comment)
        self.assertEqual(response, mock_jira_comment)

    @mock.patch(PATH + '_comment_format')
    @mock.patch(PATH + '_comment_format_legacy')
    def test_find_comment_in_jira_old_comment(self,
                                              mock_comment_format_legacy,
                                              mock_comment_format):
        """
        This function tests '_find_comment_in_jira' where we find a old comment
        """
        # Set up return values
        mock_comment_format.return_value = 'mock_comment_body'
        mock_comment_format_legacy.return_value = 'mock_legacy_comment_body'
        mock_jira_comment = MagicMock()
        mock_jira_comment.raw = {'body': 'old_comment'}
        mock_comment = {
            'id': '12345',
            'date_created': datetime(2019, 1, 1, tzinfo=timezone.utc)
        }

        # Call the function
        response = d._find_comment_in_jira(mock_comment, [mock_jira_comment])

        # Assert everything was called correctly
        mock_comment_format_legacy.assert_called_with(mock_comment)
        mock_comment_format.assert_called_with(mock_comment)
        self.assertEqual(response, mock_jira_comment)

    @mock.patch(PATH + '_comment_format')
    @mock.patch(PATH + '_comment_format_legacy')
    def test_find_comment_in_jira_none(self,
                                       mock_comment_format_legacy,
                                       mock_comment_format):
        """
        This function tests '_find_comment_in_jira' where we return None
        """
        # Set up return values
        mock_comment_format.return_value = 'mock_comment_body'
        mock_comment_format_legacy.return_value = 'mock_legacy_comment_body'
        mock_comment = {
            'id': '12345',
            'date_created': datetime(2019, 1, 1, tzinfo=timezone.utc)
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
        mock_jira_client.search_issues.assert_called_with("issueFunction in linkedIssuesOfRemote('*')")

    def test_check_jira_status_true(self):
        """
        This function tests 'check_jira_status' where we return false
        """
        # Set up return values
        mock_jira_client = MagicMock()
        mock_jira_client.search_issues.return_value = ['some', 'values']

        # Call the function
        response = d.check_jira_status(mock_jira_client)

        # Assert everything was called correctly
        self.assertEqual(response, True)
        mock_jira_client.search_issues.assert_called_with("issueFunction in linkedIssuesOfRemote('*')")

    def test_update_on_close_update(self):
        """
        This function tests '_update_on_close' where there is an
        "apply_labels" configuration, and labels need to be updated.
        """
        # Set up return values
        self.mock_downstream.fields.description = ""
        self.mock_issue.status = 'Closed'
        updates = [{"on_close": {"apply_labels": ["closed-upstream"]}}]

        # Call the function
        d._update_on_close(self.mock_downstream, self.mock_issue, updates)

        # Assert everything was called correctly
        self.mock_downstream.update.assert_called_with(
            {'labels':
                 ["closed-upstream", "tag3", "tag4"]})

    def test_update_on_close_no_change(self):
        """
        This function tests '_update_on_close' where there is an
        "apply_labels" configuration but there is no update required.
        """
        # Set up return values
        self.mock_issue.status = 'Closed'
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
        self.mock_issue.status = 'Closed'
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
        self.mock_issue.status = 'Closed'
        updates = ["description"]

        # Call the function
        d._update_on_close(self.mock_downstream, self.mock_issue, updates)

        # Assert everything was called correctly
        self.mock_downstream.update.assert_not_called()

    @mock.patch('jira.client.JIRA')
    def test_update_github_project_fields_storypoints(self, mock_client):
        """
        This function tests `_update_github_project_fields`
        with story points value.
        """
        github_project_fields = {
         "storypoints": {
           "gh_field": "Estimate"
         }}
        d._update_github_project_fields(mock_client, self.mock_downstream, self.mock_issue,
                                  github_project_fields, self.mock_config)
        self.mock_downstream.update.assert_called_with({'customfield_12310243': 2})

    @mock.patch('jira.client.JIRA')
    def test_update_github_project_fields_storypoints_bad(self, mock_client):
        """This function tests `_update_github_project_fields` with
        a bad (non-numeric) story points value.
        """
        github_project_fields = {"storypoints": {"gh_field": "Estimate"}}
        for bad_sp in [None, '', 'bad_value']:
            self.mock_issue.storypoints = bad_sp
            d._update_github_project_fields(
                mock_client, self.mock_downstream, self.mock_issue,
                github_project_fields, self.mock_config)
            self.mock_downstream.update.assert_not_called()
            mock_client.add_comment.assert_not_called()

    @mock.patch('jira.client.JIRA')
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
             "P5": "Trivial"
        }}}
        d._update_github_project_fields(mock_client, self.mock_downstream, self.mock_issue,
                                  github_project_fields, self.mock_config)
        self.mock_downstream.update.assert_called_with({'priority': {'name': 'Critical'}})

    @mock.patch('jira.client.JIRA')
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
                    "P5": "Trivial"
                }}}
        for bad_pv in [None, '', 'bad_value']:
            self.mock_issue.priority = bad_pv
            d._update_github_project_fields(
                mock_client, self.mock_downstream, self.mock_issue,
                github_project_fields, self.mock_config)
            self.mock_downstream.update.assert_not_called()
            mock_client.add_comment.assert_not_called()
