Quick Start
============

Want to quickly get started working with Sync2Jira? Follow these steps:

1. **First open up** :code:`fedmsg.d/sync2jira.py`

2. Enter your GitHub token which you can get `here <https://help.github.com/en/articles/creating-a-personal-access-token-for-the-command-line>`_
    .. code-block:: python

        'github_token': 'YOUR_TOKEN',

3. Enter relevant JIRA information
    .. code-block:: python

        'default_jira_instance': 'example',
        # This should be the username of the account corresponding with `token_auth` below.
        'jira_username': 'your-bot-account',
        'jira': {
            'example': {
                'options': {
                    'server': 'https://some_jira_server_somewhere.com',
                    'verify': True,
                },
                'token_auth': 'YOUR_TOKEN',
            },
        },

    .. note:: You might have to set verify to False

4. Add your upstream repos to the `map` section
    .. code-block:: python

        'map': {
            'pagure': {
                'Demo_project': {'project': 'FACTORY', 'component': 'gitbz',
                                 'updates': [...], 'sync': [..]},
                # 'koji': { 'project': 'BREW', 'component': None, },
            },
            'github': {
                'GITHUB_USERNAME/Demo_project': {'project': 'FACTORY', 'component': 'gitbz',
                                                 'updates': [...], 'sync': [..]},
            },
        },

    .. note:: You can learn more about what can go into the updates list `here <config-file.html>`_

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
