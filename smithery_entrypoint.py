#!/usr/bin/env python3
"""Entry point for running Nextcloud MCP Server with Smithery in container mode.

This script starts an HTTP server using uvicorn to serve the Smithery-wrapped
MCP server, handling session-based configuration from Smithery's platform.
"""

import os

if __name__ == "__main__":
    # Import the Smithery-wrapped server
    from nextcloud_mcp_server.smithery_server import create_server

    # Get the FastMCP server
    mcp_server = create_server()

    # Create the ASGI app from the MCP server
    # Use streamable_http_app() for Smithery compatibility
    from mcp.server.fastmcp import FastMCP

    # The create_server() returns mcp.server, but we need the FastMCP instance
    # to get the streamable_http_app(). Let's reconstruct it properly.
    # Actually, looking at the smithery_server.py, it returns mcp.server
    # which is the underlying Server object, not the FastMCP wrapper.
    # We need to fix this.

    # For now, let's use a simpler approach - directly import and run
    import uvicorn
    from smithery.server import create_app_from_module

    # Create the ASGI app using Smithery's helper
    # This handles session config parsing from query parameters
    app = create_app_from_module("nextcloud_mcp_server.smithery_server")

    # Get port from environment (Smithery sets PORT=8081)
    port = int(os.environ.get("PORT", 8081))
    host = os.environ.get("HOST", "0.0.0.0")

    # Run with uvicorn
    uvicorn.run(app, host=host, port=port, log_level="info")
