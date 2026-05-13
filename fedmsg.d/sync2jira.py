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
                'auth_method': 'pat',    # Use 'pat' (default) or 'oauth2'
                # For PAT: email and API token (e.g. Jira Cloud)
                'basic_auth': ('your-email@example.com', 'YOUR_JIRA_API_TOKEN'),
                # For OAuth 2.0: set auth_method to 'oauth2' and replace 'basic_auth' with:
                # 'oauth2': {
                #     'client_id': 'YOUR_CLIENT_ID',
                #     'client_secret': 'YOUR_CLIENT_SECRET',
                # },
            },
        },
        'default_jira_fields': {
            'storypoints': 'customfield_12310243',
            },
        'map': {
            'github': {
                'GITHUB_USERNAME/Demo_project': {
                    'project': 'FACTORY',
                    'component': 'gitbz',

                    # ----- Issue synchronization -----
                    'issue_updates': [
                        'comments',         # Sync GitHub issue comments to Jira
                        'title',            # Sync issue title
                        'description',      # Sync issue description/body
                        'github_markdown',  # Convert GitHub Markdown to Jira wiki format
                        'upstream_id',      # Add comment with upstream issue link on create
                        'url',              # Include upstream URL in description
                        'github_project_fields',  # Sync storypoints & priority from GitHub Projects
                        {'transition': 'Closed'},  # Transition Jira when upstream issue closes
                        {'assignee': {'overwrite': False}},  # Sync assignee (don't overwrite existing)
                        {'on_close': {'apply_labels': ['closed-upstream']}},  # Label on close
                    ],

                    # ----- PR synchronization -----
                    # pr_updates uses the same options as issue_updates.
                    # Additionally supports merge_transition and link_transition.
                    'pr_updates': [
                        'comments',         # Sync GitHub PR comments to Jira
                        'title',            # Sync PR title
                        'description',      # Sync PR description/body
                        'github_markdown',  # Convert GitHub Markdown to Jira wiki format
                        {'merge_transition': 'Closed'},    # Transition Jira when PR is merged
                        {'link_transition': 'In Progress'},  # Transition Jira when PR is first linked
                        {'assignee': {'overwrite': False}},  # Sync assignee (don't overwrite existing)
                        {'on_close': {'apply_labels': ['closed-upstream']}},  # Label on close
                    ],

                    # ----- GitHub Projects (shared by issue & PR) -----
                    'github_project_number': '1',
                    'github_project_fields': {
                        'storypoints': {'gh_field': 'Estimate'},
                        'priority': {
                            'gh_field': 'Priority',
                            'options': {
                                'P0': 'Blocker',
                                'P1': 'Critical',
                                'P2': 'Major',
                                'P3': 'Minor',
                                'P4': 'Optional',
                                'P5': 'Trivial',
                            },
                        },
                    },

                    # What to sync: 'issue', 'pullrequest', or both
                    'sync': ['issue', 'pullrequest'],
                },
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
