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
from copy import deepcopy

try:
    from urllib.parse import urlencode  # py3
    string_type = str
except ImportError:
    from urllib import urlencode  # py2
    import types
    string_type = types.StringTypes

from github import Github

import sync2jira.intermediary as i
import sync2jira.upstream_issue as u_issue


log = logging.getLogger('sync2jira')


def handle_github_message(msg, config, suffix):
    """
    Handle GitHub message from FedMsg.

    :param Dict msg: FedMsg Message
    :param Dict config: Config File
    :param String suffix: FedMsg suffix
    :returns: Issue object
    :rtype: sync2jira.intermediary.PR
    """
    owner = msg['msg']['repository']['owner']['login']
    repo = msg['msg']['repository']['name']
    upstream = '{owner}/{repo}'.format(owner=owner, repo=repo)

    mapped_repos = config['sync2jira']['map']['github']
    if upstream not in mapped_repos:
        log.debug("%r not in Github map: %r", upstream, mapped_repos.keys())
        return None
    elif 'pullrequest' not in mapped_repos[upstream]['sync']:
        log.debug("%r not in Github PR map: %r", upstream, mapped_repos.keys())
        return None

    pr = msg['msg']['pull_request']
    github_client = Github(config['sync2jira']['github_token'])
    reformat_github_pr(pr, upstream, github_client)
    return i.PR.from_github(upstream, pr, suffix, config)


def github_prs(upstream, config):
    """
    Creates a Generator for all GitHub PRs in upstream repo.

    :param String upstream: Upstream Repo
    :param Dict config: Config Dict
    :returns: GitHub Issue object generator
    :rtype: sync2jira.intermediary.PR
    """
    # Get our GitHub token
    token = config['sync2jira'].get('github_token')

    # Throw warning if we don't have a token set up
    if not token:
        headers = {}
        log.warning('No github_token found.  We will be rate-limited...')
    else:
        headers = {'Authorization': 'token ' + token}

    # Get our filters
    _filter = config['sync2jira'] \
        .get('filters', {}) \
        .get('github', {}) \
        .get(upstream, {})

    # Build our URL
    url = 'https://api.github.com/repos/%s/pulls' % upstream
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

    # Get our issues using helper functions
    prs = u_issue.get_all_github_data(url, headers)

    # Initialize Github object so we can get their full name (instead of their username)
    # And get comments if needed
    github_client = Github(config['sync2jira']['github_token'])

    # Build our final list of prs
    final_prs = []
    for pr in prs:
        reformat_github_pr(pr, upstream, github_client)

        final_prs.append(pr)
    # Build our final list of data and yield
    final_prs = list((
        i.PR.from_github(upstream, pr, 'open', config) for pr in final_prs
    ))
    for issue in final_prs:
        yield issue


def reformat_github_pr(pr, upstream, github_client):
    """Tweak PR data format to better match Pagure"""

    # Update comments:
    # If there are no comments just make an empty array
    if not pr['comments']:
        pr['comments'] = []
    else:
        # We have multiple comments and need to make api call to get them
        repo = github_client.get_repo(upstream)
        comments = []
        github_pr = repo.get_pull(number=pr['number'])
        for comment in github_pr.get_issue_comments():
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
        pr['comments'] = comments

    # Update reporter:
    # Search for the user
    reporter = github_client.get_user(pr['user']['login'])
    # Update the reporter field in the message (to match Pagure format)
    if reporter.name:
        pr['user']['fullname'] = reporter.name
    else:
        pr['user']['fullname'] = pr['user']['login']

    # Update assignee(s):
    assignees = []
    for person in pr.get('assignees', []):
        assignee = github_client.get_user(person['login'])
        assignees.append({'fullname': assignee.name})
    # Update the assignee field in the message (to match Pagure format)
    pr['assignees'] = assignees

    # Update the label field in the message (to match Pagure format)
    if pr['labels']:
        # Loop through all the labels on GitHub and add them
        # to the new label list and then reassign the message
        new_label = []
        for label in pr['labels']:
            new_label.append(label['name'])
        pr['labels'] = new_label

    # Update milestone:
    if pr.get('milestone'):
        pr['milestone'] = pr['milestone']['title']
