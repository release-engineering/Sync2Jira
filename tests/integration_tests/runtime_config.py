import os

runtime_config = {
    'sync2jira': {
        'jira': {
            'pnt-jira': {
                'options': {
                    'server': os.environ['JIRA_STAGE_URL'],
                    'verify': True,
                },
                'basic_auth': (
                    os.environ['JIRA_USER'],
                    os.environ['JIRA_PASS'],
                ),
            },
        },
        'github_token': os.environ['SYNC2JIRA_GITHUB_TOKEN'],
        'admins': [{'spremkum', 'spremkum@redhat.com'}, {'rbean', 'rbean@redhat.com'}],
        'initialize': True,
        'testing': False,
        'develop': True,

        # We don't need legacy mode anymore.  Not for a long time.  Let's
        # remove it soon.
        'legacy_matching': False,

        # Set the default jira to be pnt-jira
        'default_jira_instance': 'pnt-jira',

        'filters': {
            'pagure': {
            },
            'github': {
            },
        },
        'map': {
            'pagure': {
              'Demo_project': {'project': 'FACTORY', 'component': 'gitbz',
                                               'updates': [{'transition': True},
                                                           'description',
                                                           'title',
                                                           {'tags': {'overwrite': True}},
                                                           {'fixVersion': {'overwrite': True}},
                                                           {'assignee': {'overwrite': True}},]},
            },
            'github': {
                'sidpremkumar/Demo_repo': {'project': 'FACTORY', 'component': 'gitbz',
                                           'updates': [{'transition': True},
                                                       'description',
                                                       'title',
                                                       {'tags': {'overwrite': True}},
                                                       {'fixVersion': {'overwrite': True}},
                                                       {'assignee': {'overwrite': True}}, ]}

            },
        },
        }
}
