# AGENTS.md

This file provides guidance to LLM agents and code assistants when working with code in this repository.

## Build, Test, and Lint Commands

### Testing
```bash
# Run all tests with coverage (default, excludes integration tests)
tox

# Run tests for specific Python version
tox -e py312
tox -e py313

# Run with HTML coverage report (add this arg locally)
tox -e py313 -- --cov-report html:htmlcov-py313

# Run tests directly with pytest
coverage run -m pytest --ignore=tests/integration_tests
coverage report
coverage html  # Generate HTML coverage report
```

### Linting and Formatting
```bash
# Check linting (flake8)
tox -e lint

# Check code formatting (black)
tox -e black

# Check import sorting (isort)
tox -e isort

# Auto-format code
tox -e black-format
tox -e isort-format
```

### Running the Service
```bash
# Install in development mode
pip install -e .

# Run the main sync service
sync2jira

# Run with initialization (sync all existing issues)
INITIALIZE=1 sync2jira

# Run the sync-page web UI
cd sync-page
python event-handler.py
```

## Architecture

Sync2Jira is a fedmsg-based service that synchronizes GitHub issues and pull requests to JIRA in real-time.

### Data Flow
GitHub Event → Fedora Message Bus → sync2jira → Upstream Handler → Intermediary Object → Downstream Handler → JIRA

### Core Components

**sync2jira/main.py**: Entry point and event loop
- Loads configuration from `fedmsg.d/sync2jira.py`
- Defines `issue_handlers` and `pr_handlers` dicts that map fedmsg topics to handler functions
- Routes messages to appropriate handlers based on topic (issues vs PRs)
- Handles initialization mode for bulk syncing

**sync2jira/intermediary.py**: Platform-agnostic data models
- `Issue` and `PR` classes represent upstream items in a normalized way
- Factory methods (`from_github()`) convert between GitHub format and internal representation
- `matcher()` function extracts JIRA ticket references from PR descriptions/comments (e.g., "JIRA: FACTORY-1234")

**sync2jira/upstream_*.py**: GitHub event processors
- `upstream_issue.py`: Processes GitHub issue events, converts to intermediary objects
  - **Dual-purpose**: Also handles PRs when fedmsg contains `pull_request` field (main.py:310-329)
  - **GitHub Projects integration**: Uses GraphQL to fetch custom fields (priority, storypoints) from GitHub Projects
- `upstream_pr.py`: Processes GitHub PR events
- Filters items based on config (checks if repo is mapped, if issue/PR sync is enabled, applies custom filters)
- Handles API calls to fetch full issue/PR data when needed
- Manages upstream rate limiting (and does a less than spectactular job at it)

**sync2jira/downstream_*.py**: JIRA interaction layer
- `downstream_issue.py`: Creates/updates JIRA issues from intermediary objects
- `downstream_pr.py`: Creates/updates JIRA issues for PRs
- Handles JIRA-specific logic: custom fields, transitions, components
- Manages issue linking and remote links back to GitHub

**sync-page/**: Flask web UI for manual sync
- `event-handler.py`: Flask app that allows triggering syncs for individual repositories
- Useful for testing or one-off syncs without waiting for fedmsg events

### GitHub Projects Integration

Sync2Jira supplements downstream JIRA issues with additional metadata from GitHub Projects (v2):

- **Purpose**: Enriches JIRA issues with custom field data from GitHub Projects that isn't available in standard GitHub issue events
- **GraphQL API**: Uses GitHub's GraphQL API to fetch project field values (upstream_issue.py:32-111)
- **Supported fields**: priority (mapped to JIRA priority) and storypoints (mapped to JIRA story points)
- **Configuration**: Requires `github_project_number`, `github_project_fields`, and `github_project_fields` in `issue_updates`
- **Field mapping**: Supports custom mappings (e.g., GitHub "P0" → JIRA "Blocker")

Example configuration:
```python
'github_project_number': '1',
'github_project_fields': {
    'storypoints': {'gh_field': 'Estimate'},
    'priority': {
        'gh_field': 'Priority',
        'options': {'P0': 'Blocker', 'P1': 'Critical', 'P2': 'Major'}
    }
},
'issue_updates': [..., 'github_project_fields']
```

## Configuration

See README.md "Configuration" section and the example in `fedmsg.d/sync2jira.py`.

## Development Guidelines

See CONTRIBUTING.md for:
- Testing requirements and coverage expectations
- PR etiquette (history management, comment resolution)
- Code standards (black, isort, flake8)
