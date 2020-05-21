Sync Page
======================
We noticed that sometimes tickets would be lost and not sync. This would require taking down the entire service in order to re-sync that one ticket. To fix this we created a flask micro-service that provides a UI for users to sync individual repos.

The following environmental variables will have to be set:

Related to OpenShift:
    1. :code:`CA_URL` :: CA URL used for sync2jira
    2. :code:`DEFAULT_SERVER` :: Default server to use for mailing
    3. :code:`DEFAULT_FROM` :: Default from to use for mailing
    4. :code:`USER` :: JIRA username
    5. :code:`CONFLUENCE_SPACE` :: Confluence space (should be set to "mock_confluence_space" as we don't want any confluence syncing)
    6. :code:`INITIALIZE` :: True/False Initialize our repos on startup (Should be set to "0")
    7. :code:`IMAGE_URL` :: Image URL:TAG to pull from
    8. :code:`JIRA_PNT_PASS` :: PNT password in base64
    9. :code:`JIRA_OMEGAPRIME_PASS` :: Omegaprime password in base64
    10. :code:`GITHUB_TOKEN` :: GitHub token in base64
    11. :code:`PAAS_DOMAIN` :: Domain to use for the service

You can also use the OpenShift template to quickly deploy this service (it can be found in the repo under :code:`openshift/sync2jira-sync-page-template.yaml`)

Once deployed, you can go to the url :code:`sync2jira-page-sync.PAAS_DOMAIN` to select and sync individual repos!