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
import re


class Issue(object):
    """Issue Intermediary object"""

    def __init__(self, source, title, url, upstream, comments,
                 config, tags, fixVersion, priority, content,
                 reporter, assignee, status, id, storypoints, upstream_id, downstream=None):
        self.source = source
        self._title = title[:254]
        self.url = url
        self.upstream = upstream
        self.comments = comments
        self.tags = tags
        self.fixVersion = fixVersion
        self.priority = priority
        self.storypoints = storypoints

        # First trim the size of the content
        self.content = trimString(content)

        # JIRA treats utf-8 characters in ways we don't totally understand, so scrub content down to
        # simple ascii characters right from the start.
        self.content = self.content.encode('ascii', errors='replace').decode('ascii')

        # We also apply this content in regexs to pattern match, so remove any escape characters
        self.content = self.content.replace('\\', '')

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
        _title = u'[%s] %s' % (self.upstream, self._title)
        return _title[:254].strip()

    @property
    def upstream_title(self):
        return self._title

    @classmethod
    def from_github(cls, upstream, issue, config):
        """Helper function to create intermediary object."""
        upstream_source = 'github'
        comments = []
        for comment in issue['comments']:
            comments.append({
                'author': comment['author'],
                'name': comment['name'],
                'body': trimString(comment['body']),
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
            map_fixVersion(mapping, issue)

        # TODO: Priority is broken
        return cls(
            source=upstream_source,
            title=issue['title'],
            url=issue['html_url'],
            upstream=upstream,
            config=config,
            comments=comments,
            tags=issue['labels'],
            fixVersion=[issue['milestone']],
            priority=issue['priority'],
            content=issue['body'] or '',
            reporter=issue['user'],
            assignee=issue['assignees'],
            status=issue['state'],
            id=issue['id'],
            storypoints=issue['storypoints'],
            upstream_id=issue['number']
        )

    def __repr__(self):
        return "<Issue %s >" % self.url


class PR(object):
    """PR intermediary object"""

    def __init__(self, source, jira_key, title, url, upstream, config,
                 comments, priority, content, reporter,
                 assignee, status, id, suffix, match, downstream=None):
        self.source = source
        self.jira_key = jira_key
        self._title = title[:254]
        self.url = url
        self.upstream = upstream
        self.comments = comments
        # self.tags = tags
        # self.fixVersion = fixVersion
        self.priority = priority

        # JIRA treats utf-8 characters in ways we don't totally understand, so scrub content down to
        # simple ascii characters right from the start.
        if content:
            # First trim the size of the content
            self.content = trimString(content)

            self.content = self.content.encode('ascii', errors='replace').decode('ascii')

            # We also apply this content in regexs to pattern match, so remove any escape characters
            self.content = self.content.replace('\\', '')
        else:
            self.content = None

        self.reporter = reporter
        self.assignee = assignee
        self.status = status
        self.id = str(id)
        self.suffix = suffix
        self.match = match
        # self.upstream_id = upstream_id

        if not downstream:
            self.downstream = config['sync2jira']['map'][self.source][upstream]
        else:
            self.downstream = downstream
        return

    @property
    def title(self):
        return u'[%s] %s' % (self.upstream, self._title)

    @classmethod
    def from_github(self, upstream, pr, suffix, config):
        """Helper function to create intermediary object."""
        # Set our upstream source
        upstream_source = 'github'

        # Format our comments
        comments = []
        for comment in pr['comments']:
            comments.append({
                'author': comment['author'],
                'name': comment['name'],
                'body': trimString(comment['body']),
                'id': comment['id'],
                'date_created': comment['date_created'],
                'changed': None
            })

        # Build our URL
        url = pr['html_url']

        # Match to a JIRA
        match = matcher(pr.get("body"), comments)

        # Figure out what state we're transitioning too
        if 'reopened' in suffix:
            suffix = 'reopened'
        elif 'closed' in suffix:
            # Check if we're merging or closing
            if pr['merged']:
                suffix = 'merged'
            else:
                suffix = 'closed'

        # Return our PR object
        return PR(
            source=upstream_source,
            jira_key=match,
            title=pr['title'],
            url=url,
            upstream=upstream,
            config=config,
            comments=comments,
            # tags=issue['labels'],
            # fixVersion=[issue['milestone']],
            priority=None,
            content=pr.get('body'),
            reporter=pr['user']['fullname'],
            assignee=pr['assignee'],
            # GitHub PRs do not have status
            status=None,
            id=pr['number'],
            # upstream_id=issue['number'],
            suffix=suffix,
            match=match,
        )


def map_fixVersion(mapping, issue):
    """
    Helper function to perform any fixVersion mapping.

    :param Dict mapping: Mapping dict we are given
    :param Dict issue: Upstream issue object
    """
    # Get our fixVersion mapping
    fixVersion_map = list(filter(lambda d: "fixVersion" in d, mapping))[0]['fixVersion']

    # Now update the fixVersion
    if issue['milestone']:
        issue['milestone'] = fixVersion_map.replace('XXX', issue['milestone'])


def matcher(content, comments):
    """
    Helper function to match to a JIRA

    :param String content: PR description
    :param List comments: Comments
    :return: JIRA match or None
    :rtype: Bool
    """
    # Build out a string with all comments and initial_comment
    all_data = " "
    for comment in reversed(comments):
        all_data += f" {comment['body']}"
    if content:
        all_data += content
    if all_data:
        # Parse to extract the JIRA information. 2 types of matches:
        # 1 - To match to JIRA issue (i.e. Relates to JIRA: FACTORY-1234)
        # 2 - To match to upstream issue (i.e. Relates to Issue: !5)
        match_jira = re.findall(r"Relates to JIRA: ([\w]*-[\d]*)",
                                all_data)
        if match_jira:
            for match in match_jira:
                # Assert that the match was correct
                if re.match(r"[\w]*-[\d]*", match):
                    return match
        else:
            return None


def trimString(content):
    """
    Helper function to trim a string to ensure it is not over 50000 char
    Ref: https://github.com/release-engineering/Sync2Jira/issues/123

    :param String content: Comment content
    :rtype: String
    """
    if len(content) > 50000:
        return content[:50000]
    else:
        return content
