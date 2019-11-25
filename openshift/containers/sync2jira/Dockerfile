FROM fedora:latest
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
  && dnf -y clean all

ARG SYNC2JIRA_GIT_REPO=https://pagure.io/sync-to-jira
ARG SYNC2JIRA_GIT_REF=develop
ARG SYNC2JIRA_CACERT_URL=
ARG SYNC2JIRA_VERSION=
ENV SYNC2JIRA_VERSION=$SYNC2JIRA_VERSION
ENV SYNC2JIRA_CACERT_URL=$SYNC2JIRA_CACERT_URL

# Installing CA certificate
RUN if [ -n "$SYNC2JIRA_CACERT_URL" ]; then \
        cd /etc/pki/ca-trust/source/anchors \
        && curl -O --insecure --location "$SYNC2JIRA_CACERT_URL" \
        && update-ca-trust extract; \
    fi

# Installing sync2jira
RUN mkdir -p /usr/local/src \
  && git clone "$SYNC2JIRA_GIT_REPO" /usr/local/src/sync2jira \
  && cd /usr/local/src/sync2jira \
  && git fetch origin "$SYNC2JIRA_GIT_REF" \
  && git checkout -f "$SYNC2JIRA_GIT_REF" \
  && pip3 install --no-deps -v . \
  && test -f /usr/local/bin/sync2jira \
  && cd /

USER 1001

CMD ["/usr/local/bin/sync2jira"]
