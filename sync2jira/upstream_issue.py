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
            milestone = issue.get(key, {})
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

    if pr_filter and 'pull_request' in issue and 'closed_at' not in issue:
        log.debug("%r is a pull request.  Ignoring.", issue.get('html_url', '<missing URL>'))
        return None

    github_client = Github(config['sync2jira']['github_token'], retry=5)
    reformat_github_issue(issue, upstream, github_client)
    return i.Issue.from_github(upstream, issue, config)


def github_issues(upstream, config):
    """
    Returns a generator for all GitHub issues in upstream repo.

    :param String upstream: Upstream Repo
    :param Dict config: Config Dict
    :returns: a generator for GitHub Issue objects
    :rtype: Generator[sync2jira.intermediary.Issue]
    """
    token = config['sync2jira'].get('github_token')
    github_client = Github(token, retry=5)
    for issue in generate_github_items('issues', upstream, config):
        if 'pull_request' not in issue:  # We don't want to copy these around
            reformat_github_issue(issue, upstream, github_client)

            # Update the Story Point Estimate field in the message
            if not issue.get('storypoints'):
                issue['storypoints'] = ''
                orgname, reponame = upstream.rsplit('/', 1)
                issuenumber = issue['number']
                default_github_project_fields = config['sync2jira']['default_github_project_fields']
                project_github_project_fields = config['sync2jira']['map']['github'].get(upstream, {}).get(
                    'github_project_fields', {})
                github_project_fields = default_github_project_fields | project_github_project_fields
                headers = {'Authorization': 'token ' + token} if token else {}
                variables = {"orgname": orgname, "reponame": reponame, "issuenumber": issuenumber}
                for fieldname, values in github_project_fields.items():
                    ghfieldname, _ = values
                    variables['ghfieldname'] = ghfieldname
                    response = requests.post(graphqlurl, headers=headers,
                                             json={"query": project_items_query, "variables": variables})
                    data = response.json()
                    if fieldname == 'storypoints':
                        try:
                            issue[fieldname] = \
                                data['data']['repository']['issue']['projectItems']['nodes'][0]['fieldValueByName'][
                                    'number']
                        except (TypeError, KeyError) as err:
                            log.debug("Error fetching %s!r from GitHub %s/%s#%s: %s",
                                      ghfieldname, orgname, reponame, issuenumber, err)
                            continue
            yield i.Issue.from_github(upstream, issue, config)


def reformat_github_issue(issue, upstream, github_client):
    """Tweak Issue data format to better match Pagure"""

    # Update comments:
    # If there are no comments just make an empty array
    if not issue['comments']:
        issue['comments'] = []
    else:
        # We have multiple comments and need to make api call to get them
        repo = github_client.get_repo(upstream)
        github_issue = repo.get_issue(number=issue['number'])
        issue['comments'] = reformat_github_comments(github_issue.get_comments())

    # Update the rest of the parts
    reformat_github_common(issue, github_client)


def reformat_github_comments(comments):
    """Helper function which encapsulates reformatting comments"""
    return [
        {
            'author': comment.user.name or comment.user.login,
            'name': comment.user.login,
            'body': comment.body,
            'id': comment.id,
            'date_created': comment.created_at,
            'changed': None
        } for comment in comments
    ]


def reformat_github_common(item, github_client):
    """Helper function which tweaks the data format of the parts of Issues and
     PRs which are common so that they better match Pagure
    """
    # Update reporter:
    # Search for the user
    reporter = github_client.get_user(item['user']['login'])
    # Update the reporter field in the message (to match Pagure format)
    if reporter.name:
        item['user']['fullname'] = reporter.name
    else:
        item['user']['fullname'] = item['user']['login']

    # Update assignee(s):
    assignees = []
    for person in item.get('assignees', []):
        assignee = github_client.get_user(person['login'])
        assignees.append({'fullname': assignee.name})
    # Update the assignee field in the message (to match Pagure format)
    item['assignees'] = assignees

    # Update the label field in the message (to match Pagure format)
    if item['labels']:
        # Loop through all the labels on GitHub and add them
        # to the new label list and then reassign the message
        new_label = []
        for label in item['labels']:
            new_label.append(label['name'])
        item['labels'] = new_label

    # Update the milestone field in the message (to match Pagure format)
    if item.get('milestone'):
        item['milestone'] = item['milestone']['title']


def generate_github_items(api_method, upstream, config):
    """
    Returns a generator which yields all GitHub issues in upstream repo.

    :param String api_method: API method name
    :param String upstream: Upstream Repo
    :param Dict config: Config Dict
    :returns: a generator for GitHub Issue/PR objects
    :rtype: Generator[Any, Any, None]
    """
    token = config['sync2jira'].get('github_token')
    if not token:
        headers = {}
        log.warning('No github_token found.  We will be rate-limited...')
    else:
        headers = {'Authorization': 'token ' + token}

    params = config['sync2jira']\
        .get('filters', {})\
        .get('github', {})\
        .get(upstream, {})

    if 'labels' in params:
        # We have to flatten the labels list to a comma-separated string
        params['labels'] = ','.join(params['labels'])

    url = 'https://api.github.com/repos/' + upstream + '/' + api_method
    if params:
        url += '?' + urlencode(params)

    return get_all_github_data(url, headers)


def get_all_github_data(url, headers):
    """A generator which returns each response from a paginated GitHub API call"""
    link = {'next': url}
    while 'next' in link:
        response = api_call_get(link['next'], headers=headers)
        for issue in response.json():
            comments = api_call_get(issue['comments_url'], headers=headers)
            issue['comments'] = comments.json()
            yield issue
        link = _github_link_field_to_dict(response.headers.get('link'))


def _github_link_field_to_dict(field):
    """Utility for ripping apart GitHub's Link header field."""

    if not field:
        return {}
    return dict(
        (
            part.split('; ')[1][5:-1],
            part.split('; ')[0][1:-1]
        ) for part in field.split(', ')
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
