# Rover_Lookup

A Python package for translating GitHub usernames to Red Hat Associate email addresses using LDAP queries against the Red Hat Rover service.

## Overview

This package queries the Red Hat Rover LDAP service to find Red Hat Associates based on their GitHub profile information stored in the `rhatSocialURL` field and returns their email addresses from multiple fields (`rhatPrimaryMail`, `mail`, and `rhatPreferredAlias`).

## Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt [-r test-requirements.txt]
```

2. Add the Rover_Lookup package to your Python path or install it locally.

## Usage

### Basic Usage

```python
from Rover_Lookup import github_username_to_emails

# Look up email addresses for a GitHub username
emails = github_username_to_emails("github-username")

if emails is None:
    print("LDAP query failed")
elif not emails:
    print("No email addresses found")
else:
    print(f"Found emails: {emails}")
```

### Advanced Usage with Custom LDAP Settings

```python
from Rover_Lookup import github_username_to_emails

emails = github_username_to_emails(
    github_username="github-username",
    ldap_server="ldap://your-rover-server.com",
    ldap_base_dn="ou=users,dc=redhat,dc=com",
    ldap_bind_dn="cn=bind-user,dc=redhat,dc=com",
    ldap_password="your-password"
)
```

### Enabling Debug Logging

```python
from Rover_Lookup import configure_logging
import logging

# Configure logging to see debug information
configure_logging(level=logging.DEBUG)
```

## Function Reference

### `github_username_to_emails(github_username, **kwargs)`

Translate a GitHub username to Red Hat Associate email addresses via LDAP lookup.

**Parameters:**
- `github_username` (str): The GitHub username to look up
- `ldap_server` (str, optional): LDAP server address (default: "ldap://ldap.corp.redhat.com")
- `ldap_base_dn` (str, optional): Base DN for LDAP search (default: "ou=users,dc=redhat,dc=com")
- `ldap_bind_dn` (str, optional): DN for LDAP authentication (default: anonymous bind)
- `ldap_password` (str, optional): Password for LDAP authentication

**Returns:**
- `List[str]`: List of unique email addresses if found
- `[]`: Empty list if no email addresses found in the record(s)
- `None`: If the LDAP query failed

**Behavior:**
- Constructs an LDAP filter based on `rhatSocialURL` matching `Github->https://github.com/{username}`
- Searches for Red Hat Associates with the matching GitHub profile
- Extracts email addresses from `rhatPrimaryMail`, `mail`, and `rhatPreferredAlias` fields
- Returns a deduplicated, sorted list of email addresses
- Handles multiple records by combining email addresses from all matching entries
- Logs errors using the standard Python logger for debugging

## LDAP Query Details

The package constructs LDAP queries with the following characteristics:

- **Filter**: `(rhatSocialURL=Github->https://github.com/{username})`
- **Scope**: Subtree search
- **Attributes**: `['rhatPrimaryMail', 'mail', 'rhatPreferredAlias']`

The `rhatSocialURL` field contains values in the format:
```
Github->https://github.com/username
```

## Error Handling

The function handles various error conditions:

- **Invalid input**: Empty GitHub username
- **Missing dependencies**: ldap3 library not installed
- **LDAP errors**: Connection failures, authentication issues, search errors
- **No results**: No matching records found
- **Empty emails**: Records found but no email addresses in the expected fields

All errors are logged using the Python `logging` module for debugging purposes.

## Example

See `example.py` for a complete usage example with logging configuration.

## Requirements

- Python 3.9+
- ldap3 >= 2.9.0

## License

GNU Lesser General Public License, Version 2.1, February 1999
