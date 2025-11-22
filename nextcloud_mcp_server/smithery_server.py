"""Smithery-compatible server entry point for Nextcloud MCP Server.

This module provides a simplified entry point for deploying the Nextcloud MCP Server
on Smithery's platform. It uses session-based configuration instead of environment
variables, allowing each user session to have its own Nextcloud credentials.

Note: This is a lightweight wrapper that creates clients per-request based on
session configuration. For features like vector sync, semantic search, and OAuth,
use the standard deployment mode with environment variables.
"""

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Optional

from mcp.server.fastmcp import Context, FastMCP
from pydantic import AnyHttpUrl, BaseModel, Field
from smithery.decorators import smithery

from nextcloud_mcp_server.client import NextcloudClient
from nextcloud_mcp_server.server import (
    configure_calendar_tools,
    configure_contacts_tools,
    configure_cookbook_tools,
    configure_deck_tools,
    configure_notes_tools,
    configure_sharing_tools,
    configure_tables_tools,
    configure_webdav_tools,
)

logger = logging.getLogger(__name__)


@dataclass
class SmitheryAppContext:
    """Application context for Smithery deployment mode.

    This minimal context is used by the context helper to identify
    Smithery mode and create clients from session config.
    """

    smithery_mode: bool = True


class NextcloudConfigSchema(BaseModel):
    """Configuration schema for Nextcloud MCP Server deployment on Smithery.

    Users provide these settings when connecting to the server, allowing each
    session to use different Nextcloud credentials.
    """

    nextcloud_host: AnyHttpUrl = Field(
        ...,
        description="Your Nextcloud instance URL (e.g., https://cloud.example.com)",
    )
    username: str = Field(
        ...,
        description="Your Nextcloud username",
    )
    password: str = Field(
        ...,
        description="Your Nextcloud app password (create one in Settings → Security → Devices & sessions)",
    )


@smithery.server(config_schema=NextcloudConfigSchema)
def create_server():
    """Create and return a FastMCP server instance for Nextcloud integration.

    This function is called by Smithery for each server deployment. The server
    creates Nextcloud clients per-request based on user session configuration.

    The server operates in a simplified BasicAuth mode, suitable for individual
    user sessions on Smithery's platform. Advanced features like vector sync,
    semantic search, and OAuth are not available in this deployment mode.

    Returns:
        FastMCP: Configured Nextcloud MCP server instance
    """
    logger.info("Creating Nextcloud MCP Server instance for Smithery deployment")

    # Create a lifespan context that marks this as Smithery mode
    @asynccontextmanager
    async def smithery_lifespan(server: FastMCP) -> AsyncIterator[SmitheryAppContext]:
        """Lifespan context for Smithery deployment mode.

        This provides a minimal context that the context helper can detect
        to know it should create clients from session config.
        """
        logger.info("Starting Nextcloud MCP Server in Smithery mode")
        try:
            yield SmitheryAppContext(smithery_mode=True)
        finally:
            logger.info("Shutting down Nextcloud MCP Server")

    # Create FastMCP server instance with Smithery lifespan
    mcp = FastMCP("Nextcloud MCP", lifespan=smithery_lifespan)

    # Register capabilities resource
    @mcp.resource("nc://capabilities")
    async def nc_get_capabilities():
        """Get the Nextcloud Host capabilities."""
        from nextcloud_mcp_server.context import get_client as get_nextcloud_client

        ctx: Context = mcp.get_context()
        client = await get_nextcloud_client(ctx)
        try:
            return await client.capabilities()
        finally:
            await client.close()

    # Configure tools for all supported apps
    # In Smithery mode, all apps are available and tools will create
    # clients per-request based on session config
    available_apps = {
        "notes": configure_notes_tools,
        "calendar": configure_calendar_tools,
        "contacts": configure_contacts_tools,
        "webdav": configure_webdav_tools,
        "deck": configure_deck_tools,
        "cookbook": configure_cookbook_tools,
        "tables": configure_tables_tools,
        "sharing": configure_sharing_tools,
    }

    for app_name, configure_func in available_apps.items():
        logger.info(f"Configuring {app_name} tools")
        configure_func(mcp)

    logger.info(
        "Nextcloud MCP Server created successfully with all available app integrations"
    )
    logger.info(
        "Smithery mode: Creates clients per-request from session configuration"
    )
    logger.info(
        "Note: Vector sync, semantic search, and OAuth features are not available in Smithery mode"
    )

    return mcp.server
