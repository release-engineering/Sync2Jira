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

# Build-In Modules
import operator
import logging
import re
import difflib

# 3rd Party Modules
import arrow
import jira.client
from jira import JIRAError
from datetime import datetime
import jinja2
import pypandoc

# Local Modules
from sync2jira.intermediary import Issue, PR

# The date the service was upgraded
# This is used to ensure legacy comments are not touched
UPDATE_DATE = datetime(2019, 7, 9, 18, 18, 36, 480291)

log = logging.getLogger('sync2jira')

duplicate_issues_subject = 'FYI: Duplicate Sync2jira Issues'

jira_cache = {}

def _comment_format(comment):
    """
    Function to format JIRA comments.

    :param dict comment: Upstream comment
    :returns: Comments formatted
    :rtype: String
    """
    pretty_date = comment['date_created'].strftime("%a %b %d")
    return "[%s] Upstream, %s wrote [%s]:\n\n{quote}\n%s\n{quote}" % (
        comment['id'], comment['author'], pretty_date, comment['body'])


def get_jira_client(issue, config):
    """
    Function to match and create JIRA client.

    :param sync2jira.intermediary.Issue issue: Issue object
    :param dict config: Config dict
    :returns: Matching JIRA client
    :rtype: jira.client.JIRA
    """
    # The name of the jira instance to use is stored under the 'map'
    # key in the config where each upstream is mapped to jira projects.
    # It is conveniently added to the Issue object from intermediary.py
    # so we can use it here:

    if not isinstance(issue, Issue) and not isinstance(issue, PR):
        log.error("passed in issue is not an Issue instance")
        log.error("It is a %s" % type(issue).__name__)
        raise TypeError("Got %s, expected Issue" % type(issue).__name__)

    # Use the Jira instance set in the issue config. If none then
    # use the configured default jira instance.
    jira_instance = issue.downstream.get('jira_instance', False)
    if not jira_instance:
        jira_instance = config['sync2jira'].get('default_jira_instance', False)
    if not jira_instance:
        log.error("No jira_instance for issue and there is no default in the config")
        raise Exception
    
    client = jira.client.JIRA(**config['sync2jira']['jira'][jira_instance])
    return client


def _matching_jira_issue_query(client, issue, config, free=False):
    """
    API calls that find matching JIRA tickets if any are present.

    :param jira.client.JIRA client: JIRA client
    :param sync2jira.intermediary.Issue issue: Issue object
    :param Dict config: Config dict
    :param Bool free: Free tag to add 'statusCategory != Done' to query
    :returns: results: Returns a list of matching JIRA issues if any are found
    :rtype: List
    """
    # Searches for any remote link to the issue.url\
    issue_title = issue.title.replace('[', '').replace(']', '')
    query = f'summary ~ "{issue_title}"'

    # Query the JIRA client and store the results
    results_of_query = client.search_issues(query)
    if len(results_of_query) > 1:
        # Sometimes if an issue gets dropped it is created with the url: pagure.com/something/issue/5
        # Then when that issue is dropped and another one is created is is created with the same
        # url : pagure.com/something/issue/5.
        # We need to ensure that we are not catching a dropped issue
        # Loop through the results of the query and make sure the ids match
        final_results = []

        for result in results_of_query:
            description = result.fields.description or ""
            summary = result.fields.summary or ""
            if issue.id in description or issue.title == summary:
                search = check_comments_for_duplicate(client, result,
                                                      find_username(issue, config))
                if search is True:
                    final_results.append(result)
                else:
                    # Else search returned a linked issue
                    final_results.append(search)
            # If that's not the case, check if they have the same upstream title
            # Upstream username/repo can change if repos are merged
            elif re.search(r"\[[a-zA-Z0-9!@#$%^&*()_+\-=\[\]{};':\\|,.<>\/?]*\] "
                           + issue.upstream_title,
                           result.fields.summary):
                search = check_comments_for_duplicate(client, result,
                                                      find_username(issue, config))
                if search is True:
                    # We went through all the comments and didn't find anything
                    # that indicated it was a duplicate
                    log.warning('Matching downstream issue %s to upstream issue %s' %
                                (result.fields.summary, issue.title))
                    final_results.append(result)
                else:
                    # Else search returned a linked issue
                    final_results.append(search)
        if not final_results:
            # Just return the most updated issue
            results_of_query.sort(key=lambda x: datetime.strptime(
                x.fields.updated, '%Y-%m-%dT%H:%M:%S.%f+0000'))
            final_results.append(results_of_query[0])

        # Return the final_results
        log.debug("Found %i results for query %r", len(final_results), query)

        return final_results
    else:
        return results_of_query

def find_username(issue, config):
    """
    Finds JIRA username for an issue object.

    :param sync2jira.intermediary.Issue issue: Issue object
    :param Dict config: Config dict
    :returns: Username string
    :rtype: String
    """
    jira_instance = issue.downstream.get('jira_instance', False)
    if not jira_instance:
        jira_instance = config['sync2jira'].get('default_jira_instance', False)
    if not jira_instance:
        log.error("No jira_instance for issue and there is no default in the config")
        raise Exception
    return config['sync2jira']['jira'][jira_instance]['basic_auth'][0]


def check_comments_for_duplicate(client, result, username):
    """
    Checks comment of JIRA issue to see if it has been
    marked as a duplicate.

    :param jira.client.JIRA client: JIRA client)
    :param jira.resource.Issue result: JIRA issue
    :param string username: Username of JIRA user
    :returns: True if duplicate comment was not found or JIRA issue if \
              we were able to find it
    :rtype: Bool or jira.resource.Issue
    """
    for comment in client.comments(result):
        search = re.search(r'Marking as duplicate of (\w*)-(\d*)',
                           comment.body)
        if search and comment.author.name == username:
            issue_id = search.groups()[0] + '-' + search.groups()[1]
            return client.issue(issue_id)
    return True


def _find_comment_in_jira(comment, j_comments):
    """
    Helper function to filter out comments that are matching.

    :param Dict comment: Individual comment from upstream
    :param List j_comments: Comments from JIRA downstream
    :returns: Item/None
    :rtype: jira.resource.Comment/None
    """
    formatted_comment = _comment_format(comment)
    for item in j_comments:
        if str(comment['id']) in item.raw['body']:
            # The comment id's match, if they dont have the same body,
            # we need to edit the comment
            if item.raw['body'] != formatted_comment:
                # We need to update the comment
                item.update(body=formatted_comment)
                log.info('Updated one comment')
                # Now we can just return the item
                return item
            else:
                # Else they are equal and we can return the item
                return item
        if comment['date_created'] < UPDATE_DATE:
            # If the comments date is prior to the update_date
            # We should not try to touch the comment
            return item
    return None


def _comment_matching(g_comments, j_comments):
    """
    Function to filter out comments that are matching.

    :param List g_comments: Comments from Issue object
    :param List j_comments: Comments from JIRA downstream
    :returns: Returns a list of comments that are not matching
    :rtype: List
    """
    return list(
        filter(
            lambda x: _find_comment_in_jira(x, j_comments) is None or x['changed'] is not None,
            g_comments
            )
        )


def _get_existing_jira_issue(client, issue, config):
    """
    Get a jira issue by the linked remote issue. \
    This is the new supported way of doing this.

    :param jira.client.JIRA client: JIRA client
    :param sync2jira.intermediary.Issue issue: Issue object
    :param Dict config: Config dict
    :returns: Returns a list of matching JIRA issues if any are found
    :rtype: List
    """
    results = _matching_jira_issue_query(client, issue, config)
    if results:
        return results[0]
    else:
        return None


def attach_link(client, downstream, remote_link):
    """
    Attaches the upstream link to the JIRA ticket.

    :param jira.client.JIRA client: JIRA client
    :param jira.resources.Issue downstream: Response from creating the JIRA ticket
    :param dict remote_link: Remote link dict with {'url': ...  , 'title': ... }
    :return: downstream: Response from creating the JIRA ticket
    :rtype: jira.resources.Issue
    """
    log.info("Attaching tracking link %r to %r", remote_link, downstream.key)
    if (downstream.fields.description is None):
        previous_description = ""
    else:
        previous_description = downstream.fields.description
    modified_desc = previous_description + " "

    # This is crazy.  Querying for application links requires admin perms which
    # we don't have, so duckpunch the client to think it has already made the
    # query.
    client._applicationlinks = []  # pylint: disable=protected-access

    # Add the link.
    client.add_remote_link(downstream.id, remote_link)

    # Finally, after we've added the link we have to edit the issue so that it
    # gets re-indexed, otherwise our searches won't work. Also, Handle some
    # weird API changes here...
    log.debug("Modifying desc of %r to trigger re-index.", downstream.key)
    # downstream.update({'description': modified_desc})

    return downstream


def change_status(client, downstream, status, issue):
    """
    Change status of JIRA issue.


    :param jira.client.JIRA client: JIRA client
    :param jira.resources.Issue/PR downstream: JIRA issue or PR object
    :param String status: Title of status to which issue should be move
    :param sync2jira.intermediary.Issue issue: Issue object
    """
    transitions = client.transitions(downstream)
    id = ''
    for t in transitions:
        if t['name'] and status.upper() == str(t['name']).upper():
            id = int(t['id'])
            break
    if id:
        try:
            client.transition_issue(downstream, id)
            log.info('Updated downstream to %s status for issue %s' % (status, issue.title))
        except JIRAError:
            log.error('Updating downstream issue failed for %s: %s' % (status, issue.title))
    else:
        log.warning('Could not update JIRA %s for %s' % (status, issue.title))


def _create_jira_issue(client, issue, config):
    """
    Create a JIRA issue and adds all relevant
    information in the issue to the JIRA issue.

    :param jira.client.JIRA client: JIRA client
    :param sync2jira.intermediary.Issue issue: Issue object
    :param Dict config: Config dict
    :returns: Returns JIRA issue that was created
    :rtype: jira.resources.Issue
    """
    log.info("Creating %r issue for %r", issue.downstream, issue)
    if config['sync2jira']['testing']:
        log.info("Testing flag is true.  Skipping actual creation.")
        return

    custom_fields = issue.downstream.get('custom_fields', {})

    # Determine the type of issue based on the tags available
    issue_type = 'Bug'
    if ('story' in issue.tags):
        issue_type = 'Story'
    elif ('task' in issue.tags):
        issue_type = 'Task'

    # Build the description of the JIRA issue
    if 'description' in issue.downstream.get('issue_updates', {}):
        description = "Upstream description: {quote}%s{quote}" % issue.content
    else:
        description = ''

    if any('transition' in item for item in issue.downstream.get('issue_updates', {})):
        # Just add it to the top of the description
        formatted_status = "Upstream issue status: %s" % issue.status
        description = formatted_status + '\n' + description

    # Add the url if requested
    if 'url' in issue.downstream.get('issue_updates', {}):
        description = description + f"\nUpstream URL: {issue.url}"

    kwargs = dict(
        summary=issue.title,
        description=description,
        issuetype=dict(name=issue_type),
    )

    if issue.downstream['project']:
        kwargs['project'] = dict(key=issue.downstream['project'])
    if issue.downstream.get('component'):
        # TODO - make this a list in the config
        kwargs['components'] = [dict(name=issue.downstream['component'])]

    for key, custom_field in custom_fields.items():
        if type(custom_field) is str:
            kwargs[key] = custom_field.replace("[remote-link]", issue.url)
        else:
            kwargs[key] = custom_field

    # Add labels if needed
    if 'labels' in issue.downstream.keys():
        kwargs['labels'] = issue.downstream['labels']
    
    jira_username = get_jira_username_from_github(config, issue.reporter['fullname'])
    kwargs['reporter'] = {'id': jira_username}

    log.info("Creating issue.")
    downstream = client.create_issue(**kwargs)

    remote_link = dict(url=issue.url, title=f"[Issue] {issue.title}")
    attach_link(client, downstream, remote_link)

    default_status = issue.downstream.get('default_status', None)
    if default_status is not None:
        change_status(client, downstream, default_status, issue)

    # Update relevant information (i.e. tags, assignees etc.) if the
    # User opted in
    _update_jira_issue(downstream, issue, client, config)

    return downstream


def _label_matching(jira_labels, issue_labels):
    """
    Filters through jira_labels to ensure no duplicate labels are present and
    no jira_labels are removed.

    :param List jira_labels: Existing JIRA labels
    :param List issue_labels: Upstream labels
    :returns: Updated filtered labels
    :rtype: List
    """
    # We want to get the union of the jira_labels and the issue_labels
    # i.e. all the labels in jira_labels and no duplicates from issue_labels
    updated_labels = list(set(jira_labels).union(set(issue_labels)))
    # Return our labels
    return updated_labels


def _update_jira_issue(existing, issue, client, config):
    """
    Updates an existing JIRA issue (i.e. tags, assignee, comments etc).

    :param jira.resources.Issue existing: Existing JIRA issue that was found
    :param sync2jira.intermediary.Issue issue: Upstream issue we're pulling data from
    :param jira.client.JIRA client: JIRA Client
    :returns: Nothing
    """
    # Start with comments
    # Only synchronize comments for listings that op-in
    log.info("Updating information for upstream issue: %s" % issue.title)

    # Get a list of what the user wants to update for the upstream issue
    updates = issue.downstream.get('issue_updates', [])

    # Update relevant data if needed
    # If the user has specified nothing
    if not updates:
        return

    # Only synchronize comments for listings that op-in
    if 'comments' in updates:
        log.info("Looking for new comments")
        _update_comments(client, existing, issue)

    # Only synchronize tags for listings that op-in
    if any('tags' in item for item in updates):
        log.info("Looking for new tags")
        _update_tags(updates, existing, issue)

    # Only synchronize fixVersion for listings that op-in
    if any('fixVersion' in item for item in updates) and issue.fixVersion:
        log.info("Looking for new fixVersions")
        _update_fixVersion(updates, existing, issue, client)

    # Only synchronize assignee for listings that op-in
    if any('assignee' in item for item in updates):
        log.info("Looking for new assignee(s)")
        _update_assignee(client, existing, issue, updates, config)

    # Only synchronize descriptions for listings that op-in
    if 'description' in updates:
        log.info("Looking for new description")
        _update_description(existing, issue)

    # Only synchronize title for listings that op-in
    if 'title' in updates:
        # Update the title if needed
        if issue.title != existing.fields.summary:
            log.info("Looking for new title")
            _update_title(issue, existing)

    # Only synchronize url for listings that op-in
    if 'url' in updates:
        log.info("Looking for new url")
        _update_url(existing, issue)

    # Only synchronize transition (status) for listings that op-in
    if any('transition' in item for item in updates):
        log.info("Looking for new transition(s)")
        _update_transition(client, existing, issue)

    # Only execute 'on_close' events for listings that opt-in
    log.info("Attempting to update downstream issue on upstream closed event")
    _update_on_close(existing, issue, updates)

    log.info('Done updating %s!' % issue.title)


def _update_url(existing, issue):
    """
    Helper function to update the transition of a downstream JIRA issue.

    :param jira.resource.Issue existing: Existing JIRA issue
    :param sync2jira.intermediary.Issue issue: Upstream issue
    :returns: Nothing
    """
    # First check if the url needs to be updated
    if issue.url in existing.fields.description:
        # There is nothing to update
        return

    # Else add the url to the bottom of the description
    new_description = f"Upstream URL: {issue.url}\n"
    new_description = existing.fields.description + "\n" + new_description

    # Update our issue
    data = {'description': new_description}
    existing.update(data)
    log.info('Updated description')


def _update_transition(client, existing, issue):
    """
    Helper function to update the transition of a downstream JIRA issue.

    :param jira.client.JIRA client: JIRA client
    :param jira.resource.Issue existing: Existing JIRA issue
    :param sync2jira.intermediary.Issue issue: Upstream issue
    :returns: Nothing
    """
    # Update the issue status in the JIRA description
    # Format the status
    formatted_status = "Upstream issue status: %s" % issue.status
    new_description = existing.fields.description
    # Bool to indicate if we should update
    update = False
    # Check if the issue has the issue status line
    # First check legacy upstream status so we can update them
    if "] Upstream issue status:" in existing.fields.description:
        # Use pattern matching to find and update the status
        new_description = re.sub(
            r"\[.*\] Upstream issue status: .*",
            formatted_status,
            new_description)
        update = True
    # Now check if the status is already present
    elif formatted_status in existing.fields.description:
        pass
    # Then check for upstream status
    elif "Upstream issue status:" in existing.fields.description:
        # Use pattern matching to find and update the status
        new_description = re.sub(
            r"Upstream issue status: .*",
            formatted_status,
            new_description)
        update = True
    else:
        # We can just add this line to the very top
        new_description = formatted_status + '\n' + new_description
        update = True
    if update:
        # Now we can update the JIRA issue (always need to update this
        # as there is a timestamp involved)
        data = {'description': new_description}
        existing.update(data)
        log.info('Updated transition')

    # If the user just inputted True, only update the description
    # If the user added a custom closed status, attempt to close the
    # downstream JIRA ticket

    # First get the closed status from the config file
    try:
        # For python 3 >
        closed_status = list(filter(lambda d: "transition" in d, issue.downstream.get('issue_updates', {})))[0]['transition']
    except ValueError:
        # for python 2.7
        closed_status = (filter(lambda d: "transition" in d, issue.downstream.get('issue_updates', {})))[0]['transition']
    if closed_status is not True and issue.status == 'Closed' \
            and existing.fields.status.name.upper() != closed_status.upper():
        # Now we need to update the status of the JIRA issue
        # First add a comment indicating the change (in case it doesn't go through)
        hyperlink = f"[Upstream issue|{issue.url}]"
        comment_body = f"{hyperlink} closed. Attempting transition to {closed_status}."
        client.add_comment(existing, comment_body)
        # Ensure that closed_status is a valid choice
        # Find all possible transactions (i.e. change states) we could `do
        change_status(client, existing, closed_status, issue)


def _update_title(issue, existing):
    """
    Helper function to sync upstream/downstream title.

    :param sync2jira.intermediary.Issue issue: Upstream issue
    :param jira.resource.Issue existing: Existing JIRA issue
    :returns: Nothing
    """
    new_description = existing.fields.description
    if not new_description:
        new_description = ''

    if '] Upstream Reporter:' not in new_description:
        # We have to add the issue ID to the description so we can find it again
        if '] Upstream issue status:' in new_description:
            # We have to use regex to update the upstream reporter
            today = datetime.today()
            new_description = re.sub(
                r'\[[\w\W]*\] Upstream issue status: %s' % issue.status,
                '[%s] Upstream issue status: %s\n[%s] Upstream Reporter: %s'
                % (today.strftime("%a %b %y - %H:%M"),
                   issue.status, issue.id, issue.reporter['fullname']),
                new_description)
        else:
            # We can just add it to the top
            new_description = '[%s] Upstream Reporter: %s' % \
                              (issue.id, issue.reporter['fullname']) + new_description
        # Update the description
        # Now that we've updated the description (i.e. added
        # issue.id) we can delete the link in the description if its still there.
        new_description = re.sub(
            r'%s' % issue.url,
            r'',
            new_description
        )

        # Now we can update the JIRA issue if we need to
        if new_description.replace(' ', '') != existing.fields.description.replace(' ', ''):
            data = {'description': new_description}
            existing.update(data)
            log.info('Updated description')
    # Then we can update the title
    data = {'summary': issue.title}
    existing.update(data)
    log.info('Updated title')


def _update_comments(client, existing, issue):
    """
    Helper function to sync comments between existing JIRA issue and upstream issue.

    :param jira.client.JIRA client: JIRA client
    :param jira.resource.Issue existing: Existing JIRA issue
    :param sync2jira.intermediary.Issue issue: Upstream issue
    :returns: Nothing
    """
    # First get all existing comments
    comments = client.comments(existing)
    # Remove any comments that have already been added
    comments_d = _comment_matching(issue.comments, comments)
    # Loop through the comments that remain
    for comment in comments_d:
        # Format and add them
        comment_body = _comment_format(comment)
        client.add_comment(existing, comment_body)
    if len(comments_d) > 0:
        log.info("Comments synchronization done on %i comments." % len(comments_d))


def _update_fixVersion(updates, existing, issue, client):
    """
    Helper function to sync comments between existing JIRA issue and upstream issue.

    :param List updates: Downstream updates requested by the user
    :param jira.resource.Issue existing: Existing JIRA issue
    :param sync2jira.intermediary.Issue issue: Upstream issue
    :param jira.client.JIRA client: JIRA client
    :returns: Nothing
    """
    fix_version = []
    # If we are not supposed to overwrite JIRA content
    try:
        # For python 3 >
        if not bool(list(filter(lambda d: "fixVersion" in d, updates))[0]['fixVersion']['overwrite']):
            # We need to make sure we're not deleting any fixVersions on JIRA
            # Get all fixVersions for the issue
            for version in existing.fields.fixVersions:
                fix_version.append({'name': version.name})
    except ValueError:
        # for python 2.7
        if not bool((filter(lambda d: "fixVersion" in d, updates))[0]['fixVersion']['overwrite']):
            # We need to make sure we're not deleting any fixVersions on JIRA
            # Get all fixVersions for the issue
            for version in existing.fields.fixVersions:
                fix_version.append({'name': version.name})

    # Github and Pagure do not allow for multiple fixVersions (milestones)
    # But JIRA does, that is why we're looping here. Hopefully one
    # Day Github/Pagure will support multiple fixVersions :0
    for version in issue.fixVersion:
        if version is not None:
            # Update the fixVersion only if it's already not in JIRA
            result = filter(lambda v: v['name'] == str(version), fix_version)
            # If we have a result skip, if not then add it to fix_version
            if not result or not list(result):
                fix_version.append({'name': version})

    # We don't want to make an API call if the labels are the same
    jira_labels = []
    for label in existing.fields.fixVersions:
        jira_labels.append({'name': label.name})
    res = [i for i in jira_labels if i not in fix_version] + \
          [j for j in fix_version if j not in jira_labels]
    if res:
        data = {'fixVersions': fix_version}
        # If the fixVersion is not in JIRA, it will throw an error
        try:
            existing.update(data)
            log.info('Updated %s fixVersion(s)' % len(fix_version))
        except JIRAError:
            log.warning('Error updating the fixVersion. %s is an invalid fixVersion.' % issue.fixVersion)
            # Add a comment to indicate there was an issue
            client.add_comment(existing, f"Error updating fixVersion: {issue.fixVersion}")


def _update_assignee(client, existing, issue, updates, config):
    """
        Helper function update existing JIRA assignee from downstream issue.

        :param jira.client.JIRA client: JIRA client
        :param jira.resource.Issue existing: Existing JIRA issue
        :param sync2jira.intermediary.Issue issue: Upstream issue
        :param List updates: Downstream updates requested by the user
        :param dict config: Config dict
        :returns: Nothing
    """


    # First check if overwrite is set to True
    try:
        # For python 3 >
        overwrite = bool(list(filter(lambda d: "assignee" in d, updates))[0]['assignee']['overwrite'])
    except ValueError:
        # for python 2.7
        overwrite = bool((filter(lambda d: "assignee" in d, updates))[0]['assignee']['overwrite'])

    if not issue.assignee and overwrite is False:
        return
    elif not issue.assignee and overwrite is True:
        existing.update({'assignee': {'name': ''}})
        log.info('Updated assignee')
        return

    # First find our mapped user in JIRA if they exist, else just quit
    mapped_jira_id = config['mapping'][issue.assignee[0].name]['jira']

    if not mapped_jira_id:
        log.warn('Could not update assignee')
        return

    # First check if the issue is already assigned to the same person
    update = False
    if issue.assignee and issue.assignee[0]:
        try:
            update = mapped_jira_id != existing.fields.assignee.key
        except AttributeError:
            update = True

    if not overwrite:
        # Only assign if the existing JIRA issue doesn't have an assignee
        # And the issue has an assignee
        if not existing.fields.assignee and issue.assignee:
            if issue.assignee[0] and update:
                existing.update({'assignee': {'id': mapped_jira_id}})
                log.info('Updated assignee')
                return
    else:
        # Update the assignee if we have someone to assignee it too
        if update:
            existing.update({'assignee': {'id': mapped_jira_id}})
            log.info('Updated assignee')
        else:
            if existing.fields.assignee and not issue.assignee:
                # Else we should remove all assignees
                # Set removeAll flag to true
                existing.update({'assignee': {'name': ''}})
                log.info('Updated assignee')


def _update_jira_labels(issue, labels):
    """Update a Jira issue with 'labels'

    Do this only if the current labels would change.

    :param jira.resource.Issue issue: Jira issue to be updated
    :param list<strings> labels: Lables to be applied on the issue
    :returns: None
    """
    _labels = sorted(labels)
    if _labels == sorted(issue.fields.labels):
        return

    data = {'labels': _labels}
    issue.update(data)
    log.info('Updated %s tag(s)' % len(_labels))


def _update_tags(updates, existing, issue):
    """
    Helper function to sync tags between upstream issue and downstream JIRA issue.

    :param List updates: Downstream updates requested by the user
    :param jira.resource.Issue existing: Existing JIRA issue
    :param sync2jira.intermediary.Issue issue: Upstream issue
    :returns: Nothing
    """
    # First get all existing tags on the issue
    updated_labels = issue.tags

    # Ensure no duplicates if overwrite is set to false
    try:
        # for python 3 >
        if not bool(list(filter(lambda d: "tags" in d, updates))[0]['tags']['overwrite']):
            updated_labels = _label_matching(updated_labels, existing.fields.labels)
    except ValueError:
        # for python 2.7
        if not bool(filter(lambda d: "tags" in d, updates)[0]['tags']['overwrite']):
            updated_labels = _label_matching(updated_labels, existing.fields.labels)

    # Ensure that the tags are all valid
    updated_labels = verify_tags(updated_labels)

    # Now we can update the JIRA if labels are different
    _update_jira_labels(existing, updated_labels)


def _update_description(existing, issue):
    """
    Helper function to sync description between upstream issue and downstream JIRA issue.

    :param jira.resource.Issue existing: Existing JIRA issue
    :param sync2jira.intermediary.Issue issue: Upstream issue
    :returns: Nothing
    """
    new_description = existing.fields.description
    if not new_description:
        new_description = ''
    if 'Upstream description' in new_description:
        # If we just need to update the content of the description
        new_description = re.sub(
            r"Upstream description:(\r\n*|\r*|\n*|.*){quote}((?s).*){quote}",
            r"Upstream description: {quote}%s{quote}" % issue.content,
            new_description)
    else:
        # Just add description to the top
        upstream_description = "Upstream description: " \
                               "{quote}%s{quote}" % \
                               (issue.content)
        new_description = '%s \n %s' % \
                          (upstream_description, new_description)
    # Now that we've updated the description (i.e. added
    # issue.id) we can delete the link in the description if its still there.
    if 'url' not in issue.downstream.get('issue_updates', {}):
        new_description = re.sub(
            r'%s' % issue.url,
            r'',
            new_description
        )

    # Now we can update the JIRA issue if we need to
    if new_description != existing.fields.description:
        data = {'description': new_description}
        existing.update(data)
        log.info('Updated description')


def _update_on_close(existing, issue, updates):
    """Update downstream Jira issue when upstream issue was closed

    Example update configuration:
    [
        ...,
        {
            "on_close": {
                {
                    "apply_labels": [
                        "closed-upstream"
                    ]
                }
            }
        },
        ...
    ]

    :param jira.resource.Issue existing: existing Jira issue
    :param sync2jira.intermediary.Issue issue: Upstream issue
    :param dict updates: update configuration
    :return: None
    """
    on_close_updates = None
    for item in updates:
        if 'on_close' in item:
            on_close_updates = item['on_close']
            break

    if not on_close_updates:
        return

    if issue.status != 'Closed':
        return

    if 'apply_labels' not in on_close_updates:
        return

    updated_labels = list(
        set(existing.fields.labels).union(set(on_close_updates['apply_labels']))
    )
    log.info("Applying 'on_close' labels to downstrem Jira issue")
    _update_jira_labels(existing, updated_labels)


def verify_tags(tags):
    """
    Helper function to ensure tag are JIRA ready :).

    :param List tags: Input tags
    :returns: Updates tags
    :rtype: List
    """
    updated_tags = []
    for tag in tags:
        updated_tags.append(tag.replace(" ", "_"))
    return updated_tags


def sync_with_jira(issue, config):
    """
    Attempts to sync a upstream issue with JIRA (i.e. by finding
    an existing issue or creating a new one).

    :param sync2jira.intermediary.Issue issue: Issue object
    :param Dict config: Config dict
    :returns: Nothing
    """

    log.info("[Issue] Considering upstream %s, %s", issue.url, issue.title)

    # Create a client connection for this issue
    client = get_jira_client(issue, config)

    if issue.downstream.get('issue_updates', None):
        if issue.source == 'github' and issue.content and \
                'github_markdown' in issue.downstream['issue_updates']:
            issue.content = pypandoc.convert_text(issue.content, 'plain', format='md')

    # First, check to see if we have a matching issue using the new method.
    # If we do, then just bail out.  No sync needed.
    log.info("Looking for matching downstream issue via new method.")
    existing = _get_existing_jira_issue(client, issue, config)
    if existing:
        # If we found an existing JIRA issue already
        log.info("Found existing, matching downstream %r.", existing.key)
        if config['sync2jira']['testing']:
            log.info("Testing flag is true.  Skipping actual update.")
            return
        # Update relevant metadata (i.e. tags, assignee, etc)
        _update_jira_issue(existing, issue, client, config)
        return

    # If we're *not* configured to do legacy matching (upgrade mode) then there
    # is nothing left to do than to but to create the issue and return.
    if not config['sync2jira'].get('legacy_matching', True):
        log.debug("Legacy matching disabled.")
        _create_jira_issue(client, issue, config)
        return

    # Otherwise, if we *are* configured to do legacy matching, then try and
    # find this issue the old way.
    # - If we can't find it, create it.
    # - If we can find it, upgrade it to the new method.
    log.info("Looking for matching downstream issue via legacy method.")
    match = _get_existing_jira_issue_legacy(client, issue, config)
    if not match:
        _create_jira_issue(client, issue, config)
    else:
        _upgrade_jira_issue(client, match, issue, config)

def get_jira_username_from_github(config, github_login):
    """ Helper function to get JIRA username from Github login """
    for name, data in config['mapping'].items():
        if name == github_login:
            return data['jira']