#!/usr/bin/env python3
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
"""Sync GitHub issues to a jira instance, via fedora-messaging."""

# Build-In Modules
import logging
import os
from time import sleep
import traceback
import warnings

# 3rd Party Modules
import fedmsg.config
import fedora_messaging.api
import jinja2

# Local Modules
import sync2jira.downstream_issue as d_issue
import sync2jira.downstream_pr as d_pr
from sync2jira.intermediary import matcher
from sync2jira.mailer import send_mail
import sync2jira.upstream_issue as u_issue
import sync2jira.upstream_pr as u_pr

# Set up our logging
FORMAT = "[%(asctime)s] %(levelname)s: %(message)s"
logging.basicConfig(format=FORMAT, level=logging.INFO)
logging.basicConfig(format=FORMAT, level=logging.DEBUG)
logging.basicConfig(format=FORMAT, level=logging.WARNING)
log = logging.getLogger("sync2jira")

# Only allow fedmsg logs that are critical
fedmsg_log = logging.getLogger("fedmsg.crypto.utils")
fedmsg_log.setLevel(50)

remote_link_title = "Upstream issue"
failure_email_subject = "Sync2Jira Has Failed!"

# Issue related handlers
issue_handlers = {
    # GitHub
    # New webhook-2fm topics
    "github.issues": u_issue.handle_github_message,
    "github.issue_comment": u_issue.handle_github_message,
    # Old github2fedmsg topics
    "github.issue.opened": u_issue.handle_github_message,
    "github.issue.reopened": u_issue.handle_github_message,
    "github.issue.labeled": u_issue.handle_github_message,
    "github.issue.assigned": u_issue.handle_github_message,
    "github.issue.unassigned": u_issue.handle_github_message,
    "github.issue.closed": u_issue.handle_github_message,
    "github.issue.comment": u_issue.handle_github_message,
    "github.issue.unlabeled": u_issue.handle_github_message,
    "github.issue.milestoned": u_issue.handle_github_message,
    "github.issue.demilestoned": u_issue.handle_github_message,
    "github.issue.edited": u_issue.handle_github_message,
}

# PR related handlers
pr_handlers = {
    # GitHub
    # New webhook-2fm topics
    "github.pull_request": u_pr.handle_github_message,
    "github.issue_comment": u_pr.handle_github_message,
    # Old github2fedmsg topics
    "github.pull_request.opened": u_pr.handle_github_message,
    "github.pull_request.edited": u_pr.handle_github_message,
    "github.issue.comment": u_pr.handle_github_message,
    "github.pull_request.reopened": u_pr.handle_github_message,
    "github.pull_request.closed": u_pr.handle_github_message,
}
INITIALIZE = os.getenv("INITIALIZE", "0")


def load_config(loader=fedmsg.config.load_config):
    """
    Generates and validates the config file \
    that will be used by fedmsg and JIRA client.

    :param Function loader: Function to set up runtime config
    :returns: The config dict to be used later in the program
    :rtype: Dict
    """
    config = loader()

    # Force some vars that we like
    config["mute"] = True

    # debug mode
    if config.get("sync2jira", {}).get("debug", False):
        handler = logging.FileHandler("sync2jira_main.log")
        log.addHandler(handler)
        log.setLevel(logging.DEBUG)

    # Validate it
    if "sync2jira" not in config:
        raise ValueError("No sync2jira section found in fedmsg.d/ config")

    if "map" not in config["sync2jira"]:
        raise ValueError("No sync2jira.map section found in fedmsg.d/ config")

    possible = {"github"}
    specified = set(config["sync2jira"]["map"].keys())
    if not specified.issubset(possible):
        message = "Specified handlers: %s, must be a subset of %s."
        raise ValueError(
            message
            % (
                ", ".join(f'"{item}"' for item in specified),
                ", ".join(f'"{item}"' for item in possible),
            )
        )

    if "jira" not in config["sync2jira"]:
        raise ValueError("No sync2jira.jira section found in fedmsg.d/ config")

    # Provide some default values
    defaults = {
        "listen": True,
    }
    for key, value in defaults.items():
        config["sync2jira"][key] = config["sync2jira"].get(key, value)

    return config


def callback(msg):
    topic = msg.topic
    idx = msg.id
    suffix = ".".join(topic.split(".")[3:])

    if suffix not in issue_handlers and suffix not in pr_handlers:
        log.info("No handler for %r %r %r", suffix, topic, idx)
        return

    config = load_config()
    body = msg.body.get("body") or msg.body
    handle_msg(body, suffix, config)


def listen(config):
    """
    Listens to activity on upstream repos on GitHub
    via fedmsg, and syncs new issues there to the JIRA instance
    defined in 'fedmsg.d/sync2jira.py'

    :param Dict config: Config dict
    :returns: Nothing
    """
    if not config["sync2jira"].get("listen"):
        log.info("`listen` is disabled.  Exiting.")
        return

    # Next, we need a queue to consume messages from. We can define
    # the queue and binding configurations in these dictionaries:
    queue = os.getenv("FEDORA_MESSAGING_QUEUE", "8b16c196-7ee3-4e33-92b9-e69d80fce333")
    queues = {
        queue: {
            "durable": True,  # Persist the queue on broker restart
            "auto_delete": False,  # Delete the queue when the client terminates
            "exclusive": False,  # Allow multiple simultaneous consumers
            "arguments": {},
        },
    }
    bindings = {
        "exchange": "amq.topic",  # The AMQP exchange to bind our queue to
        "queue": queue,
        "routing_keys": [  # The topics that should be delivered to the queue
            # New style
            "org.fedoraproject.prod.github.issues",
            "org.fedoraproject.prod.github.issue_comment",
            "org.fedoraproject.prod.github.pull_request",
            # Old style
            "org.fedoraproject.prod.github.issue.#",
            "org.fedoraproject.prod.github.pull_request.#",
        ],
    }

    log.info("Waiting for a relevant fedmsg message to arrive...")
    fedora_messaging.api.consume(callback, bindings=bindings, queues=queues)


def initialize_issues(config, testing=False, repo_name=None):
    """
    Initial initialization needed to sync any upstream
    repo with JIRA. Goes through all issues and
    checks if they're already on JIRA / Need to be
    created.

    :param Dict config: Config dict for JIRA
    :param Bool testing: Flag to indicate if we are testing. Default false
    :param String repo_name: Optional individual repo name. If defined we will only sync the provided repo
    :returns: Nothing
    """
    log.info("Running initialization to sync all issues from upstream to jira")
    log.info("Testing flag is %r", config["sync2jira"]["testing"])
    mapping = config["sync2jira"]["map"]
    for upstream in mapping.get("github", {}).keys():
        if "issue" not in mapping.get("github", {}).get(upstream, {}).get("sync", []):
            continue
        if repo_name is not None and upstream != repo_name:
            continue
        # Try and except for GitHub API limit
        try:
            for issue in u_issue.github_issues(upstream, config):
                try:
                    d_issue.sync_with_jira(issue, config)
                except Exception:
                    log.error("   Failed on %r", issue)
                    raise
        except Exception as e:
            if "API rate limit exceeded" in e.__str__():
                # If we've hit our API limit, sleep for 1 hour, and call our
                # function again.
                log.info("Hit Github API limit. Sleeping for 1 hour...")
                sleep(3600)
                if not testing:
                    initialize_issues(config)
                return
            else:
                if not config["sync2jira"]["develop"]:
                    # Only send the failure email if we are not developing
                    report_failure(config)
                    raise
    log.info("Done with GitHub issue initialization.")


def initialize_pr(config, testing=False, repo_name=None):
    """
    Initial initialization needed to sync any upstream
    repo with JIRA. Goes through all PRs and
    checks if they're already on JIRA / Need to be
    created.

    :param Dict config: Config dict for JIRA
    :param Bool testing: Flag to indicate if we are testing. Default false
    :param String repo_name: Optional individual repo name. If defined we will only sync the provided repo
    :returns: Nothing
    """
    log.info("Running initialization to sync all PRs from upstream to jira")
    log.info("Testing flag is %r", config["sync2jira"]["testing"])
    mapping = config["sync2jira"]["map"]
    for upstream in mapping.get("github", {}).keys():
        if "pullrequest" not in mapping.get("github", {}).get(upstream, {}).get(
            "sync", []
        ):
            continue
        if repo_name is not None and upstream != repo_name:
            continue
        # Try and except for GitHub API limit
        try:
            for pr in u_pr.github_prs(upstream, config):
                try:
                    if pr:
                        d_pr.sync_with_jira(pr, config)
                except Exception:
                    log.error("   Failed on %r", pr)
                    raise
        except Exception as e:
            if "API rate limit exceeded" in e.__str__():
                # If we've hit our API limit, sleep for 1 hour, and call our
                # function again.
                log.info("Hit Github API limit. Sleeping for 1 hour...")
                sleep(3600)
                if not testing:
                    initialize_pr(config)
                return
            else:
                if not config["sync2jira"]["develop"]:
                    # Only send the failure email if we are not developing
                    report_failure(config)
                    raise
    log.info("Done with GitHub PR initialization.")


def handle_msg(body, suffix, config):
    """
    Function to handle incoming message
    :param Dict body: Incoming message body
    :param String suffix: Incoming suffix
    :param Dict config: Config dict
    """
    if handler := issue_handlers.get(suffix):
        # GitHub '.issue*' is used for both PR and Issue; check if this update
        # is actually for a PR
        if "pull_request" in body["issue"]:
            if body["action"] == "deleted":
                # FIXME:  What _should_ we be doing in this case?  Calling pr_handlers[]()??
                log.info("Not handling PR 'action' == 'deleted'")
                return
            # Handle this PR update as though it were an Issue, if that's
            # acceptable to the configuration.
            if not (pr := handler(body, config, is_pr=True)):
                log.info("Not handling PR issue update -- not configured")
                return
            # PRs require additional handling (Issues do not have suffix, and
            # reporter needs to be reformatted).
            pr.suffix = suffix
            pr.reporter = pr.reporter.get("fullname")
            setattr(pr, "match", matcher(pr.content, pr.comments))
            d_pr.sync_with_jira(pr, config)
        else:
            if issue := handler(body, config):
                d_issue.sync_with_jira(issue, config)
            else:
                log.info("Not handling Issue update -- not configured")
    elif handler := pr_handlers.get(suffix):
        if pr := handler(body, config, suffix):
            d_pr.sync_with_jira(pr, config)
        else:
            log.info("Not handling PR update -- not configured")


def main(runtime_test=False, runtime_config=None):
    """
    Main function to check for initial sync
    and listen for fedmsgs.

    :param Bool runtime_test: Flag to indicate if we are performing a runtime test. Default false
    :param Dict runtime_config: Config file to be used if it is a runtime test. runtime_test must be true
    :return: Nothing
    """
    # Load config and disable warnings
    config = runtime_config if runtime_test and runtime_config else load_config()

    logging.basicConfig(level=logging.INFO)
    warnings.simplefilter("ignore")
    config["validate_signatures"] = False

    try:
        if str(INITIALIZE) == "1":
            log.info("Initialization True")
            # Initialize issues
            log.info("Initializing Issues...")
            initialize_issues(config)
            log.info("Initializing PRs...")
            initialize_pr(config)
            if runtime_test:
                return
        try:
            listen(config)
        except KeyboardInterrupt:
            pass
    except:  # noqa: E722
        if not config["sync2jira"]["develop"]:
            # Only send the failure email if we are not developing
            report_failure(config)
            raise


def report_failure(config):
    """
    Helper function to alert admins in case of failure.

    :param Dict config: Config dict for JIRA
    """
    # Email our admins with the traceback
    template_loader = jinja2.FileSystemLoader(
        searchpath="usr/local/src/sync2jira/sync2jira/"
    )
    template_env = jinja2.Environment(loader=template_loader, autoescape=True)
    template = template_env.get_template("failure_template.jinja")
    html_text = template.render(traceback=traceback.format_exc())

    # Send mail
    send_mail(
        recipients=[config["sync2jira"]["mailing-list"]],
        cc=None,
        subject=failure_email_subject,
        text=html_text,
    )


if __name__ == "__main__":
    main()
