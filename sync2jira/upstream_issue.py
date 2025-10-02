# This file is part of sync2jira.
# Copyright (C) 2016 Red Hat, Inc.
#
# sync2jira is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# sync2jira is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with sync2jira; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110.15.0 USA
#
# Authors:  Ralph Bean <rbean@redhat.com>

from copy import deepcopy
import logging
from urllib.parse import urlencode

from github import Github, UnknownObjectException
import requests

import sync2jira.intermediary as i

log = logging.getLogger("sync2jira")
graphqlurl = "https://api.github.com/graphql"

ghquery = """
    query MyQuery(
        $orgname: String!, $reponame: String!, $issuenumber: Int!
    ) {
        repository(owner: $orgname, name: $reponame) {
          issue(number: $issuenumber) {
            title
            body
            projectItems(first: 3) {
              nodes {
                project {
                  title
                  number
                  url
                }
                fieldValues(first: 100) {
                  nodes {
                    ... on ProjectV2ItemFieldSingleSelectValue {
                      name
                      fieldName: field {
                        ... on ProjectV2FieldCommon {
                          name
                        }
                      }
                    }
                    ... on ProjectV2ItemFieldTextValue {
                      text
                      fieldName: field {
                        ... on ProjectV2FieldCommon {
                          name
                        }
                      }
                    }
                    ... on ProjectV2ItemFieldNumberValue {
                      number
                      fieldName: field {
                        ... on ProjectV2FieldCommon {
                          name
                        }
                      }
                    }
                    ... on ProjectV2ItemFieldDateValue {
                      date
                      fieldName: field {
                        ... on ProjectV2FieldCommon {
                          name
                        }
                      }
                    }
                    ... on ProjectV2ItemFieldUserValue {
                      users(first: 10) {
                        nodes {
                          login
                        }
                      }
                      fieldName: field {
                        ... on ProjectV2FieldCommon {
                          name
                        }
                      }
                    }
                    ... on ProjectV2ItemFieldIterationValue {
                      title
                      duration
                      startDate
                      fieldName: field {
                        ... on ProjectV2FieldCommon {
                          name
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
"""


def handle_github_message(body, config, is_pr=False):
    """
    Handle GitHub message from FedMsg.

    :param Dict body: FedMsg Message body
    :param Dict config: Config File
    :param Bool is_pr: msg refers to a pull request
    :returns: Issue object
    :rtype: sync2jira.intermediary.Issue
    """
    owner = body["repository"]["owner"]["login"]
    repo = body["repository"]["name"]
    upstream = "{owner}/{repo}".format(owner=owner, repo=repo)

    mapped_repos = config["sync2jira"]["map"]["github"]
    if upstream not in mapped_repos:
        log.debug("%r not in Github map: %r", upstream, mapped_repos.keys())
        return None
    key = "pullrequest" if is_pr else "issue"
    if key not in mapped_repos[upstream].get("sync", []):
        log.debug(
            "%r not in Github sync map: %r",
            key,
            mapped_repos[upstream].get("sync", []),
        )
        return None

    _filter = config["sync2jira"].get("filters", {}).get("github", {}).get(upstream, {})

    issue = body["issue"]
    for key, expected in _filter.items():
        if key == "labels":
            # special handling for label: we look for it in the list of msg labels
            actual = {label["name"] for label in issue["labels"]}
            if actual.isdisjoint(expected):
                log.debug("Labels %s not found on issue: %s", expected, upstream)
                return None
        elif key == "milestone":
            # special handling for milestone: use the number
            milestone = issue.get(key) or {}  # Key might exist with value `None`
            actual = milestone.get("number")
            if expected != actual:
                log.debug("Milestone %s not set on issue: %s", expected, upstream)
                return None
        else:
            # direct comparison
            actual = issue.get(key)
            if actual != expected:
                log.debug(
                    "Actual %r %r != expected %r on issue %s",
                    key,
                    actual,
                    expected,
                    upstream,
                )
                return None

    if is_pr and not issue.get("closed_at"):
        log.debug(
            "%r is a pull request.  Ignoring.", issue.get("html_url", "<missing URL>")
        )
        return None

    token = config["sync2jira"].get("github_token")
    headers = {"Authorization": "token " + token} if token else {}
    github_client = Github(token, retry=5)
    reformat_github_issue(issue, upstream, github_client)
    add_project_values(issue, upstream, headers, config)
    return i.Issue.from_github(upstream, issue, config)


def github_issues(upstream, config):
    """
    Returns a generator for all GitHub issues in upstream repo.

    :param String upstream: Upstream Repo
    :param Dict config: Config Dict
    :returns: a generator for GitHub Issue objects
    :rtype: Generator[sync2jira.intermediary.Issue]
    """
    token = config["sync2jira"].get("github_token")
    headers = {"Authorization": "token " + token} if token else {}
    github_client = Github(token, retry=5)
    github_items=generate_github_items("issues", upstream, config)
    for issue in github_items:
        if "pull_request" in issue or "/pull/" in issue.get("html_url", ""):
            # We don't want to copy these around
            orgname, reponame = upstream.rsplit("/", 1)
            log.debug(
                "Issue %s/%s#%s is a pull request; skipping",
                orgname,
                reponame,
                issue["number"],
            )
            continue
        reformat_github_issue(issue, upstream, github_client)
        add_project_values(issue, upstream, headers, config)
        yield i.Issue.from_github(upstream, issue, config)


def add_project_values(issue, upstream, headers, config):
    """Add values to an issue from its corresponding card in a GitHub Project

    :param dict issue: Issue
    :param str upstream: Upstream repo name
    :param dict headers: HTTP Request headers, including access token, if any
    :param dict config: Config
    """
    upstream_config = config["sync2jira"]["map"]["github"][upstream]
    project_number = upstream_config.get("github_project_number")
    issue_updates = upstream_config.get("issue_updates", {})
    if "github_project_fields" not in issue_updates:
        return
    issue["storypoints"] = None
    issue["priority"] = None
    issuenumber = issue["number"]
    github_project_fields = upstream_config["github_project_fields"]
    orgname, reponame = upstream.rsplit("/", 1)
    variables = {"orgname": orgname, "reponame": reponame, "issuenumber": issuenumber}
    response = requests.post(
        graphqlurl, headers=headers, json={"query": ghquery, "variables": variables}
    )
    if response.status_code != 200:
        log.info(
            "HTTP error while fetching issue %s/%s#%s: %s",
            orgname,
            reponame,
            issuenumber,
            response.text,
        )
        return
    data = response.json()
    gh_issue = data.get("data", {}).get("repository", {}).get("issue")
    if not gh_issue:
        log.info(
            "GitHub error while fetching issue %s/%s#%s: %s",
            orgname,
            reponame,
            issuenumber,
            response.text,
        )
        return
    project_node = _get_current_project_node(
        upstream, project_number, issuenumber, gh_issue
    )
    if not project_node:
        return
    item_nodes = project_node.get("fieldValues", {}).get("nodes", {})
    for item in item_nodes:
        gh_field_name = item.get("fieldName", {}).get("name")
        if not gh_field_name:
            continue
        prio_field = github_project_fields.get("priority", {}).get("gh_field")
        if gh_field_name == prio_field:
            issue["priority"] = item.get("name")
            continue
        sp_field = github_project_fields.get("storypoints", {}).get("gh_field")
        if gh_field_name == sp_field:
            try:
                issue["storypoints"] = int(item["number"])
            except (ValueError, KeyError) as err:
                log.info(
                    "Error while processing storypoints for issue %s/%s#%s: %s",
                    orgname,
                    reponame,
                    issuenumber,
                    err,
                )
            continue


def reformat_github_issue(issue, upstream, github_client):
    """Tweak Issue data format to better match Pagure"""

    # Update comments:
    # If there are no comments just make an empty array
    if not issue["comments"]:
        issue["comments"] = []
    else:
        # We have multiple comments and need to make api call to get them
        try:
            repo = github_client.get_repo(upstream)
        except UnknownObjectException:
            logging.warning(
                "GitHub repo %r not found (has it been deleted or made private?)",
                upstream,
            )
            raise
        github_issue = repo.get_issue(number=issue["number"])
        issue["comments"] = reformat_github_comments(github_issue.get_comments())

    # Update the rest of the parts
    reformat_github_common(issue, github_client)


def reformat_github_comments(comments):
    """Helper function which encapsulates reformatting comments"""
    return [
        {
            "author": comment.user.name or comment.user.login,
            "name": comment.user.login,
            "body": comment.body,
            "id": comment.id,
            "date_created": comment.created_at,
            "changed": None,
        }
        for comment in comments
    ]


def reformat_github_common(item, github_client):
    """Helper function which tweaks the data format of the parts of Issues and
    PRs which are common so that they better match Pagure
    """
    # Update reporter:
    # Search for the user
    reporter = github_client.get_user(item["user"]["login"])
    # Update the reporter field in the message (to match Pagure format)
    if reporter.name and reporter.name != "None":
        item["user"]["fullname"] = reporter.name
    else:
        item["user"]["fullname"] = item["user"]["login"]

    # Update assignee(s):
    assignees = []
    for person in item.get("assignees", []):
        assignee = github_client.get_user(person["login"])
        if assignee.name and assignee.name != "None":
            assignees.append({"fullname": assignee.name})
    # Update the assignee field in the message (to match Pagure format)
    item["assignees"] = assignees

    # Update the label field in the message (to match Pagure format)
    if item["labels"]:
        # Loop through all the labels on GitHub and add them
        # to the new label list and then reassign the message
        new_label = []
        for label in item["labels"]:
            new_label.append(label["name"])
        item["labels"] = new_label

    # Update the milestone field in the message (to match Pagure format)
    if item.get("milestone"):
        item["milestone"] = item["milestone"]["title"]


def generate_github_items(api_method, upstream, config):
    """
    Returns a generator which yields all GitHub issues in upstream repo.

    :param String api_method: API method name
    :param String upstream: Upstream Repo
    :param Dict config: Config Dict
    :returns: a generator for GitHub Issue/PR objects
    :rtype: Generator[Any, Any, None]
    """
    token = config["sync2jira"].get("github_token")
    if not token:
        headers = {}
        log.warning("No github_token found.  We will be rate-limited...")
    else:
        headers = {"Authorization": "token " + token}

    params = config["sync2jira"].get("filters", {}).get("github", {}).get(upstream, {})

    url = "https://api.github.com/repos/" + upstream + "/" + api_method
    if params:
        labels = params.get("labels")
        if isinstance(labels, list):
            # We have to flatten the labels list to a comma-separated string,
            # so make a copy to avoid mutating the config object
            url_filter = deepcopy(params)
            url_filter["labels"] = ",".join(labels)
        else:
            url_filter = params  # Use the existing filter, unmodified
        url += "?" + urlencode(url_filter)

    return get_all_github_data(url, headers)


def _get_current_project_node(upstream, project_number, issue_number, gh_issue):
    project_items = gh_issue["projectItems"]["nodes"]
    # If there are no project items, there is nothing to return.
    if len(project_items) == 0:
        log.debug(
            "Issue %s#%s is not associated with any project", upstream, issue_number
        )
        return None

    if not project_number:
        # We don't have a configured project.  If there is exactly one project
        # item, we'll assume it's the right one and return it.
        if len(project_items) == 1:
            return project_items[0]

        # There are multiple projects associated with this issue; since we
        # don't have a configured project, we don't know which one to return,
        # so return none.
        prj = (f"{x['project']['url']}: {x['project']['title']}" for x in project_items)
        log.debug(
            "Project number is not configured, and the issue %s#%s"
            " is associated with more than one project: %s",
            upstream,
            issue_number,
            ", ".join(prj),
        )
        return None

    # Return the associated project which matches the configured project if we
    # can find it.
    for item in project_items:
        if item["project"]["number"] == project_number:
            return item

    log.debug(
        "Issue %s#%s is associated with multiple projects, "
        "but none match the configured project.",
        upstream,
        issue_number,
    )
    return None


def get_all_github_data(url, headers):
    """A generator which returns each response from a paginated GitHub API call"""
    link = {"next": url}
    while "next" in link:
        response = api_call_get(link["next"], headers=headers)
        for issue in response.json():
            comments = api_call_get(issue["comments_url"], headers=headers)
            issue["comments"] = comments.json()
            yield issue
        link = _github_link_field_to_dict(response.headers.get("link"))


def _github_link_field_to_dict(field):
    """Utility for ripping apart GitHub's Link header field."""

    if not field:
        return {}
    return dict(
        (part.split("; ")[1][5:-1], part.split("; ")[0][1:-1])
        for part in field.split(", ")
    )


def api_call_get(url, **kwargs):
    """Helper function to encapsulate a REST API GET call"""
    response = requests.get(url, **kwargs)
    if not bool(response):
        # noinspection PyBroadException
        try:
            reason = response.json()
        except Exception:
            reason = response.text
        raise IOError("response: %r %r %r" % (response, reason, response.request.url))
    return response
