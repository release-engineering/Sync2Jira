Quick Start
============

Want to quickly get started working with Sync2Jira? Follow these steps:

1. **First open up** :code:`fedmsg.d/sync2jira.py`

2. Enter your GitHub token which you can get `here <https://help.github.com/en/articles/creating-a-personal-access-token-for-the-command-line>`_
    .. code-block:: python

        'github_token': 'YOUR_TOKEN',

3. Enter relevant JIRA information. **PAT (default):** use ``basic_auth``. **OAuth 2.0:**
   set ``auth_method`` to ``'oauth2'`` and provide ``oauth2.client_id`` and
   ``oauth2.client_secret`` (see :doc:`config-file` for full options).

    .. code-block:: python

        'default_jira_instance': 'example',
        'jira_username': 'your-bot-account',  # optional, for duplicate detection
        'jira': {
            'example': {
                'options': {
                    'server': 'https://some_jira_server_somewhere.com',
                    'verify': True,
                },
                'auth_method': 'pat',
                'basic_auth': ('your-email@example.com', 'YOUR_API_TOKEN'),
            },
        },

    For OAuth 2.0 (e.g. Atlassian service account), use instead:

    .. code-block:: python

        'example': {
            'options': {
                'server': 'https://your-domain.atlassian.net',
                'verify': True,
            },
            'auth_method': 'oauth2',
            'oauth2': {
                'client_id': 'YOUR_CLIENT_ID',
                'client_secret': 'YOUR_CLIENT_SECRET',
            },
        },

    .. note:: You might have to set verify to False

4. Add your upstream repos to the `map` section
    .. code-block:: python

        'map': {
            'github': {
                'GITHUB_USERNAME/Demo_project': {'project': 'FACTORY', 'component': 'gitbz',
                                                 'issue_updates': [...], 'sync': [..]},
            },
        },

    .. note:: You can learn more about what can go into the issue_updates list `here <config-file.html>`_

5. Finally you can tweak the config files optional settings to your liking
    .. code-block:: python

        # Admins to be cc'd in duplicate emails
            'admins': ['demo_jira_username'],
        # Scrape sources at startup
            'initialize': True,
        # Don't actually make changes to JIRA...
            'testing': True,

        'filters': {
                'github': {
                    # Only sync multi-type tickets from bodhi.
                    'fedora-infra/bodhi': {'state': 'open', 'milestone': 4, },
                },
            }
6. Now that you're done with the config file you can install sync2jira and run
    .. code-block:: shell

        python setup.py install
        >> ....
        >> Finished processing dependencies for sync2jira==1.7
        sync2jira
    .. note:: You might have to add `config['validate_signatures'] = False`.
              You can find out more under the `main <main.html#main-anchor>`_.
