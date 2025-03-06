"""
This is a helper program to listen for UMB trigger. Test and then deploy Sync2Jira
"""

# Built-In Modules
import logging
import os

# 3rd Party Modules
import jira.client

# Local Modules
from jira_values import PAGURE, GITHUB
from runtime_config import runtime_config

from sync2jira.main import main as m

# Global Variables
URL = os.environ["JIRA_STAGE_URL"]
TOKEN = os.environ["JIRA_TOKEN"]
log = logging.getLogger(__name__)
hdlr = logging.FileHandler("integration_test.log")
formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
hdlr.setFormatter(formatter)
log.addHandler(hdlr)
log.setLevel(logging.DEBUG)


def main():
    """
    Main message to listen and react to messages.
    """
    log.info("[OS-BUILD] Running sync2jira.main...")

    # Make our JIRA client
    client = get_jira_client()

    # First init with what we have
    m(runtime_test=True, runtime_config=runtime_config)

    # Now we need to make sure that Sync2Jira didn't update anything,
    failed = False

    # Compare to our old values
    log.info("[OS-BUILD] Comparing values with Pagure...")
    try:
        compare_data(client, PAGURE)
    except Exception as e:
        failed = True
        log.info(
            f"[OS-BUILD] When comparing Pagure something went wrong.\nException {e}"
        )

    log.info("[OS-BUILD] Comparing values with GitHub...")
    try:
        compare_data(client, GITHUB)
    except Exception as e:
        failed = True
        log.info(
            f"[OS-BUILD] When comparing GitHub something went wrong.\nException {e}"
        )

    if failed:
        log.info("[OS-BUILD] Tests have failed :(")
        raise Exception()
    else:
        log.info("[OS-BUILD] Tests have passed :)")


def compare_data(client, data):
    """
    Helper function to loop over values and compare to ensure they are the same
    :param jira.client.JIRA client: JIRA client
    :param Dict data: Data used to compare against
    :return: True/False if we
    """
    # First get our existing JIRA issue
    jira_ticket = data["JIRA"]
    existing = client.search_issues(f"Key = {jira_ticket}")

    # Throw an error if too many issues were found
    if len(existing) > 1:
        raise Exception(f"Too many issues were found with ticket {jira_ticket}")

    existing = existing[0]
    log.info("TEST - " + existing.fields.summary)
    # Check Tags
    if data["tags"] != existing.fields.labels:
        raise Exception(
            f"Error when comparing tags for {jira_ticket}\n"
            f"Expected: {data['tags']}\n"
            f"Actual: {existing.fields.labels}"
        )

    # Check FixVersion
    formatted_fixVersion = format_fixVersion(existing.fields.fixVersions)

    if data["fixVersions"] != formatted_fixVersion:
        raise Exception(
            f"Error when comparing fixVersions for {jira_ticket}\n"
            f"Expected: {data['fixVersions']}\n"
            f"Actual: {formatted_fixVersion}"
        )

    # Check Assignee
    if not existing.fields.assignee:
        raise Exception(
            f"Error when comparing assignee for {jira_ticket}\n"
            f"Expected: {data['assignee']}\n"
            f"Actual: {existing.fields.assignee}"
        )

    elif data["assignee"] != existing.fields.assignee.name:
        raise Exception(
            f"Error when comparing assignee for {jira_ticket}\n"
            f"Expected: {data['assignee']}\n"
            f"Actual: {existing.fields.assignee.name}"
        )

    # Check Title
    if data["title"] != existing.fields.summary:
        raise Exception(
            f"Error when comparing title for {jira_ticket}\n"
            f"Expected: {data['title']}\n"
            f"Actual: {existing.fields.summary}"
        )

    # Check Descriptions
    if data["description"].replace("\n", "").replace(" ", "").replace(
        "\r", ""
    ) != existing.fields.description.replace("\n", "").replace(" ", "").replace(
        "\r", ""
    ):
        raise Exception(
            f"Error when comparing descriptions for {jira_ticket}\n"
            f"Expected: {data['description']}\n"
            f"Actual: {existing.fields.description}"
        )


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
    return jira.client.JIRA(
        **{
            "options": {
                "server": URL,
                "verify": False,
            },
            "token_auth": TOKEN,
        }
    )


if __name__ == "__main__":
    # Call our main method after parsing out message
    main()
