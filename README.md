# Sync2Jira

[![Documentation Status](https://readthedocs.org/projects/sync2jira/badge/?version=master)](https://sync2jira.readthedocs.io/en/master/?badge=master)
[![Docker Repository on Quay](https://quay.io/repository/redhat-aqe/sync2jira/status "Docker Repository on Quay")](https://quay.io/repository/redhat-aqe/sync2jira)
![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)

## Overview

Sync2Jira is a service that listens to activity on upstream GitHub repositories via fedmsg and automatically syncs issues and pull requests to downstream JIRA instances. It provides real-time synchronization capabilities, ensuring that your JIRA project stays up-to-date with upstream development activity.

### Key Features

- **Real-time Synchronization**: Listens to fedmsg events from GitHub for immediate updates
- **Sync**: Supports both issues and pull requests
- **Flexible Configuration**: Map multiple GitHub repositories to different JIRA projects
- **Custom Field Support**: Sync labels, assignees, milestones,custom fields and GitHub repo data (priority, story points)
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

- Python 3.9+
- Access to a JIRA with API tokens
- GitHub API token
- Fedora messaging environment (for production)

### Using Docker

```bash
# Pull the latest image
docker pull quay.io/redhat-aqe/sync2jira:latest

# Run with your configuration
docker run -v /path/to/your/config:/etc/fedmsg.d/ \
           -e GITHUB_TOKEN=your_token \
           -e JIRA_TOKEN=your_jira_token \
           quay.io/redhat-aqe/sync2jira:latest
```

### From Source

```bash
# Clone the repository
git clone https://github.com/release-engineering/Sync2Jira.git
cd Sync2Jira

# Install dependencies
pip install -r requirements.txt

#install package 
pip install .

# Run the service
sync2jira

# With initialization (sync all existing issues)
INITIALIZE=1 sync2jira

# Testing mode (dry run)
# Set testing: True in config file
sync2jira
```

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

### Manual Sync Interface

The sync page is a separate web application that provides a UI for manually triggering synchronization.

**Running the sync page locally:**
```bash
# Navigate to the sync-page directory
cd sync-page

# Run the Flask application
python event-handler.py
```

**Access the interface:**
- Local development: `http://localhost:5000` (or whatever port Flask shows)
- Production: Configure according to your deployment environment


### Environment Variables

- `INITIALIZE`: Set to `1` to perform initial sync of all issues
- `FEDORA_MESSAGING_QUEUE`: Custom message queue name
- `GITHUB_TOKEN`: GitHub API token (can override config)
- `JIRA_TOKEN`: JIRA API token (can override config)


## Documentation

Comprehensive documentation is available at [sync2jira.readthedocs.io](https://sync2jira.readthedocs.io/en/latest/):

- [Quick Start Guide](https://sync2jira.readthedocs.io/en/master/quickstart.html)
- [Configuration Reference](https://sync2jira.readthedocs.io/en/master/config-file.html)
- [Sync Page Usage](https://sync2jira.readthedocs.io/en/master/sync_page.html)


## Troubleshooting

### Common Issues

1. **API Rate Limits**: The service automatically handles GitHub API rate limits by sleeping and retrying
2. **JIRA Connection Issues**: Check your JIRA server URL and authentication tokens
3. **Missing Issues**: Verify your fedmsg configuration and repository mappings
4. **Duplicate Issues**: The service includes duplicate detection and prevention

### Logging

Enable debug logging by setting the `debug` option in your configuration:

```python
'sync2jira': {
    'debug': True,
    # ... other options
}
```

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
