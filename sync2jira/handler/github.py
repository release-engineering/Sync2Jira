import logging

# Local Modules
import sync2jira.downstream_issue as d_issue
import sync2jira.downstream_pr as d_pr
import sync2jira.handler.github_upstream_issue as u_issue
import sync2jira.handler.github_upstream_pr as u_pr
from sync2jira.intermediary import matcher

log = logging.getLogger("sync2jira")


def handle_issue_msg(body, suffix, config):
    """
    Function to handle incoming github issue message
    :param Dict body: Incoming message body
    :param String suffix: Incoming suffix
    :param Dict config: Config dict
    """
    # GitHub '.issue*' is used for both PR and Issue; check if this update
    # is actually for a PR
    if "pull_request" in body["issue"]:
        if body["action"] == "deleted":
            # I think this gets triggered when someone deletes a comment
            # from a PR.  Since we don't capture PR comments (only Issue
            # comments), we don't need to react if one is deleted.
            log.debug("Not handling PR 'action' == 'deleted'")
            return
        # Handle this PR update as though it were an Issue, if that's
        # acceptable to the configuration.
        if not (pr := u_issue.handle_github_message(body, config, is_pr=True)):
            log.info("Not handling PR issue update -- not configured")
            return
        # PRs require additional handling (Issues do not have suffix, and
        # reporter needs to be reformatted).
        pr.suffix = suffix
        pr.reporter = pr.reporter.get("fullname")
        setattr(pr, "match", matcher(pr.content, pr.comments))
        d_pr.sync_with_jira(pr, config)
    else:
        if issue := u_issue.handle_github_message(body, config):
            d_issue.sync_with_jira(issue, config)
        else:
            log.info("Not handling Issue update -- not configured")


def handle_pr_msg(body, suffix, config):
    """
    Function to handle incoming github PR message
    :param Dict body: Incoming message body
    :param String suffix: Incoming suffix
    :param Dict config: Config dict
    """
    if pr := u_pr.handle_github_message(body, config, suffix):
        d_pr.sync_with_jira(pr, config)
    else:
        log.info("Not handling PR update -- not configured")


# Issue related handlers
issue_handlers = {
    # GitHub
    # New webhook-2fm topics
    "github.issues": handle_issue_msg,
    "github.issue_comment": handle_issue_msg,
    # Old github2fedmsg topics
    "github.issue.opened": handle_issue_msg,
    "github.issue.reopened": handle_issue_msg,
    "github.issue.labeled": handle_issue_msg,
    "github.issue.assigned": handle_issue_msg,
    "github.issue.unassigned": handle_issue_msg,
    "github.issue.closed": handle_issue_msg,
    "github.issue.comment": handle_issue_msg,
    "github.issue.unlabeled": handle_issue_msg,
    "github.issue.milestoned": handle_issue_msg,
    "github.issue.demilestoned": handle_issue_msg,
    "github.issue.edited": handle_issue_msg,
}

# PR related handlers
pr_handlers = {
    # GitHub
    # New webhook-2fm topics
    "github.pull_request": handle_pr_msg,
    "github.issue_comment": handle_pr_msg,
    # Old github2fedmsg topics
    "github.pull_request.opened": handle_pr_msg,
    "github.pull_request.edited": handle_pr_msg,
    "github.issue.comment": handle_pr_msg,
    "github.pull_request.reopened": handle_pr_msg,
    "github.pull_request.closed": handle_pr_msg,
}


def get_handler_for(suffix, topic, idx):
    """
    Function to check if a handler for given suffix is configured
    :param String suffix: Incoming suffix
    :param String topic: Topic of incoming message
    :param String idx: Id of incoming message
    :returns: Handler function if configured for suffix. Otherwise None.
    """
    if suffix in issue_handlers:
        return issue_handlers.get(suffix)
    elif suffix in pr_handlers:
        return pr_handlers.get(suffix)
    log.info("No handler for %r %r %r", suffix, topic, idx)
    return None
