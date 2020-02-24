# Built-In Modules
import os
import requests
import json
import traceback

# 3rd Party Modules
import jinja2
from rhmsg.activemq.consumer import AMQConsumer

# Local Modules
from sync2jira.mailer import send_mail
from sync2jira.main import load_config

# Global Variables
handlers = [
    'repotracker.container.tag.updated'
]
# OpenShift Related
TOKEN = os.environ['TOKEN']
ENDPOINT = os.environ['ENDPOINT']
NAMESPACE = os.environ['NAMESPACE']
# Message Bus Related
CERT = os.environ['CERT']
KEY = os.environ['KEY']
CA_CERTS = os.environ['CA_CERTS']
ACTIVEMQ_QUERY = os.environ['ACTIVEMQ_QUERY']
ACTIVEMQ_URL_1 = os.environ['ACTIVEMQ_URL_1']
ACTIVEMQ_URL_2 = os.environ['ACTIVEMQ_URL_2']
# Message Bus Query Related
ACTIVEMQ_REPO_NAME = os.environ['ACTIVEMQ_REPO_NAME']


def main():
    """
    Main function to start listening
    """
    try:
        # Load in config
        # Create our consumer
        c = AMQConsumer(
            urls=(ACTIVEMQ_URL_1, ACTIVEMQ_URL_2),
            certificate=CERT,
            private_key=KEY,
            trusted_certificates=CA_CERTS
        )
        # Start listening
        print('Starting up CD service...')
        c.consume(
            ACTIVEMQ_QUERY,
            lambda msg, data: handle_message(msg, data)
        )

    except:
        print("Error! Sending email..")
        report_email('failure', 'Continuous-Deployment-Main', traceback.format_exc())


def handle_message(msg, data):
    """
    Handle incoming message
    :param Dict msg: Incoming message
    :param Dict data: Incoming data, if any
    :return:
    """
    msg_dict = json.loads(msg.body)

    if msg_dict['repo'] == ACTIVEMQ_REPO_NAME:
        if msg_dict['tag'] == "master":
            ret = update_tag(master=True)
        if msg_dict['tag'] == "stage":
            ret = update_tag(stage=True)
        if msg_dict['tag'] == "openshift-build":
            ret = update_tag(openshift_build=True)
        if ret:
            report_email('success', msg_dict['repo'])
        else:
            report_email('failure', msg_dict['repo'], 'No additional data available at this view')


def update_tag(master=False, stage=False, openshift_build=False):
    """
    Update OpenShift master image when fedmsg topic comes in.

    :param Bool master: If we are tagging master
    :param Bool stage: If we are tagging stage
    :param Bool openshift_build: If we are tagging openshift-build
    :rtype (Bool, response):
    :return: (Indication if we updated out image on OpenShift, API call response)
    """
    # Format the URL
    # Note: Here we assume that we have a pod for openshift-build running under the pod for stage.
    if master:
        umb_url = f"https://{ENDPOINT}/apis/image.openshift.io/v1/namespaces/sync2jira/imagestreamtags/sync2jira:latest"
        namespace = 'sync2jira'
        name = 'sync2jira:latest'
    elif stage:
        umb_url = f"https://{ENDPOINT}/apis/image.openshift.io/v1/namespaces/sync2jira-stage/imagestreamtags/sync2jira=stage:latest"
        namespace = 'sync2jira-stage'
        name = 'sync2jira-stage:latest'
    elif openshift_build:
        umb_url = f"https://{ENDPOINT}/apis/image.openshift.io/v1/namespaces/sync2jira-stage/imagestreamtags/openshift-build:latest"
        namespace = 'sync2ijra-stage'
        name = 'openshift-build'
    else:
        raise Exception("No type passed")

    # Make our put call
    try:
        ret = requests.put(umb_url,
                           headers=create_header(),
                           data=json.dumps({
                               "kind": "ImageStreamTag",
                               "apiVersion": "image.openshift.io/v1",
                               "metadata": {
                                   "name": name,
                                   "namespace": namespace,
                                   "creationTimestamp": None},
                               "tag": {
                                   "name": "",
                                   "annotations": None,
                                   "from": {
                                       "kind": "DockerImage",
                                       "name": f"quay.io/redhat-aqe/sync2jira:{namespace}"
                                   },
                                   "generation": 0,
                                   "importPolicy": {},
                                   "referencePolicy": {
                                       "type": "Source"
                                   }
                               },
                               "generation": 0,
                               "lookupPolicy": {
                                   "local": False
                               },
                               "image": {
                                   "metadata": {
                                       "creationTimestamp": None
                                   },
                                   "dockerImageMetadata": None,
                                   "dockerImageLayers": None
                               }
                           }))
    except Exception as e:
        report_email('failure', namespace, e)
    if ret.status_code == 200:
        return True, ret
    else:
        return False, ret


def report_email(type, namespace=None, data=None):
    """
    Helper function to alert admins in case of failure.

    :param String type: Type to be used
    :param String namespace: Namespace being used
    :param String data: Data being used\
    """
    # Load in the Sync2Jira config
    config = load_config()

    # Email our admins with the traceback
    templateLoader = jinja2.FileSystemLoader(searchpath='usr/local/src/sync2jira/continuous-deployment')
    templateEnv = jinja2.Environment(loader=templateLoader)

    # Load in the type of template
    if type is 'failure':
        template = templateEnv.get_template('failure_template.jinja')
        html_text = template.render(namespace=namespace, response=data)
    elif type is 'success':
        template = templateEnv.get_template('success_template.jinja')
        html_text = template.render(namespace=namespace)

    # Send mail
    send_mail(recipients=config['mailing-list'],
              cc=None,
              subject=f"Sync2Jira Build Image Update Status: {type}!",
              text=html_text)


def create_header():
    """
    Helper function to create default header
    :rtype Dict:
    :return: Default header
    """
    return {
        'Authorization': f'Bearer {TOKEN}',
        'Accept': 'application/json',
        'Content-Type': 'application/json',
    }


if __name__ == '__main__':
    main()
