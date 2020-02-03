import unittest

import mock

try:
    # Python 3.3 >
    from unittest.mock import MagicMock  # noqa: F401
except ImportError:
    from mock import MagicMock  # noqa: F401

PATH = 'sync2jira.confluence_client.'

from sync2jira.confluence_client import ConfluenceClient


class TestConfluenceClient(unittest.TestCase):
    """
    This class tests the confluence_client.py file
    """

    @mock.patch(PATH + 'ConfluenceClient.find_page')
    def setUp(self,
              mock_find_page):
        mock_find_page.return_value = "mock_page_id"
        self.confluence_client = ConfluenceClient()

        self.mock_resp_bad = MagicMock()
        self.mock_resp_bad.raise_for_status.side_effect = ValueError()
        self.mock_resp_bad.ok = False

    def test_update_state_value(self):
        """
        This function tests the 'update_stat_value' function
        """
        # Call the function
        self.confluence_client.update_stat_value(True)

        # Assert Everything was called correctly
        self.assertEqual(self.confluence_client.update_stat, True)

    @mock.patch(PATH + 'ConfluenceClient.get_auth_object')
    @mock.patch(PATH + 'requests')
    def test_req_kwargs_basic(self,
                              mock_requests,
                              mock_get_auth_object):
        """
        This function tests 'req_kwargs' property with a basic client
        """
        # Set up return values
        mock_get_auth_object.return_value = 'mock_auth_object'

        # Call the function
        response = self.confluence_client.req_kwargs

        # Assert everything was called correctly
        mock_requests.get.assert_not_called()
        mock_get_auth_object.assert_called()
        self.assertEqual(response, {'auth': 'mock_auth_object'})

    @mock.patch(PATH + 'requests')
    @mock.patch(PATH + 'ConfluenceClient.req_kwargs')
    def test_find_page_found(self,
                             mock_req_kwargs,
                             mock_requests):
        """
        This function tests the 'find_page' function where we find a page
        """
        # Set up return values
        mock_resp = MagicMock()
        mock_resp.json.return_value = {'results': [{'id': 'mock_id'}]}
        mock_requests.get.return_value = mock_resp

        # Call the function
        response = self.confluence_client.find_page()

        # Assert everything was called correctly
        mock_requests.get.assert_called_with(
            "http://mock_confluence_url/rest/api/content/search?cql=title='mock_confluence_page_title' and space=mock_confluence_space")
        mock_resp.raise_for_status.assert_called()
        mock_resp.json.assert_called()
        self.assertEqual(response, 'mock_id')

    @mock.patch(PATH + 'requests')
    @mock.patch(PATH + 'ConfluenceClient.req_kwargs')
    def test_find_page_not_found(self,
                                 mock_req_kwargs,
                                 mock_requests):
        """
        This function tests the 'find_page' function where we don't find a page
        """
        # Set up return values
        mock_resp = MagicMock()
        mock_resp.json.return_value = {'results': []}
        mock_requests.get.return_value = mock_resp

        # Call the function
        response = self.confluence_client.find_page()

        # Assert everything was called correctly
        mock_requests.get.assert_called_with(
            "http://mock_confluence_url/rest/api/content/search?cql=title='mock_confluence_page_title' and space=mock_confluence_space")
        mock_resp.raise_for_status.assert_called()
        mock_resp.json.assert_called()
        self.assertEqual(response, None)

    @mock.patch(PATH + 'requests')
    @mock.patch(PATH + 'ConfluenceClient.req_kwargs')
    def test_find_page_error(self,
                             mock_req_kwargs,
                             mock_requests):
        """
        This function tests the 'find_page' function where we get an Error
        """
        # Set up return values
        mock_resp = MagicMock()
        mock_resp.json.return_value = {'results': []}
        mock_requests.get.return_value = self.mock_resp_bad

        # Call the function
        with self.assertRaises(ValueError):
            self.confluence_client.find_page()

        # Assert everything was called correctly
        mock_requests.get.assert_called_with(
            "http://mock_confluence_url/rest/api/content/search?cql=title='mock_confluence_page_title' and space=mock_confluence_space")
        self.mock_resp_bad.raise_for_status.assert_called()
        self.mock_resp_bad.json.assert_not_called()

    @mock.patch(PATH + 'requests')
    @mock.patch(PATH + 'ConfluenceClient.req_kwargs')
    def test_get_page_info(self,
                           mock_req_kwargs,
                           mock_requests):
        """
        This function tests the 'get_page_info' function where we have no Errors
        """
        # Set up return values
        mock_resp = MagicMock()
        mock_resp.json.return_value = 'mock_json'
        mock_requests.get.return_value = mock_resp

        # Call the function
        response = self.confluence_client.get_page_info('mock_page_id')

        # Assert everything was called correctly
        mock_requests.get.assert_called_with(
            'http://mock_confluence_url/rest/api/content/mock_page_id?expand=ancestors,version,body.storage')
        self.assertEqual(response, 'mock_json')
        mock_resp.raise_for_status.assert_called()

    @mock.patch(PATH + 'requests')
    @mock.patch(PATH + 'ConfluenceClient.req_kwargs')
    def test_get_page_info_error(self,
                                 mock_req_kwargs,
                                 mock_requests):
        """
        This function tests the 'get_page_info' function where we have Errors
        """
        # Set up return values
        mock_resp = MagicMock()
        mock_resp.json.return_value = 'mock_json'
        mock_requests.get.return_value = self.mock_resp_bad

        # Call the function
        with self.assertRaises(ValueError):
            self.confluence_client.get_page_info('mock_page_id')

        # Assert everything was called correctly
        mock_requests.get.assert_called_with(
            'http://mock_confluence_url/rest/api/content/mock_page_id?expand=ancestors,version,body.storage')
        self.mock_resp_bad.raise_for_status.assert_called()

    @mock.patch(PATH + 'ConfluenceClient.get_page_info')
    @mock.patch(PATH + 'requests')
    @mock.patch(PATH + 'ConfluenceClient.req_kwargs')
    def test_update_page(self,
                         mock_req_kwargs,
                         mock_requests,
                         mock_get_page_info):
        """
        This function tests the 'update_page' function where we have no Errors
        """
        # Set up return values
        mock_get_page_info.return_value = {
            'version': {'number': 1},
            'title': 'mock_title'}
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = 'mock_json'
        mock_requests.put.return_value = mock_resp

        # Call the function
        response = self.confluence_client.update_page(
            page_id='mock_page_id',
            html_str='mock_html_str',
        )

        # Assert everything was called correctly
        mock_requests.put.assert_called_with(
            'http://mock_confluence_url/rest/api/content/mock_page_id',
            json={'id': 'mock_page_id', 'type': 'page',
                  'title': 'mock_title', 'version': {'number': 2},
                  'body': {'storage':
                               {'representation': 'storage', 'value': 'mock_html_str'}}})
        mock_resp.raise_for_status.assert_called()
        self.assertEqual(response, 'mock_json')

    @mock.patch(PATH + 'ConfluenceClient.get_page_info')
    @mock.patch(PATH + 'requests')
    @mock.patch(PATH + 'ConfluenceClient.req_kwargs')
    def test_update_page_error(self,
                               mock_req_kwargs,
                               mock_requests,
                               mock_get_page_info):
        """
        This function tests the 'update_page' function where we have Errors
        """
        # Set up return values
        mock_get_page_info.return_value = {
            'version': {'number': 1},
            'title': 'mock_title'}
        mock_requests.put.return_value = self.mock_resp_bad

        # Call the function
        with self.assertRaises(ValueError):
            self.confluence_client.update_page(
                page_id='mock_page_id',
                html_str='mock_html_str',
            )

        # Assert everything was called correctly
        mock_requests.put.assert_called_with(
            'http://mock_confluence_url/rest/api/content/mock_page_id',
            json={
                'id': 'mock_page_id',
                'type': 'page',
                'title': 'mock_title',
                'version': {'number': 2},
                'body':
                    {'storage': {'representation': 'storage', 'value': 'mock_html_str'}}})
        self.mock_resp_bad.raise_for_status.assert_called()

    @mock.patch(PATH + 'HTTPBasicAuth')
    def test_get_auth_object_basic(self,
                                   mock_basic,):
        """
        This function tests 'get_auth_object' with basic auth
        """
        # Set up return values
        mock_basic.return_value = 'mock_basic_auth'

        # Call the function
        response = self.confluence_client.get_auth_object()

        # Assert everything was called correctly
        self.assertEqual(response, 'mock_basic_auth')
        mock_basic.assert_called_with('mock_confluence_username', 'mock_confluence_password')

    @mock.patch(PATH + 'ConfluenceClient.update_page')
    @mock.patch(PATH + 'jinja2')
    @mock.patch(PATH + 'ConfluenceClient.get_page_info')
    def test_update_stat_page(self,
                              mock_get_page_info,
                              mock_jinja2,
                              mock_update_page):
        """
        This function tests 'update_stat_page' function
        """
        # Set up return values
        mock_html = """
                        Created Issues</td><td>1<
                        Descriptions</td><td>1<
                        Comments</td><td>1<
                        Reporters</td><td>1<
                        Assignees</td><td>1<
                        Status</td><td>1<
                        Transitions</td><td>1<
                        Titles</td><td>1<
                        Tags</td><td>1<
                        Fix Version</td><td>1<
                        Misc. Fields</td><td>1<
                        Total</strong></td><td colspan="1"><strong>1<
                    """
        mock_get_page_info.return_value = {'body': {'storage': {'value': mock_html}}}
        mock_confluence_data = {
            'Created Issues': 10,
            'Descriptions': 10,
            'Comments': 10,
            'Reporters': 10,
            'Status': 10,
            'Assignees': 10,
            'Transitions': 10,
            'Title': 10,
            'Tags': 10,
            'FixVersion': 10,
            'Misc. Fields': 10,
        }
        mock_templateLoader = MagicMock()
        mock_templateEnv = MagicMock()
        mock_template = MagicMock()
        mock_template.render.return_value = 'mock_render'
        mock_templateEnv.get_template.return_value = mock_template
        mock_jinja2.FileSystemLoader.return_value = mock_templateLoader
        mock_jinja2.Environment.return_value = mock_templateEnv

        # Call the function
        self.confluence_client.update_stat_page(mock_confluence_data)

        # Assert Everything was called correctly
        mock_jinja2.FileSystemLoader.assert_called_with(searchpath='usr/local/src/sync2jira/sync2jira/')
        mock_jinja2.Environment.assert_called_with(loader=mock_templateLoader)
        mock_templateEnv.get_template.assert_called_with('confluence_stat.jinja')
        mock_template.render.assert_called_with(confluence_data={
            'Created Issues': 11, 'Descriptions': 11, 'Comments': 11,
            'Reporters': 11, 'Status': 11, 'Assignees': 11, 'Transitions': 11,
            'Title': 11, 'Tags': 11, 'FixVersion': 11, 'Misc. Fields': 11,
            'Total': 121, 'Total Time': '0:50:25 (HR:MIN:SEC)'})
        mock_update_page.assert_called_with('mock_page_id', 'mock_render')
