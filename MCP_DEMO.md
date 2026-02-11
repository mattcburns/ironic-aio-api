# MCP Server Demo Guide

This guide shows how to demo the Model Context Protocol (MCP) integration in the Ironic AIO API using the MCP Inspector tool.

## What is MCP?

The Model Context Protocol (MCP) is an open standard that enables AI assistants to securely access data and tools. This API exposes all its functionality via both REST endpoints and MCP tools, making it accessible to AI assistants like Claude.

## Prerequisites

- Node.js and npm installed (for MCP Inspector - already included in the devcontainer)
- The Ironic AIO API running locally or accessible via network
- Optional: An Ironic instance to connect to (or use mock mode for demo)

## Setup Steps

### Working in the Devcontainer

If you're using the devcontainer (recommended), Node.js and npm are already installed, and ports 8000 (API) and 5173 (MCP Inspector) are automatically forwarded to your host machine. You can proceed directly to starting the API server.

### 1. Start the API Server

In one terminal, start the unified API server:

```bash
cd /workspaces/ironic-aio-api
source .venv/bin/activate  # If using virtual environment
uvicorn app:app --host 0.0.0.0 --port 8000
```

The server exposes:
- REST API at `http://localhost:8000`
- MCP Server at `http://localhost:8000/mcp/sse` (Server-Sent Events)
- API docs at `http://localhost:8000/docs`

### 2. Launch MCP Inspector

In another terminal, run the MCP Inspector pointing to your MCP endpoint:

```bash
npx @modelcontextprotocol/inspector http://localhost:8000/mcp/sse
```

The Inspector will:
- Connect to your MCP server
- Discover all available tools
- Open a web interface (usually at `http://localhost:6274`)
- Start a proxy server (usually at `http://localhost:6277`)

### 3. Open the Inspector Web UI

The Inspector automatically opens your browser to its web interface. If not, navigate to the URL shown in the terminal (typically `http://localhost:6274`).

If you are running inside the devcontainer, use the forwarded port URL from VS Code's Ports panel. The default localhost URL inside the container does not always map to your host browser unless the port is forwarded.

## Available MCP Tools

Your Ironic AIO API exposes the following tools via MCP:

### Health & Status
- **check_health**: Verify API and Ironic connectivity

### Server Management
- **list_servers**: List all servers with optional filtering
  - Filter by provision state (e.g., 'available', 'active')
  - Filter by resource class
  - Filter to show only available servers
- **get_server**: Get detailed information about a specific server

### Enrollment Workflow
- **enroll_server**: Enroll a new physical server into Ironic
  - Requires: BMC credentials, network configuration, MAC address
  - Optional: custom kernel/ramdisk URLs, Redfish settings
- **get_enrollment_status**: Check enrollment progress
- **provide_server**: Explicitly transition server to 'available' state

### Provisioning Workflow
- **provision_server**: Deploy an OS image to a server
  - Requires: server ID, image URL, network configuration
- **get_provision_status**: Check provisioning progress

### Unprovisioning Workflow
- **unprovision_server**: Remove OS and return server to available pool
- **get_unprovision_status**: Check unprovisioning progress

## Demo Walkthrough

### Demo 1: Health Check

1. In the Inspector UI, find the **check_health** tool
2. Click to expand it
3. Click "Execute" (no parameters required)
4. View the response showing API and Ironic status

**Expected Response:**
```json
{
  "status": "healthy",
  "ironic_api": "http://localhost:6385",
  "ironic_version": "1.82"
}
```

### Demo 2: List Servers

1. Find the **list_servers** tool
2. Try different parameter combinations:
   - No parameters: List all servers
   - `provision_state: "available"`: List only available servers
   - `available_only: true`: Show servers ready for provisioning
3. Click "Execute"
4. Review the server list with details

**Example Response:**
```json
{
  "servers": [
    {
      "id": "uuid-here",
      "name": "server-01",
      "provision_state": "available",
      "power_state": "power off",
      "resource_class": "baremetal",
      "available": true,
      "properties": {
        "cpus": 8,
        "memory_mb": 16384,
        "local_gb": 500
      }
    }
  ]
}
```

### Demo 3: Enroll a Server

1. Find the **enroll_server** tool
2. Fill in required parameters:
   ```
   name: demo-server-01
   bmc_address: 192.168.1.100
   bmc_username: admin
   bmc_password: secret
   mac_address: aa:bb:cc:dd:ee:ff
   nic_name: eth0
   ip_address: 192.168.1.50
   netmask: 255.255.255.0
   gateway: 192.168.1.1
   ```
3. Optional parameters:
   ```
   resource_class: baremetal
   redfish_verify_ca: false
   ```
4. Click "Execute"
5. Note the returned server ID from the response

**Example Response:**
```json
{
  "id": "new-server-uuid",
  "name": "demo-server-01",
  "provision_state": "enroll",
  "message": "Server enrolled successfully"
}
```

### Demo 4: Check Enrollment Status

1. Find the **get_enrollment_status** tool
2. Use the server ID from Demo 3
3. Click "Execute"
4. Repeat periodically to watch the state transition
5. Status should eventually reach `provision_state: "available"`

**Expected States:**
- `enroll` → `verifying` → `manageable` → `inspecting` → `available`

### Demo 5: Get Server Details

1. Find the **get_server** tool
2. Enter a server ID (from list_servers or enroll_server)
3. Click "Execute"
4. View comprehensive server information

**Example Response:**
```json
{
  "id": "server-uuid",
  "name": "demo-server-01",
  "provision_state": "available",
  "power_state": "power off",
  "resource_class": "baremetal",
  "available": true,
  "properties": {
    "cpus": 8,
    "memory_mb": 16384,
    "local_gb": 500,
    "cpu_arch": "x86_64"
  },
  "created_at": "2026-02-11T10:00:00Z",
  "updated_at": "2026-02-11T10:15:00Z"
}
```

### Demo 6: Provision a Server

1. Find the **provision_server** tool
2. Fill in parameters:
   ```
   server_id: <use a server in 'available' state>
   image_url: http://images.example.com/ubuntu-22.04.qcow2
   ip_address: 192.168.1.60
   netmask: 255.255.255.0
   gateway: 192.168.1.1
   ```
3. Click "Execute"
4. Use **get_provision_status** to monitor progress

**Expected States:**
- `available` → `deploying` → `wait call-back` → `deploying` → `active`

### Demo 7: Unprovision a Server

1. Find the **unprovision_server** tool
2. Enter the server ID of an active server
3. Click "Execute"
4. Use **get_unprovision_status** to monitor

**Expected States:**
- `active` → `cleaning` → `clean wait` → `available`

## Troubleshooting

### MCP Inspector in Devcontainer/WSL2

**Problem:** Inspector UI spins forever or proxy times out

**Root Cause:** MCP Inspector binds to `localhost` inside the container, which may not be accessible from your host browser in WSL2/Docker setups.

**Solutions:**

1. **Use VS Code's forwarded ports** - Don't manually type `localhost:6274` in your browser. Instead:
   - Open VS Code's **Ports panel** (View → Ports)
   - Find port **6274** (Inspector UI) - it should be automatically forwarded
   - Click the **"Open in Browser"** icon or copy the forwarded URL
   - The forwarded URL will work correctly through VS Code's tunnel

2. **Verify ports are forwarded** - In the Ports panel, ensure these are listed:
   - **8000** - Ironic AIO API
   - **6274** - MCP Inspector UI
   - **6277** - MCP Inspector Proxy

3. **Check the Ports panel shows the process** - If a port shows "No running process", the Inspector isn't running or crashed. Check the Inspector terminal for errors.

4. **Alternative: Use inspector from your host** - If you have Node.js on your Windows/Mac host:
   ```bash
   # On your host (not in container)
   npx @modelcontextprotocol/inspector http://localhost:8000/mcp/sse
   ```
   This avoids the container port forwarding complexity entirely.

### MCP Inspector Won't Connect

**Problem:** Inspector shows connection error

**Solutions:**
- Verify the API server is running: `curl http://localhost:8000/health`
- Check the MCP endpoint: `curl -N http://localhost:8000/mcp/sse`
- Ensure no firewall blocking port 8000
- Try the full URL with protocol: `http://localhost:8000/mcp/sse`

### Tools Return Errors

**Problem:** API returns error messages

**Solutions:**
- Check Ironic connectivity in environment variables
- Verify `.env` file or `IRONIC_AIO_*` variables are set
- Review API logs in the terminal running uvicorn
- Check Ironic API is accessible: `curl http://<ironic-url>:6385/v1/nodes`

### State Transitions Stuck

**Problem:** Server stuck in intermediate state

**Solutions:**
- Check Ironic logs for details
- Use Ironic API directly to inspect node: `openstack baremetal node show <uuid>`
- Some states require manual intervention in Ironic
- Network or BMC connectivity issues may block transitions

## Integration with Claude Desktop

To use these tools directly in Claude Desktop conversations:

1. Edit Claude Desktop config:
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

2. Add your MCP server:
   ```json
   {
     "mcpServers": {
       "ironic-aio": {
         "url": "http://localhost:8000/mcp/sse"
       }
     }
   }
   ```

3. Restart Claude Desktop

4. In conversations, ask Claude to use the Ironic tools:
   - "List all available servers"
   - "Enroll a new server with BMC at 192.168.1.100"
   - "What's the status of server abc123?"

## API Comparison: REST vs MCP

Both interfaces provide identical functionality:

| Operation | REST Endpoint | MCP Tool |
|-----------|--------------|----------|
| Health check | `GET /health` | `check_health` |
| List servers | `GET /servers` | `list_servers` |
| Get server | `GET /servers/{id}` | `get_server` |
| Enroll | `POST /enroll` | `enroll_server` |
| Enrollment status | `GET /enroll/{id}/status` | `get_enrollment_status` |
| Provide | `POST /enroll/{id}/provide` | `provide_server` |
| Provision | `POST /provision` | `provision_server` |
| Provision status | `GET /provision/{id}/status` | `get_provision_status` |
| Unprovision | `POST /unprovision` | `unprovision_server` |
| Unprovision status | `GET /unprovision/{id}/status` | `get_unprovision_status` |

Benefits of MCP:
- AI assistants can discover and use tools automatically
- Natural language interface via Claude or other LLMs
- Type-safe parameter validation
- Self-documenting tool descriptions

Benefits of REST:
- Standard HTTP clients and tooling
- OpenAPI documentation at `/docs`
- Easier integration with existing systems
- Direct browser access

## Next Steps

- Review the [OpenAPI documentation](http://localhost:8000/docs) for REST API details
- Check the `designs/` directory for implementation specifications
- Read `README.md` for development setup and testing
- See `AGENTS.md` for contribution guidelines
