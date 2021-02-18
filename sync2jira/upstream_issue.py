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


log = logging.getLogger('sync2jira')


def handle_github_message(config, msg):
    """
    Handle GitHub message from webhook.

    :param Dict msg: webhook Message
    :param Dict config: Config File
    :returns: Issue object
    :rtype: sync2jira.intermediary.Issue
    """
    owner = msg['repository']['owner']['login']
    repo = msg['repository']['name']

    upstream = '{owner}/{repo}'.format(owner=owner, repo=repo)
    mapped_repos = config['sync2jira']['map']['github']

    if upstream not in mapped_repos:
        log.debug("%r not in Github map: %r", upstream, mapped_repos.keys())
        return None

    # Initialize Github object so we can get their full name (instead of their username)
    # And get comments if needed
    github_client = Github(config['sync2jira']['github_token'], retry=5)

    # If there are no comments just make an empty array
    if msg['issue']['comments'] == 0:
        msg['issue']['comments'] = []
    else:
        # We have multiple comments and need to make api call to get them
        repo = github_client.get_repo(upstream)
        comments = []
        github_issue = repo.get_issue(number=msg['issue']['number'])
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
        msg['issue']['comments'] = comments

    # Search for the user
    reporter = github_client.get_user(msg['issue']['user']['login'])
    # Update the reporter field in the message (to match Pagure format)
    if reporter.name:
        msg['issue']['user']['fullname'] = reporter.name
    else:
        msg['issue']['user']['fullname'] = \
            msg['issue']['user']['login']

    # Now do the same thing for the assignees
    assignees = []
    for person in msg['issue']['assignees']:
        assignee = github_client.get_user(person['login'])
        assignees.append({'fullname': assignee.name})

    # Update the assignee field in the message (to match Pagure format)
    msg['issue']['assignees'] = assignees

    # Update the label field in the message (to match Pagure format)
    if msg['issue']['labels']:
        # loop through all the labels on Github and add them
        # to the new label list and then reassign the message
        new_label = []
        for label in msg['issue']['labels']:
            new_label.append(label['name'])
        msg['issue']['labels'] = new_label

    # Update the milestone field in the message (to match Pagure format)
    if msg['issue']['milestone']:
        msg['issue']['milestone'] = msg['issue']['milestone']['title']

    return i.Issue.from_github(upstream, msg['issue'], config)


def github_issues(upstream, config):
    """
    Creates a Generator for all GitHub issues in upstream repo.

    :param String upstream: Upstream Repo
    :param Dict config: Config Dict
    :returns: Pagure Issue object generator
    :rtype: sync2jira.intermediary.Issue
    """
    token = config['sync2jira'].get('github_token')
    
    # Initialize Github object so we can get their full name (instead of their username)
    # And get comments if needed
    github_client = Github(config['sync2jira']['github_token'], retry=5)
    issues = get_all_github_data(upstream, github_client)

    # We need to format everything to a standard to we can create an issue object
    final_issues = []
    for issue in issues:
        final_issue = {}

        # Update comments:
        # If there are no comments just make an empty array
        if issue.comments == 0:
            final_issue['comments'] = []
        else:
            # We have multiple comments and need to make api call to get them
            repo = github_client.get_repo(upstream)
            comments = []
            github_issue = repo.get_issue(number=issue.number)
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
            final_issue['comments'] = comments

        # Update reporter:
        # Search for the user
        reporter = github_client.get_user(issue.user.login)
        final_issue['user'] = {}
        if reporter.name:
            final_issue['user']['fullname'] = reporter.name
        else:
            final_issue['user']['fullname'] = issue.user.login

        # Update assignee(s):
        assignees = []
        for person in issue.assignees:
            assignee = github_client.get_user(person.login)
            assignees.append({'fullname': assignee.name})
        # Update the assignee field in the message (to match Pagure format)
        final_issue['assignees'] = assignees

        # Update label(s):
        if issue.labels:
            # loop through all the labels on Github and add them
            # to the new label list and then reassign the message
            new_label = []
            for label in issue.labels:
                new_label.append(label.name)
            final_issue['labels'] = new_label
        else: 
            final_issue['labels'] = []

        # Update milestone:
        if issue.milestone:
            final_issue['milestone'] = issue.milestone.title
        else: 
            final_issue['milestone'] = None

        # Finish up creating any other mappings
        final_issue['state'] = issue.state
        final_issue['title'] = issue.title
        final_issue['html_url'] = issue.html_url
        final_issue['body'] = issue.body
        final_issue['assignees'] = issue.assignees
        final_issue['state'] = issue.state
        final_issue['id'] = issue.id
        final_issue['number'] = issue.number

        final_issues.append(final_issue)

    final_issues = list((
        i.Issue.from_github(upstream, issue, config) for issue in final_issues
    ))

    for issue in final_issues:
        yield issue


def get_all_github_data(upstream, github_client):
    """ Helper function to get all issues for a upstream repo """
    repo = github_client.get_repo(upstream)
    for issue in repo.get_issues():
        if (not issue.pull_request):
            yield issue


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
