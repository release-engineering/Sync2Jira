sync2jira
=========
This is a process that listens to activity on upstream repos on pagure and
github via fedmsg, and syncs new issues there to a Jira instance elsewhere.

Full documentation can be found `here <https://sync2jira.readthedocs.io/en/latest/>`_

Configuration
-------------
Configuration is in ``fedmsg.d/``.

You can maintain a mapping there that allows you to match one upstream repo
(say, 'pungi' on pagure) to a downstream project/component pair in Jira (say,
'COMPOSE', and 'Pungi').

On startup, if the ``initialize`` option is set to ``True`` in the
``fedmsg.d/`` config, then all open issues from all upstream repos will be
scraped and added to Jira if they are absent.

If the ``testing`` option is set to ``True``, then the script will perform a
"dry run" and not actually add any new issues to Jira.

What To Sync
____________

Each project is accompanied by an 'updates' array as seen below::

    'Demo_project': {'project': 'PROJECT', 'component': 'COMP',
                     'updates': [...], 'mapping': [...],
                     'owner': 'project_owner_username',
                     'default_status': 'start_status_for_issue'
                     'labels: ['tag1'..], 'qa-contact': 'some@some.com',
                     'epic-link': 'FACTORY-1234'},


The following can be added to the updates array to specify what to sync with downstream
JIRA issues::

    'comments' :: Sync comments and comment edits
    {'tags': {'overwrite': True/False}} :: Sync tags, do/don't overwrite downstream tags
    {'fixVersion'; {'overwrite': True/False}} :: Sync fixVersion (downstream milestone),
                                                 do/don't overwrite downstream fixVersion
    {'assignee': {'overwrite': True/False}} :: Sync assignee (for Github only the first assignee will sync)
                                               do/don't overwrite downstream assignee
    'description' :: Sync description
    'title' :: Sync title
    {'transition': True/'CUSTOM_TRANSITION'} :: Sync status (open/closed), Sync only status/
                                                Attempt to transition JIRA ticket to
                                                CUSTOM_TRANSITION on upstream closure
    'labels': ['tag1'..] :: Optional field to have custom set labels on all downstream issues created.
    'github_markdown' :: If description syncing is turned on, this flag will convert Github markdown to plaintext.
    'upstream_id' :: This flag will add a comment indicating the upstream issue id when an issue is created,
                     allowing the user to search for the issue downstream via the upstream ID.
    'url' :: This flag will add the upstream url to the bottom of the JIRA ticket

Note: Overwrite set to True will ensure that upstream issue fields will clear downstream
issue fields, overwrite set to False will never delete downstream issue fields only append.

The following can be added to the mapping array to specify a type of mapping between upstream/downstream fields::

    {'fixVersion': 'Test XXX'} :: This will map the upstream milestone 'milestone' to downstream fixVersion 'Text milestone'

The optional owner field can be used to specify a username that should be used if
the program cannot find a matching downstream user to assignee an issue too. The owner
field will also be used to alert users if duplicate downstream issues exist.

To set up the mailer you need to set the following environmental variables:

1. DEFAULT_FROM - Email address used to send emails

2. DEFAULT_SERVER - Mail server to be used

Custom Fields
-------------
Sync2Jira supports custom fields. You can pass them in as a parameter in your project ``custom-fields: {...}``.
If you need to add remote link to your custom field, you could use as value: `[remote-link]`.

Development
-----------

To run it yourself, you're going to need to put in some jira authentication
options into ``fedmsg.d/`` including the JIRA url and your username and
password.  Furthermore, you need the fedmsg configuration from the Fedora
rpm.  Get that with ``dnf install fedmsg``.

You will also need to get a github API token and store it in the
config as ``github_token`` to avoid being rate-limited.

If you run into SSL errors, you may need to tell python-requests to use the
system CA cert::

   $ export REQUESTS_CA_BUNDLE=/etc/pki/tls/certs/ca-bundle.crt

Caveats
-------

Here are some things that this program *does not do*:

- This program does not close Jira tickets when their corresponding ticket is
  closed upstream, although that would be cool.
- This program does not attempt to copy comments from upstream tickets to their
  corresponding downstream tickets, although that would be cool.

If there is interest in having those things, please file an RFE or comment on
an existing one `here <https://pagure.io/sync-to-jira/issues>`_ and we'll see
about prioritizing it.

Tests
-----

We have decent test coverage.

Run the tests with::

    $ sudo dnf install detox
    $ detox

    
