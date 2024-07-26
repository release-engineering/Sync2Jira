FROM registry.access.redhat.com/ubi9/ubi:latest

ARG SYNC2JIRA_GIT_REPO=https://github.com/release-engineering/Sync2Jira.git
ARG SYNC2JIRA_GIT_REF=master
ARG SYNC2JIRA_VERSION=

LABEL \
    name="sync2jira" \
    org.opencontainers.image.name="sync2jira" \
    description="sync2jira application" \
    org.opencontainers.image.description="sync2jira application" \
    io.k8s.description="sync2jira application" \
    vendor="Red Hat, Inc." \
    org.opencontainers.image.vendor="Red Hat, Inc." \
    license="GPLv2+" \
    org.opencontainers.image.license="GPLv2+" \
    url="$SYNC2JIRA_GIT_REPO" \
    org.opencontainers.image.url="$SYNC2JIRA_GIT_REPO" \
    release="$SYNC2JIRA_GIT_REF" \
    com.redhat.component="null" \
    build-date="" \
    distribution-scope="public"

# Installing sync2jira dependencies
RUN dnf -y install \
    git \
    python3-pip \
    krb5-devel \
    python-devel \
    gcc \
  && dnf -y clean all

ENV SYNC2JIRA_VERSION=$SYNC2JIRA_VERSION

USER root

# Create Sync2Jira folder
RUN mkdir -p /usr/local/src/sync2jira

# Copy over our repo
COPY . /usr/local/src/sync2jira

# Install deps
RUN pip install -r /usr/local/src/sync2jira/requirements.txt

# Install Sync2Jira
RUN  pip3 install --no-deps -v /usr/local/src/sync2jira

USER 1001

CMD ["/usr/local/bin/sync2jira"]
