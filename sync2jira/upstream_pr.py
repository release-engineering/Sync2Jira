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

try:
    from urllib.parse import urlencode  # py3
    string_type = str
except ImportError:
    from urllib import urlencode  # py2
    import types
    string_type = types.StringTypes

import requests
from github import Github

import sync2jira.intermediary as i
import sync2jira.upstream_issue as u_issue


log = logging.getLogger('sync2jira')


def handle_github_message(config, msg):
    """
    Handle GitHub message from FedMsg.

    :param Dict msg: Webhook Message
    :param Dict config: Config File
    :returns: Issue object
    :rtype: sync2jira.intermediary.PR
    """
    # Create our title (i.e. owner/repo)
    owner = msg['repository']['owner']['login']
    repo = msg['repository']['name']
    upstream = '{owner}/{repo}'.format(owner=owner, repo=repo)

    # Check if upstream is in mapped repos
    mapped_repos = config['sync2jira']['map']['github']
    if upstream not in mapped_repos:
        log.debug("%r not in Github map: %r", upstream, mapped_repos.keys())
        return None
    elif 'pullrequest' not in mapped_repos[upstream]['sync']:
        log.debug("%r not in Github PR map: %r", upstream, mapped_repos.keys())
        return None

    # Initialize Github object so we can get their full name (instead of their username)
    # And get comments if needed
    github_client = Github(config['sync2jira']['github_token'])

    # If there are no comments just make an empty array
    if msg['pull_request']['comments'] == 0:
        msg['pull_request']['comments'] = []
    else:
        # We have multiple comments and need to make api call to get them
        repo = github_client.get_repo(upstream)
        comments = []
        github_pr = repo.get_pull(number=msg['pull_request']['number'])
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
        msg['pull_request']['comments'] = comments

    # Search for the user
    reporter = github_client.get_user(msg['pull_request']['user']['login'])
    # Update the reporter field in the message (to match Pagure format)
    if reporter.name:
        msg['pull_request']['user']['fullname'] = reporter.name
    else:
        msg['pull_request']['user']['fullname'] = \
            msg['pull_request']['user']['login']

    # Now do the same thing for the assignees
    assignees = []
    for person in msg['pull_request']['assignees']:
        assignee = github_client.get_user(person['login'])
        assignees.append({'fullname': assignee.name})

    # Update the assignee field in the message (to match Pagure format)
    msg['pull_request']['assignees'] = assignees

    # Update the label field in the message (to match Pagure format)
    if msg['pull_request']['labels']:
        # loop through all the labels on Github and add them
        # to the new label list and then reassign the message
        new_label = []
        for label in msg['pull_request']['labels']:
            new_label.append(label['name'])
        msg['pull_request']['labels'] = new_label

    # Update the milestone field in the message (to match Pagure format)
    if msg['pull_request']['milestone']:
        msg['pull_request']['milestone'] = msg['pull_request']['milestone']['title']

    # Determin the suffix 
    suffix = msg['action']
    if (suffix == 'closed'):
        # Check if this PR has been merged
        if (msg['pull_request']['merged_at'] is not None):
            suffix = 'merged'

    return i.PR.from_github(upstream, msg['pull_request'], suffix, config)


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

    github_client = Github(config['sync2jira']['github_token'])

    # Get our issues using helper functions
    prs = get_all_github_prs(upstream, github_client)

    # Build our final list of prs
    final_prs = []
    for pr in prs:
        final_pr = {}
        # Update comments:
        # If there are no comments just make an empty array
        if pr.comments == 0:
            final_pr['comments'] = []
        else:
            # We have multiple comments and need to make api call to get them
            repo = github_client.get_repo(upstream)
            comments = []
            github_pr = repo.get_pull(number=pr.number)
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
            final_pr['comments'] = comments

        # Update reporter:
        # Search for the user
        reporter = github_client.get_user(pr.user.login)
        # Update the reporter field in the message (to match Pagure format)
        final_pr['user'] = {}
        if reporter.name:
            final_pr['user']['fullname'] = reporter.name
        else:
            final_pr['user']['fullname'] = pr.user.login

        # Update assignee(s):
        assignees = []
        for person in pr.assignees:
            assignee = github_client.get_user(person.login)
            assignees.append({'fullname': assignee.name})

        # Update the assignee field in the message (to match Pagure format)
        final_pr['assignees'] = assignees

        # Update label(s):
        if pr.labels:
            # loop through all the labels on Github and add them
            # to the new label list and then reassign the message
            new_label = []
            for label in pr.labels:
                new_label.append(label['name'])
            final_pr['labels'] = new_label

        # Update milestone:
        if pr.milestone:
            final_pr['milestone'] = pr.milestone.title
        
        # Finish up creating any other mappings
        final_pr['html_url'] = pr.html_url
        final_pr['title'] = pr.title
        final_pr['body'] = pr.body
        final_pr['number'] = pr.number

        final_prs.append(final_pr)
    # Build our final list of data and yield
    final_prs = list((
        i.PR.from_github(upstream, pr, 'open', config) for pr in final_prs
    ))
    for issue in final_prs:
        yield issue


def get_all_github_prs(upstream, github_client):
    """ Helper function to get all Prs for an upstream repo """
    repo = github_client.get_repo(upstream)
    for issue in repo.get_issues():
        if (issue.pull_request):
            yield issue