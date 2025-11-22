#!/usr/bin/env python3
"""Entry point for Nextcloud MCP Server container deployment on Smithery.

This creates an HTTP server that handles session configuration from query parameters,
as required by Smithery's container runtime specification.
"""

import json
import os
from urllib.parse import parse_qs, urlparse

import uvicorn
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Mount

from nextcloud_mcp_server.smithery_server import create_server


def parse_config_from_query(query_string: str) -> dict:
    """Parse session configuration from query string parameters.

    Smithery passes configuration as URL query parameters.

    Args:
        query_string: Raw query string from the request

    Returns:
        Dictionary with nextcloud_host, username, and password
    """
    params = parse_qs(query_string)

    # Extract config values (take first value from each list)
    config = {}
    if "nextcloud_host" in params:
        config["nextcloud_host"] = params["nextcloud_host"][0]
    if "username" in params:
        config["username"] = params["username"][0]
    if "password" in params:
        config["password"] = params["password"][0]

    return config


def create_app():
    """Create the Starlette application with MCP server.

    This manually wraps the FastMCP server to handle Smithery's
    session configuration from query parameters.
    """
    # Get the FastMCP server (without Smithery decorator for container mode)
    # We'll handle session config manually
    from nextcloud_mcp_server.smithery_server import NextcloudConfigSchema, SmitheryAppContext
    from mcp.server.fastmcp import FastMCP
    from contextlib import asynccontextmanager
    from collections.abc import AsyncIterator
    import logging

    logger = logging.getLogger(__name__)

    # Create a lifespan that provides Smithery context
    @asynccontextmanager
    async def smithery_lifespan(server: FastMCP) -> AsyncIterator[SmitheryAppContext]:
        """Lifespan context for Smithery deployment mode."""
        logger.info("Starting Nextcloud MCP Server in Smithery container mode")
        try:
            yield SmitheryAppContext(smithery_mode=True)
        finally:
            logger.info("Shutting down Nextcloud MCP Server")

    # Create FastMCP server
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

    mcp = FastMCP("Nextcloud MCP", lifespan=smithery_lifespan)

    # Register all tools
    from nextcloud_mcp_server.context import get_client as get_nextcloud_client
    from mcp.server.fastmcp import Context

    @mcp.resource("nc://capabilities")
    async def nc_get_capabilities():
        """Get the Nextcloud Host capabilities."""
        ctx: Context = mcp.get_context()
        client = await get_nextcloud_client(ctx)
        try:
            return await client.capabilities()
        finally:
            await client.close()

    # Configure all app tools
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

    # Get the ASGI app from FastMCP
    mcp_app = mcp.streamable_http_app()

    # Wrap it in Starlette to add CORS and config parsing
    async def mcp_handler(request: Request):
        """Handle MCP requests with session config from query parameters."""
        # Parse config from query parameters
        config = parse_config_from_query(request.url.query.decode())

        # Inject config into request scope for FastMCP to access
        # FastMCP will make this available via ctx.session_config
        request.scope["session_config"] = config

        # Forward to FastMCP app
        return await mcp_app(request.scope, request.receive, request._send)

    # Create Starlette app with CORS
    app = Starlette(
        routes=[
            Mount("/mcp", app=mcp_handler),
        ],
    )

    # Add CORS middleware (required by Smithery)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    logger.info("Nextcloud MCP Server container app created successfully")
    return app


if __name__ == "__main__":
    # Get port from environment (Smithery sets PORT=8081)
    port = int(os.environ.get("PORT", 8081))
    host = os.environ.get("HOST", "0.0.0.0")

    # Create and run the app
    app = create_app()
    uvicorn.run(app, host=host, port=port, log_level="info")
