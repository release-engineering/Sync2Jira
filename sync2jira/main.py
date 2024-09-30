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
""" Sync github issues to a jira instance, via fedmsg.

Run with systemd, please.
"""
# Build-In Modules
import logging
import warnings
import traceback
from time import sleep
import requests
from copy import deepcopy
import os

# 3rd Party Modules
import fedmsg
import fedmsg.config
import jinja2
from requests_kerberos import HTTPKerberosAuth, OPTIONAL

# Local Modules
import sync2jira.upstream_issue as u_issue
import sync2jira.upstream_pr as u_pr
import sync2jira.downstream_issue as d_issue
import sync2jira.downstream_pr as d_pr
from sync2jira.mailer import send_mail
from sync2jira.intermediary import matcher

# Set up our logging
FORMAT = "[%(asctime)s] %(levelname)s: %(message)s"
logging.basicConfig(format=FORMAT, level=logging.INFO)
logging.basicConfig(format=FORMAT, level=logging.DEBUG)
logging.basicConfig(format=FORMAT, level=logging.WARNING)
log = logging.getLogger('sync2jira')

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
}

# PR related handlers
pr_handlers = {
    # GitHub
    'github.pull_request.opened': u_pr.handle_github_message,
    'github.pull_request.edited': u_pr.handle_github_message,
    'github.issue.comment': u_pr.handle_github_message,
    'github.pull_request.reopened': u_pr.handle_github_message,
    'github.pull_request.closed': u_pr.handle_github_message,
}
DATAGREPPER_URL = "http://apps.fedoraproject.org/datagrepper/raw"
INITIALIZE = os.getenv('INITIALIZE', '0')


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

    # debug mode
    if config.get('sync2jira', {}).get('debug', False):
        hdlr = logging.FileHandler('sync2jira_main.log')
        log.addHandler(hdlr)
        log.setLevel(logging.DEBUG)

    # Validate it
    if 'sync2jira' not in config:
        raise ValueError("No sync2jira section found in fedmsg.d/ config")

    if 'map' not in config['sync2jira']:
        raise ValueError("No sync2jira.map section found in fedmsg.d/ config")

    possible = {'github'}
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
    Listens to activity on upstream repos on github \
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

        handle_msg(msg, suffix, config)


def initialize_issues(config, testing=False, repo_name=None):
    """
    Initial initialization needed to sync any upstream \
    repo with JIRA. Goes through all issues and \
    checks if they're already on JIRA / Need to be \
    created.

    :param Dict config: Config dict for JIRA
    :param Bool testing: Flag to indicate if we are testing. Default false
    :param String repo_name: Optional individual repo name. If defined we will only sync the provided repo
    :returns: Nothing
    """
    log.info("Running initialization to sync all issues from upstream to jira")
    log.info("Testing flag is %r", config['sync2jira']['testing'])
    mapping = config['sync2jira']['map']
    for upstream in mapping.get('github', {}).keys():
        if 'issue' not in mapping.get('github', {}).get(upstream, {}).get('sync', []):
            continue
        if repo_name is not None and upstream != repo_name:
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


def initialize_pr(config, testing=False, repo_name=None):
    """
    Initial initialization needed to sync any upstream \
    repo with JIRA. Goes through all PRs and \
    checks if they're already on JIRA / Need to be \
    created.

    :param Dict config: Config dict for JIRA
    :param Bool testing: Flag to indicate if we are testing. Default false
    :param String repo_name: Optional individual repo name. If defined we will only sync the provided repo
    :returns: Nothing
    """
    log.info("Running initialization to sync all PRs from upstream to jira")
    log.info("Testing flag is %r", config['sync2jira']['testing'])
    mapping = config['sync2jira']['map']
    for upstream in mapping.get('github', {}).keys():
        if 'pullrequest' not in mapping.get('github', {}).get(upstream, {}).get('sync', []):
            continue
        if repo_name is not None and upstream != repo_name:
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


def initialize_recent(config):
    """
    Initializes based on the recent history of datagrepper

    :param Dict config: Config dict
    :return: Nothing
    """
    # Query datagrepper
    ret = query(category=['github'], delta=int(600), rows_per_page=100)

    # Loop and sync
    for entry in ret:
        # Extract our topic
        suffix = ".".join(entry['topic'].split('.')[3:])
        log.debug("Encountered %r %r", suffix, entry['topic'])

        # Disregard if it's invalid
        if suffix not in issue_handlers and suffix not in pr_handlers:
            continue

        # Deal with the message
        log.debug("Handling %r %r", suffix, entry['topic'])
        msg = entry['msg']
        handle_msg({'msg': msg}, suffix, config)


def handle_msg(msg, suffix, config):
    """
    Function to handle incomming message from datagrepper
    :param Dict msg: Incoming message
    :param String suffix: Incoming suffix
    :param Dict config: Config dict
    """
    issue = None
    pr = None
    # Github '.issue.' is used for both PR and Issue
    # Check for that edge case
    if suffix == 'github.issue.comment':
        if 'pull_request' in msg['msg']['issue'] and msg['msg']['action'] != 'deleted':
            # pr_filter turns on/off the filtering of PRs
            pr = issue_handlers[suffix](msg, config, pr_filter=False)
            if not pr:
                return
            # Issues do not have suffix and reporter needs to be reformatted
            pr.suffix = suffix
            pr.reporter = pr.reporter.get('fullname')
            setattr(pr, 'match', matcher(pr.content, pr.comments))
        else:
            issue = issue_handlers[suffix](msg, config)
    elif suffix in issue_handlers:
        issue = issue_handlers[suffix](msg, config)
    elif suffix in pr_handlers:
        pr = pr_handlers[suffix](msg, config, suffix)

    if not issue and not pr:
        return
    if issue:
        d_issue.sync_with_jira(issue, config)
    elif pr:
        d_pr.sync_with_jira(pr, config)


def query(limit=None, **kwargs):
    """
    Run query on Datagrepper

    Args:
        limit: the max number of messages to fetch at a time
        kwargs: keyword arguments to build request parameters
    """
    # Pack up the kwargs into a parameter list for request
    params = deepcopy(kwargs)

    # Set up for paging requests
    all_results = []
    page = params.get('page', 1)

    # Important to set ASC order when paging to avoid duplicates
    params['order'] = 'asc'

    results = get(params=params)

    # Collect the messages
    all_results.extend(results['raw_messages'])

    # Set up for loop
    fetched = results['count']
    total = limit or results['total']

    # Fetch results until no more are left
    while fetched < total:
        page += 1
        params['page'] = page

        results = get(params=params)
        count = results['count']
        fetched += count

        # if we missed the condition and haven't fetched any
        if count == 0:
            break

        all_results.extend(results['raw_messages'])

    return all_results


def get(params):
    url = DATAGREPPER_URL
    headers = {'Accept': 'application/json', }

    response = requests.get(url=url, params=params, headers=headers,
                            auth=HTTPKerberosAuth(mutual_authentication=OPTIONAL))
    return response.json()


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
        if str(INITIALIZE) == '1':
            log.info("Initialization True")
            # Initialize issues
            log.info("Initializing Issues...")
            initialize_issues(config)
            log.info("Initializing PRs...")
            initialize_pr(config)
            if runtime_test:
                return
        else:
            # Pool datagrepper from the last 10 mins
            log.info("Initialization False. Pulling data from datagrepper...")
            initialize_recent(config)
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
    templateEnv = jinja2.Environment(loader=templateLoader, autoescape=True)
    template = templateEnv.get_template('failure_template.jinja')
    html_text = template.render(traceback=traceback.format_exc())

    # Send mail
    send_mail(recipients=[config['sync2jira']['mailing-list']],
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
