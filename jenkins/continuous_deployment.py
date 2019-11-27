"""
This is a helper program to listen for UMB trigger. Test and then deploy Sync2Jira
"""
# Built-In Modules
import json
import os

# Local Modules
from jira_values import PAGURE, GITHUB

# 3rd Party Modules
import jira.client

# Global Variables
URL = os.environ['JIRA_STAGE_URL']
USERNAME = os.environ['JIRA_USER']
PASSWORD = os.environ['JIRA_PASS']

def main(msg):
    """
    Main message to listen and react to messages.

    :param Dict msg: UMB Message
    """
    # Check if this is a Sync2Jira image update
    if msg['msg']['repo'] != 'quay.io/redhat-aqe/sync2jira':
        return

    # Make our JIRA client
    client = get_jira_client()

    # Else we need to first use our build image to test
    # TODO: Something here to build and start Sync2Jira and use template

    print("Starting comparison with Pagure...")
    # Now we need to make sure that Sync2Jira didn't update anything,
    # compare to our old values
    response = compare_data(client, PAGURE)

    if response is False:
        print('When comparing Pagure something went wrong. Check logs.')
        raise ValueError

    print("Starting comparison with Github...")
    response = compare_data(client, GITHUB)

    if response is False:
        print('When comparing GitHub something went wrong. Check logs.')
        raise ValueError

    print("Tests have passed :)")


def compare_data(client, data):
    """
    Helper function to loop over values and compare to ensure they are the same

    :param jira.client.JIRA client: JIRA client
    :param Dict data: Data used to compare against
    :return: True/False if we
    """
    # First get our existing JIRA issue
    jira_ticket = data['JIRA']
    existing = client.search_issues(f"Key = {jira_ticket}")

    # Throw an error if too many issues were found
    if len(existing) > 1:
        print(f"Too many issues were found with ticket {jira_ticket}")
        raise ValueError

    existing = existing[0]

    # Check Tags
    if data['tags'] != existing.fields.labels:
        print(f"Error when comparing tags for {jira_ticket}")
        print(f"Expected: {data['tags']}")
        print(f"Actual: {existing.fields.labels}")
        raise ValueError

    # Check FixVersion
    formatted_fixVersion = format_fixVersion(existing.fields.fixVersions)

    if data['fixVersions'] != formatted_fixVersion:
        print(f"Error when comparing fixVersions for {jira_ticket}")
        print(f"Expected: {data['fixVersions']}")
        print(f"Actual: {formatted_fixVersion}")
        raise ValueError

    # Check Assignee
    if not existing.fields.assignee:
        print(f"Error when comparing assignee for {jira_ticket}")
        print(f"Expected: {data['assignee']}")
        print(f"Actual: {existing.fields.assignee}")
        raise ValueError

    elif data['assignee'] != existing.fields.assignee.name:
        print(f"Error when comparing assignee for {jira_ticket}")
        print(f"Expected: {data['assignee']}")
        print(f"Actual: {existing.fields.assignee.name}")
        raise ValueError

    # Check Title
    if data['title'] != existing.fields.summary:
        print(f"Error when comparing title for {jira_ticket}")
        print(f"Expected: {data['title']}")
        print(f"Actual: {existing.fields.summary}")
        raise ValueError

    # Check Descriptions
    if data['description'] != existing.fields.description:
        print(f"Error when comparing descriptions for {jira_ticket}")
        print(f"Expected: {data['description']}")
        print(f"Actual: {existing.fields.description}")
        raise ValueError


def format_fixVersion(existing):
    """
    Helper function to format fixVersions

    :param jira.version existing: Existing fixVersions
    :return: Formatted fixVersions
    :rtype: List
    """
    new_list = []
    for version in existing:
        new_list.append(version.name)
    return new_list


def get_jira_client():
    """
    Helper function to get JIRA client

    :return: JIRA Client
    :rtype: jira.client.JIRA
    """
    return jira.client.JIRA(**{
        'options': {
            'server': URL,
            'verify': False,
        },
        'basic_auth': (USERNAME, PASSWORD),
    })


if __name__ == '__main__':
    # Call our main method after parsing out message
    msg = json.loads(os.environ["CI_MESSAGE"])
    main({})

