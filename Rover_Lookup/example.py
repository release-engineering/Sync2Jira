#!/usr/bin/env python3
"""
Example usage of the Rover_Lookup package.

This script demonstrates how to use the github_username_to_emails function
to look up Red Hat Associate email addresses based on their GitHub username.
"""

import logging

from Rover_Lookup import github_username_to_emails


def main():
    # Configure logging to see debug information
    logging.getLogger().setLevel(logging.DEBUG)

    # Example GitHub username (replace with actual username)
    github_username = "ninja-quokka"

    print(f"Looking up email addresses for GitHub username: {github_username}")

    # Call the lookup function
    # Note: You may need to provide LDAP connection parameters depending on your setup
    emails = github_username_to_emails(
        github_username=github_username,
        # Uncomment and modify these if you need custom LDAP settings:
        # ldap_server="ldap://your-rover-server.com",
        # ldap_base_dn="ou=users,dc=example,dc=com",
        # ldap_bind_dn="cn=your-bind-user,dc=example,dc=com",
        # ldap_password="your-password"
    )

    if emails is None:
        print("❌ LDAP query failed. Check the logs for details.")
    elif not emails:
        print("📭 No email addresses found for this GitHub username.")
    else:
        print(f"✅ Found {len(emails)} email address(es):")
        for i, email in enumerate(emails, 1):
            print(f"  {i}. {email}")


if __name__ == "__main__":
    main()
