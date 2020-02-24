// Global Variables
APP_NAME=process.env.APP_NAME;
TEST_COMMAND=process.env.TEST_COMMAND;
const fs = require('fs');
const childProcess = require("child_process");

module.exports = app => {
  // When a Pull Request is opened or Re-Opened
  app.on(['pull_request.opened', 'pull_request.reopened', 'pull_request.synchronize'], pull_request);
  async function pull_request (context) {
    // Identify start time
    const startTime = new Date();

    // Extract relevant information
    const pr = context.payload.pull_request;
    const headBranch = pr.head.ref;
    const headSha = pr.head.sha;

    // Mark the check as pending
    await context.github.checks.create(context.repo({
        name: APP_NAME,
        head_branch: headBranch,
        head_sha: headSha,
        status: 'in_progress',
        started_at: startTime,
    }));

    try {
      console.log("Running tests...");
      await childProcess.exec("/usr/local/src/sync2jira/openshift-build/runTests.sh " + headSha + " \"" + TEST_COMMAND + "\"", function(error, standardOutput, standardError) {
        console.log("Ran tests. " + standardOutput);

        // Check if failure file exists
        let passed = 'failure';
        if(fs.existsSync('/usr/local/src/sync2jira/openshift-build/temp/failure.sync2jira')) {
          console.log("The failure file exists.");
          childProcess.exec("rm /usr/local/src/sync2jira/openshift-build/temp/failure.sync2jira", function(error, standardOutput, standardError) {
            console.log("Deleting sync2jira.failure...");
            console.log(standardOutput);
            console.log(standardError);
          });
        } else {
          console.log('The failure file does not exist.');
          passed = 'success'
        }

        console.log("Pushing results of test...");
        return context.github.checks.create(context.repo({
          name: APP_NAME,
          head_branch: headBranch,
          head_sha: headSha,
          status: 'completed',
          started_at: startTime,
          conclusion: passed,
          completed_at: new Date(),
          output: {
            title: passed,
            summary: standardOutput.toString()
          }
        }))
      });
    }
    catch {
      return await context.github.checks.create(context.repo({
        name: APP_NAME,
        head_branch: headBranch,
        head_sha: headSha,
        status: 'completed',
        started_at: startTime,
        conclusion: passed,
        completed_at: new Date(),
        output: {
          title: passed,
          summary: 'Error when cloning or running tests.'
        }
      }))
    }
  }

  // When someone adds a commit to a Pull Request
  app.on(['check_suite.requested', 'check_run.rerequested'], check_suite);
  async function check_suite (context) {
     // Identify start time
    const startTime = new Date();

    // Extract relevant information
    let pr = context.payload.check_suite;
    if (typeof pr == 'undefined') {
      pr = context.payload.check_run
    }
    const headBranch = pr.head_branch;
    const headSha = pr.head_sha;

    // Mark the check as pending
    await context.github.checks.create(context.repo({
        name: APP_NAME,
        head_branch: headBranch,
        head_sha: headSha,
        status: 'in_progress',
        started_at: startTime,
      }));

    try {
      console.log("Running Tests...");
      await childProcess.exec("/usr/local/src/sync2jira/openshift-build/runTests.sh " + headSha + " \"" + TEST_COMMAND + "\"", function(error, standardOutput, standardError) {
        console.log("Ran tests. " + standardOutput);

        // Check if failure file exists
        let passed = 'failure';
        if(fs.existsSync('/usr/local/src/sync2jira/openshift-build/temp/failure.sync2jira')) {
          console.log("The failure file exists.");
          childProcess.exec("rm /usr/local/src/sync2jira/openshift-build/temp/failure.sync2jira", function(error, standardOutput, standardError) {
            console.log("Deleting sync2jira.failure...");
            console.log(standardOutput);
            console.log(standardError);
          });
        } else {
          console.log('The failure file does not exist.');
          passed = 'success'
        }

        console.log("Pushing results of test...");
        return context.github.checks.create(context.repo({
          name: APP_NAME,
          head_branch: headBranch,
          head_sha: headSha,
          status: 'completed',
          started_at: startTime,
          conclusion: passed,
          completed_at: new Date(),
          output: {
            title: passed,
            summary: standardOutput.toString()
          }
        }))
      });
    }
    catch {
      return await context.github.checks.create(context.repo({
        name: APP_NAME,
        head_branch: headBranch,
        head_sha: headSha,
        status: 'completed',
        started_at: startTime,
        conclusion: passed,
        completed_at: new Date(),
        output: {
          title: passed,
          summary: 'Error when cloning or running tests.'
        }
      }))
    }
  }
};
