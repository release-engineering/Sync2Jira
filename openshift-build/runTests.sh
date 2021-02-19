#!/bin/bash
set -ex

# Arguments
HEAD_SHA=$1
TEST_COMMAND=$2

# cd into our temp repo
cd /usr/local/src/sync2jira/openshift-build/temp

run_tests() {
  echo "**Using:**"
  echo "**HEAD_SHA:** ${HEAD_SHA}"
  echo "**TEST_COMMAND:** ${TEST_COMMAND}"

  # Declare our name
  git config user.email "sync2jira@redhat.com"
  git config user.name "Red User"

  # Checkout to a new branch with our new sha
  echo "**Moving to sha ${HEAD_SHA}**"
  git fetch --all
  git reset --hard ${HEAD_SHA}

  # Run our commands, if failure touch a file
  echo "**Running test command...**"
  ${TEST_COMMAND} || touch failure.sync2jira

  # Display the results of our test
  echo "**Integration log:**"
  INTEGRATION_LOG=$(cat integration_test.log)
  echo "$INTEGRATION_LOG"

  echo "**Main log:**"
  MAIN_LOG=$(cat sync2jira_main.log)
  echo "$MAIN_LOG"

  # Delete our logs
  rm integration_test.log
  rm sync2jira_main.log
}

run_tests || touch failure.sync2jira
