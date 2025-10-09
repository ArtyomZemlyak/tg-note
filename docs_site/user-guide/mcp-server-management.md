# MCP Server Management via Telegram Bot

This guide explains how to manage MCP (Model Context Protocol) server configurations through the Telegram bot.

## Overview

You can add, list, enable, disable, and delete MCP server configurations directly through Telegram commands. This makes it easy to manage your MCP servers without editing configuration files manually.

## Commands

### Add a New MCP Server

**Command:** `/addmcpserver`

You can add a new MCP server configuration by sending a JSON configuration:

```
/addmcpserver
```

The bot will prompt you to send the JSON configuration. Example:

```json
{
  "name": "my-mcp-server",
  "description": "My custom MCP server",
  "command": "python3",
  "args": ["-m", "my_package.server"],
  "env": {
    "API_KEY": "your-api-key"
  },
  "enabled": true
}
```

Alternatively, you can send the JSON directly with the command:

```
/addmcpserver {"name": "my-server", "description": "Test server", "command": "python3", "args": ["-m", "test"], "enabled": true}
```

#### Required Fields

- `name` - Unique server name (used as identifier)
- `description` - Human-readable description
- `command` - Executable command (e.g., "python3", "node", "npx")
- `args` - Command-line arguments (array of strings)

#### Optional Fields

- `env` - Environment variables (object with key-value pairs)
- `working_dir` - Working directory for the server
- `enabled` - Whether to enable immediately (default: true)

### List All MCP Servers

**Command:** `/listmcpservers`

Shows all registered MCP servers with their current status (enabled/disabled). You can also enable/disable servers directly from the interactive buttons.

### MCP Status Summary

**Command:** `/mcpstatus`

Shows a quick summary:

- Total number of servers
- Number of enabled servers
- Number of disabled servers

### Enable an MCP Server

**Command:** `/enablemcp <server_name>`

Example:

```
/enablemcp my-mcp-server
```

This activates the specified MCP server, making it available for use.

### Disable an MCP Server

**Command:** `/disablemcp <server_name>`

Example:

```
/disablemcp my-mcp-server
```

This deactivates the specified MCP server without deleting its configuration.

### Remove an MCP Server

**Command:** `/removemcp <server_name>`

Example:

```
/removemcp my-mcp-server
```

⚠️ **Warning:** This permanently deletes the server configuration. The bot will ask for confirmation before deletion.

## Configuration Storage

MCP server configurations are stored as JSON files in the `data/mcp_servers/` directory. Each server has its own `.json` file named after the server name.

Example file structure:

```
data/
└── mcp_servers/
    ├── example-server.json
    ├── my-custom-server.json
    └── memory-agent.json
```

## Use Cases

### Adding a Memory Agent

```json
{
  "name": "memory-agent",
  "description": "Personal memory agent for storing and retrieving information",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-memory"],
  "enabled": true
}
```

### Adding a GitHub MCP Server

```json
{
  "name": "github-server",
  "description": "GitHub repository access via MCP",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-github"],
  "env": {
    "GITHUB_TOKEN": "your-github-token"
  },
  "enabled": true
}
```

### Adding a Custom Python MCP Server

```json
{
  "name": "my-python-server",
  "description": "Custom Python MCP server",
  "command": "python3",
  "args": ["-m", "my_package.mcp_server"],
  "working_dir": "/path/to/project",
  "env": {
    "API_KEY": "secret-key",
    "DEBUG": "true"
  },
  "enabled": true
}
```

## Tips

1. **Test servers before enabling** - Set `"enabled": false` when adding a new server, test it manually first, then enable it via `/enablemcp`.

2. **Use descriptive names** - Use clear, descriptive names for your servers to make management easier.

3. **Secure your secrets** - Environment variables are stored in the JSON files. Make sure to protect these files and don't commit them to public repositories.

4. **Check status regularly** - Use `/mcpstatus` to quickly see which servers are running.

5. **Interactive management** - The `/listmcpservers` command provides interactive buttons for quick enable/disable actions.

## Troubleshooting

### Server not appearing in the list

- Check that the JSON configuration is valid
- Verify the server name is unique
- Check the logs for any error messages

### Server fails to start

- Verify the command and arguments are correct
- Check that all required environment variables are set
- Ensure the working directory (if specified) exists
- Check that the executable is in your PATH

### Cannot delete a server

- Verify you're using the correct server name
- Check file permissions in the `data/mcp_servers/` directory

## Security Notes

⚠️ **Important Security Considerations:**

1. **Access Control** - Only authorized users should be able to add MCP servers, as they can execute arbitrary commands
2. **Environment Variables** - Be careful with API keys and secrets in environment variables
3. **Command Validation** - The system doesn't validate commands, so only add trusted MCP servers
4. **File Permissions** - Ensure the `data/mcp_servers/` directory has appropriate permissions

## See Also

- [MCP Server Registry](../agents/mcp-server-registry.md)
- [MCP Tools](../agents/mcp-tools.md)
- [Bot Commands](bot-commands.md)
