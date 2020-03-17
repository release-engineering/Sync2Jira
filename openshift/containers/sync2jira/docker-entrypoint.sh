#!/bin/bash
set -e

# START_CD is a flag (1/None) to start our CD server
# CA_URL is the URL of a custom root CA certificate to be installed at run-time
: ${CA_URL:=}


# installing CA certificate
if [ -n "${CA_URL}" ] && [ ! -f "/tmp/.ca-imported" ]; then
  # Since update-ca-trust doesn't work as a non-root user, let's just append to the bundle directly
  curl --silent --show-error --location "${CA_URL}" >> /etc/pki/tls/certs/ca-bundle.crt
  # Create a file so we know not to import it again if the container is restarted
  touch /tmp/.ca-imported
  echo "ca-bundle.crt Downloaded!"
fi

exec "$@"
