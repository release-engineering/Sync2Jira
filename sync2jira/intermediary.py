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
from typing import Optional


class Issue(object):
    """Issue Intermediary object"""

    def __init__(
        self,
        source,
        title,
        url,
        upstream,
        comments,
        config,
        tags,
        fixVersion,
        priority,
        content,
        reporter,
        assignee,
        status,
        id_,
        storypoints,
        upstream_id,
        issue_type,
        downstream=None,
    ):
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
        self.content = trim_string(content)

        # JIRA treats utf-8 characters in ways we don't totally understand, so scrub content down to
        # simple ascii characters right from the start.
        self.content = self.content.encode("ascii", errors="replace").decode("ascii")

        # We also apply this content in regexs to pattern match, so remove any escape characters
        self.content = self.content.replace("\\", "")

        self.reporter = reporter
        self.assignee = assignee
        self.status = status
        self.id = str(id_)
        self.upstream_id = upstream_id
        self.issue_type = issue_type
        if not downstream:
            self.downstream = config["sync2jira"]["map"][self.source][upstream]
        else:
            self.downstream = downstream

    @property
    def title(self):
        _title = "[%s] %s" % (self.upstream, self._title)
        return _title[:254].strip()

    @property
    def upstream_title(self):
        return self._title

    @classmethod
    def from_github(cls, upstream, issue, config):
        """Helper function to create an intermediary Issue object."""
        upstream_source = "github"
        comments = reformat_github_comments(issue)

        # Reformat the state field
        if issue["state"]:
            if issue["state"] == "open":
                issue["state"] = "Open"
            elif issue["state"] == "closed":
                issue["state"] = "Closed"

        # Get the issue type if any
        issue_type = issue.get("type")
        if isinstance(issue_type, dict):
            issue_type = issue_type.get("name")

        # Perform any mapping
        mapping = config["sync2jira"]["map"][upstream_source][upstream].get(
            "mapping", []
        )

        # Check for fixVersion
        if any("fixVersion" in item for item in mapping):
            map_fixVersion(mapping, issue)

        return cls(
            source=upstream_source,
            title=issue["title"],
            url=issue["html_url"],
            upstream=upstream,
            config=config,
            comments=comments,
            tags=issue["labels"],
            fixVersion=[issue["milestone"]],
            priority=issue.get("priority"),
            content=issue["body"] or "",
            reporter=issue["user"],
            assignee=issue["assignees"],
            status=issue["state"],
            id_=issue["id"],
            storypoints=issue.get("storypoints"),
            upstream_id=issue["number"],
            issue_type=issue_type,
        )

    def __repr__(self):
        return f"<Issue {self.url} >"


class PR(object):
    """PR intermediary object"""

    def __init__(
        self,
        source,
        jira_key,
        title,
        url,
        upstream,
        config,
        comments,
        priority,
        content,
        reporter,
        assignee,
        status,
        id_,
        suffix,
        match,
        downstream=None,
    ):
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
            self.content = trim_string(content)

            self.content = self.content.encode("ascii", errors="replace").decode(
                "ascii"
            )

            # We also apply this content in regexs to pattern match, so remove any escape characters
            self.content = self.content.replace("\\", "")
        else:
            self.content = None

        self.reporter = reporter
        self.assignee = assignee
        self.status = status
        self.id = str(id_)
        self.suffix = suffix
        self.match = match
        # self.upstream_id = upstream_id

        if not downstream:
            self.downstream = config["sync2jira"]["map"][self.source][upstream]
        else:
            self.downstream = downstream
        return

    @property
    def title(self):
        return "[%s] %s" % (self.upstream, self._title)

    @classmethod
    def from_github(cls, upstream, pr, suffix, config):
        """Helper function to create an intermediary PR object."""
        # Set our upstream source
        upstream_source = "github"

        # Format our comments
        comments = reformat_github_comments(pr)

        # Build our URL
        url = pr["html_url"]

        # Match to a JIRA
        match = matcher(pr.get("body"), comments)

        # Figure out what state we're transitioning too
        if "reopened" in suffix:
            suffix = "reopened"
        elif "closed" in suffix:
            # Check if we're merging or closing
            if pr["merged"]:
                suffix = "merged"
            else:
                suffix = "closed"

        # Return our PR object
        return cls(
            source=upstream_source,
            jira_key=match,
            title=pr["title"],
            url=url,
            upstream=upstream,
            config=config,
            comments=comments,
            # tags=issue['labels'],
            # fixVersion=[issue['milestone']],
            priority=None,
            content=pr.get("body"),
            reporter=pr["user"]["fullname"],
            assignee=pr["assignee"],
            # GitHub PRs do not have status
            status=None,
            id_=pr["number"],
            # upstream_id=issue['number'],
            suffix=suffix,
            match=match,
        )


def reformat_github_comments(issue):
    return [
        {
            "author": comment["author"],
            "name": comment["name"],
            "body": trim_string(comment["body"]),
            "id": comment["id"],
            "date_created": comment["date_created"],
            "changed": None,
        }
        for comment in issue["comments"]
    ]


def map_fixVersion(mapping, issue):
    """
    Helper function to perform any fixVersion mapping.

    :param Dict mapping: Mapping dict we are given
    :param Dict issue: Upstream issue object
    """
    # Get our fixVersion mapping
    fixVersion_map = next(filter(lambda d: "fixVersion" in d, mapping))["fixVersion"]

    # Now update the fixVersion
    if issue["milestone"]:
        issue["milestone"] = fixVersion_map.replace("XXX", issue["milestone"])


JIRA_REFERENCE = re.compile(r"\bJIRA:\s*([A-Z][A-Z0-9]*-\d+)\b")


def matcher(content: Optional[str], comments: list[dict[str, str]]) -> str:
    """
    Helper function to match to a JIRA

    Extract the Jira ticket reference from the first instance of the magic
    cookie (e.g., "JIRA: FACTORY-1234") found when searching
    through the comments in reverse order.  If no reference is found in the
    comments, then look in the PR description.  This ordering allows later
    comments to override earlier ones as well as any reference in the
    description.

    :param String content: PR description
    :param List comments: Comments
    :return: JIRA match or None
    :rtype: Bool
    """

    def find_it(input_str: str) -> Optional[str]:
        if not input_str:
            return None
        match = JIRA_REFERENCE.search(input_str)
        return match.group(1) if match else None

    for comment in reversed(comments):
        match_str = find_it(comment["body"])
        if match_str:
            break
    else:
        match_str = find_it(content)
    return match_str


def trim_string(content):
    """
    Helper function to trim a string to ensure it is not over 50,000 char
    Ref: https://github.com/release-engineering/Sync2Jira/issues/123

    :param String content: Comment content
    :rtype: String
    """
    if len(content) > 50000:
        return content[:50000]
    else:
        return content
