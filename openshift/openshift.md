# OpenShift Deployment
Sync2Jira is designed to be deployed on OpenShift (although it isn't required). We have provided the OpenShift templates 
needed to deploy [Sync2Jira](sync2jira-template.yaml) and the [Continuous-Deployment](sync2jira-deploy-template.yaml) 
feature of Sync2Jira.

The templates assumes the following:

1. You have an ImageStream called 'sync2jira'. It can be created on OpenShift in your project with the following command:
     ```shell script
    oc create imagestream sync2jira
    ```
2. You have a config map called fedmsgd where you load your config `sync2jira.py` file. 
    ```shell script
    oc create configmap fedmsgd --from-file=sync2jira.py
    ```
3. You deployed `sync2jira-stage-template.yaml` BEFORE `sync2jira-deploy-template.yaml`

## Continuous Deployment
To use the continuous-deployment feature you have to have service accounts on your stage and namespace. You can create 
them and get their token with the following commands: 
```shell script
oc create sa sync2jira-deploy
oc policy add-role-to-user edit -z sync2jira-deploy
oc sa get-token sync2jira-deploy
```
You will then have to set the `INITILIZE` environmental variable in your stage and prod deployment to 0 as you will enable CD

You will also have to build the image in OpenShift. You will need to pass a URL (RCM_TOOLS_REPO) to a .repo file to 
install rhmsg which is what we use to listen for repo changes. 

## OpenShift-Build
Sync2Jira uses [OpenShift-Build](https://github.com/sidpremkumsidpremkumar/OpenShift-Build) to achieve integration tests against 
real values. You can use the [openshift-build-template.yml](openshift-build-template.yaml) to deploy an instance of 
OpenShift build in your namespace. Make sure to configure your GitHub repo to push checks and pull requests to a 
[Smee.io](https://smeel.io) url. See the documentation under [OpenShift-Build](https://github.com/sidpremkumar/OpenShift-Build)
to learn more. 

Note: To deploy OpenShift build you must have the fedmsg.d config map