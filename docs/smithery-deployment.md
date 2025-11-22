# Smithery Deployment Guide

This guide explains how to deploy the Nextcloud MCP Server on [Smithery](https://smithery.ai), a platform for deploying and publishing MCP servers.

## Overview

Smithery provides automatic containerization and infrastructure for deploying MCP servers. The Nextcloud MCP Server supports Smithery deployment with session-based configuration, allowing each user to connect with their own Nextcloud credentials.

## Deployment Modes

The Nextcloud MCP Server can be deployed in two ways:

1. **Standard Deployment** (Docker, Kubernetes, local): Full-featured with OAuth, vector sync, semantic search, and all advanced capabilities.
2. **Smithery Deployment**: Simplified deployment with session-based configuration, suitable for individual users. Advanced features like vector sync and semantic search are not available.

## Prerequisites

- GitHub account
- Nextcloud instance with app password access enabled
- Python 3.11+ (for local testing)

## Project Structure

The Smithery deployment uses these key files:

```
nextcloud-mcp-server/
  smithery.yaml                    # Smithery configuration
  pyproject.toml                   # Python dependencies and Smithery server path
  nextcloud_mcp_server/
    smithery_server.py             # Smithery-compatible entry point
    context.py                     # Updated to support Smithery mode
```

## Configuration Files

### smithery.yaml

The minimal configuration file that tells Smithery this is a Python project:

```yaml
runtime: "python"
```

### pyproject.toml

The project configuration includes:

1. **Smithery dependency**: `smithery>=0.4.2` in the dependencies list
2. **Scripts for development**:
   ```toml
   [project.scripts]
   dev = "smithery.cli.dev:main"
   playground = "smithery.cli.playground:main"
   ```
3. **Server entry point**:
   ```toml
   [tool.smithery]
   server = "nextcloud_mcp_server.smithery_server:create_server"
   ```

### smithery_server.py

The Smithery-compatible server entry point with:

- **Configuration Schema**: Defines the settings users provide when connecting (Nextcloud host, username, password)
- **Server Creation Function**: Decorated with `@smithery.server()` to create a FastMCP server instance
- **Session-based Clients**: Creates Nextcloud clients per-request using session configuration

## Session Configuration

When users connect to your Smithery-deployed server, they provide:

- **nextcloud_host**: Their Nextcloud instance URL (e.g., `https://cloud.example.com`)
- **username**: Their Nextcloud username
- **password**: Their Nextcloud app password

These credentials are used to create a Nextcloud client for each request, allowing multiple users to use the same server deployment with their own credentials.

## Local Development

Test your Smithery deployment locally:

```bash
# Install dependencies
uv sync

# Start development server with interactive playground
uv run playground

# Or just run the server
uv run dev
```

The playground opens in your browser where you can:
- Test your MCP server tools in real-time
- See tool responses and debug issues
- Experiment with different session configurations

## Deploying to Smithery

1. **Push your code to GitHub**: Ensure `smithery.yaml` and updated `pyproject.toml` are committed

2. **Connect to Smithery**:
   - Visit [https://smithery.ai/new](https://smithery.ai/new)
   - Connect your GitHub account
   - Select the `nextcloud-mcp-server` repository

3. **Deploy**:
   - Navigate to the Deployments tab on your server page
   - Click "Deploy" to build and host your server
   - Smithery will automatically build and deploy your container

4. **Share**:
   - Your server will be available at `https://server.smithery.ai/your-server/mcp`
   - Users can discover and connect through Smithery's registry

## Features Available in Smithery Mode

The Smithery deployment supports:

- **Notes**: Full CRUD, keyword search
- **Calendar**: Events, todos, recurring events, attendees
- **Contacts**: Full CardDAV support, address books
- **Files (WebDAV)**: Filesystem access (OCR/document processing requires external services)
- **Deck**: Boards, stacks, cards, labels
- **Cookbook**: Recipe management
- **Tables**: Row operations
- **Sharing**: Create and manage shares

## Features NOT Available in Smithery Mode

The following features are only available in standard deployment modes:

- **Semantic Search**: Requires Qdrant and vector sync infrastructure
- **Vector Sync**: Background document indexing
- **OAuth/OIDC**: Session config uses BasicAuth only
- **Offline Access**: No refresh token storage
- **Background Jobs**: No persistent storage or task scheduling

## Architecture

### Smithery Mode Detection

The server detects Smithery mode by checking the lifespan context:

```python
# In context.py
if hasattr(lifespan_ctx, "smithery_mode") and lifespan_ctx.smithery_mode:
    # Create client from session config
    session_config = ctx.session_config
    client = create_client_from_config(session_config)
```

### Per-Request Client Creation

Unlike standard deployment where a single client is shared across requests (BasicAuth) or clients are managed per-user session (OAuth), Smithery mode creates a new client for each request:

1. Tool is called with `ctx: Context`
2. `get_client(ctx)` detects Smithery mode
3. Extracts session config from context
4. Creates a new NextcloudClient with those credentials
5. Returns the client to the tool

### Client Cleanup

Clients created in Smithery mode should be closed after use to prevent connection leaks:

```python
@mcp.tool()
async def my_tool(ctx: Context):
    client = await get_client(ctx)
    try:
        result = await client.some_operation()
        return result
    finally:
        await client.close()
```

Most existing tools don't include this cleanup, which is acceptable for short-lived requests but may need to be addressed for long-running operations.

## Troubleshooting

### Build Fails

- **Missing dependencies**: Ensure all dependencies are in `pyproject.toml`
- **Import errors**: Verify the server module path in `[tool.smithery]`
- **Version conflicts**: Check that `smithery>=0.4.2` is compatible with other dependencies

### Server Doesn't Run Locally

- **Missing Smithery**: Install with `uv sync`
- **Import errors**: Ensure the module path is correct
- **Configuration errors**: Check that `NextcloudConfigSchema` matches your needs

### Connection Issues

- **Invalid credentials**: Users should create app passwords in Nextcloud
- **Network access**: Ensure the Nextcloud instance is accessible from Smithery's infrastructure
- **HTTPS required**: Most Nextcloud instances require HTTPS; HTTP may not work

## Best Practices

1. **App Passwords**: Always use app-specific passwords, never the main account password
2. **HTTPS**: Use HTTPS for Nextcloud instances to ensure secure credential transmission
3. **Error Handling**: Implement proper error handling for invalid credentials
4. **Documentation**: Provide clear instructions for users on how to create app passwords

## Migration from Standard Deployment

If you're currently using standard deployment and want to also support Smithery:

1. The Smithery entry point (`smithery_server.py`) is completely separate
2. Your existing deployment methods (Docker, Kubernetes, local) continue to work unchanged
3. Users can choose which deployment method suits their needs

## References

- [Smithery Documentation](https://smithery.ai/docs)
- [Smithery Python Deployment Guide](https://docs.smithery.ai/build/deployments/python)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [MCP Specification](https://modelcontextprotocol.io)
