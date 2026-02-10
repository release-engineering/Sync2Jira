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

from github import Github, UnknownObjectException

import sync2jira.intermediary as i
import sync2jira.upstream_issue as u_issue

log = logging.getLogger("sync2jira")


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
    if not u_issue.passes_github_filters(pr, config, upstream, item_type="PR"):
        return None
    github_client = Github(config["sync2jira"]["github_token"])
    reformat_github_pr(pr, upstream, github_client)
    return i.PR.from_github(upstream, pr, suffix, config)


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
        try:
            repo = github_client.get_repo(upstream)
        except UnknownObjectException:
            logging.warning(
                "GitHub repo %r not found (has it been deleted or made private?)",
                upstream,
            )
            raise
        github_pr = repo.get_pull(number=pr["number"])
        pr["comments"] = u_issue.reformat_github_comments(
            github_pr.get_issue_comments()
        )

    u_issue.reformat_github_common(pr, github_client)
