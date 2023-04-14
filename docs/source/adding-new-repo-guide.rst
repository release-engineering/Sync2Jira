Adding New Repos Guide 
=======================

Have you ever wanted to add new upstream repos? Well now you can! 

1. First ensure that your upstream repo is on the Fed Message Bus
2. Now add two new functions to `sync2jira/upstream_pr.py` and `sync2jira/upstream_issue.py`
    * :code:`def hande_REPO-NAME_message(msg, config)`
        * This function will take in a fedmessage message (msg) and the config dict
        * This function will return a sync2jira.Intermediary.Issue object
        * This function will be used when listening to the message bus
    * :code:`def REPO-NAME_issues(upstream, config)`
        * This function will take in an upstream repo name and the config dict 
        * This function will return a generator of sync2jira.Intermediary.Issue objects that contain all upstream Issues
        * This function will be used to initialize and sync upstream/downstream issues
3. Now modify the `sync2jira/main.py` functions: 
    * :code:`def initialize_pr(config, ...)` and `def initialize_issues(config, ...)`
        * Add another section (like Pagure and GitHub) to utlize the :code:`REPO-NAME_issues` function you just made. 
    * :code:`def listen(config)`
        * Add another section to the if statement under Pagure and GitHub
            * :code:`elif 'REPO-NAME' in suffix:`
            * Now utilize the :code:`handle_REPO-NAME_message` function you just made
4. If all goes smoothly, your new repo should work with Sync2Jira!

.. note:: If you want to submit a Pull Request, ensure that you add appropriate Unit Tests, Tox is passing, and you have appropriate documentation!
