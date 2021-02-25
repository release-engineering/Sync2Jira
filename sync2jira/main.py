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
# Authors:  Ralph Bean <rbean@redhat.com>, Sid Premkumar <sid@bastionzero.com>
""" Sync github and pagure issues to a jira instance, via fedmsg.

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
import json
import threading

# 3rd Party Modules
import jinja2
from requests_kerberos import HTTPKerberosAuth, OPTIONAL

# Local Modules
import sync2jira.upstream_issue as u_issue
import sync2jira.upstream_pr as u_pr
import sync2jira.downstream_issue as d_issue
import sync2jira.downstream_pr as d_pr
from sync2jira.intermediary import matcher

# Set up our logging
FORMAT = "[%(asctime)s] %(levelname)s: %(message)s"
logging.basicConfig(format=FORMAT, level=logging.INFO)
logging.basicConfig(format=FORMAT, level=logging.DEBUG)
logging.basicConfig(format=FORMAT, level=logging.WARNING)
log = logging.getLogger('sync2jira')

INITIALIZE = os.getenv('INITIALIZE', '0')

# Build our lock
lock = threading.Lock()


def load_config(config=os.environ['SYNC2JIRA_CONFIG']):
    """
    Generates and validates the config file \
    that will be used by fedmsg and JIRA client.

    :param Function loader: Function to set up runtime config
    :returns: The config dict to be used later in the program
    :rtype: Dict
    """
    with open(config, 'r') as jsonFile:
     config = json.loads(jsonFile.read())

    # Validate it
    if 'sync2jira' not in config:
        raise ValueError("No sync2jira section found in fedmsg.d/ config")

    if 'map' not in config['sync2jira']:
        raise ValueError("No sync2jira.map section found in fedmsg.d/ config")

    possible = set(['github'])
    specified = set(config['sync2jira']['map'].keys())
    if not specified.issubset(possible):
        message = "Specified handlers: %s, must be a subset of %s."
        raise ValueError(message % (
            ", ".join(['"%s"' % item for item in specified]),
            ", ".join(['"%s"' % item for item in possible]),
        ))

    if 'jira' not in config['sync2jira']:
        raise ValueError("No sync2jira.jira section found in config")

    # Update config based on env vars
    config['sync2jira']['github_token'] = os.environ['SYNC2JIRA_GITHUB_TOKEN']
    config['sync2jira']['jira'][config['sync2jira']['default_jira_instance']]['basic_auth'] = (
        os.environ['SYNC2JIRA_JIRA_USERNAME'],
        os.environ['SYNC2JIRA_JIRA_PASSWORD']
    )

    # Provide some default values
    defaults = {
        'listen': True,
    }
    for key, value in defaults.items():
        config['sync2jira'][key] = config['sync2jira'].get(key, value)

    return config


def listen(config, event_emitter):
    """
    Listens to activity on upstream repos on pagure and github \
    via fedmsg, and syncs new issues there to the JIRA instance \
    defined in 'fedmsg.d/sync2jira.py'

    :param Dict config: Config dict
    :param rxObject event_emitter: Event emitter to wait for 
    :returns: Nothing
    """
    if not config['sync2jira'].get('listen'):
        log.info("`listen` is disabled.  Exiting.")
        return
    
    log.info("Waiting for a relevant webhook message to arrive...")
    event_emitter.subscribe(
        lambda x: handle_message(config, x)
    )

    while True:

        sleep(10)

def handle_message(config, incoming_json):
    # Constantly refresh the config file when we handle a new message
    config = load_config()
    
    # Ensure we are only dealing with one issue at a time, get our lock
    with lock:
        if ('pull_request' in incoming_json.keys()):
            pr = u_pr.handle_github_message(config, incoming_json)
            if pr:
                d_pr.sync_with_jira(pr, config)
        elif ('issue' in incoming_json.keys()):
            issue = u_issue.handle_github_message(config, incoming_json)
            if issue:
                d_issue.sync_with_jira(issue, config)
            

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
                    raise
    log.info("Done with github PR initialization.")

def main(event_emitter):
    """
    Main function to check for initial sync
    and listen.
    """
    # Load config
    config = load_config()

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
        else:
            # Pool datagrepper from the last 10 mins
            log.info("Initialization False...")
        try:
            listen(config, event_emitter)
        except KeyboardInterrupt:
            pass
    except:  # noqa: E722
        if not config['sync2jira']['develop']:
            # Only send the failure email if we are not developing
            raise

if __name__ == '__main__':
    main()