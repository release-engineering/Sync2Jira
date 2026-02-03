"""
LDAP lookup functions for translating GitHub usernames to Red Hat Associate email addresses
"""

import logging
from typing import List, Optional
import warnings

# Ignore deprecation warnings related to pyasn1's use of typeMap and tagMap
# which are triggered by ldap3's use of pyasn1.
warnings.filterwarnings(
    "ignore",
    message=r"(tag|type)Map is deprecated. Please use (TAG|TYPE)_MAP instead.",
    category=DeprecationWarning,
    module="pyasn1.codec.ber.encoder",
)
from ldap3 import Connection, SUBTREE  # noqa: E402
from ldap3.core.exceptions import LDAPException  # noqa: E402

logger = logging.getLogger(__name__)


def github_username_to_emails(
    github_username: str,
    ldap_server: Optional[str] = None,
    ldap_base_dn: Optional[str] = None,
    ldap_bind_dn: Optional[str] = None,
    ldap_password: Optional[str] = None,
) -> Optional[List[str]]:
    """
    Translate a GitHub username to Red Hat Associate email addresses via LDAP lookup.

    Args:
        github_username (str): The GitHub username to look up
        ldap_server (str, optional): LDAP server address; if None, uses default Rover server
        ldap_base_dn (str, optional): Base DN for LDAP search; if None, uses default
        ldap_bind_dn (str, optional): DN for LDAP authentication; if None, uses anonymous bind
        ldap_password (str, optional): Password for LDAP authentication

    Returns:
        Optional[List[str]]: List of unique email addresses if found, empty list if no emails,
                            None if query failed
    """
    if not github_username:
        logger.error("GitHub username cannot be empty")
        return None

    # Default LDAP configuration for Red Hat Rover service
    # FIXME:  These should be configured via config file.
    if ldap_server is None:
        ldap_server = "ldap://ldap.corp.redhat.com"  # Default Rover LDAP server
    if ldap_base_dn is None:
        ldap_base_dn = "ou=users,dc=redhat,dc=com"  # Default base DN

    # Construct the LDAP filter to match the GitHub "Professional Social Media" URL.
    # The rhatSocialURL field contains values like "Github->https://github.com/username".
    # However, 5% of the entries include a trailing slash (which GitHub accepts),
    # so look for those, too.
    github_url = f"https://github.com/{github_username}"
    filter_clause = f"rhatSocialURL=Github->{github_url}"
    ldap_filter = f"(|({filter_clause})({filter_clause}/))"

    # Attributes to retrieve (email fields)
    attributes = ["rhatPrimaryMail", "mail", "rhatPreferredAlias"]

    try:
        # Create LDAP server connection; if credentials were not provided, the connection
        # will use an anonymous binding.
        conn = Connection(
            ldap_server,
            ldap_bind_dn,
            ldap_password,
            auto_bind=True,
            raise_exceptions=True,
        )
    except LDAPException as e:
        msg = f"Error connecting to LDAP server {ldap_server!r}: {str(e)}"
        if "redhat.com" in ldap_server and "invalid server address" in str(e):
            msg += "; is the VPN active?"
        logger.error(msg)
        return None
    except Exception as e:
        logger.error(
            f"Unexpected error connecting to LDAP server {ldap_server!r}: {str(e)}"
        )
        return None

    logger.debug("Searching for GitHub username: %r", github_username)
    logger.debug("LDAP filter: %r", ldap_filter)

    try:
        # Perform the LDAP search
        success = conn.search(
            search_base=ldap_base_dn,
            search_filter=ldap_filter,
            search_scope=SUBTREE,
            attributes=attributes,
        )

        if not success:
            logger.info("LDAP search failed for GitHub username: %r", github_username)
            return None

        entries = conn.entries
        logger.debug("Found %d LDAP entries", len(entries))

        if not entries:
            logger.info(
                "No LDAP entries found for GitHub username: %r", github_username
            )
            return []

        # Extract email addresses from all entries
        email_addresses = set()  # Use set to automatically handle uniqueness

        for entry in entries:
            logger.debug("Processing LDAP entry: %r", entry.entry_dn)

            # Check each email field
            for attr_name in attributes:
                if hasattr(entry, attr_name):
                    attr_value = getattr(entry, attr_name)
                    if attr_value:
                        # Handle both single values and lists
                        emails = (
                            attr_value.value
                            if isinstance(attr_value.value, list)
                            else [attr_value.value]
                        )
                        for email in emails:
                            if email:  # Skip empty strings
                                email_addresses.add(str(email).strip())

        # Convert set to sorted list for consistent output
        result_emails = sorted(list(email_addresses))

        logger.debug(
            "Found %d unique email addresses for GitHub username, %r: %s",
            len(result_emails),
            github_username,
            result_emails,
        )

        return result_emails

    except LDAPException as e:
        logger.error(
            f"LDAP error while looking up GitHub username {github_username}: {str(e)}"
        )
        return None
    except Exception as e:
        logger.error(
            f"Unexpected error while looking up GitHub username {github_username}: {str(e)}"
        )
        return None
    finally:
        conn.unbind()
