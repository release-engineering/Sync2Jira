"""
Pytest tests for the Rover_Lookup package.

These tests verify the functionality of the github_username_to_emails function
and related components.
"""

import logging
from unittest.mock import Mock, patch

# Import the function we're testing
from Rover_Lookup import github_username_to_emails


class TestGithubUsernameToEmails:
    """Test cases for the github_username_to_emails function."""

    LDAP_SERVER = "ldaps://ipa.redhat.com"
    LDAP_BASE_DN = "cn=users,cn=accounts,dc=redhat,dc=com"
    LDAP_BIND_DN = "uid=sync2jira,cn=users,cn=accounts,dc=redhat,dc=com"
    LDAP_PASSWORD = "test-password"

    def _call(self, username, **overrides):
        """Helper to call github_username_to_emails with IPA defaults."""
        kwargs = dict(
            ldap_server=self.LDAP_SERVER,
            ldap_base_dn=self.LDAP_BASE_DN,
            ldap_bind_dn=self.LDAP_BIND_DN,
            ldap_password=self.LDAP_PASSWORD,
        )
        kwargs.update(overrides)
        return github_username_to_emails(username, **kwargs)

    def test_empty_username_returns_none(self, caplog):
        """Test that empty username returns None and logs error."""
        with caplog.at_level(logging.ERROR):
            result = github_username_to_emails("")

        assert result is None
        assert "GitHub username cannot be empty" in caplog.text

    def test_none_username_returns_none(self, caplog):
        """Test that None username returns None and logs error."""
        with caplog.at_level(logging.ERROR):
            result = github_username_to_emails(None)

        assert result is None
        assert "GitHub username cannot be empty" in caplog.text

    @patch("Rover_Lookup.lookup.Connection")
    def test_successful_lookup_single_record(self, mock_connection_class, caplog):
        """Test successful LDAP lookup with single record containing multiple emails."""
        # Mock the LDAP server connection
        mock_conn = Mock()
        mock_connection_class.return_value = mock_conn
        mock_conn.search.return_value = True

        # Mock the LDAP entry
        mock_entry = Mock()
        mock_entry.entry_dn = "cn=testuser,cn=users,cn=accounts,dc=redhat,dc=com"

        # Mock email attributes
        mock_primary_mail = Mock()
        mock_primary_mail.value = "user@redhat.com"
        mock_entry.rhatPrimaryMail = mock_primary_mail

        mock_mail = Mock()
        mock_mail.value = ["user@example.com", "user.alias@redhat.com"]
        mock_entry.mail = mock_mail

        mock_preferred_alias = Mock()
        # Duplicate value to test deduplication
        mock_preferred_alias.value = "user@redhat.com"
        mock_entry.rhatPreferredAlias = mock_preferred_alias

        mock_conn.entries = [mock_entry]

        with caplog.at_level(logging.DEBUG):
            result = self._call("test-user")

        # Verify result
        assert result == [
            "user.alias@redhat.com",
            "user@example.com",
            "user@redhat.com",
        ]
        mock_connection_class.assert_called_with(
            self.LDAP_SERVER,
            self.LDAP_BIND_DN,
            self.LDAP_PASSWORD,
            auto_bind=True,
            raise_exceptions=True,
        )

        # Verify LDAP query was called correctly
        mock_conn.search.assert_called_once()
        search_args = mock_conn.search.call_args
        filter_part = "rhatSocialURL=Github->https://github.com/test-user"
        expected_filter = f"(|({filter_part})({filter_part}/))"
        assert search_args[1]["search_filter"] == expected_filter
        assert search_args[1]["search_base"] == self.LDAP_BASE_DN
        assert "rhatPrimaryMail" in search_args[1]["attributes"]
        assert "mail" in search_args[1]["attributes"]
        assert "rhatPreferredAlias" in search_args[1]["attributes"]

        mock_conn.unbind.assert_called_once()

    @patch("Rover_Lookup.lookup.Connection")
    def test_successful_lookup_multiple_records(self, mock_connection_class):
        """Test successful LDAP lookup with multiple records."""
        # Mock the LDAP server connection
        mock_conn = Mock()
        mock_connection_class.return_value = mock_conn
        mock_conn.search.return_value = True

        # Create two mock entries
        mock_entry1 = Mock()
        mock_entry1.entry_dn = "cn=user1,cn=users,cn=accounts,dc=redhat,dc=com"
        mock_primary_mail1 = Mock()
        mock_primary_mail1.value = "user1@redhat.com"
        mock_entry1.rhatPrimaryMail = mock_primary_mail1
        mock_entry1.mail = Mock()
        mock_entry1.mail.value = "zmail@redhat.com"
        mock_entry1.rhatPreferredAlias = Mock()
        mock_entry1.rhatPreferredAlias.value = "team@redhat.com"

        mock_entry2 = Mock()
        mock_entry2.entry_dn = "cn=user2,cn=users,cn=accounts,dc=redhat,dc=com"
        mock_primary_mail2 = Mock()
        mock_primary_mail2.value = "user2@redhat.com"
        mock_entry2.rhatPrimaryMail = mock_primary_mail2
        mock_entry2.mail = Mock()
        mock_entry2.mail.value = None
        mock_entry2.rhatPreferredAlias = Mock()
        mock_entry2.rhatPreferredAlias.value = "team@redhat.com"

        mock_conn.entries = [mock_entry1, mock_entry2]

        result = self._call("test-user")

        # Verify result combines emails from both records
        assert result == [
            "team@redhat.com",
            "user1@redhat.com",
            "user2@redhat.com",
            "zmail@redhat.com",
        ]

    @patch("Rover_Lookup.lookup.Connection")
    def test_no_records_found(self, mock_connection_class, caplog):
        """Test LDAP lookup when no records are found."""
        mock_conn = Mock()
        mock_connection_class.return_value = mock_conn
        mock_conn.search.return_value = True
        mock_conn.entries = []  # No entries found

        with caplog.at_level(logging.INFO):
            result = self._call("nonexistent-user")

        assert result == []
        assert "No LDAP entries found" in caplog.text
        mock_conn.unbind.assert_called_once()

    @patch("Rover_Lookup.lookup.Connection")
    def test_records_with_no_emails(self, mock_connection_class):
        """Test LDAP lookup when records are found but contain no email addresses."""
        mock_conn = Mock()
        mock_connection_class.return_value = mock_conn
        mock_conn.search.return_value = True

        # Mock entry with no email attributes
        mock_entry = Mock()
        mock_entry.entry_dn = "cn=testuser,cn=users,cn=accounts,dc=redhat,dc=com"

        # Mock attributes that don't exist or are empty
        mock_entry.rhatPrimaryMail = Mock()
        mock_entry.rhatPrimaryMail.value = None
        mock_entry.mail = Mock()
        mock_entry.mail.value = []
        mock_entry.rhatPreferredAlias = Mock()
        mock_entry.rhatPreferredAlias.value = ""

        mock_conn.entries = [mock_entry]

        result = self._call("test-user")

        assert result == []

    @patch("Rover_Lookup.lookup.Connection")
    def test_ldap_search_failure(self, mock_connection_class, caplog):
        """Test LDAP search failure."""
        mock_conn = Mock()
        mock_connection_class.return_value = mock_conn
        mock_conn.search.return_value = False  # Search failed

        with caplog.at_level(logging.INFO):
            result = self._call("test-user")

        assert result is None
        assert "LDAP search failed" in caplog.text
        mock_conn.unbind.assert_called_once()

    @patch("Rover_Lookup.lookup.Connection")
    def test_connection_ldap_exception(self, mock_connection_class, caplog):
        """Test LDAP exception handling."""
        from Rover_Lookup.lookup import LDAPException

        mock_connection_class.side_effect = LDAPException("Connection refused")

        with caplog.at_level(logging.ERROR):
            result = self._call("test-user")

        assert result is None
        assert "Error connecting to LDAP server" in caplog.text
        assert "Connection refused" in caplog.text

    @patch("Rover_Lookup.lookup.Connection")
    def test_connection_ldap_vpn_exception(self, mock_connection_class, caplog):
        """Test LDAP exception with VPN hint for redhat.com servers."""
        from Rover_Lookup.lookup import LDAPException

        mock_connection_class.side_effect = LDAPException("invalid server address")

        with caplog.at_level(logging.ERROR):
            result = self._call("test-user")

        assert result is None
        assert "Error connecting to LDAP server" in caplog.text
        assert "is the VPN active?" in caplog.text

    @patch("Rover_Lookup.lookup.Connection")
    def test_connection_unexpected_exception(self, mock_connection_class, caplog):
        """Test unexpected exception handling."""
        mock_connection_class.side_effect = ValueError("An error occurred")

        with caplog.at_level(logging.ERROR):
            result = self._call("test-user")

        assert result is None
        assert "Unexpected error connecting to LDAP server" in caplog.text
        assert "An error occurred" in caplog.text

    @patch("Rover_Lookup.lookup.Connection")
    def test_search_ldap_exceptions(self, mock_connection_class, caplog):
        """Test LDAP exception handling."""
        from Rover_Lookup.lookup import LDAPException

        mock_conn = Mock()
        mock_connection_class.return_value = mock_conn
        mock_conn.search.side_effect = LDAPException("Connection failed")

        with caplog.at_level(logging.ERROR):
            result = self._call("test-user")

        assert result is None
        assert "LDAP error while looking up" in caplog.text
        assert "Connection failed" in caplog.text

    @patch("Rover_Lookup.lookup.Connection")
    def test_search_unexpected_exceptions(self, mock_connection_class, caplog):
        """Test unexpected exception handling."""
        mock_conn = Mock()
        mock_connection_class.return_value = mock_conn
        mock_conn.search.side_effect = ValueError("An error occurred")

        with caplog.at_level(logging.ERROR):
            result = self._call("test-user")

        assert result is None
        assert "Unexpected error while looking up" in caplog.text
        assert "An error occurred" in caplog.text

    @patch("Rover_Lookup.lookup.Connection")
    def test_custom_ldap_parameters(self, mock_connection_class):
        """Test function with custom LDAP parameters overriding defaults."""
        mock_conn = Mock()
        mock_connection_class.return_value = mock_conn
        mock_conn.search.return_value = True
        mock_conn.entries = []

        result = self._call(
            "test-user",
            ldap_server="ldap://custom.server.com",
            ldap_base_dn="ou=people,dc=custom,dc=com",
            ldap_bind_dn="cn=bind,dc=custom,dc=com",
            ldap_password="secret",
        )

        # Verify custom parameters were used
        mock_connection_class.assert_called_with(
            "ldap://custom.server.com",
            "cn=bind,dc=custom,dc=com",
            "secret",
            auto_bind=True,
            raise_exceptions=True,
        )

        # Verify custom base DN was used in search
        search_args = mock_conn.search.call_args
        assert search_args[1]["search_base"] == "ou=people,dc=custom,dc=com"

        assert result == []
