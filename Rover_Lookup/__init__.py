"""
Rover_Lookup - A Python package for translating GitHub usernames to Red Hat Associate email addresses.

This package queries the Red Hat Rover LDAP service to find Associates based on their
GitHub profile information and returns their email addresses.
"""

from .lookup import github_username_to_emails

__version__ = "1.0.0"
__all__ = ["github_username_to_emails"]
