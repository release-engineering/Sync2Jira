# Sync2Jira

[![Documentation Status](https://readthedocs.org/projects/sync2jira/badge/?version=main)](https://sync2jira.readthedocs.io/en/main/?badge=main)
[![Coverage Status](https://coveralls.io/repos/github/release-engineering/Sync2Jira/badge.svg?branch=main)](https://coveralls.io/github/release-engineering/Sync2Jira?branch=main)
![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)

## Overview

Sync2Jira is a service that listens to activity on upstream GitHub repositories via fedmsg and automatically syncs issues and pull requests to downstream JIRA instances. It provides real-time synchronization capabilities, ensuring that your JIRA project stays up-to-date with upstream development activity.

### Key Features

- **Real-time Synchronization**: Listens to fedmsg events from GitHub for immediate updates
- **Sync**: Supports both issues and pull requests
- **Flexible Configuration**: Map multiple GitHub repositories to different JIRA projects
- **Custom Field Support**: Sync labels, assignees, milestones and custom fields such as priority and story points
- **Batch Initialization**: Initial sync of all existing issues and PRs
- **Manual Sync Interface**: Web UI for on-demand repository synchronization
- **Comprehensive Filtering**: Filter by labels, milestones, and other criteria
- **Email Notifications**: Alert administrators on sync failures

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   GitHub Repo   │───▶│   Fedmsg/       │───▶│   Sync2Jira     │───▶│   JIRA Project  │
│   (Issues/PRs)  │    │   Fedora        │    │   (Service)     │    │   (Issues)      │
│                 │    │   Messaging     │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘

```

### Core Components

- **Sync2Jira**: Main synchronization service that listens for GitHub events and creates/updates JIRA issues
- **Sync Page**: UI for manually triggering synchronization of specific repositories when needed

## Installation

### Prerequisites

- Python 3.12+
- API access (via Personal Access Token) to a Jira Data Center instance
- GitHub API token
- Fedora messaging environment (for production)

### From Source

```bash
# Clone the repository
git clone https://github.com/release-engineering/Sync2Jira.git
cd Sync2Jira

# Install dependencies
pip install -r requirements.txt

# Install package
pip install .

# Run the service
sync2jira

# With initialization (sync all existing issues)
INITIALIZE=1 sync2jira

# Testing mode (dry run)
# Set testing: True in config file
sync2jira
```

**Note**: Container images are also available as an alternative to native installation. See the [Usage](#usage) section for container deployment instructions.

## Configuration

Create a configuration file in the `fedmsg.d/` directory. Here's a basic example:

```python
# fedmsg.d/sync2jira.py
config = {
    'sync2jira': {
        # GitHub API token
        'github_token': 'your_github_token',
        
        # JIRA configuration
        'default_jira_instance': 'primary',
        'jira': {
            'primary': {
                'options': {
                    'server': 'https://your-jira.example.com',
                    'verify': True,
                },
                'token_auth': 'your_jira_token',
            },
        },
        
        # Repository mappings
        'map': {
            'github': {
                'username/repository': {
                    'project': 'JIRA_PROJECT_KEY',
                    'component': 'component-name',
                    'sync': ['issue', 'pullrequest'],
                    'issue_updates': [
                        'comments',
                        'title',
                        'description',
                        {'tags': {'overwrite': True}},
                        {'assignee': {'overwrite': False}},
                        'url'
                    ],
                },
            },
        },
        
        # Optional settings
        'testing': False,  # Set to True for dry-run mode
        'initialize': False,  # Set to True to sync all existing issues
        'admins': ['admin_username'],  # Email notifications
    }
}
```

### Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `github_token` | GitHub API token for authentication | Required |
| `jira` | JIRA instance configurations | Required |
| `map` | Repository-to-project mappings | Required |
| `testing` | Enable dry-run mode (no actual changes) | `False` |
| `initialize` | Sync all existing issues on startup | `False` |
| `filters` | Filter issues by labels, milestones, etc. | `{}` |
| `admins` | List of admin users for notifications | `[]` |

## Usage

### Sync2Jira Service

The main synchronization service that listens for GitHub events and creates/updates JIRA issues.

#### Native Installation

```bash
# Run the service
sync2jira

# With initialization (sync all existing issues)
INITIALIZE=1 sync2jira

# Testing mode (dry run)
# Set testing: True in config file
sync2jira
```

#### Container Deployment

```bash
# Basic usage - run the sync service
docker run -v /path/to/your/config:/etc/fedmsg.d/ \
           -e GITHUB_TOKEN=your_token \
           -e JIRA_TOKEN=your_jira_token \
           quay.io/redhat-services-prod/sync2jira/sync2jira:latest

# With initialization (sync all existing issues)
docker run -v /path/to/your/config:/etc/fedmsg.d/ \
           -e GITHUB_TOKEN=your_token \
           -e JIRA_TOKEN=your_jira_token \
           -e INITIALIZE=1 \
           quay.io/redhat-services-prod/sync2jira/sync2jira:latest
```

**Note**: The `-v /path/to/your/config:/etc/fedmsg.d/` option mounts your local configuration directory inside the container, allowing the containerized application to use your host system's configuration files.

### Sync Page UI

A web interface for manually triggering synchronization of specific repositories when needed.

#### Native Installation

```bash
# Navigate to the sync-page directory
cd sync-page

# Run the Flask application
python event-handler.py
```

#### Container Deployment

```bash
# Run the web interface for manual synchronization
docker run -v /path/to/your/config:/etc/fedmsg.d/ \
           -p 5000:5000 \
           -e GITHUB_TOKEN=your_token \
           -e JIRA_TOKEN=your_jira_token \
           quay.io/redhat-aqe/sync2jira:sync-page
```

**Access the interface:**
- Local development: `http://localhost:5000` (or whatever port Flask shows)
- Production: Configure according to your deployment environment

### Environment Variables

The following environment variables can be used to configure both tools:

**Common Variables (used by both sync2jira and sync-page):**
- `GITHUB_TOKEN`: GitHub API token (can override config)
- `JIRA_TOKEN`: JIRA API token (can override config)

**Sync2Jira Service Only:**
- `INITIALIZE`: Set to `1` to perform initial sync of all issues
- `FEDORA_MESSAGING_QUEUE`: Custom message queue name

## Documentation

Comprehensive documentation is available at [sync2jira.readthedocs.io](https://sync2jira.readthedocs.io/en/latest/):

- [Quick Start Guide](https://sync2jira.readthedocs.io/en/main/quickstart.html)
- [Configuration Reference](https://sync2jira.readthedocs.io/en/main/config-file.html)
- [Sync Page Usage](https://sync2jira.readthedocs.io/en/main/sync_page.html)


## License

This project is licensed under the GNU Lesser General Public License v2.1 or later (LGPLv2+). See the [LICENSE](LICENSE) file for details.

## Support

- **Documentation**: [https://sync2jira.readthedocs.io](https://sync2jira.readthedocs.io)
- **Issues**: [GitHub Issues](https://github.com/release-engineering/Sync2Jira/issues)


## Maintainers

- Ralph Bean ([@ralphbean](https://github.com/ralphbean))
- Red Hat Release Engineering Team

---

*Sync2Jira is part of the Red Hat Release Engineering toolchain and is used in production to sync thousands of issues across multiple projects.*
