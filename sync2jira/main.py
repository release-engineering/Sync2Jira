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

import sync2jira.upstream as u
import sync2jira.downstream as d
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

handlers = {
    # Example: https://apps.fedoraproject.org/datagrepper/id?id=2016-895ed21e-5d53-4fde-86ac-64dab36a14ad&is_raw=true&size=extra-large
    'github.issue.opened': u.handle_github_message,
    # Example: https://apps.fedoraproject.org/datagrepper/id?id=2017-ef579c6c-c391-449b-8cc2-837c41bd6c85&is_raw=true&size=extra-large
    'github.issue.reopened': u.handle_github_message,
    # Example: https://apps.fedoraproject.org/datagrepper/id?id=2017-a053e0c2-f514-47d6-8cb2-f7b2858f7052&is_raw=true&size=extra-large
    'github.issue.labeled': u.handle_github_message,
    'github.issue.assigned': u.handle_github_message,
    'github.issue.unassigned': u.handle_github_message,
    'github.issue.closed': u.handle_github_message,
    'github.issue.comment': u.handle_github_message,
    'github.issue.unlabeled': u.handle_github_message,
    'github.issue.milestoned': u.handle_github_message,
    'github.issue.demilestoned': u.handle_github_message,
    'github.issue.edited': u.handle_github_message,
    # Example: https://apps.fedoraproject.org/datagrepper/id?id=2016-d578d8f6-0c4c-493d-9535-4e138a03e197&is_raw=true&size=extra-large
    'pagure.issue.new': u.handle_pagure_message,
    # Example: https://apps.fedoraproject.org/datagrepper/id?id=2017-c2e81259-8576-41a9-83c6-6db2cbcf67d3&is_raw=true&size=extra-large
    'pagure.issue.tag.added': u.handle_pagure_message,
    'pagure.issue.comment.added': u.handle_pagure_message,
    'pagure.issue.comment.edited': u.handle_pagure_message,
    'pagure.issue.assigned.added': u.handle_pagure_message,
    'pagure.issue.assigned.reset': u.handle_pagure_message,
    'pagure.issue.edit': u.handle_pagure_message,
    'pagure.issue.drop': u.handle_pagure_message,
    'pagure.issue.tag.removed': u.handle_pagure_message,
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

        if suffix not in handlers:
            continue

        log.debug("Handling %r %r %r", suffix, topic, idx)

        if 'pagure' in suffix:
            issue = u.handle_pagure_message(msg, config)
        elif 'github' in suffix:
            issue = u.handle_github_message(msg, config)

        if not issue:
            continue

        d.sync_with_jira(issue, config)


def initialize(config, testing=False):
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
        for issue in u.pagure_issues(upstream, config):
            try:
                d.sync_with_jira(issue, config)
            except Exception:
                log.error("   Failed on %r", issue)
                raise
    log.info("Done with pagure initialization.")

    for upstream in mapping.get('github', {}).keys():
        # Try and except for github API limit
        try:
            for issue in u.github_issues(upstream, config):
                try:
                    d.sync_with_jira(issue, config)
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
                    initialize(config)
                return
            else:
                if not config['sync2jira']['develop']:
                    # Only send the failure email if we are not developing
                    report_failure(config)
                    raise
    log.info("Done with github initialization.")


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
            log.info("Initializing...")
            initialize(config)
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
    templateLoader = jinja2.FileSystemLoader(searchpath='usr/local/src/sync2jira')
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
        for issue in u.pagure_issues(upstream, config):
            print(issue.url)

    for upstream in mapping.get('github', {}).keys():
        for issue in u.github_issues(upstream, config):
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
        for issue in u.pagure_issues(upstream, config):
            try:
                d.close_duplicates(issue, config)
            except Exception:
                log.error("Failed on %r", issue)
                raise
    log.info("Done with pagure duplicates.")

    for upstream in mapping.get('github', {}).keys():
        for issue in u.github_issues(upstream, config):
            try:
                d.close_duplicates(issue, config)
            except Exception:
                log.error("Failed on %r", issue)
                raise
    log.info("Done with github duplicates.")


if __name__ == '__main__':
    main()
