#FIXME: The Pipeline is currently using this Dockerfile to produce images. The one located at the project root is not changed in case of breaking anything.
FROM docker-registry.engineering.redhat.com/devops-automation/rad-slave-fedora-28:latest
LABEL name="sync2jira-jenkins-slave" \
      description="Jenkins slave for sync2jira dev tests" \
      vendor="sync2jira Developers" \
      license="GPLv2+"

USER root

# Add dependency Tini, a tiny but valid init for containers
ARG TINI_VERSION=0.18.0
# OpenShift Jenkins Pipeline (DSL) Plugin requires oc binary to be present in the PATH environment variable of all Jenkins nodes
ARG OPENSHIFT_CLIENTS_VERSION=3.10.0
ARG OPENSHIFT_CLIENTS_COMMIT=dd10d17

RUN dnf -y install 'dnf-command(builddep)' dnf-utils git mock-core-configs tar gzip skopeo \
    wget postgresql make rpmdevtools rpmlint \
    python3-flake8 python3-pylint python3-pytest \
    python3-nose \
    python3-tox \
    python3-sphinx python3-sphinxcontrib-httpdomain \
  && mkdir -p /usr/local/src/sync2jira \
  && TEMPDIR=$(mktemp -d) \
  # install oc
  && wget -O "$TEMPDIR"/openshift-origin-client-tools.tar \
    "https://github.com/openshift/origin/releases/download/v${OPENSHIFT_CLIENTS_VERSION}/openshift-origin-client-tools-v${OPENSHIFT_CLIENTS_VERSION}-${OPENSHIFT_CLIENTS_COMMIT}-linux-64bit.tar.gz" \
  && tar -xvf "$TEMPDIR"/openshift-origin-client-tools.tar -C "$TEMPDIR" --strip-components=1 \
  && cp "$TEMPDIR"/oc /usr/local/bin/oc && chmod +rx /usr/local/bin/oc \
  # install tini
  && wget -O /usr/local/bin/tini "https://github.com/krallin/tini/releases/download/v${TINI_VERSION}/tini" \
  && chmod +rx /usr/local/bin/tini \
  # install wait-for-it.sh, to allow containers to wait for other services to come up
  && wget -O /usr/local/bin/wait-for-it "https://raw.githubusercontent.com/vishnubob/wait-for-it/master/wait-for-it.sh" \
  && chmod +rx /usr/local/bin/tini /usr/local/bin/wait-for-it \
  # clean up
  && rm -rf "$TEMPDIR" \
  && dnf clean all

  # Pull down our spec file.
RUN curl https://pagure.io/sync-to-jira/raw/develop/f/sync2jira.spec > /usr/local/src/sync2jira/sync2jira.spec

# install build dependencies for sync2jira
RUN cd /usr/local/src/sync2jira \
  && dnf -y builddep ./sync2jira.spec \
  && dnf clean all \
  && chgrp -R root /usr/local/src/sync2jira \
  && chmod -R g+rwX /usr/local/src/sync2jira
WORKDIR /var/lib/jenkins/
ENTRYPOINT ["/usr/local/bin/tini", "--", "jenkins-slave"]
USER 1000
