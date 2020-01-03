# Sync2Jira

[![Documentation Status](https://readthedocs.org/projects/sync2jira/badge/?version=master)](https://sync2jira.readthedocs.io/en/master/?badge=master)
[![Docker Repository on Quay](https://quay.io/repository/redhat-aqe/sync2jira/status "Docker Repository on Quay")](https://quay.io/repository/redhat-aqe/sync2jira)
[![Build Status](https://travis-ci.org/sidpremkumar/Sync2Jira.svg?branch=master)](https://travis-ci.org/sidpremkumar/Sync2Jira)
[![Coverage Status](https://coveralls.io/repos/github/sidpremkumar/Sync2Jira/badge.svg?branch=add-coverage-badge)](https://coveralls.io/github/sidpremkumar/Sync2Jira?branch=add-coverage-badge)
![Python 3.7](https://img.shields.io/badge/python-3.7-blue.svg)
## What is Sync2Jira?
This is a process that listens to activity on upstream repos on pagure and
github via fedmsg, and syncs new issues there to a Jira instance elsewhere.


## Documentation
Documentation is hosted on ReadTheDocs.io and can be found [here](https://sync2jira.readthedocs.io/en/latest/)

## Configuration

We have set up a quick-start [here](https://sync2jira.readthedocs.io/en/master/quickstart.html)

Configuration is in `fedmsg.d/`.

You can maintain a mapping there that allows you to match one upstream repo (say, 'pungi' on pagure) to a downstream project/component pair in Jira (say, 'COMPOSE', and 'Pungi').

On startup, if the initialize option is set to True in the fedmsg.d/ config, then all open issues from all upstream repos will be scraped and added to Jira if they are absent.

If the testing option is set to True, then the script will perform a "dry run" and not actually add any new issues to Jira.

Please look at our documentation [here](https://sync2jira.readthedocs.io/en/master/config-file.html) for a full list of what can be synced and how to set it up. 