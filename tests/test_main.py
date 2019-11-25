import mock
import unittest
try:
    # Python 3.3 >
    from unittest.mock import MagicMock  # noqa: F401
except ImportError:
    from mock import MagicMock  # noqa: F401

import sync2jira.main as m


PATH = 'sync2jira.main.'


class TestMain(unittest.TestCase):
    """
    This class tests the main.py file under sync2jira
    """
    def setUp(self):
        """
        Set up the testing environment
        """
        # Mock Config dict
        self.mock_config = {
            'sync2jira': {
                'jira': {
                    'mock_jira_instance': {'mock_jira': 'mock_jira'}
                },
                'testing': {},
                'legacy_matching': False,
                'map': {
                    'pagure': {'key_pagure': 'value1'},
                    'github': {'key_github': 'value1'}
                },
                'initialize': True,
                'listen': True,
                'develop': False,
            },
        }

        # Mock Fedmsg Message
        self.mock_message = {
            'msg_id': 'mock_id'
        }

    def _check_for_exception(self, loader, target, exc=ValueError):
        try:
            m.load_config(loader)
            assert False, "Exception expected."
        except exc as e:
            self.assertIn(target, repr(e))

    def test_config_validate_empty(self):
        loader = lambda: {}
        self._check_for_exception(loader, 'No sync2jira section')

    def test_config_validate_missing_map(self):
        loader = lambda: {'sync2jira': {}}
        self._check_for_exception(loader, 'No sync2jira.map section')

    def test_config_validate_mispelled_mappings(self):
        loader = lambda: {'sync2jira': {'map': {'pageur': {}}}, 'jira': {}}
        self._check_for_exception(loader, 'Specified handlers: "pageur", must')

    def test_config_validate_missing_jira(self):
        loader = lambda: {'sync2jira': {'map': {'pagure': {}}}}
        self._check_for_exception(loader, 'No sync2jira.jira section')

    def test_config_validate_all_good(self):
        loader = lambda: {'sync2jira': {'map': {'pagure': {}}, 'jira': {}}}
        m.load_config(loader)  # ahhh, no exception.

    @mock.patch(PATH + 'u')
    @mock.patch(PATH + 'd')
    @mock.patch(PATH + 'load_config')
    def test_close_duplicates(self,
                              mock_load_config,
                              mock_d,
                              mock_u):
        """
        This tests the 'close_duplicates' function where everything goes smoothly
        """
        # Set up return values
        mock_load_config.return_value = self.mock_config
        mock_u.pagure_issues.return_value = ['mock_issue_github']
        mock_u.github_issues.return_value = ['mock_issue_pagure']

        # Call the function
        m.close_duplicates()

        # Assert everything was called correctly
        mock_load_config.assert_called_once()
        mock_u.pagure_issues.assert_called_with('key_pagure', self.mock_config)
        mock_u.github_issues.assert_called_with('key_github', self.mock_config)
        mock_d.close_duplicates.assert_any_call('mock_issue_github', self.mock_config)
        mock_d.close_duplicates.assert_any_call('mock_issue_pagure', self.mock_config)

    @mock.patch(PATH + 'u')
    @mock.patch(PATH + 'd')
    @mock.patch(PATH + 'load_config')
    def test_close_duplicates_errors(self,
                              mock_load_config,
                              mock_d,
                              mock_u):
        """
        This tests the 'close_duplicates' function where closing duplicates raises an exception
        """
        # Set up return values
        mock_load_config.return_value = self.mock_config
        mock_u.pagure_issues.return_value = ['mock_issue']
        mock_u.github_issues.return_value = ['mock_issue']
        mock_d.close_duplicates.side_effect = Exception()

        # Call the function
        with self.assertRaises(Exception):
            m.close_duplicates()

        # Assert everything was called correctly
        mock_load_config.assert_called_once()
        mock_u.pagure_issues.assert_called_with('key_pagure', self.mock_config)
        mock_u.github_issues.assert_not_called()
        mock_d.close_duplicates.assert_called_with('mock_issue', self.mock_config)

    @mock.patch(PATH + 'load_config')
    @mock.patch(PATH + 'u')
    def test_list_managed(self,
                          mock_u,
                          mock_load_config):
        """
        This tests the 'list_managed' function
        """
        # Set up return values
        mock_load_config.return_value = self.mock_config

        # Call the function
        m.list_managed()

        # Assert everything was called correctly
        mock_load_config.assert_called_once()
        mock_u.pagure_issues.assert_called_with('key_pagure', self.mock_config)
        mock_u.github_issues.assert_called_with('key_github', self.mock_config)

    @mock.patch(PATH + 'initialize')
    @mock.patch(PATH + 'load_config')
    @mock.patch(PATH + 'listen')
    def test_main(self,
                  mock_listen,
                  mock_load_config,
                  mock_initialize):
        """
        This tests the 'main' function
        """
        # Set up return values
        mock_load_config.return_value = self.mock_config

        # Call the function
        m.main()

        # Assert everything was called correctly
        mock_load_config.assert_called_once()
        mock_listen.assert_called_with(self.mock_config)
        mock_listen.assert_called_with(self.mock_config)
        mock_initialize.assert_called_with(self.mock_config)

    @mock.patch(PATH + 'u')
    @mock.patch(PATH + 'd')
    def test_initialize(self,
                        mock_d,
                        mock_u):
        """
        This tests 'initialize' function where everything goes smoothly!
        """
        # Set up return values
        mock_u.pagure_issues.return_value = ['mock_issue_pagure']
        mock_u.github_issues.return_value = ['mock_issue_github']

        # Call the function
        m.initialize(self.mock_config)

        # Assert everything was called correctly
        mock_u.pagure_issues.assert_called_with('key_pagure', self.mock_config)
        mock_u.github_issues.assert_called_with('key_github', self.mock_config)
        mock_d.sync_with_jira.assert_any_call('mock_issue_pagure', self.mock_config)
        mock_d.sync_with_jira.assert_any_call('mock_issue_github', self.mock_config)

    @mock.patch(PATH + 'u')
    @mock.patch(PATH + 'd')
    def test_initialize_errors(self,
                               mock_d,
                               mock_u):
        """
        This tests 'initialize' function where syncing with JIRA throws an exception
        """
        # Set up return values
        mock_u.pagure_issues.return_value = ['mock_issue_pagure']
        mock_u.github_issues.return_value = ['mock_issue_github']
        mock_d.sync_with_jira.side_effect = Exception()

        # Call the function
        with self.assertRaises(Exception):
            m.initialize(self.mock_config)

        # Assert everything was called correctly
        mock_u.pagure_issues.assert_called_with('key_pagure', self.mock_config)
        mock_d.sync_with_jira.assert_any_call('mock_issue_pagure', self.mock_config)

    @mock.patch(PATH + 'u')
    @mock.patch(PATH + 'd')
    @mock.patch(PATH + 'sleep')
    @mock.patch(PATH + 'report_failure')
    def test_initialize_api_limit(self,
                                  mock_report_failure,
                                  mock_sleep,
                                  mock_d,
                                  mock_u):
        """
        This tests 'initialize' where we get an GitHub API limit error.
        """
        # Set up return values
        mock_error = MagicMock(side_effect=Exception('API rate limit exceeded'))
        mock_u.pagure_issues.return_value = ['mock_issue_pagure']
        mock_u.github_issues.side_effect = mock_error

        # Call the function
        m.initialize(self.mock_config, testing=True)

        # Assert everything was called correctly
        mock_u.pagure_issues.assert_called_with('key_pagure', self.mock_config)
        mock_d.sync_with_jira.assert_any_call('mock_issue_pagure', self.mock_config)
        mock_u.github_issues.assert_called_with('key_github', self.mock_config)
        mock_sleep.assert_called_with(3600)
        mock_report_failure.assert_not_called()

    @mock.patch(PATH + 'u')
    @mock.patch(PATH + 'd')
    @mock.patch(PATH + 'sleep')
    @mock.patch(PATH + 'report_failure')
    def test_initialize_github_error(self,
                                     mock_report_failure,
                                     mock_sleep,
                                     mock_d,
                                     mock_u):
        """
        This tests 'initialize' where we get a GitHub API (not limit) error.
        """
        # Set up return values
        mock_error = MagicMock(side_effect=Exception('Random Error'))
        mock_u.pagure_issues.return_value = ['mock_issue_pagure']
        mock_u.github_issues.side_effect = mock_error

        # Call the function
        with self.assertRaises(Exception):
            m.initialize(self.mock_config, testing=True)

        # Assert everything was called correctly
        mock_u.pagure_issues.assert_called_with('key_pagure', self.mock_config)
        mock_d.sync_with_jira.assert_any_call('mock_issue_pagure', self.mock_config)
        mock_u.github_issues.assert_called_with('key_github', self.mock_config)
        mock_sleep.assert_not_called()
        mock_report_failure.assert_called_with(self.mock_config)


    @mock.patch(PATH + 'u')
    @mock.patch(PATH + 'd')
    @mock.patch(PATH + 'fedmsg')
    def test_listen_no_handlers(self,
                                mock_fedmsg,
                                mock_d,
                                mock_u):
        """
        Test 'listen' function where suffix is not in handlers
        """
        # Set up return values
        mock_fedmsg.tail_messages.return_value = [("dummy", "dummy", "mock_topic", self.mock_message)]

        # Call the function
        m.listen(self.mock_config)

        # Assert everything was called correctly
        mock_d.sync_with_jira.assert_not_called()
        mock_u.handle_github_message.assert_not_called()
        mock_u.handle_pagure_message.assert_not_called()

    @mock.patch(PATH + 'u')
    @mock.patch(PATH + 'd')
    @mock.patch(PATH + 'fedmsg')
    def test_listen_no_issue(self,
                             mock_fedmsg,
                             mock_d,
                             mock_u):
        """
        Test 'listen' function where the handler returns none
        """
        # Set up return values
        mock_fedmsg.tail_messages.return_value = [("dummy", "dummy", "d.d.d.pagure.issue.drop", self.mock_message)]
        mock_u.handle_pagure_message.return_value = None

        # Call the function
        m.listen(self.mock_config)

        # Assert everything was called correctly
        mock_d.sync_with_jira.assert_not_called()
        mock_u.handle_github_message.assert_not_called()
        mock_u.handle_pagure_message.assert_called_with(self.mock_message, self.mock_config)

    @mock.patch(PATH + 'u')
    @mock.patch(PATH + 'd')
    @mock.patch(PATH + 'fedmsg')
    def test_listen(self,
                    mock_fedmsg,
                    mock_d,
                    mock_u):
        """
        Test 'listen' function where everything goes smoothly
        """
        # Set up return values
        mock_fedmsg.tail_messages.return_value = [("dummy", "dummy", "d.d.d.github.issue.comment", self.mock_message)]
        mock_u.handle_github_message.return_value = 'dummy_issue'

        # Call the function
        m.listen(self.mock_config)

        # Assert everything was called correctly
        mock_d.sync_with_jira.assert_called_with('dummy_issue', self.mock_config)
        mock_u.handle_github_message.assert_called_with(self.mock_message, self.mock_config)
        mock_u.handle_pagure_message.assert_not_called()

    @mock.patch(PATH + 'send_mail')
    @mock.patch(PATH + 'jinja2')
    def test_report_failure(self,
                            mock_jinja2,
                            mock_send_mail):
        """
        Tests 'report_failure' function
        """
        # Set up return values
        mock_templateLoader = MagicMock()
        mock_templateEnv = MagicMock()
        mock_template = MagicMock()
        mock_template.render.return_value = 'mock_html'
        mock_templateEnv.get_template.return_value = mock_template
        mock_jinja2.FileSystemLoader.return_value = mock_templateLoader
        mock_jinja2.Environment.return_value = mock_templateEnv

        # Call the function
        m.report_failure({'sync2jira': {'admins': [{'mock_user': 'mock_email'}]}})

        # Assert everything was called correctly
        mock_send_mail.assert_called_with(cc=None,
                                          recipients=['mock_email'],
                                          subject='Sync2Jira Has Failed!',
                                          text='mock_html')