Intermediary
============

Sync2Jira converts upstream issues into custom Issue objects. You can see the __init__ below: 

.. code-block:: python

        def __init__(self, source, title, url, upstream, comments,
                 config, tags, fixVersion, priority, content,
                 reporter, assignee, status, id, downstream=None):
            self.source = source
            self._title = title
            self.url = url
            self.upstream = upstream
            self.comments = comments
            self.tags = tags
            self.fixVersion = fixVersion
            self.priority = priority
            self.content = content
            self.reporter = reporter
            self.assignee = assignee
            self.status = status
            self.id = str(id)
            if not downstream:
                self.downstream = config['sync2jira']['map'][self.source][upstream]
            else:
                self.downstream = downstream

The object has two properties: 

.. code-block:: python

    @property
    def title(self):
        return u'[%s] %s' % (self.upstream, self._title)

* This will return the title in downstream form (i.e. [UPSTREAM_REPO] TITLE)

.. code-block:: python
    
    @property
    def upstream_title(self):
        return self._title

* This will return the raw title (i.e. TITLE)

Currently the service is set up create Issue objects from Pagure and Github: 

.. code-block:: python

    @classmethod
    def from_pagure(cls, upstream, issue, config):
        base = config['sync2jira'].get('pagure_url', 'https://pagure.io')
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

        return Issue(
            source='pagure',
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
            id=issue['date_created']
        )
    
.. code-block:: python

    @classmethod
    def from_github(cls, upstream, issue, config):
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

        # TODO: Priority is broken
        return Issue(
            source='github',
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
            id=issue['id']
        )
.. note:: Currently Priority is broken and is a known issue. 
