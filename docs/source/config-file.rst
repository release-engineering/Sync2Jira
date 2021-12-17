Config File
===========
The config file is made up of multiple parts

.. code-block:: python

    'admins': ['demo_jira_username']

* Admins can be users who manage Sync2Jira. They will be cc'd in any emails regarding duplicate issues found.

.. code-block:: python

    'mailing-list': 'demo_email@demo.com'

* Mailing list is used to alert users when there is a failure. A failure email with the traceback will be sent to the email address.

.. code-block:: python

    'initialize': 1

* Initialization set to 1 will ensure that there is an initial sync done when Sync2Jira starts.
  It is recommended to leave this as 1 to ensure that all issues are in sync.

.. code-block:: python

    'testing': True

* Testing is a flag that will determine if any changes are actually made downstream (on JIRA tickets).
  Set to false if you are developing and don't want any changes to take effect.

.. code-block:: python

    'develop': False

* If the develop flag is set to :code:`False` then Sync2Jira will perform a sentinel query after
  getting a JIRA client and failure email will be sent anytime the service fails.

.. code-block:: python

  'github_token': 'YOUR_TOKEN',

* This is where you can enter your GitHub API token.

.. code-block:: python

    'default_jira_instance': 'example'

* This is the default JIRA instance to be used if none is provided in the project.

.. code-block:: python

    'confluence_statistics': False

* Adds the ability to post statistics to confluence. See note below.

.. note:: Optional: Confluence Statistic Support

    a. What is it? If :code:`confluence_statistics` is set to `True` in the config file (default `False`) you can set up a Confluence page and space to post statistic too (i.e. how many comments synced etc)

    b. Set up the following variables:
        1. :code:`CONFLUENCE_SPACE` :: The Confluence space we're posting too
        2. :code:`CONFLUENCE_PAGE_TITLE` :: The Confluence page we're posting too
        3. :code:`CONFLUENCE_URL` :: The Confluence URL
        4. :code:`CONFLUENCE_USERNAME` :: Confluence username data
        5. :code:`CONFLUENCE_PASSWORD` :: Confluence password data

    c. Create the related confluence page and space. Make sure to add the template (use :code:`sync2jira/confluence_stat.jinja` and replace the JINJA code with 0's


.. code-block:: python

    'jira': {
        'example': {
            'options': {
                'server': 'https://some_jira_server_somewhere.com',
                'verify': True,
            },
            'token_auth': 'YOUR_API_TOKEN',
        },
    },

* Here you can configure multiple JIRA instances if you have projects with differing downstream JIRA instances.
  Ensure to name them approproialty, in name of the JIRA instance above is `example`.

.. code-block:: python

    'map': {
            'pagure': {
                'Demo_project': {'project': 'FACTORY', 'component': 'gitbz',
                                'issue_updates': [...], 'pr_updates': [...], 'mapping': [...], 'labels': [...],
                                 'owner': 'jira_username'},
                # 'koji': { 'project': 'BREW', 'component': None, },
            },
            'github': {
                'GITHUB_USERNAME/Demo_project': {'project': 'FACTORY', 'component': 'gitbz',
                                                'issue_updates': [...], 'pr_updates': [...], 'mapping': [...], 'labels': [...],
                                                'owner': 'jira_username'},
            },
        },

* You can add the following to your project configuration:

    * :code:`'project'`
        * Downstream project to sync with
    * :code:`'component'`
        * Downstream component to sync with
    * :code:`sync`
        * This array contains information on what to sync from upstream repos (i.e. 'issue' and/or 'pullrequest')
    * :code:`'owner'`
        * Optional (Recommended): Alerts the owner of an issue if there are duplicate issues present
    * :code:`'qa-contact'`
        * Optional: Automatically add a QA contact field when issues are created
    * :code:`'epic-link'`
        * Optional: Pass the downstream key to automatically create an epic-link when issues are created
    * :code:`'labels': ['tag1'..]`
        * Optional: Field to have custom set labels on all downstream issues created.
   * :code:`'EXD-Service': {'guild': 'SOME_GUILD', 'value': 'SOME_VALUE'}`
        * Sync custom EXD-Service field

     .. note::

            :pullrequest: After enabling PR syncing, just type "Relates to JIRA: XXXX-1234" in the comment or description of the PR to sync with a JIRA issue. After this, updates such as when it has been merged will automatically be added to the JIRA ticket.

* You can add your projects here. The 'project' field is associated with downstream JIRA projects, and 'component' with downstream components
  You can add the following to the :code:`issue_updates` array:

    * :code:`'comments'`
        * Sync comments and comment edits
    * :code:`{'tags': {'overwrite': True/False}}`
        * Sync tags, do/don't overwrite downstream tags
    * :code:`{'fixVersion': {'overwrite': True/False}}`
        * Sync fixVersion (downstream milestone), do/don't overwrite downstream fixVersion
    * :code:`{'assignee': {'overwrite': True/False}}`
        * Sync assignee (for Github only the first assignee will sync) do/don't overwrite downstream assignee
    * :code:`'description'`
        * Sync description
    * :code:`'title'`
        * Sync title
    * :code:`{'transition': True/'CUSTOM_TRANSITION'}`
        * Sync status (open/closed), Sync only status/Attempt to transition JIRA ticket to CUSTOM_TRANSITION on upstream closure
    * :code:`{'on_close': {'apply_lables': ['label', ...]}}`
        * When the upstream issue is closed, apply additional labels on the corresponding Jira ticket.
    * :code:`github_markdown`
        * If description syncing is turned on, this flag will convert Github markdown to plaintext. This uses the pypandoc module.
    * :code:`upstream_id`
        * If selected this will add a comment to all newly created JIRA issue in the format 'UPSTREAM_PROJECT-#1' where the number indicates the issue ID. This allows users to search for the issue on JIRA via the issue number.
    * :code:`url`
        * This flag will add the upstream url to the bottom of the JIRA ticket

    .. note::

        :Overwrite: Setting this to :code:`True` will ensure that Upstream (GitHub or Pagure) values will overwrite downstream ones (i.e. if its empty upstream it'll be empty downstream)
        :CUSTOM_TRANSITION: Setting this value will get Sync2Jira to automatially transition downstream tickets once their upstream counterparts get closed. Set this to whatever 'closed' means downstream.

* You can add your projects here. The 'project' field is associated with downstream JIRA projects, and 'component' with downstream components
  You can add the following to the :code:`pr_updates` array:

    * :code:`{'merge_transition': 'CUSTOM_TRANSITION'}`
        * Sync when upstream PR gets merged. Attempts to transition JIRA ticket to CUSTOM_TRANSITION on upstream merge
    * :code:`{'link_transition': 'CUSTOM_TRANSITION'}`
        * Sync when upstream PR gets linked. Attempts to transition JIRA ticket to CUSTOM_TRANSITION on upstream link

* You can add the following to the mapping array. This array will map an upstream field to the downstream counterpart with XXX replaced.

    * :code:`{'fixVersion': 'Test XXX'}`
        * Maps upstream milestone (suppose it's called 'milesone') to downstream fixVersion with a mapping (for our example it would be 'Test milesone')

* It is strongly encouraged for teams to use the :code:`owner` field. If configured, owners will be alerted if Sync2Jira finds duplicate downstream issues.
  Further the owner will be used as a default in case the program is unable to find a valid assignee.

.. code-block:: python

    'filters': {
            'github': {
                # Only sync multi-type tickets from bodhi.
                'fedora-infra/bodhi': {'status': 'open', 'milestone': 4, },
            },
        }

* You can also add filters per-project. The following can be added to the filter dict:

    * :code:`status`
        * Open/Closed
    * :code:`tags`
        * List of tags to look for
    * :code:`milestone`
        * Upstream milestone status
