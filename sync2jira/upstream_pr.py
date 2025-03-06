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

import requests
from github import Github

import sync2jira.intermediary as i
import sync2jira.upstream_issue as u_issue

log = logging.getLogger("sync2jira")


def handle_pagure_message(msg, config, suffix):
    """
    Handle Pagure message from FedMsg.

    :param Dict msg: FedMsg Message
    :param Dict config: Config File
    :returns: Issue object
    :rtype: sync2jira.intermediary.PR
    """
    # Extract our upstream name
    upstream = msg['msg']['pullrequest']['project']['name']
    ns = msg['msg']['pullrequest']['project'].get('namespace') or None
    if ns:
        upstream = '{ns}/{upstream}'.format(ns=ns, upstream=upstream)
    mapped_repos = config['sync2jira']['map']['pagure']

    # Check if we should sync this PR
    if upstream not in mapped_repos:
        log.debug("%r not in Pagure map: %r", upstream, mapped_repos.keys())
        return None
    elif 'pullrequest' not in mapped_repos[upstream]['sync']:
        log.debug("%r not in Pagure PR map: %r", upstream, mapped_repos.keys())
        return None

    # Format the assignee field to match github (i.e. in a list)
    msg['msg']['pullrequest']['assignee'] = [msg['msg']['pullrequest']['assignee']]

    # Update suffix, Pagure suffix only register as comments
    if msg['msg']['pullrequest']['status'] == 'Closed':
        suffix = 'closed'
    elif msg['msg']['pullrequest']['status'] == 'Merged':
        suffix = 'merged'
    elif msg['msg']['pullrequest'].get('closed_by') and \
            msg['msg']['pullrequest']['status'] == 'Open':
        suffix = 'reopened'
    elif msg['msg']['pullrequest']['status'] == 'Open':
        suffix = 'open'

    return i.PR.from_pagure(upstream, msg['msg']['pullrequest'], suffix, config)


def handle_github_message(body, config, suffix):
    """
    Handle GitHub message from FedMsg.

    :param Dict body: FedMsg Message body
    :param Dict config: Config File
    :param String suffix: FedMsg suffix
    :returns: Issue object
    :rtype: sync2jira.intermediary.PR
    """
    owner = body["repository"]["owner"]["login"]
    repo = body["repository"]["name"]
    upstream = "{owner}/{repo}".format(owner=owner, repo=repo)

    mapped_repos = config["sync2jira"]["map"]["github"]
    if upstream not in mapped_repos:
        log.debug("%r not in Github map: %r", upstream, mapped_repos.keys())
        return None
    elif "pullrequest" not in mapped_repos[upstream].get("sync", []):
        log.debug("%r not in Github PR map: %r", upstream, mapped_repos.keys())
        return None

    pr = body["pull_request"]
    github_client = Github(config["sync2jira"]["github_token"])
    reformat_github_pr(pr, upstream, github_client)
    return i.PR.from_github(upstream, pr, suffix, config)


def pagure_prs(upstream, config):
    """
    Creates a Generator for all Pagure PRs in upstream repo.

    :param String upstream: Upstream Repo
    :param Dict config: Config Dict
    :returns: Pagure Issue object generator
    :rtype: sync2jira.intermediary.PR
    """
    # Build our our URL
    base = config['sync2jira'].get('pagure_url', 'https://pagure.io')
    url = base + '/api/0/' + upstream + '/pull-requests'

    # Get our filters
    params = config['sync2jira']\
        .get('filters', {})\
        .get('pagure', {}) \
        .get(upstream, {})

    # Make a GET call to Pagure.io
    response = requests.get(url, params=params)

    # Catch if we have an error
    if not bool(response):
        try:
            reason = response.json()
        except Exception:
            reason = response.text
        raise IOError("response: %r %r %r" % (response, reason, response.request.url))

    # Extract and format our data
    data = response.json()['requests']

    # Reformat Assignee
    for pr in data:
        pr['assignee'] = [pr['assignee']]

    # Build our final list of data and yield
    prs = (i.PR.from_pagure(upstream, pr, 'open', config) for pr in data)
    for pr in prs:
        yield pr


def github_prs(upstream, config):
    """
    Returns a generator for all GitHub PRs in upstream repo.

    :param String upstream: Upstream Repo
    :param Dict config: Config Dict
    :returns: a generator for GitHub PR objects
    :rtype: Generator[sync2jira.intermediary.PR]
    """
    github_client = Github(config["sync2jira"]["github_token"])
    for pr in u_issue.generate_github_items("pulls", upstream, config):
        reformat_github_pr(pr, upstream, github_client)
        yield i.PR.from_github(upstream, pr, "open", config)


def reformat_github_pr(pr, upstream, github_client):
    """Tweak PR data format to better match Pagure"""

    # Update comments:
    # If there are no comments just make an empty array
    if not pr["comments"]:
        pr["comments"] = []
    else:
        # We have multiple comments and need to make api call to get them
        repo = github_client.get_repo(upstream)
        github_pr = repo.get_pull(number=pr["number"])
        pr["comments"] = u_issue.reformat_github_comments(
            github_pr.get_issue_comments()
        )

    u_issue.reformat_github_common(pr, github_client)
