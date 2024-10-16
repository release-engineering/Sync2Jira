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

config = {
    'sync2jira': {
        # Admins to be cc'd in duplicate emails
        'admins': [{'admin_username': 'admin_email@demo.com'}],

        # Mailing list email to send failure-email notices too
        'mailing-list': 'some_email@demo.com',

        # Enable debug logging
        'debug': False,

        # Listen on the message bus
        'listen': True,

        # Don't actually make changes to JIRA...
        'testing': True,

        # Set to True when developing to disable sentinel query
        'develop': False,

        # Your Github token
        'github_token': 'YOUR_GITHUB_API_TOKEN',

        'legacy_matching': False,

        'default_jira_instance': 'example',
        'jira_username': 'your-bot-account',
        'jira': {
            'example': {
                'options': {
                    'server': 'https://some_jira_server_somewhere.com',
                    'verify': True,
                },
                'token_auth': 'YOUR_JIRA_ACCESS_TOKEN',
            },
        },
        'map': {
            'github': {
                'GITHUB_USERNAME/Demo_project': {'project': 'FACTORY', 'component': 'gitbz',
                                                 'updates': [...], 'sync': ['pullrequest', 'issue']},
            },
        },
        'filters': {
            'github': {
                # Only sync multi-type tickets from bodhi.
                'fedora-infra/bodhi': {'status': 'open', 'milestone': 4, },
            },
        }
    },
}
