"""Helper functions for accessing context in MCP tools."""

import os

from mcp.server.fastmcp import Context

from nextcloud_mcp_server.client import NextcloudClient
from nextcloud_mcp_server.config import get_settings


async def get_client(ctx: Context) -> NextcloudClient:
    """
    Get the appropriate Nextcloud client based on authentication mode.

    ADR-005 compliant implementation supporting three deployment modes:
    1. BasicAuth mode: Returns shared client from lifespan context
    2. Multi-audience mode (ENABLE_TOKEN_EXCHANGE=false, default):
       Token already contains both MCP and Nextcloud audiences - use directly
    3. Token exchange mode (ENABLE_TOKEN_EXCHANGE=true):
       Exchange MCP token for Nextcloud token via RFC 8693
    4. Smithery mode: Creates client from session config (per-request)

    SECURITY: Token passthrough has been REMOVED. All OAuth modes validate
    proper token audiences per MCP Security Best Practices specification.

    Note: Nextcloud doesn't support OAuth scopes natively. Scopes are enforced
    by the MCP server via @require_scopes decorator, not by the IdP.

    This function automatically detects the authentication mode by checking
    the type of the lifespan context.

    Args:
        ctx: MCP request context

    Returns:
        NextcloudClient configured for the current authentication mode

    Raises:
        AttributeError: If context doesn't contain expected data

    Example:
        ```python
        @mcp.tool()
        async def my_tool(ctx: Context):
            client = await get_client(ctx)
            return await client.capabilities()
        ```
    """
    settings = get_settings()
    lifespan_ctx = ctx.request_context.lifespan_context

    # Smithery mode - create client from session config (per-request)
    if hasattr(lifespan_ctx, "smithery_mode") and lifespan_ctx.smithery_mode:
        # Get session config from context
        session_config = ctx.session_config

        # Temporarily set environment variables from session config
        # This allows NextcloudClient.from_env() to work with session-specific values
        old_host = os.environ.get("NEXTCLOUD_HOST")
        old_username = os.environ.get("NEXTCLOUD_USERNAME")
        old_password = os.environ.get("NEXTCLOUD_PASSWORD")

        try:
            os.environ["NEXTCLOUD_HOST"] = str(session_config.nextcloud_host)
            os.environ["NEXTCLOUD_USERNAME"] = session_config.username
            os.environ["NEXTCLOUD_PASSWORD"] = session_config.password

            # Create client from environment (which now has session-specific values)
            client = NextcloudClient.from_env()
            return client
        finally:
            # Restore original environment variables
            if old_host is not None:
                os.environ["NEXTCLOUD_HOST"] = old_host
            elif "NEXTCLOUD_HOST" in os.environ:
                del os.environ["NEXTCLOUD_HOST"]

            if old_username is not None:
                os.environ["NEXTCLOUD_USERNAME"] = old_username
            elif "NEXTCLOUD_USERNAME" in os.environ:
                del os.environ["NEXTCLOUD_USERNAME"]

            if old_password is not None:
                os.environ["NEXTCLOUD_PASSWORD"] = old_password
            elif "NEXTCLOUD_PASSWORD" in os.environ:
                del os.environ["NEXTCLOUD_PASSWORD"]

    # BasicAuth mode - use shared client (no token exchange)
    if hasattr(lifespan_ctx, "client"):
        return lifespan_ctx.client

    # OAuth mode (has 'nextcloud_host' attribute)
    if hasattr(lifespan_ctx, "nextcloud_host"):
        from nextcloud_mcp_server.auth.context_helper import (
            get_client_from_context,
            get_session_client_from_context,
        )

        if settings.enable_token_exchange:
            # Mode 2: Exchange MCP token for Nextcloud token
            # Token was validated to have MCP audience in UnifiedTokenVerifier
            # Now exchange it for Nextcloud audience
            return await get_session_client_from_context(
                ctx, lifespan_ctx.nextcloud_host
            )
        else:
            # Mode 1: Multi-audience token - use directly
            # Token was validated to have MCP audience in UnifiedTokenVerifier
            # Nextcloud will independently validate its own audience when receiving API calls
            return get_client_from_context(ctx, lifespan_ctx.nextcloud_host)

    # Unknown context type
    raise AttributeError(
        f"Lifespan context does not have 'client', 'nextcloud_host', or 'smithery_mode' attribute. "
        f"Type: {type(lifespan_ctx)}"
    )
