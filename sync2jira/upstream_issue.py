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
project_items_query = '''
    query MyQuery(
        $orgname: String!, $reponame: String!, $ghfieldname: String!, $issuenumber: Int!
    ) {
        repository(owner: $orgname, name: $reponame) {
            issue(number: $issuenumber) {
                title
                body
                projectItems(first: 1) {
                    nodes {
                        fieldValueByName(name: $ghfieldname) {
                            ... on ProjectV2ItemFieldNumberValue {
                                number
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

    for key, expected in _filter.items():
        if key == 'labels':
            # special handling for label: we look for it in the list of msg labels
            actual = {label['name'] for label in msg['msg']['issue']['labels']}
            if actual.isdisjoint(expected):
                log.debug("Labels %s not found on issue: %s", expected, upstream)
                return None
        elif key == 'milestone':
            # special handling for milestone: use the number
            milestone = msg['msg']['issue'].get(key) or {}
            actual = milestone.get('number')
            if expected != actual:
                log.debug("Milestone %s not set on issue: %s", expected, upstream)
                return None
        else:
            # direct comparison
            actual = msg['msg']['issue'].get(key)
            if actual != expected:
                log.debug("Actual %r %r != expected %r on issue %s",
                          key, actual, expected, upstream)
                return None

    if pr_filter and 'pull_request' in msg['msg']['issue']:
        if not msg['msg']['issue'].get('closed_at', None):
            log.debug("%r is a pull request.  Ignoring.", msg['msg']['issue'].get('html_url'))
            return None

    # Initialize Github object so we can get their full name (instead of their username)
    # And get comments if needed
    github_client = Github(config['sync2jira']['github_token'], retry=5)

    # If there are no comments just make an empty array
    if msg['msg']['issue']['comments'] == 0:
        msg['msg']['issue']['comments'] = []
    else:
        # We have multiple comments and need to make api call to get them
        repo = github_client.get_repo(upstream)
        comments = []
        github_issue = repo.get_issue(number=msg['msg']['issue']['number'])
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
        msg['msg']['issue']['comments'] = comments

    # Search for the user
    reporter = github_client.get_user(msg['msg']['issue']['user']['login'])
    # Update the reporter field in the message (to match Pagure format)
    if reporter.name:
        msg['msg']['issue']['user']['fullname'] = reporter.name
    else:
        msg['msg']['issue']['user']['fullname'] = \
            msg['msg']['issue']['user']['login']

    # Now do the same thing for the assignees
    assignees = []
    for person in msg['msg']['issue']['assignees']:
        assignee = github_client.get_user(person['login'])
        assignees.append({'fullname': assignee.name})

    # Update the assignee field in the message (to match Pagure format)
    msg['msg']['issue']['assignees'] = assignees

    # Update the label field in the message (to match Pagure format)
    if msg['msg']['issue']['labels']:
        # loop through all the labels on Github and add them
        # to the new label list and then reassign the message
        new_label = []
        for label in msg['msg']['issue']['labels']:
            new_label.append(label['name'])
        msg['msg']['issue']['labels'] = new_label

    # Update the milestone field in the message (to match Pagure format)
    if msg['msg']['issue']['milestone']:
        msg['msg']['issue']['milestone'] = msg['msg']['issue']['milestone']['title']

    return i.Issue.from_github(upstream, msg['msg']['issue'], config)


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

    # We need to format everything to a standard to we can create an issue object
    final_issues = []
    for issue in issues:
        # Update comments:
        # If there are no comments just make an empty array
        if issue['comments'] == 0:
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

        # Update reporter:
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

        # Update label(s):
        if issue['labels']:
            # loop through all the labels on Github and add them
            # to the new label list and then reassign the message
            new_label = []
            for label in issue['labels']:
                new_label.append(label['name'])
            issue['labels'] = new_label

        # Update milestone:
        if issue.get('milestone', None):
            issue['milestone'] = issue['milestone']['title']

        if not issue.get('storypoints', None):
            issue['storypoints'] = ''
            orgname, reponame = upstream.rsplit('/', 1)
            issuenumber = issue['number']
            default_github_project_fields = config['sync2jira']['default_github_project_fields']
            project_github_project_fields = config['sync2jira']['map']['github'].get(upstream, {}).get('github_project_fields', {})
            github_project_fields = default_github_project_fields | project_github_project_fields
            variables = {"orgname": orgname, "reponame": reponame, "issuenumber": issuenumber}
            for fieldname, values in github_project_fields.items():
                ghfieldname, _ = values
                variables['ghfieldname'] = ghfieldname
                response = requests.post(graphqlurl, headers=headers, json={"query": project_items_query, "variables": variables})
                data = response.json()
                if fieldname == 'storypoints':
                    try:
                        issue[fieldname] = data['data']['repository']['issue']['projectItems']['nodes'][0]['fieldValueByName']['number']
                    except (TypeError, KeyError) as err:
                        log.debug("Error fetching %s!r from GitHub %s/%s#%s: %s",
                                  ghfieldname, orgname, reponame, issuenumber, err)
                        continue

        final_issues.append(issue)

    final_issues = list((
        i.Issue.from_github(upstream, issue, config) for issue in final_issues
        if 'pull_request' not in issue  # We don't want to copy these around
    ))
    for issue in final_issues:
        yield issue


def get_all_github_data(url, headers):
    """ Pagination utility.  Obnoxious. """
    link = dict(next=url)
    while 'next' in link:
        response = _fetch_github_data(link['next'], headers)
        for issue in response.json():
            comments = _fetch_github_data(issue['comments_url'], headers)
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


def _fetch_github_data(url, headers):
    """
        Helper function to gather GitHub data
    """
    response = requests.get(url, headers=headers)
    if not bool(response):
        try:
            reason = response.json()
        except Exception:
            reason = response.text
        raise IOError("response: %r %r %r" % (response, reason, response.request.url))
    return response
