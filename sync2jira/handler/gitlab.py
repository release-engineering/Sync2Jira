import logging

from sync2jira.api.gitlab_client import GitlabClient
import sync2jira.downstream_issue as d_issue
import sync2jira.downstream_pr as d_pr

# Local Modules
import sync2jira.intermediary as i

log = logging.getLogger("sync2jira")


def should_sync(upstream, labels, config, event_type):
    mapped_repos = config["sync2jira"]["map"]["gitlab"]
    if upstream not in mapped_repos:
        log.debug("%r not in Gitlab map: %r", upstream, mapped_repos.keys())
        return None
    if event_type not in mapped_repos[upstream].get("sync", []):
        log.debug(
            "%r not in Gitlab sync map: %r",
            event_type,
            mapped_repos[upstream].get("sync", []),
        )
        return None

    _filter = config["sync2jira"].get("filters", {}).get("gitlab", {}).get(upstream, {})
    for key, expected in _filter.items():
        if key == "labels":
            if labels.isdisjoint(expected):
                log.debug("Labels %s not found on issue: %s", expected, upstream)
                return None


def handle_gitlab_issue(body, headers, config, suffix):
    """
    Handle GitLab issue from FedMsg.

    :param Dict body: FedMsg Message body
    :param Dict body: FedMsg Message headers
    :param Dict config: Config File
    :param Bool is_pr: msg refers to a pull request
    """
    upstream = body["project"]["path_with_namespace"]
    url = headers["x-gitlab-instance"]
    token = config["sync2jira"].get("github_token")
    labels = {label["title"] for label in body.get("labels", [])}
    iid = body.get("object_attributes").get("iid")

    if should_sync(upstream, labels, config, "issue"):
        sync_gitlab_issue(GitlabClient(url, token, upstream), iid, upstream, config)


def handle_gitlab_note(body, headers, config, suffix):
    """
    Handle Gitlab note from FedMsg.

    :param Dict body: FedMsg Message body
    :param Dict body: FedMsg Message headers
    :param Dict config: Config File
    :param String suffix: FedMsg suffix
    """
    upstream = body["project"]["path_with_namespace"]
    url = headers["x-gitlab-instance"]
    token = config["sync2jira"].get("github_token")

    if "merge_request" in body:
        labels = {
            label["title"] for label in body.get("merge_request").get("labels", [])
        }
        iid = body.get("merge_request").get("iid")

        if should_sync(upstream, labels, config, "issue"):
            sync_gitlab_mr(GitlabClient(url, token, upstream), iid, upstream)
    if "issue" in body:
        labels = {label["title"] for label in body.get("issue").get("labels", [])}
        iid = body.get("issue").get("iid")

        if should_sync(upstream, labels, config, "pullrequest"):
            sync_gitlab_issue(GitlabClient(url, token, upstream), iid, upstream)
    log.info("Note was not added to an issue or merge request. Skipping note event.")


def handle_gitlab_mr(body, headers, config, suffix):
    """
    Handle Gitlab merge request from FedMsg.

    :param Dict body: FedMsg Message body
    :param Dict body: FedMsg Message headers
    :param Dict config: Config File
    :param String suffix: FedMsg suffix
    """
    upstream = body["project"]["path_with_namespace"]
    url = headers["x-gitlab-instance"]
    token = config["sync2jira"].get("github_token")
    labels = {label["title"] for label in body.get("labels", [])}
    iid = body.get("object_attributes").get("iid")

    if should_sync(upstream, labels, config, "pullrequest"):
        sync_gitlab_mr(GitlabClient(url, token, upstream), iid, upstream, config)


def sync_gitlab_issue(client, iid, upstream, config):
    gitlab_issue = client.fetch_issue(iid)
    comments = gitlab_issue.notes.list(all=True)

    issue = i.Issue.from_gitlab(gitlab_issue, comments, upstream, config)
    d_issue.sync_with_jira(issue, config)


def sync_gitlab_mr(client, iid, upstream, config):
    gitlab_mr = client.fetch_mr(iid)
    comments = gitlab_mr.notes.list(all=True)

    mr = i.PR.from_gitlab(gitlab_mr, comments, upstream, config)
    d_pr.sync_with_jira(mr, config)


handlers = {
    "gitlab.issues": handle_gitlab_issue,
    "gitlab.issue_comment": handle_gitlab_mr,
    "gitlab.note": handle_gitlab_note,
}


def get_handler_for(suffix, topic, idx):
    """
    Function to check if a handler for given suffix is configured
    :param String suffix: Incoming suffix
    :param String topic: Topic of incoming message
    :param String idx: Id of incoming message
    :returns: Handler function if configured for suffix. Otherwise None.
    """
    if suffix in handlers:
        return handlers.get(suffix)
    log.info("No gitlab handler for %r %r %r", suffix, topic, idx)
    return None
