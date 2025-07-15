# Contributing to Sync2Jira

Thank you for your interest in contributing to Sync2Jira! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Environment](#development-environment)
- [Code Standards](#code-standards)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Adding New Repositories](#adding-new-repositories)
- [Architecture Overview](#architecture-overview)
- [Debugging](#debugging)
- [Release Process](#release-process)

## Getting Started

### Prerequisites

Before contributing, ensure you have:

- Python 3.12 or higher
- Git
- Access to a JIRA instance for testing (optional but recommended)
- GitHub API token for testing


## Development Environment

## Cloning the repo

```bash
# Fork the repository on GitHub
# Clone your fork
git clone https://github.com/YOUR_USERNAME/Sync2Jira.git
cd Sync2Jira

# Set up the upstream remote
git remote add upstream https://github.com/release-engineering/Sync2Jira.git


```
### Setting up Your Environment

1. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -e .
   ```


### Configuration for Development

Create a test configuration file in `fedmsg.d/sync2jira.py`:

```python
config = {
    'sync2jira': {
        'github_token': 'your_test_token',
        'default_jira_instance': 'test',
        'jira': {
            'test': {
                'options': {
                    'server': 'https://your-test-jira.example.com',
                    'verify': True,
                },
                'token_auth': 'your_test_jira_token',
            },
        },
        'map': {
            'github': {
                'your-test-org/test-repo': {
                    'project': 'TEST',
                    'component': 'test-component',
                    'sync': ['issue'],
                    'issue_updates': ['title', 'description', 'comments'],
                },
            },
        },
        'testing': True,  # Enable dry-run mode
        'develop': True,  # Enable development mode
        'admins': ['your-username'],
    }
}
```

## Code Standards

### Style Guidelines

We follow PEP 8 with some project-specific conventions:

- **Import formatting**: Use `isort` with the black profile
- **Code formatting**: Use `black` for consistent formatting
- **Docstrings**: Use Google-style docstrings for all functions and classes

### Code Quality Tools

Before submitting your changes, ensure that the `tox` command passes when run with the default environments (i.e., with no arguments).
As a convenience, you can run the environments individually (see `tox.ini`).  Also, you can run `tox -e black-format` and `tox -e isort-format` to format your code.

### Example Function Documentation

```python
def sync_with_jira(issue: sync2jira.intermediary.Issue, config:dict[str, Any]) -> None:
    """
    Attempts to sync an upstream issue with JIRA.
    
    Raises:
        JIRAError: If JIRA API call fails
        ValueError: If configuration is invalid
    """
    # Implementation here
```

## Testing

### Running Tests

```bash
# Run all tests
tox

# Run specific test environments
tox -e py39          # Python 3.9 tests
tox -e py313         # Python 3.13 tests
tox -e lint          # Linting only
tox -e black         # Code formatting check
tox -e isort         # Import sorting check

# Run tests with coverage
coverage run -m pytest
coverage report
coverage html        # Generate HTML coverage report
```

### Test Environment Variables

Set these environment variables for testing:

```bash
export DEFAULT_FROM=test@example.com
export DEFAULT_SERVER=test_server
export INITIALIZE=1
```

### Writing Tests

#### Unit Tests

- Place unit tests in the `tests/` directory
- Follow the naming convention: `test_<module_name>.py`
- Use `unittest.mock` for mocking external dependencies
- Test both success and failure scenarios

Example unit test:

```python
import unittest
from unittest.mock import MagicMock, patch

import sync2jira.downstream_issue as d_issue

class TestDownstreamIssue(unittest.TestCase):
    def setUp(self):
        self.mock_config = {
            'sync2jira': {
                'testing': True,
                'jira': {'test': {'options': {'server': 'test'}}},
            }
        }

    @patch('sync2jira.downstream_issue.get_jira_client')
    def test_sync_with_jira(self, mock_get_client):
        # Test implementation
        pass
```

#### Integration Tests

- Integration tests are in `tests/integration_tests/`
- These tests require real JIRA and GitHub instances
- Use environment variables for credentials
- Integration tests are excluded from regular test runs

### Test Coverage

- **No coverage regression**: A PR should not be merged if it decreases the level of test coverage
- **New code requires tests**: New code submissions should be accompanied by unit tests which exercise, at a minimum, all non-fatal paths through it -- that is, all "success" paths as well as all paths which successfully recover from errors
- **Bug fixes require tests**: PRs containing bug fixes should include at least one test which demonstrates that the bug is fixed
- **Continuous improvement**: Each PR should ideally improve the overall test coverage, moving us toward comprehensive coverage
- Update tests when modifying existing functionality

## Submitting Changes

### Workflow

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**:
   - Follow the code standards
   - Add tests for new functionality
   - Update documentation if needed

3. **Run tests locally**:
   ```bash
   tox
   ```

4. **Commit your changes**:
   ```bash
   git add [filename(s)...]
   git commit -m "Add feature: brief description"
   ```

5. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create a Pull Request**:
   - Use the GitHub web interface
   - Provide a clear description of changes
   - Reference related Issues and/or PRs in the description, and feel free to use [Github keywords](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/using-keywords-in-issues-and-pull-requests#linking-a-pull-request-to-an-issue) to trigger closure of the issue.

### Commit Message Guidelines

- Use present tense ("Add feature" not "Added feature")
- Use imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 50 characters
- Reference issues and pull requests when applicable

Examples:
```
Add support for GitHub Projects v2 fields

Fix issue with duplicate JIRA tickets
Fixes #123

Update documentation for new configuration options
```


#### Pull Request Etiquette

When working with pull requests, please follow these guidelines to ensure a smooth review process:

**History Management:**
- **Don't rewrite history:** Once a PR is open for review, you may add commits to the branch and you may rebase the entire branch, but do not modify the existing commits in the branch -- do not edit them or squash them together -- rewriting the history makes it difficult to do incremental reviews; if you need to rework the commits, do this before opening the PR for review (after the review is complete, the branch can be squashed automatically when it is merged if this is appropriate).

**Comment Resolution:**
- The author of a comment thread (i.e., the reviewer) should be the one to mark it as resolved -- this makes it clear whether the PR author's response actually resolved the commenter's concern. Note, there are two exceptions to this:
  - If the comment uses the GH "suggestion" mechanism, the comment will automatically be marked resolved if the suggestion is accepted (it is assumed that accepting the commenter's solution resolves the commenter's whole concern).
  - The commenter may not have permission to mark the comment as resolved, in which case the commenter should respond and indicate that the thread can be closed (and then it can be closed by someone with write-access to the repo).

**Comment Organization:**
- Avoid identifying multiple (unrelated) concerns in a single comment -- open separate conversations for separate concerns (so that they can be resolved separately, and so that they don't get lost in each other).

**Response Guidelines:**
- If the PR author agrees or otherwise intends to make a change based on a reviewer's comment, s/he does not need to reply to the comment (s/he may do so if it adds value, but consider using the GH reaction emojis instead, as these cause less "noise") -- the reviewer will see the change in the code when s/he next reviews; however, if the PR author disagrees or declines to make a change as a result of the comment, s/he should respond to the comment with the reason(s) or justification for declining -- the comment author should resolve the conversation or offer a response. A PR should not be merged with unresolved conversations.

**PR Structure:**
- Take care in how you structure your change. Ideally, a PR should consist of a single, focused, coherent change. Unrelated changes should likely be submitted as separate PRs. However, there is an economy of scale for reviewers, such that it is better to present a modest number of small changes as a single PR rather than as a series of separate, tiny PRs, but, be aware that, if any of the changes prove controversial, it will hold up the whole PR. For large changes, consider splitting them up into multiple PRs. Otherwise, large PRs should be structured as a series of commits where each commit represents a clear step toward the completed change. Commits containing tangential changes or dead ends should be squashed before opening the PR; oversized or unfocused commits should be split into multiple commits (see the `git rebase -i` and `git add -p` commands for help with this).

## Architecture Overview

Understanding the architecture helps when contributing:

### Core Components

1. **Upstream Handlers** (`sync2jira/upstream_*.py`):
   - Process events from upstream repositories
   - Convert to intermediary objects
   - Handle API rate limits

2. **Downstream Handlers** (`sync2jira/downstream_*.py`):
   - Manage JIRA interactions
   - Create and update issues
   - Handle JIRA-specific logic

3. **Intermediary Objects** (`sync2jira/intermediary.py`):
   - Abstract representation of issues and PRs
   - Platform-independent data models
   - Handle data transformation

4. **Main Service** (`sync2jira/main.py`):
   - Event loop and message handling
   - Configuration management
   - Error handling and reporting

5. **Sync Page** (`sync-page/`):
   - Web interface for manual synchronization
   - Flask application
   - Individual repository sync

### Data Flow

```
GitHub Event → Webhook → Fedora Message Bus → Sync2Jira → Upstream Handler → Intermediary Object → Downstream Handler → JIRA Issue
```

### Configuration Processing

1. Load configuration from `fedmsg.d/sync2jira.py`
2. Validate required fields and mappings
3. Set up JIRA client and GitHub authentication
4. Process repository mappings and filters

## Debugging

### Debug Mode

Enable debug logging in your configuration:

```python
config = {
    'sync2jira': {
        'debug': True,
        'testing': True,    # Enable dry-run mode
        'develop': True,    # Enable development mode
        # ... other options
    }
}
```


## Release Process


### Documentation Updates

- Update documentation in `docs/` directory
- Ensure all new features are documented
- Update configuration examples

### Container Images

- Docker images are built automatically on push
- Images are available on Quay.io
- Test images before release

## Getting Help

- **Documentation**: [https://sync2jira.readthedocs.io](https://sync2jira.readthedocs.io)
- **Issues**: [GitHub Issues](https://github.com/release-engineering/Sync2Jira/issues)


## Code of Conduct

Please be respectful and professional in all interactions. We follow the [Contributor Covenant](https://www.contributor-covenant.org/) code of conduct.

## License

By contributing to Sync2Jira, you agree that your contributions will be licensed under the GNU Lesser General Public License v2.1 or later (LGPLv2+).

---

Thank you for contributing to Sync2Jira! Your contributions help improve the tool for everyone in the community. 