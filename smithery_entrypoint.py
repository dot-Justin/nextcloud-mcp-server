#!/usr/bin/env python3
"""Entry point for running Nextcloud MCP Server with Smithery in container mode.

This script starts an HTTP server that serves the Smithery-wrapped MCP server,
handling session-based configuration from Smithery's platform.
"""

import os
import sys

# Ensure the package is importable
sys.path.insert(0, os.path.dirname(__file__))

if __name__ == "__main__":
    # Use Smithery's CLI to run the server
    # This handles all the HTTP server setup, session config parsing, etc.
    from smithery.cli.dev import main

    # Set port from environment (Smithery sets PORT=8081)
    port = int(os.environ.get("PORT", 8081))
    host = os.environ.get("HOST", "0.0.0.0")

    # Run the Smithery development server
    # In production, this still works fine as it's just an HTTP server
    sys.argv = ["smithery", "dev", "--host", host, "--port", str(port)]
    main()
