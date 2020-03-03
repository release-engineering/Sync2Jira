# Continuous Deployment

## TLDR
We use a message bus configured to listen to a topic pushed by [RepoTracker](https://github.com/release-engineering/repotracker). Once we find a message that indicates a change in any of the branches we're watching, we tag the new image in OpenShift which triggers a new deployment.


## Where can I learn more?
You can check our documentation [here](https://sync2jira.readthedocs.io/en/latest/continuous_deployment.html) to learn more about how to configure this feature in your project.  