# This file is part of sync2jira.
# Copyright (C) 2016 Red Hat, Inc.
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

Supports two authentication methods, selectable per Jira instance in config:
- PAT (Personal Access Token / API token): use ``auth_method: "pat"`` and
  ``token_auth`` or ``basic_auth``.
- OAuth 2.0 2-Legged (2LO) with Atlassian service account: use
  ``auth_method: "oauth2"`` and ``oauth2`` with ``client_id`` and
  ``client_secret``.
"""

import logging
import time
from typing import Any, Dict, Tuple

import requests

log = logging.getLogger("sync2jira")

# Default Atlassian OAuth 2.0 token endpoint (client credentials grant)
DEFAULT_OAUTH2_TOKEN_URL = "https://auth.atlassian.com/oauth/token"

# Auth method config values
AUTH_METHOD_PAT = "pat"
AUTH_METHOD_OAUTH2 = "oauth2"

# OAuth2 token cache: key (client_id, client_secret, token_url) -> (token, expires_at).
# Reused across syncs so we don't request a new token per issue/PR. No lock (single-threaded).
_oauth2_token_cache: Dict[Tuple[str, str, str], Tuple[str, float]] = {}

# Refresh token this many seconds before expiry (e.g. 5 min)
OAUTH2_TOKEN_REFRESH_BUFFER_SECONDS = 300


def _fetch_oauth2_token(
    client_id: str,
    client_secret: str,
    token_url: str = DEFAULT_OAUTH2_TOKEN_URL,
) -> Tuple[str, int]:
    """Request a new OAuth2 access token. Returns (access_token, expires_in_seconds)."""
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
    return access_token, expires_in


def _get_oauth2_token(
    client_id: str,
    client_secret: str,
    token_url: str = DEFAULT_OAUTH2_TOKEN_URL,
) -> str:
    """Return a valid OAuth2 token, reusing cache if not expired (with refresh buffer)."""
    key = (client_id, client_secret, token_url)
    now = time.time()
    entry = _oauth2_token_cache.get(key)
    if entry:
        token, expires_at = entry
        if now < expires_at - OAUTH2_TOKEN_REFRESH_BUFFER_SECONDS:
            return token
    token, expires_in = _fetch_oauth2_token(
        client_id=client_id,
        client_secret=client_secret,
        token_url=token_url,
    )
    _oauth2_token_cache[key] = (token, now + expires_in)
    return token


def build_jira_client_kwargs(jira_instance_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build keyword arguments for jira.client.JIRA() from a jira instance config.

    Supports:
    - PAT: ``auth_method: "pat"`` (or omitted) with ``token_auth`` or
      ``basic_auth`` and ``options``.
    - OAuth 2LO: ``auth_method: "oauth2"`` with ``oauth2`` (client_id,
      client_secret, optional token_url) and ``options``.

    :param jira_instance_config: One entry from config["sync2jira"]["jira"].
    :returns: Dict suitable for JIRA(**kwargs).
    :raises ValueError: If auth method is invalid or required keys are missing.
    """
    # Copy so we don't mutate the original config
    kwargs = dict(jira_instance_config)

    auth_method = kwargs.pop("auth_method", AUTH_METHOD_PAT)

    if auth_method == AUTH_METHOD_OAUTH2:
        oauth2_cfg = kwargs.pop("oauth2", None) or {}
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
            raise ValueError(f"OAuth 2.0 token request failed: {e}") from e
        kwargs["token_auth"] = access_token
        return kwargs

    if auth_method == AUTH_METHOD_PAT:
        # PAT: keep token_auth or basic_auth and options as-is; remove oauth2
        kwargs.pop("oauth2", None)
        if "basic_auth" not in kwargs and "token_auth" not in kwargs:
            raise ValueError(
                "PAT auth requires token_auth or basic_auth in the jira instance config"
            )
        return kwargs

    raise ValueError(
        f"Unsupported auth_method: {auth_method!r}. Use {AUTH_METHOD_PAT!r} or {AUTH_METHOD_OAUTH2!r}"
    )
