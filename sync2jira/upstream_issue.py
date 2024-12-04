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

import logging
from urllib.parse import urlencode
from copy import deepcopy

import requests
from github import Github

import sync2jira.intermediary as i


log = logging.getLogger('sync2jira')
graphqlurl = 'https://api.github.com/graphql'

ghquery = '''
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
'''


def handle_github_message(msg, config, pr_filter=True):
    """
    Handle GitHub message from FedMsg.

    :param Dict msg: FedMsg Message
    :param Dict config: Config File
    :param Bool pr_filter: Switch to ignore pull_requests
    :returns: Issue object
    :rtype: sync2jira.intermediary.Issue
    """
    owner = msg['msg']['repository']['owner']['login']
    repo = msg['msg']['repository']['name']
    upstream = '{owner}/{repo}'.format(owner=owner, repo=repo)

    mapped_repos = config['sync2jira']['map']['github']
    if upstream not in mapped_repos:
        log.debug("%r not in Github map: %r", upstream, mapped_repos.keys())
        return None
    elif 'issue' not in mapped_repos[upstream].get('sync', {}) and pr_filter is True:
        log.debug("%r not in Github Issue map: %r", upstream, mapped_repos.keys())
        return None
    elif 'pullrequest' not in mapped_repos[upstream].get('sync', {}) and pr_filter is False:
        log.debug("%r not in Github PR map: %r", upstream, mapped_repos.keys())
        return None

    _filter = config['sync2jira']\
        .get('filters', {})\
        .get('github', {})\
        .get(upstream, {})

    issue = msg['msg']['issue']
    for key, expected in _filter.items():
        if key == 'labels':
            # special handling for label: we look for it in the list of msg labels
            actual = {label['name'] for label in issue['labels']}
            if actual.isdisjoint(expected):
                log.debug("Labels %s not found on issue: %s", expected, upstream)
                return None
        elif key == 'milestone':
            # special handling for milestone: use the number
            milestone = issue.get(key) or {}
            actual = milestone.get('number')
            if expected != actual:
                log.debug("Milestone %s not set on issue: %s", expected, upstream)
                return None
        else:
            # direct comparison
            actual = issue.get(key)
            if actual != expected:
                log.debug("Actual %r %r != expected %r on issue %s",
                          key, actual, expected, upstream)
                return None

    if pr_filter and 'pull_request' in issue:
        if not issue.get('closed_at'):
            log.debug("%r is a pull request.  Ignoring.", issue.get('html_url'))
            return None

    github_client = Github(config['sync2jira']['github_token'], retry=5)
    reformat_github_issue(issue, upstream, github_client)
    return i.Issue.from_github(upstream, issue, config)


def github_issues(upstream, config):
    """
    Creates a Generator for all GitHub issues in upstream repo.

    :param String upstream: Upstream Repo
    :param Dict config: Config Dict
    :returns: GitHub Issue object generator
    :rtype: sync2jira.intermediary.Issue
    """
    token = config['sync2jira'].get('github_token')
    if not token:
        headers = {}
        log.warning('No github_token found.  We will be rate-limited...')
    else:
        headers = {'Authorization': 'token ' + token}

    _filter = config['sync2jira']\
        .get('filters', {})\
        .get('github', {})\
        .get(upstream, {})

    url = 'https://api.github.com/repos/%s/issues' % upstream
    if _filter:
        labels = _filter.get('labels')
        if isinstance(labels, list):
            # We have to flatten the labels list to a comma-separated string,
            # so make a copy to avoid mutating the config object
            url_filter = deepcopy(_filter)
            url_filter['labels'] = ','.join(labels)
        else:
            url_filter = _filter  # Use the existing filter, unmodified
        url += '?' + urlencode(url_filter)

    issues = get_all_github_data(url, headers)

    # Initialize Github object so we can get their full name (instead of their username)
    # And get comments if needed
    github_client = Github(config['sync2jira']['github_token'], retry=5)

    orgname, reponame = upstream.rsplit('/', 1)
    # We need to format everything to a standard to we can create an issue object
    final_issues = []
    project_number = config['sync2jira']['map']['github'][upstream].get('github_project_number')
    for issue in issues:
        reformat_github_issue(issue, upstream, github_client)

        issue_updates = config['sync2jira']['map']['github'][upstream].get('issue_updates', {})

        if '/pull/' in issue.get('html_url', ''):
            log.debug(
                "Issue %s/%s#%s is a pull request; skipping project fields",
                orgname, reponame, issue['number'])
        elif 'github_project_fields' in issue_updates:
            issue['storypoints'] = None
            issue['priority'] = ''
            issuenumber = issue['number']
            github_project_fields = config['sync2jira']['map']['github'][upstream]['github_project_fields']
            variables = {"orgname": orgname, "reponame": reponame, "issuenumber": issuenumber}
            response = requests.post(graphqlurl, headers=headers, json={"query": ghquery, "variables": variables})
            if response.status_code != 200:
                log.debug("HTTP error while fetching issue %s/%s#%s: %s",
                          orgname, reponame, issuenumber, response.text)
                continue
            data = response.json()
            gh_issue = data['data']['repository']['issue']
            if not gh_issue:
                log.debug("GitHub error while fetching issue %s/%s#%s: %s",
                          orgname, reponame, issuenumber, response.text)
                continue
            project_node = _get_current_project_node(
                upstream, project_number, issuenumber, gh_issue)
            if project_node:
                item_nodes = project_node.get('fieldValues', {}).get('nodes', {})
                for item in item_nodes:
                    gh_field_name = item.get('fieldName', {}).get('name')
                    if not gh_field_name:
                        continue
                    prio_field = github_project_fields.get('priority', {}).get('gh_field')
                    if gh_field_name == prio_field:
                        issue['priority'] = item.get('name')
                    sp_field = github_project_fields.get('storypoints', {}).get('gh_field')
                    if gh_field_name == sp_field:
                        try:
                            issue['storypoints'] = int(item['number'])
                        except (ValueError, KeyError) as err:
                            log.debug(
                                "Error while processing storypoints for issue %s/%s#%s: %s",
                                orgname, reponame, issuenumber, err)

        final_issues.append(issue)

    final_issues = list((
        i.Issue.from_github(upstream, issue, config) for issue in final_issues
        if 'pull_request' not in issue  # We don't want to copy these around
    ))
    for issue in final_issues:
        yield issue


def reformat_github_issue(issue, upstream, github_client):
    """Tweak Issue data format to better match Pagure"""

    # Update comments:
    # If there are no comments just make an empty array
    if not issue['comments']:
        issue['comments'] = []
    else:
        # We have multiple comments and need to make api call to get them
        repo = github_client.get_repo(upstream)
        comments = []
        github_issue = repo.get_issue(number=issue['number'])
        for comment in github_issue.get_comments():
            # First make API call to get the users name
            comments.append({
                'author': comment.user.name or comment.user.login,
                'name': comment.user.login,
                'body': comment.body,
                'id': comment.id,
                'date_created': comment.created_at,
                'changed': None
            })
        # Assign the message with the newly formatted comments :)
        issue['comments'] = comments

    # Search for the user
    reporter = github_client.get_user(issue['user']['login'])
    # Update the reporter field in the message (to match Pagure format)
    if reporter.name:
        issue['user']['fullname'] = reporter.name
    else:
        issue['user']['fullname'] = issue['user']['login']

    # Update assignee(s):
    assignees = []
    for person in issue['assignees']:
        assignee = github_client.get_user(person['login'])
        assignees.append({'fullname': assignee.name})
    # Update the assignee field in the message (to match Pagure format)
    issue['assignees'] = assignees

    # Update the label field in the message (to match Pagure format)
    if issue['labels']:
        # loop through all the labels on GitHub and add them
        # to the new label list and then reassign the message
        new_label = []
        for label in issue['labels']:
            new_label.append(label['name'])
        issue['labels'] = new_label

    # Update the milestone field in the message (to match Pagure format)
    if issue.get('milestone'):
        issue['milestone'] = issue['milestone']['title']


def _get_current_project_node(upstream, project_number, issue_number, gh_issue):
    project_items = gh_issue['projectItems']['nodes']
    # If there are no project items, there is nothing to return.
    if len(project_items) == 0:
        log.debug("Issue %s#%s is not associated with any project",
                  upstream, issue_number)
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
            upstream, issue_number, ", ".join(prj))
        return None

    # Return the associated project which matches the configured project if we
    # can find it.
    for item in project_items:
        if item['project']['number'] == project_number:
            return item

    log.debug(
        "Issue %s#%s is associated with multiple projects, "
        "but none match the configured project.",
        upstream, issue_number)
    return None


def get_all_github_data(url, headers):
    """ Pagination utility.  Obnoxious. """
    link = dict(next=url)
    while 'next' in link:
        response = api_call_get(link['next'], headers=headers)
        for issue in response.json():
            comments = api_call_get(issue['comments_url'], headers=headers)
            issue['comments'] = comments.json()
            yield issue
        link = _github_link_field_to_dict(response.headers.get('link', None))


def _github_link_field_to_dict(field):
    """
        Utility for ripping apart github's Link header field.
        It's kind of ugly.
    """

    if not field:
        return dict()
    return dict([
        (
            part.split('; ')[1][5:-1],
            part.split('; ')[0][1:-1],
        ) for part in field.split(', ')
    ])


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
