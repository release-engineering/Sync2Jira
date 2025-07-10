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

- Python 3.9 or higher
- Git
- Access to a JIRA instance for testing (optional but recommended)
- GitHub API token for testing

### Quick Setup

```bash
# Fork the repository on GitHub
# Clone your fork
git clone https://github.com/YOUR_USERNAME/Sync2Jira.git
cd Sync2Jira

# Set up the upstream remote
git remote add upstream https://github.com/release-engineering/Sync2Jira.git

# Install in development mode
pip install -e .

# Install development dependencies
pip install -r test-requirements.txt
```

## Development Environment

### Setting up Your Environment

1. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -r test-requirements.txt
   ```

3. **Install pre-commit hooks** (optional but recommended):
   ```bash
   pip install pre-commit
   pre-commit install
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

- **Maximum line length**: 140 characters
- **Import formatting**: Use `isort` with the black profile
- **Code formatting**: Use `black` for consistent formatting
- **Docstrings**: Use Google-style docstrings for all functions and classes

### Code Quality Tools

Run these tools before submitting your changes:

```bash
# Format code
tox -e black-format
tox -e isort-format

# Check formatting and style
tox -e black
tox -e isort
tox -e lint

# Run all checks
tox -e py39,lint,black,isort
```

### Example Function Documentation

```python
def sync_with_jira(issue, config):
    """
    Attempts to sync an upstream issue with JIRA.

    Args:
        issue (sync2jira.intermediary.Issue): Issue object to sync
        config (Dict): Configuration dictionary containing JIRA settings

    Returns:
        None

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

- Maintain test coverage above 80%
- Add tests for new features and bug fixes
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
   git add .
   git commit -m "Add feature: brief description"
   ```

5. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create a Pull Request**:
   - Use the GitHub web interface
   - Provide a clear description of changes
   - Reference any related issues

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

### Pull Request Requirements

Before your PR can be merged, ensure:

- [ ] All tests pass
- [ ] Code follows style guidelines
- [ ] Documentation is updated (if applicable)
- [ ] Commit messages are clear and descriptive
- [ ] No merge conflicts with the main branch

## Adding New Repositories

If you want to add support for a new upstream repository type (beyond GitHub), follow these steps:

1. **Add upstream handler functions** in `sync2jira/upstream_issue.py` and `sync2jira/upstream_pr.py`:
   ```python
   def handle_NEWREPO_message(msg, config):
       """Handle messages from new repository type"""
       pass

   def NEWREPO_issues(upstream, config):
       """Generator for all issues from new repository type"""
       pass
   ```

2. **Update the main handler** in `sync2jira/main.py`:
   ```python
   # Add to issue_handlers and pr_handlers dictionaries
   issue_handlers = {
       # ... existing handlers
       "newrepo.issue.opened": handle_NEWREPO_message,
   }
   ```

3. **Update initialization functions** in `sync2jira/main.py`:
   ```python
   def initialize_issues(config, testing=False, repo_name=None):
       # Add section for new repository type
       for upstream in mapping.get("newrepo", {}).keys():
           # Implementation
   ```

4. **Add tests** for the new repository type

5. **Update documentation** with configuration examples

See the [Adding New Repos Guide](https://sync2jira.readthedocs.io/en/master/adding-new-repo-guide.html) for detailed instructions.

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
GitHub Event → Upstream Handler → Intermediary Object → Downstream Handler → JIRA Issue
```

### Configuration Processing

1. Load configuration from `fedmsg.d/sync2jira.py`
2. Validate required fields and mappings
3. Set up JIRA clients and GitHub authentication
4. Process repository mappings and filters

## Debugging

### Debug Mode

Enable debug logging in your configuration:

```python
config = {
    'sync2jira': {
        'debug': True,
        # ... other options
    }
}
```

### Common Debugging Scenarios

1. **Issue not syncing**:
   - Check repository mapping in configuration
   - Verify filters aren't excluding the issue
   - Check JIRA project permissions

2. **JIRA connection issues**:
   - Verify JIRA URL and credentials
   - Check network connectivity
   - Validate JIRA project exists

3. **GitHub API issues**:
   - Verify token has correct permissions
   - Check API rate limits
   - Ensure repository is accessible

### Logging

The service uses Python's logging module:

```python
import logging

log = logging.getLogger("sync2jira")
log.info("Information message")
log.error("Error message")
log.debug("Debug message")  # Only shown in debug mode
```

## Release Process

### Version Management

- Version is defined in `sync2jira/__init__.py`
- Follow semantic versioning (MAJOR.MINOR.PATCH)
- Update version for releases

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
- **Discussions**: [GitHub Discussions](https://github.com/release-engineering/Sync2Jira/discussions)

## Code of Conduct

Please be respectful and professional in all interactions. We follow the [Contributor Covenant](https://www.contributor-covenant.org/) code of conduct.

## License

By contributing to Sync2Jira, you agree that your contributions will be licensed under the GNU Lesser General Public License v2.1 or later (LGPLv2+).

---

Thank you for contributing to Sync2Jira! Your contributions help improve the tool for everyone in the community. 