Continuous Deployment
======================
We utilize OpenShift to deploy our Sync2Jira instance. Here we assume you have configured your quay.io repo to push to some sort of message bus. This will likely have to be done with an external script (something we do not support).

The following environmental variables will have to be set:

Related to OpenShift:
    1. :code:`TOKEN` :: OpenShift Token to be used
    2. :code:`ENDPOINT` :: OpenShift Endpoint to use
    3. :code:`NAMESPACE` :: OpenShift Namespace to use
Message Bus Related:
    1. :code:`CERT` :: Cert file that should be used (can be in .pem format)
    2. :code:`KEY` :: Key file that should be used (in .key format)
    3. :code:`CA_CERTS` :: CA Certs that should be used
    4. :code:`ACTIVEMQ_QUERY` :: Query that we should be using
    5. :code:`ACTIVEMQ_URL_1` :: Message Bus URL are tuple, this is the first part of that tuple
    6. :code:`ACTIVEMQ_URL_2` :: Message Bus URL are tuple, this is the second part of that tuple
    7. :code:`ACTIVEMQ_REPO_NAME` :: Repo (or topic/category) that we should be listening for

Once these variables have been set in an OpenShift pod (using `Dockerfile.deploy` image) it will listen for messages that trigger an OpenShift tag (i.e. :code:`oc tag ...`).
The script is set up for 3 different tags:
    1. `master`
    2. `stage`
    3. `openshift-build`

Please make sure these 3 branches exists and are maintained. Also make sure to examine the code and set up your project correctly. We assume that `openshift-build` is running under the stage namespace.

.. note:: How do we listen to repo builds?

    We use `repotracker <https://github.com/release-engineering/repotracker>` to listen for repo changes.