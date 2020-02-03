#!/usr/bin/python3
"""
This script acts as a client to confluence, connects to confluence and create
pages
"""
import os
import re
import requests
from requests.auth import HTTPBasicAuth
import jinja2
import datetime


class ConfluenceClient:

    """ A conflence component used to connect to confluence and perform
    confluence related tasks
    """

    def __init__(
        self,
        confluence_space=os.environ.get("CONFLUENCE_SPACE"),
        confluence_page_title=os.environ.get("CONFLUENCE_PAGE_TITLE"),
        confluence_url=os.environ.get("CONFLUENCE_URL"),
        username=os.environ.get("CONFLUENCE_USERNAME"),
        password=os.environ.get("CONFLUENCE_PASSWORD"),
        auth_type="basic",
    ):
        """ Returns confluence client object
        :param string confluence_space : space to be used in confluence
        :param string confluence_page_title : Title of page to be created in
        confluence
        :param string confluence_url : url to connect confluence
        :param string username : optional username for basic auth
        :param string password : optional password for basic auth
        :param string auth_type : indicate auth scheme (basic/kerberos)
        """
        self.confluence_space = confluence_space
        self.confluence_page_title = confluence_page_title
        self.confluence_url = confluence_url
        self.confluence_rest_url = self.confluence_url + "/rest/api/content/"
        self.username = username
        self.password = password
        self.authtype = auth_type
        self.update_stat = False
        self._req_kwargs = None

        # Find our page ID and save it
        resp = self.find_page()
        if not resp:
            raise ValueError("Invalid page name")
        self.page_id = resp

    def update_stat_value(self, new_value):
        """ Update the 'update_stat' attribute.
        :param Bool new_value: Bool value
        """
        self.update_stat = new_value

    @property
    def req_kwargs(self):
        """ Set the key-word arguments for python-requests depending on the
        auth type. This code should run on demand exactly once, which is
        why it is a property.
        :return dict _req_kwargs: dict with the right options to pass in
        """
        if self._req_kwargs is None:
            if self.authtype == "basic":
                self._req_kwargs = {"auth": self.get_auth_object()}
        return self._req_kwargs

    def update_stat_page(self, confluence_data):
        """
        Updates the statistic page with more data
        :param dict confluence_data: Variable amount of new data
        """
        # Get the HTML to update
        page_info = self.get_page_info(self.page_id)
        page_html = page_info['body']['storage']['value']
        # Maintain and update our final data
        confluence_data_update = {
            'Created Issues': 0,
            'Descriptions': 0,
            'Comments': 0,
            'Reporters': 0,
            'Status': 0,
            'Assignees': 0,
            'Transitions': 0,
            'Title': 0,
            'Tags': 0,
            'FixVersion': 0,
            'Misc. Fields': 0,
            'Total': 0
        }
        confluence_data_times = {
            'Created Issues': 60,
            'Descriptions': 30,
            'Comments': 30,
            'Reporters': 30,
            'Assignees': 15,
            'Status': 30,
            'Transitions': 30,
            'Title': 15,
            'Tags': 10,
            'FixVersion': 10,
            'Misc. Fields': 15,
        }
        # Use these HTML patterns to search for previous values
        confluence_html_patterns = {
            'Created Issues': "Created Issues</td><td>",
            'Descriptions': "Descriptions</td><td>",
            'Comments': "Comments</td><td>",
            'Reporters': "Reporters</td><td>",
            'Assignees': "Assignees</td><td>",
            'Status': "Status</td><td>",
            'Transitions': "Transitions</td><td>",
            'Title': "Titles</td><td>",
            'Tags': "Tags</td><td>",
            'FixVersion': "Fix Version</td><td>",
            'Misc. Fields': "Misc. Fields</td><td>",
        }
        # Update all our data
        total = 0
        for topic, html in confluence_html_patterns.items():
            # Search for previous data
            ret = re.search(html, page_html)
            start_index = ret.span()[1]
            new_val = ""
            while page_html[start_index] != "<":
                new_val += page_html[start_index]
                start_index += 1
            confluence_data_update[topic] = int(new_val)
            total += int(new_val)

        # Now add new data
        for topic in confluence_html_patterns.keys():
            if topic in confluence_data:
                confluence_data_update[topic] += confluence_data[topic]
                total += confluence_data[topic]
        confluence_data_update["Total"] = total

        # Calculate Total Time
        total_time = 0
        for topic in confluence_data_times.keys():
            total_time += confluence_data_update[topic] * confluence_data_times[topic]
        total_time = datetime.timedelta(seconds=total_time)
        confluence_data_update["Total Time"] = str(total_time) + " (HR:MIN:SEC)"

        # Build our updated HTML page
        templateLoader = jinja2.FileSystemLoader(
            searchpath='usr/local/src/sync2jira/sync2jira/')
        templateEnv = jinja2.Environment(loader=templateLoader)
        template = templateEnv.get_template('confluence_stat.jinja')
        html_text = template.render(confluence_data=confluence_data_update)

        # Finally update our page
        if html_text.replace(" ", "") != page_html.replace(" ", ""):
            self.update_page(self.page_id, html_text)

    def find_page(self):
        """ finds the page with confluence_page_title in confluence_space
        return string page_id : id of the page if found, otherwise None
        """
        search_url = (
            self.confluence_url
            + "/rest/api/content/search?cql=title='"
            + self.confluence_page_title
            + "' and "
            + "space="
            + self.confluence_space
        )
        resp = requests.get(search_url, **self.req_kwargs)
        resp.raise_for_status()
        if len(resp.json()["results"]) > 0:
            return resp.json()["results"][0].get("id", None)
        else:
            return None

    def get_page_info(self, page_id):
        """Gives information like ancestors,version of a  page
        :param string page_id: id of the confluence page
        :return json conf_resp: response from the confluence
        """
        conf_rest_url = (
            self.confluence_url
            + "/rest/api/content/"
            + page_id
            + "?expand=ancestors,version,body.storage"
        )
        resp = requests.get(conf_rest_url, **self.req_kwargs)
        resp.raise_for_status()
        return resp.json()

    def update_page(self, page_id, html_str):
        """
        Updates the page with id page_id
        :param string page_id: id  of the page
        :param string html_str : html_str content of the page
        :return json conf_resp: response from the confluence
        """
        rest_url = self.confluence_rest_url + page_id
        info = self.get_page_info(page_id)
        updated_page_version = int(info["version"]["number"] + 1)

        data = {
            "id": str(page_id),
            "type": "page",
            "title": info["title"],
            "version": {"number": updated_page_version},
            "body": {"storage": {"representation": "storage", "value": html_str}},
        }
        resp = requests.put(rest_url, json=data, **self.req_kwargs)
        if not resp.ok:
            print("Confluence response: \n", resp.json())

        resp.raise_for_status()

        return resp.json()

    def get_auth_object(self):
        """Returns Auth object based on auth type
        :return : Auth Object
        """
        if self.authtype == "basic":
            return HTTPBasicAuth(self.username, self.password)


if os.environ.get('CONFLUENCE_SPACE') != 'mock_confluence_space':
    confluence_client = ConfluenceClient()
else:
    # Else we are testing, and create a mock_client
    class mock_confluence_client(object):
        mock_data = False
    confluence_client = mock_confluence_client()
