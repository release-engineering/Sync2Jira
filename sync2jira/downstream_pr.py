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
# Built-In Modules
import fnmatch
import logging

# 3rd Party Modules
from jira import JIRAError
from jira.client import Issue as JIRAIssue
from jira.client import ResultList

# Local Modules
import sync2jira.downstream_issue as d_issue
from sync2jira.intermediary import Issue, matcher

log = logging.getLogger("sync2jira")

UPDATES_KEY = "pr_updates"


def format_comment(pr, pr_suffix, client):
    """
    Formats comment to link PR.
    :param sync2jira.intermediary.PR pr: Upstream issue we're pulling data from
    :param String pr_suffix: Suffix to indicate what state we're transitioning too
    :param jira.client.JIRA client: JIRA Client
    :return: Formatted comment
    :rtype: String
    """
    # Find the pr.reporter's Jira user (use query= for Jira Cloud GDPR strict mode).
    ret = client.search_users(query=pr.reporter)
    # Loop through ret till we find a match
    for user in ret:
        if getattr(user, "displayName", "") == pr.reporter:
            reporter = f"[~accountId:{user.accountId}]"
            break
    else:
        reporter = pr.reporter

    if "closed" in pr_suffix:
        comment = f"Merge request [{pr.title}| {pr.url}] was closed."
    elif "reopened" in pr_suffix:
        comment = f"Merge request [{pr.title}| {pr.url}] was reopened."
    elif "merged" in pr_suffix:
        comment = f"Merge request [{pr.title}| {pr.url}] was merged!"
    else:
        comment = (
            f"{reporter} mentioned this issue in "
            f"merge request [{pr.title}| {pr.url}]."
        )
    return comment


def issue_link_exists(client, existing: JIRAIssue, pr):
    """
    Checks if we've already linked this PR

    :param jira.client.JIRA client: JIRA Client
    :param jira.resources.Issue existing: Existing JIRA issue that was found
    :param sync2jira.intermediary.PR pr: Upstream issue we're pulling data from
    :returns: True/False if the issue exists/does not exist
    """
    # Query for our issue
    for issue_link in client.remote_links(existing):
        if issue_link.object.url == pr.url:
            # Issue has already been linked
            return True
    return False


def comment_exists(client, existing: JIRAIssue, new_comment):
    """
    Checks if new_comment exists in existing
    :param jira.client.JIRA client: JIRA Client
    :param jira.resources.Issue existing: Existing JIRA issue that was found
    :param String new_comment: Formatted comment we're looking for
    :returns: Nothing
    """
    # Grab and loop over comments
    comments = client.comments(existing)
    for comment in comments:
        if new_comment == comment.body:
            return True
    return False


def _update_pr_transitions(client, existing, pr):
    """Handle merge_transition and link_transition for a PR.

    These are PR-only concepts that have no Issue counterpart.
    :param jira.client.JIRA client: JIRA Client
    :param jira.resources.Issue existing: Existing JIRA issue that was found
    :param sync2jira.intermediary.PR pr: Upstream issue we're pulling data from
    :returns: Nothing
    """
    # Get our updates array
    updates = pr.downstream.get(UPDATES_KEY, {})

    # Format and add comment to indicate PR has been linked
    new_comment = format_comment(pr, pr.suffix, client)
    # See if the issue_link and comment exists
    exists = issue_link_exists(client, existing, pr)
    comment_exist = comment_exists(client, existing, new_comment)
    # Check if the comment is already there
    if not exists:
        if not comment_exist:
            log.info(f"Added comment for PR {pr.title} on JIRA {pr.jira_key}")
            client.add_comment(existing, new_comment)
        # Attach remote link
        remote_link = dict(url=pr.url, title=f"[PR] {pr.title}")
        d_issue.attach_link(client, existing, remote_link)

    # Only synchronize merge_transition for listings that opt-in
    if any("merge_transition" in item for item in updates) and "merged" in pr.suffix:
        log.info("Looking for new merged_transition")
        _update_pr_transition(client, existing, pr, "merge_transition")

    # Only synchronize link_transition for listings that opt-in
    # and a link comment has been created
    if (
        any("link_transition" in item for item in updates)
        and "mentioned" in new_comment
        and not exists
    ):
        log.info("Looking for new link_transition")
        _update_pr_transition(client, existing, pr, "link_transition")


def _matches_transition_filters(transition_config, pr, existing):
    """
    Check whether a transition config entry's optional filters match the
    current PR and downstream JIRA issue.

    Supported filters:
      - ``branches``: list of glob patterns matched against ``pr.base_branch``
      - ``issue_types``: list of JIRA issue type names matched against the
        existing downstream issue's type

    :param dict transition_config: Single pr_updates entry
    :param sync2jira.intermediary.PR pr: Upstream PR
    :param jira.resources.Issue existing: Existing downstream JIRA issue
    :returns: True if all filters pass (or no filters are specified)
    :rtype: bool
    """
    branch_filters = transition_config.get("branches")
    if branch_filters is not None:
        if not pr.base_branch or not any(
            fnmatch.fnmatch(pr.base_branch, pattern) for pattern in branch_filters
        ):
            log.info(
                "Skipping transition: branch '%s' does not match %s",
                pr.base_branch,
                branch_filters,
            )
            return False

    type_filters = transition_config.get("issue_types")
    if type_filters is not None:
        jira_type = existing.fields.issuetype.name
        if jira_type not in type_filters:
            log.info(
                "Skipping transition: issue type '%s' does not match %s",
                jira_type,
                type_filters,
            )
            return False

    return True


def _update_pr_transition(client, existing, pr, transition_type):
    """
    Helper function to update the transition of a downstream JIRA issue.

    Applies optional ``branches`` and ``issue_types`` filters from the
    pr_updates config entry before executing the transition.

    :param jira.client.JIRA client: JIRA client
    :param jira.resource.Issue existing: Existing JIRA issue
    :param sync2jira.intermediary.PR pr: Upstream issue
    :param string transition_type: Transition type (link vs merged)
    :returns: Nothing
    """
    pr_updates = pr.downstream.get(UPDATES_KEY)
    if not pr_updates:
        return

    for entry in pr_updates:
        if transition_type not in entry:
            continue
        if not _matches_transition_filters(entry, pr, existing):
            continue
        d_issue.change_status(client, existing, entry[transition_type], pr)
        log.info(f"Updated {transition_type} for issue {pr.title}")
        return

    log.info(
        "No matching %s entry for PR %s (branch=%s)",
        transition_type,
        pr.title,
        pr.base_branch,
    )


def update_jira_issue(existing, pr, client, config):
    """
    Updates an existing JIRA issue for a PR event.

    First applies PR-specific steps (link comment, remote link,
    merge/link transitions), then delegates to the shared update
    pipeline in downstream_issue for common operations (comments,
    description, title, assignee, tags, etc.).

    :param jira.resources.Issue existing: Existing JIRA issue that was found
    :param sync2jira.intermediary.PR pr: Upstream PR we're pulling data from
    :param jira.client.JIRA client: JIRA Client
    :param dict config: Config dict
    :returns: Nothing
    """
    # PR-specific: link comment, remote link, merge/link transitions
    _update_pr_transitions(client, existing, pr)

    # Shared pipeline: comments, description, title, assignee, tags, etc.
    d_issue._update_jira_issue(existing, pr, client, config, updates_key=UPDATES_KEY)


def sync_with_jira(pr, config):
    """
    Attempts to sync an upstream PR with JIRA (i.e. by finding
    an existing issue).

    :param sync2jira.intermediary.PR/Issue pr: PR or Issue object
    :param Dict config: Config dict
    :returns: Nothing
    """
    log.info("[PR] Considering upstream %s, %s", pr.url, pr.title)

    # Return if testing
    if config["sync2jira"]["testing"]:
        log.info("Testing flag is true.  Skipping actual update.")
        return

    # Check if we should create issues for PRs without JIRA keys
    create_pr_issue = pr.downstream.get("create_pr_issue", False)

    if not pr.match and not create_pr_issue:
        log.info(f"[PR] No match found for {pr.title}")
        return

    # Create a client connection for this issue
    client = d_issue.get_jira_client(pr, config)

    retry = False
    while True:
        try:
            update_jira(client, config, pr)
            break
        except JIRAError:
            if retry:
                log.info("[PR] Jira retry failed; aborting")
                raise

            log.info("[PR] Jira request failed; refreshing the Jira client")
            client = d_issue.get_jira_client(pr, config, invalidate_oauth2_cache=True)

        retry = True


def update_jira(client, config, pr):
    # Check the status of the JIRA client
    if not config["sync2jira"]["develop"] and not d_issue.check_jira_status(client):
        log.warning("The JIRA server looks like its down. Shutting down...")
        raise RuntimeError("Jira server status check failed; aborting...")

    # Apply GitHub markdown conversion if configured
    d_issue.maybe_convert_markdown(pr, updates_key=UPDATES_KEY)

    # Find our JIRA issue if one exists
    if isinstance(pr, Issue):
        # Instances of the `PR` type already have an initialized `jira_key`
        # attribute; since what we have here is actually an `Issue`, we need to
        # add it.
        pr.jira_key = matcher(pr.content, pr.comments)

    if not pr.jira_key:
        create_pr_issue = pr.downstream.get("create_pr_issue", False)
        if create_pr_issue:
            if existing := d_issue.get_existing_jira_issue(client, pr, config):
                log.info(f"Found existing JIRA issue {existing.key} for PR {pr.url}")
                update_jira_issue(existing, pr, client, config)
            else:
                _create_jira_issue_from_pr(client, pr, config)
        else:
            log.info("No JIRA key found in PR, skipping.")
        return

    response: ResultList[JIRAIssue] = client.search_issues(f"Key = {pr.jira_key}")
    if len(response) == 1:
        # Syncing relevant information
        log.info(f"Syncing PR {pr.url}")
        update_jira_issue(response[0], pr, client, config)
        log.info(f"Done syncing PR {pr.url}")
    elif len(response) == 0:
        log.info(f"No issue found for referenced key, {pr.jira_key}")
    else:
        log.warning(
            f"Unexpectedly received {len(response)} matches for JIRA issue {pr.jira_key}"
        )


def _create_jira_issue_from_pr(client, pr, config):
    """
    Create a new JIRA issue from a PR when no JIRA key is referenced.

    :param jira.client.JIRA client: JIRA client
    :param sync2jira.intermediary.PR pr: PR object
    :param Dict config: Config dict
    :returns: Created JIRA issue
    :rtype: jira.resources.Issue
    """

    pr_content = pr.content or f"PR: {pr.url}"
    if pr.downstream.get("issue_updates"):
        if (
            pr.source == "github"
            and pr_content
            and "github_markdown" in pr.downstream["issue_updates"]
        ):
            pr_content = d_issue.convert_content(pr_content)

    # Convert PR to Issue-like object for creation
    # PR and Issue share similar structure, but we need to adapt it
    issue_like = Issue(
        source=pr.source,
        title=pr._title,  # Use original title without [upstream] prefix
        url=pr.url,
        upstream=pr.upstream,
        comments=pr.comments,
        config=config,
        tags=[],  # PRs don't have tags in the same way
        fixVersion=[],
        priority=pr.priority,
        content=pr_content,
        reporter=(
            pr.reporter
            if isinstance(pr.reporter, dict)
            else {"fullname": str(pr.reporter)}
        ),
        assignee=pr.assignee or [],
        status=pr.status,
        id_=pr.id,
        storypoints=None,
        upstream_id=pr.id,
        issue_type=None,
        downstream=pr.downstream,  # Use PR's downstream config
    )

    # Use existing issue creation logic
    return d_issue._create_jira_issue(client, issue_like, config)
