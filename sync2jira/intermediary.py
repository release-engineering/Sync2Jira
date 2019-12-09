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
from datetime import datetime


class Issue(object):

    def __init__(self, source, title, url, upstream, comments,
                 config, tags, fixVersion, priority, content,
                 reporter, assignee, status, id, upstream_id, downstream=None):
        self.source = source
        self._title = title
        self.url = url
        self.upstream = upstream
        self.comments = comments
        self.tags = tags
        self.fixVersion = fixVersion
        self.priority = priority
        self.content = content.encode('ascii', errors='replace').decode('ascii')
        self.reporter = reporter
        self.assignee = assignee
        self.status = status
        self.id = str(id)
        self.upstream_id = upstream_id
        if not downstream:
            self.downstream = config['sync2jira']['map'][self.source][upstream]
        else:
            self.downstream = downstream

    @property
    def title(self):
        return u'[%s] %s' % (self.upstream, self._title)

    @property
    def upstream_title(self):
        return self._title

    @classmethod
    def from_pagure(cls, upstream, issue, config):
        base = config['sync2jira'].get('pagure_url', 'https://pagure.io')
        upstream_source = 'pagure'
        comments = []
        for comment in issue['comments']:
            # Only add comments that are not Metadata updates
            if '**Metadata Update' in comment['comment']:
                continue
            # Else add the comment
            # Convert the date to datetime
            comment['date_created'] = datetime.fromtimestamp(float(comment['date_created']))
            comments.append({
                'author': comment['user']['name'],
                'body': comment['comment'],
                'name': comment['user']['name'],
                'id': comment['id'],
                'date_created': comment['date_created'],
                'changed': None
            })

        # Perform any mapping
        mapping = config['sync2jira']['map'][upstream_source][upstream].get('mapping', [])

        # Check for fixVersion
        if any('fixVersion' in item for item in mapping):
            cls.map_fixVersion(cls, mapping, issue)

        return Issue(
            source=upstream_source,
            title=issue['title'],
            url=base + '/%s/issue/%i' % (upstream, issue['id']),
            upstream=upstream,
            config=config,
            comments=comments,
            tags=issue['tags'],
            fixVersion=[issue['milestone']],
            priority=issue['priority'],
            content=issue['content'],
            reporter=issue['user'],
            assignee=issue['assignee'],
            status=issue['status'],
            id=issue['date_created'],
            upstream_id=issue['id']
        )

    @classmethod
    def from_github(cls, upstream, issue, config):
        upstream_source = 'github'
        comments = []
        for comment in issue['comments']:
            comments.append({
                'author': comment['author'],
                'name': comment['name'],
                'body': comment['body'],
                'id': comment['id'],
                'date_created': comment['date_created'],
                'changed': None
            })

        # Reformat the state field
        if issue['state']:
            if issue['state'] == 'open':
                issue['state'] = 'Open'
            elif issue['state'] == 'closed':
                issue['state'] = 'Closed'

        # Perform any mapping
        mapping = config['sync2jira']['map'][upstream_source][upstream].get('mapping', [])

        # Check for fixVersion
        if any('fixVersion' in item for item in mapping):
            cls.map_fixVersion(cls, mapping, issue)

        # TODO: Priority is broken
        return Issue(
            source=upstream_source,
            title=issue['title'],
            url=issue['html_url'],
            upstream=upstream,
            config=config,
            comments=comments,
            tags=issue['labels'],
            fixVersion=[issue['milestone']],
            priority=None,
            content=issue['body'],
            reporter=issue['user'],
            assignee=issue['assignees'],
            status=issue['state'],
            id=issue['id'],
            upstream_id=issue['number']
        )

    def __repr__(self):
        return "<Issue %s >" % self.url

    def map_fixVersion(self, mapping, issue):
        """
        Helper function to perform any fixVersion mapping.

        :param Dict mapping: Mapping dict we are given
        :param Dict issue: Upstream issue object
        """
        # Get our fixVersion mapping
        try:
            # for python 3 >
            fixVersion_map = list(filter(lambda d: "fixVersion" in d, mapping))[0]['fixVersion']
        except ValueError:
            # for python 2.7
            fixVersion_map = filter(lambda d: "fixVersion" in d, mapping)[0]['fixVersion']

        # Now update the fixVersion
        if issue.get('milestone'):
            issue['milestone'] = fixVersion_map.replace('XXX', issue['milestone'])
