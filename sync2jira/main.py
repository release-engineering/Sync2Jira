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
""" Sync github and pagure issues to a jira instance, via fedmsg.

Run with systemd, please.
"""

import logging
import warnings
import traceback
from time import sleep

import fedmsg
import fedmsg.config
import jinja2

import sync2jira.upstream_issue as u_issue
import sync2jira.upstream_pr as u_pr
import sync2jira.downstream_issue as d_issue
import sync2jira.downstream_pr as d_pr
from sync2jira.mailer import send_mail

# Set up our logging
FORMAT = "[%(asctime)s] %(levelname)s: %(message)s"
logging.basicConfig(format=FORMAT, level=logging.INFO)
logging.basicConfig(format=FORMAT, level=logging.DEBUG)
logging.basicConfig(format=FORMAT, level=logging.WARNING)
log = logging.getLogger('sync2jira.main')

# Only allow fedmsg logs that are critical
fedmsg_log = logging.getLogger('fedmsg.crypto.utils')
fedmsg_log.setLevel(50)

remote_link_title = "Upstream issue"
failure_email_subject = "Sync2Jira Has Failed!"

# Issue related handlers
issue_handlers = {
    # GitHub
    'github.issue.opened': u_issue.handle_github_message,
    'github.issue.reopened': u_issue.handle_github_message,
    'github.issue.labeled': u_issue.handle_github_message,
    'github.issue.assigned': u_issue.handle_github_message,
    'github.issue.unassigned': u_issue.handle_github_message,
    'github.issue.closed': u_issue.handle_github_message,
    'github.issue.comment': u_issue.handle_github_message,
    'github.issue.unlabeled': u_issue.handle_github_message,
    'github.issue.milestoned': u_issue.handle_github_message,
    'github.issue.demilestoned': u_issue.handle_github_message,
    'github.issue.edited': u_issue.handle_github_message,
    # Pagure
    'pagure.issue.new': u_issue.handle_pagure_message,
    'pagure.issue.tag.added': u_issue.handle_pagure_message,
    'pagure.issue.comment.added': u_issue.handle_pagure_message,
    'pagure.issue.comment.edited': u_issue.handle_pagure_message,
    'pagure.issue.assigned.added': u_issue.handle_pagure_message,
    'pagure.issue.assigned.reset': u_issue.handle_pagure_message,
    'pagure.issue.edit': u_issue.handle_pagure_message,
    'pagure.issue.drop': u_issue.handle_pagure_message,
    'pagure.issue.tag.removed': u_issue.handle_pagure_message,
}

# PR related handlers
pr_handlers = {
    # GitHub
    'github.pull_request.opened': u_pr.handle_github_message,
    'github.pull_request.edited': u_pr.handle_github_message,
    'github.issue.comment': u_pr.handle_github_message,
    'github.pull_request.reopened': u_pr.handle_github_message,
    'github.pull_request.closed': u_pr.handle_github_message,
    # Pagure
    'pagure.pull-request.new': u_pr.handle_pagure_message,
    'pagure.pull-request.comment.added': u_pr.handle_pagure_message,
    'pagure.pull-request.initial_comment.edited': u_pr.handle_pagure_message,
}


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
    config['mute'] = True

    # Validate it
    if 'sync2jira' not in config:
        raise ValueError("No sync2jira section found in fedmsg.d/ config")

    if 'map' not in config['sync2jira']:
        raise ValueError("No sync2jira.map section found in fedmsg.d/ config")

    possible = set(['pagure', 'github'])
    specified = set(config['sync2jira']['map'].keys())
    if not specified.issubset(possible):
        message = "Specified handlers: %s, must be a subset of %s."
        raise ValueError(message % (
            ", ".join(['"%s"' % item for item in specified]),
            ", ".join(['"%s"' % item for item in possible]),
        ))

    if 'jira' not in config['sync2jira']:
        raise ValueError("No sync2jira.jira section found in fedmsg.d/ config")

    # Provide some default values
    defaults = {
        'listen': True,
    }
    for key, value in defaults.items():
        config['sync2jira'][key] = config['sync2jira'].get(key, value)

    return config


def listen(config):
    """
    Listens to activity on upstream repos on pagure and github \
    via fedmsg, and syncs new issues there to the JIRA instance \
    defined in 'fedmsg.d/sync2jira.py'

    :param Dict config: Config dict
    :returns: Nothing
    """
    if not config['sync2jira'].get('listen'):
        log.info("`listen` is disabled.  Exiting.")
        return

    log.info("Waiting for a relevant fedmsg message to arrive...")
    for _, _, topic, msg in fedmsg.tail_messages(**config):
        idx = msg['msg_id']
        suffix = ".".join(topic.split('.')[3:])
        log.debug("Encountered %r %r %r", suffix, topic, idx)

        if suffix not in issue_handlers and suffix not in pr_handlers:
            continue

        log.debug("Handling %r %r %r", suffix, topic, idx)

        issue = None
        pr = None

        # Github '.issue.' is used for both PR and Issue
        # Check for that edge case
        if suffix == 'github.issue.comment':
            if 'pull_request' in msg['msg']['issue']:
                # pr_filter turns on/off the filtering of PRs
                pr = issue_handlers[suffix](msg, config, pr_filter=False)
                if not pr:
                    continue
                # Issues do not have suffix and reporter needs to be reformatted
                pr.suffix = suffix
                pr.reporter = pr.reporter.get('fullname')
            else:
                issue = issue_handlers[suffix](msg, config)
        elif suffix in issue_handlers:
            issue = issue_handlers[suffix](msg, config)
        elif suffix in pr_handlers:
            pr = pr_handlers[suffix](msg, config, suffix)

        if not issue and not pr:
            continue
        if issue:
            d_issue.sync_with_jira(issue, config)
        elif pr:
            d_pr.sync_with_jira(pr, config)


def initialize_issues(config, testing=False):
    """
    Initial initialization needed to sync any upstream \
    repo with JIRA. Goes through all issues and \
    checks if they're already on JIRA / Need to be \
    created.

    :param Dict config: Config dict for JIRA
    :param Bool testing: Flag to indicate if we are testing. Default false
    :returns: Nothing
    """
    log.info("Running initialization to sync all issues from upstream to jira")
    log.info("Testing flag is %r", config['sync2jira']['testing'])
    mapping = config['sync2jira']['map']
    for upstream in mapping.get('pagure', {}).keys():
        if 'issue' not in mapping.get('pagure', {}).get(upstream, {}).get('sync', []):
            continue
        for issue in u_issue.pagure_issues(upstream, config):
            try:
                d_issue.sync_with_jira(issue, config)
            except Exception:
                log.error("   Failed on %r", issue)
                raise
    log.info("Done with pagure issue initialization.")

    for upstream in mapping.get('github', {}).keys():
        if 'issue' not in mapping.get('github', {}).get(upstream, {}).get('sync', []):
            continue
        # Try and except for github API limit
        try:
            for issue in u_issue.github_issues(upstream, config):
                try:
                    d_issue.sync_with_jira(issue, config)
                except Exception:
                    log.error("   Failed on %r", issue)
                    raise
        except Exception as e:
            if "API rate limit exceeded" in e.__str__():
                # If we've hit out API limit:
                # Sleep for 1 hour and call our function again
                log.info("Hit Github API limit. Sleeping for 1 hour...")
                sleep(3600)
                if not testing:
                    initialize_issues(config)
                return
            else:
                if not config['sync2jira']['develop']:
                    # Only send the failure email if we are not developing
                    report_failure(config)
                    raise
    log.info("Done with github issue initialization.")


def initialize_pr(config, testing=False):
    """
    Initial initialization needed to sync any upstream \
    repo with JIRA. Goes through all PRs and \
    checks if they're already on JIRA / Need to be \
    created.

    :param Dict config: Config dict for JIRA
    :param Bool testing: Flag to indicate if we are testing. Default false
    :returns: Nothing
    """
    log.info("Running initialization to sync all PRs from upstream to jira")
    log.info("Testing flag is %r", config['sync2jira']['testing'])
    mapping = config['sync2jira']['map']
    for upstream in mapping.get('pagure', {}).keys():
        if 'pullrequest' not in mapping.get('pagure', {}).get(upstream, {}).get('sync', []):
            continue
        for pr in u_pr.pagure_prs(upstream, config):
            if pr:
                d_pr.sync_with_jira(pr, config)
    log.info("Done with pagure PR initialization.")

    for upstream in mapping.get('github', {}).keys():
        if 'pullrequest' not in mapping.get('github', {}).get(upstream, {}).get('sync', []):
            continue
        # Try and except for github API limit
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
                # If we've hit out API limit:
                # Sleep for 1 hour and call our function again
                log.info("Hit Github API limit. Sleeping for 1 hour...")
                sleep(3600)
                if not testing:
                    initialize_pr(config)
                return
            else:
                if not config['sync2jira']['develop']:
                    # Only send the failure email if we are not developing
                    report_failure(config)
                    raise
    log.info("Done with github PR initialization.")


def main(runtime_test=False, runtime_config=None):
    """
    Main function to check for initial sync
    and listen for fedmgs.

    :param Bool runtime_test: Flag to indicate if we are performing a runtime test. Default false
    :param Dict runtime_config: Config file to be used if it is a runtime test. runtime_test must be true
    :return: Nothing
    """
    # Load config and disable warnings
    if not runtime_test or not runtime_config:
        config = load_config()
    else:
        config = runtime_config

    logging.basicConfig(level=logging.INFO)
    warnings.simplefilter("ignore")
    config['validate_signatures'] = False

    try:
        if config['sync2jira'].get('initialize'):
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
        if not config['sync2jira']['develop']:
            # Only send the failure email if we are not developing
            report_failure(config)
            raise


def report_failure(config):
    """
    Helper function to alert admins in case of failure.


    :param Dict config: Config dict for JIRA
    """
    # Email our admins with the traceback
    templateLoader = jinja2.FileSystemLoader(
        searchpath='usr/local/src/sync2jira/sync2jira/')
    templateEnv = jinja2.Environment(loader=templateLoader)
    template = templateEnv.get_template('failure_template.jinja')
    html_text = template.render(traceback=traceback.format_exc())

    # Get admin information
    admins = []
    for admin in config['sync2jira']['admins']:
        admins.append(list(admin.values())[0])

    # Send mail
    send_mail(recipients=admins,
              cc=None,
              subject=failure_email_subject,
              text=html_text)


def list_managed():
    """
    Function to list URL for issues under map in config.

    :return: Nothing
    """
    config = load_config()
    mapping = config['sync2jira']['map']
    warnings.simplefilter("ignore")

    for upstream in mapping.get('pagure', {}).keys():
        for issue in u_issue.pagure_issues(upstream, config):
            print(issue.url)

    for upstream in mapping.get('github', {}).keys():
        for issue in u_issue.github_issues(upstream, config):
            print(issue.url)


def close_duplicates():
    """
    Function to close duplicate functions. Uses downstream:close_duplicates.

    :return: Nothing
    """
    config = load_config()
    logging.basicConfig(level=logging.INFO)
    log.info("Testing flag is %r", config['sync2jira']['testing'])
    mapping = config['sync2jira']['map']
    warnings.simplefilter("ignore")

    for upstream in mapping.get('pagure', {}).keys():
        for issue in u_issue.pagure_issues(upstream, config):
            try:
                d_issue.close_duplicates(issue, config)
            except Exception:
                log.error("Failed on %r", issue)
                raise
    log.info("Done with pagure duplicates.")

    for upstream in mapping.get('github', {}).keys():
        for issue in u_issue.github_issues(upstream, config):
            try:
                d_issue.close_duplicates(issue, config)
            except Exception:
                log.error("Failed on %r", issue)
                raise
    log.info("Done with github duplicates.")


if __name__ == '__main__':
    main()
