FROM registry.fedoraproject.org/fedora:38
LABEL \
    name="sync2jira" \
    description="sync2jira application" \
    vendor="sync2jira developers" \
    license="GPLv2+" \
    build-date=""

# Installing sync2jira dependencies
RUN dnf -y install \
    git \
    python3-pip \
    python3-requests \
    python3-jira \
    python3-fedmsg-core \
    python3-pygithub \
    python3-jinja2 \
    python3-pypandoc \
    python3-requests-kerberos \
  && dnf -y clean all

ARG SYNC2JIRA_GIT_REPO=https://github.com/release-engineering/Sync2Jira.git
ARG SYNC2JIRA_GIT_REF=master
ARG SYNC2JIRA_CACERT_URL=
ARG SYNC2JIRA_VERSION=
ENV SYNC2JIRA_VERSION=$SYNC2JIRA_VERSION
ENV SYNC2JIRA_CACERT_URL=$SYNC2JIRA_CACERT_URL

USER root

# Create Sync2Jira folder
RUN mkdir -p /usr/local/src/sync2jira

# Copy over our repo
COPY . /usr/local/src/sync2jira

# Install Sync2Jira
RUN  pip3 install --no-deps -v /usr/local/src/sync2jira

# To deal with JIRA issues (i.e. SSL errors)
RUN chmod g+w /etc/pki/tls/certs/ca-bundle.crt
RUN chmod 777 /usr/local/src/sync2jira/openshift/docker-entrypoint.sh

USER 1001

ENTRYPOINT ["/usr/local/src/sync2jira/openshift/docker-entrypoint.sh"]

CMD ["/usr/local/bin/sync2jira"]
