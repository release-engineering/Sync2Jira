# This file is part of sync2jira.
# Copyright (C) 2026 Red Hat, Inc.
#
# sync2jira is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# sync2jira is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with sync2jira; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110.15.0 USA

"""
Jira authentication helpers.

This module's interface: pass a Jira instance config dict to
:func:`build_jira_client_kwargs`; the config may include ``auth_method``
(one of :const:`AUTH_METHOD_PAT` or :const:`AUTH_METHOD_OAUTH2`, default if
omitted is :const:`AUTH_METHOD_PAT`), and credentials as described below.
We ignore or remove config keys that do not apply to the chosen auth method
and validate their values as needed.

- **PAT (Personal Access Token / API token)**: set ``auth_method`` to
  :const:`AUTH_METHOD_PAT` and provide ``basic_auth`` in the config.
- **OAuth 2.0 2-Legged (2LO)** with Atlassian service account: set
  ``auth_method`` to :const:`AUTH_METHOD_OAUTH2` and provide an ``oauth2``
  dict with ``client_id`` and ``client_secret``.
"""

import logging
import time
from typing import Any, Dict, NamedTuple, Tuple

import requests

log = logging.getLogger("sync2jira")

# Default Atlassian OAuth 2.0 token endpoint (client credentials grant)
DEFAULT_OAUTH2_TOKEN_URL = "https://auth.atlassian.com/oauth/token"

# Auth method config values
AUTH_METHOD_PAT = "pat"
AUTH_METHOD_OAUTH2 = "oauth2"

# Refresh token this many seconds before expiry (e.g. 5 min)
OAUTH2_TOKEN_REFRESH_BUFFER_SECONDS = 300


class OAuth2CachedToken(NamedTuple):
    """OAuth2 access token and its expiry timestamp (seconds since epoch)."""

    token: str
    expires_at: float


# OAuth2 token cache: key (client_id, client_secret, token_url) -> OAuth2CachedToken.
# Reused across syncs so we don't request a new token per issue/PR. No lock (single-threaded).
_oauth2_token_cache: Dict[Tuple[str, str, str], OAuth2CachedToken] = {}


def _fetch_oauth2_token(
    client_id: str,
    client_secret: str,
    token_url: str = DEFAULT_OAUTH2_TOKEN_URL,
) -> OAuth2CachedToken:
    """Request a new OAuth2 access token. Returns token and expiry timestamp."""
    response = requests.post(
        token_url,
        json={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    access_token = data.get("access_token")
    if not access_token:
        raise ValueError("OAuth 2.0 token response did not contain access_token")
    expires_in = int(data.get("expires_in", 3600))
    return OAuth2CachedToken(access_token, time.time() + expires_in)


def _get_oauth2_token(
    client_id: str,
    client_secret: str,
    token_url: str = DEFAULT_OAUTH2_TOKEN_URL,
) -> str:
    """Return a valid OAuth2 token, reusing cache if not expired (with refresh buffer)."""
    key = (client_id, client_secret, token_url)
    now = time.time()
    if entry := _oauth2_token_cache.get(key):
        if now < entry.expires_at - OAUTH2_TOKEN_REFRESH_BUFFER_SECONDS:
            return entry.token
    cached = _fetch_oauth2_token(
        client_id=client_id,
        client_secret=client_secret,
        token_url=token_url,
    )
    _oauth2_token_cache[key] = cached
    return cached.token


def build_jira_client_kwargs(jira_instance_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build keyword arguments for jira.client.JIRA() from a jira instance config.

    :param jira_instance_config: One entry from config["sync2jira"]["jira"].
    :returns: Dict suitable for JIRA(**kwargs).
    :raises ValueError: If auth method is invalid or required keys are missing.
    """
    # Copy so we don't mutate the original config
    kwargs = dict(jira_instance_config)

    auth_method = kwargs.pop("auth_method", AUTH_METHOD_PAT)

    if auth_method == AUTH_METHOD_OAUTH2:
        oauth2_cfg = kwargs.pop("oauth2", {}) or {}
        if not isinstance(oauth2_cfg, dict):
            raise ValueError("oauth2 must be a dict with client_id and client_secret")
        client_id = oauth2_cfg.get("client_id")
        client_secret = oauth2_cfg.get("client_secret")
        if not client_id or not client_secret:
            raise ValueError(
                "OAuth 2.0 (oauth2) auth requires oauth2.client_id and oauth2.client_secret"
            )
        token_url = oauth2_cfg.get("token_url", DEFAULT_OAUTH2_TOKEN_URL)
        kwargs.pop("basic_auth", None)
        try:
            access_token = _get_oauth2_token(
                client_id=client_id,
                client_secret=client_secret,
                token_url=token_url,
            )
        except requests.RequestException as e:
            log.error("OAuth 2.0 token request failed: %s", e)
            raise
        kwargs["token_auth"] = access_token
        return kwargs

    if auth_method == AUTH_METHOD_PAT:
        # PAT: keep basic_auth and options as-is; remove oauth2
        kwargs.pop("oauth2", None)
        if "basic_auth" not in kwargs:
            raise ValueError("PAT auth requires basic_auth in the jira instance config")
        return kwargs

    raise ValueError(
        f"Unsupported auth_method: {auth_method!r}. Use {AUTH_METHOD_PAT!r} or {AUTH_METHOD_OAUTH2!r}"
    )


def invalidate_oauth2_cache_for_config(jira_instance_config: Dict[str, Any]):
    """
    Invalidate the OAuth2 token cache for the given Jira instance config.

    If the config has oauth2 credentials, the cached token (if any) is removed so
    the next client build will request a new token. Use this when Jira has
    rejected a request (e.g. JIRAError) so a retry does not reuse a revoked or
    invalid token.
    """
    oauth2_cfg = jira_instance_config.get("oauth2")
    if not oauth2_cfg or not isinstance(oauth2_cfg, dict):
        return
    client_id = oauth2_cfg.get("client_id")
    client_secret = oauth2_cfg.get("client_secret")
    token_url = oauth2_cfg.get("token_url", DEFAULT_OAUTH2_TOKEN_URL)
    key = (client_id, client_secret, token_url)
    _oauth2_token_cache.pop(key, None)
    log.debug("Invalidated OAuth2 token cache for Jira instance")
