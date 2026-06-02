# **Keila MCP**

  

[![PyPI](https://img.shields.io/pypi/v/keila-mcp?v=1)](https://pypi.org/project/keila-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/keila-mcp?v=1)](https://pypi.org/project/keila-mcp/)
[![License](https://img.shields.io/github/license/punkyard/keila-mcp)](https://github.com/punkyard/keila-mcp/blob/main/LICENSE)
[![Stars](https://img.shields.io/github/stars/punkyard/keila-mcp)](https://github.com/punkyard/keila-mcp/stargazers)
[![Downloads](https://img.shields.io/pypi/dm/keila-mcp)](https://pypi.org/project/keila-mcp/)

  

MCP server for [Keila](https://github.com/pentacent/keila) — gives any MCP-compatible AI assistant full control over your Keila email campaigns, contacts, segments and forms.

  

> [!NOTE]
> **Migrating from an earlier clone?** The source directory was renamed from `repo/` to `keila-mcp/`. Update any paths in your MCP client config accordingly.

  

---
 
  
 
## **Two ways to use keila-mcp**

  

| | **Option A — `uvx`** ✅ recommended | **Option B — Local install** |
|---|---|---|
| **What it does** | Downloads and runs keila-mcp automatically from PyPI | You clone the repo and manage the install yourself |
| **Requires** | [`uv`](https://docs.astral.sh/uv/) | Python 3.10+, git |
| **Updates** | Automatic — always runs the latest version | Manual — `git pull` + `pip install .` |
| **Best for** | Most users | Offline use, development, contributors |

  

---

  

## **Requirements**

- A running [Keila](https://www.keila.io/docs) instance — [self-host with Docker](https://www.keila.io/docs/self-hosting) or use [Keila Cloud](https://app.keila.io)
- A Keila API key — Settings → API Keys → Create

  

---

  

## **Option A — uvx (recommended)**

> [!IMPORTANT]
> You need [`uv`](https://docs.astral.sh/uv/) installed first. If you don't have it:
> ```bash
> # macOS / Linux
> curl -LsSf https://astral.sh/uv/install.sh | sh
> # Windows
> powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
> ```
> Then restart your terminal.

No cloning, no virtualenv, no `pip install`. Just add the config to your MCP client — `uvx` downloads and caches keila-mcp automatically on first run.

Skip straight to [**Client Configuration**](#client-configuration) and use the **Option A** config for your client.

  

---

  

## **Option B — Local install**

  

Use this for offline access, to modify the code, or to contribute.

- Python 3.10+, git
 
  
 
### macOS / Linux

  

```bash
git clone https://github.com/punkyard/keila-mcp.git keila-mcp
cd keila-mcp
python -m venv .venv
source .venv/bin/activate
pip install .
pwd
```

Copy the path printed by `pwd` — you will need it in the **Option B** configs below.

### Windows

  

```bash
git clone https://github.com/punkyard/keila-mcp.git keila-mcp
cd keila-mcp
python -m venv .venv
.venv\Scripts\activate
pip install .
cd
```

Copy the path printed by `cd` — you will need it in the **Option B** configs below.

  

---
 
  
 
## **Client Configuration**

  


Set these environment variables in your MCP client config:

| Variable | Value |
|---|---|
| `KEILA_URL` | Your Keila instance URL, e.g. `https://keila.mydomain.com` |
| `KEILA_API_KEY` | Your Keila API key — Settings → API Keys → Create |
| `KEILA_MCP_HTTP_PORT` | *(optional)* HTTP port for the MCP server. Default: `3001` |

  

![Keila API Keys](https://raw.githubusercontent.com/punkyard/keila-mcp/main/docs/img/keila-create-api-key.png)

  

Each client below shows **Option A (uvx)** and **Option B (local install)** — pick yours.

  

> [!IMPORTANT]
> **Option B users:** replace `/path/to/keila-mcp` with the path printed by `pwd` (or `cd` on Windows) from the install step above.
 
  
 
### **Claude Desktop**
 
  
 
**File** (macOS): `~/Library/Application Support/Claude/claude_desktop_config.json`  
**File** (Windows): `%APPDATA%\Claude\claude_desktop_config.json`

**Option A — uvx:**
```json
{
  "mcpServers": {
    "keila": {
      "command": "uvx",
      "args": ["keila-mcp"],
      "env": {
        "KEILA_URL": "https://your-keila-instance.com",
        "KEILA_API_KEY": "your-api-key"
      }
    }
  }
}
```

**Option B — Local install:**
```json
{
  "mcpServers": {
    "keila": {
      "command": "/path/to/keila-mcp/.venv/bin/python",
      "args": ["-m", "keila_mcp.mcp_server"],
      "env": {
        "KEILA_URL": "https://your-keila-instance.com",
        "KEILA_API_KEY": "your-api-key"
      }
    }
  }
}
```

Fully quit and relaunch Claude Desktop after saving.
 
  
 
### **Claude Code**
 
  
 
**Option A — uvx:**
```bash
claude mcp add-json keila '{
  "type": "stdio",
  "command": "uvx",
  "args": ["keila-mcp"],
  "env": {
    "KEILA_URL": "https://your-keila-instance.com",
    "KEILA_API_KEY": "your-api-key"
  }
}'
```

**Option B — Local install:**
```bash
claude mcp add-json keila '{
  "type": "stdio",
  "command": "/path/to/keila-mcp/.venv/bin/python",
  "args": ["-m", "keila_mcp.mcp_server"],
  "env": {
    "KEILA_URL": "https://your-keila-instance.com",
    "KEILA_API_KEY": "your-api-key"
  }
}'
```

Add `--scope global` to make it available in all projects.
 
  
 
### **Cursor · Cline / Roo Code · Windsurf · OpenClaw**
 
  
 
- **Cursor**: `.cursor/mcp.json` in your project, or `~/.cursor/mcp.json` for global
- **Cline / Roo Code**: MCP Servers config via the sidebar
- **Windsurf**: `~/.codeium/windsurf/mcp_config.json`
- **OpenClaw**: `~/.openclaw/mcp.json`

**Option A — uvx:**
```json
{
  "mcpServers": {
    "keila": {
      "command": "uvx",
      "args": ["keila-mcp"],
      "env": {
        "KEILA_URL": "https://your-keila-instance.com",
        "KEILA_API_KEY": "your-api-key"
      }
    }
  }
}
```

**Option B — Local install:**
```json
{
  "mcpServers": {
    "keila": {
      "command": "/path/to/keila-mcp/.venv/bin/python",
      "args": ["-m", "keila_mcp.mcp_server"],
      "env": {
        "KEILA_URL": "https://your-keila-instance.com",
        "KEILA_API_KEY": "your-api-key"
      }
    }
  }
}
```

  

### **VS Code (GitHub Copilot Agent Mode)**
 
  
 
Create `.vscode/mcp.json` in your project:

**Option A — uvx:**
```json
{
  "servers": {
    "keila": {
      "command": "uvx",
      "args": ["keila-mcp"],
      "env": {
        "KEILA_URL": "https://your-keila-instance.com",
        "KEILA_API_KEY": "${input:keilaApiKey}"
      }
    }
  },
  "inputs": [
    {
      "id": "keilaApiKey",
      "type": "promptString",
      "description": "Keila API Key",
      "password": true
    }
  ]
}
```

**Option B — Local install:**
```json
{
  "servers": {
    "keila": {
      "command": "/path/to/keila-mcp/.venv/bin/python",
      "args": ["-m", "keila_mcp.mcp_server"],
      "env": {
        "KEILA_URL": "https://your-keila-instance.com",
        "KEILA_API_KEY": "${input:keilaApiKey}"
      }
    }
  },
  "inputs": [
    {
      "id": "keilaApiKey",
      "type": "promptString",
      "description": "Keila API Key",
      "password": true
    }
  ]
}
```

Requires Copilot Chat in Agent mode. VS Code will prompt for the API key on first use.
 
  
 
### **Zed**
 
  
 
In `~/.config/zed/settings.json` (global) or `.zed/settings.json` (project):

**Option A — uvx:**
```json
{
  "context_servers": {
    "keila": {
      "command": {
        "path": "uvx",
        "args": ["keila-mcp"],
        "env": {
          "KEILA_URL": "https://your-keila-instance.com",
          "KEILA_API_KEY": "your-api-key"
        }
      }
    }
  }
}
```

**Option B — Local install:**
```json
{
  "context_servers": {
    "keila": {
      "command": {
        "path": "/path/to/keila-mcp/.venv/bin/python",
        "args": ["-m", "keila_mcp.mcp_server"],
        "env": {
          "KEILA_URL": "https://your-keila-instance.com",
          "KEILA_API_KEY": "your-api-key"
        }
      }
    }
  }
}
```
 
  
 
### **OpenCode**
 
  
 
In `~/.config/opencode/opencode.json` (global) or `opencode.json` (project):

**Option A — uvx:**
```json
{
  "mcp": {
    "keila": {
      "type": "local",
      "command": ["uvx", "keila-mcp"],
      "env": {
        "KEILA_URL": "https://your-keila-instance.com",
        "KEILA_API_KEY": "your-api-key"
      }
    }
  }
}
```

**Option B — Local install:**
```json
{
  "mcp": {
    "keila": {
      "type": "local",
      "command": ["/path/to/keila-mcp/.venv/bin/python", "-m", "keila_mcp.mcp_server"],
      "env": {
        "KEILA_URL": "https://your-keila-instance.com",
        "KEILA_API_KEY": "your-api-key"
      }
    }
  }
}
```
 
  
 
### **Pi Agent**
 
  
 
In `~/.pi/agent/mcp.json`:

**Option A — uvx:**
```json
{
  "keila": {
    "command": "uvx",
    "args": ["keila-mcp"],
    "env": {
      "KEILA_URL": "https://your-keila-instance.com",
      "KEILA_API_KEY": "your-api-key"
    },
    "lifecycle": "on-demand"
  }
}
```

**Option B — Local install:**
```json
{
  "keila": {
    "command": "/path/to/keila-mcp/.venv/bin/python",
    "args": ["-m", "keila_mcp.mcp_server"],
    "env": {
      "KEILA_URL": "https://your-keila-instance.com",
      "KEILA_API_KEY": "your-api-key"
    },
    "lifecycle": "on-demand"
  }
}
```
 
  
 
### **Hermes**
 
  
 
In `~/.hermes/config.yaml`:

**Option A — uvx:**
```yaml
mcp_servers:
  keila:
    command: uvx
    args:
      - keila-mcp
    env:
      KEILA_URL: https://your-keila-instance.com
      KEILA_API_KEY: your-api-key
```

**Option B — Local install:**
```yaml
mcp_servers:
  keila:
    command: /path/to/keila-mcp/.venv/bin/python
    args:
      - -m
      - keila_mcp.mcp_server
    env:
      KEILA_URL: https://your-keila-instance.com
      KEILA_API_KEY: your-api-key
```
 
  
 
### **OpenAI Codex CLI**
 
  
 
**File**: `~/.codex/config.toml` (global) or `.codex/config.toml` (project):

**Option A — uvx:**
```toml
[mcp_servers.keila]
command = "uvx"
args = ["keila-mcp"]

[mcp_servers.keila.env]
KEILA_URL = "https://your-keila-instance.com"
KEILA_API_KEY = "your-api-key"
```

**Option B — Local install:**
```toml
[mcp_servers.keila]
command = "/path/to/keila-mcp/.venv/bin/python"
args = ["-m", "keila_mcp.mcp_server"]

[mcp_servers.keila.env]
KEILA_URL = "https://your-keila-instance.com"
KEILA_API_KEY = "your-api-key"
```

  

---
 
  
 
## **Running manually (for testing)**

```bash
# Option A — uvx
uvx keila-mcp

# Option B — local install, stdio mode (default)
python -m keila_mcp.mcp_server

# Option B — local install, HTTP mode
python -m keila_mcp.mcp_server --http
# optional: export KEILA_MCP_HTTP_PORT=8325
```

  

---
 
  
 
## **Tools**
 
  
 
| Tool | Description |
|------|-------------|
| `list_campaigns`       | List all campaigns with optional status/search filter |
| `create_campaign`      | Create a new campaign |
| `get_campaign`         | Get a campaign by ID |
| `update_campaign`      | Update an existing campaign |
| `delete_campaign`      | Delete a campaign |
| `send_campaign`        | Send a campaign immediately |
| `schedule_campaign`    | Schedule a campaign for later delivery |
| `create_contact`       | Create a new contact |
| `get_contact`          | Get a contact by ID |
| `update_contact`       | Update a contact |
| `delete_contact`       | Delete a contact |
| `list_contacts`        | List contacts with optional filtering |
| `update_contact_data`  | Merge custom data fields on a contact |
| `replace_contact_data` | Replace all custom data fields on a contact |
| `list_senders`         | List all senders |
| `create_segment`       | Create a new segment |
| `list_segments`        | List all segments |
| `get_segment`          | Get a segment by ID |
| `update_segment`       | Update a segment |
| `delete_segment`       | Delete a segment |
| `list_forms`           | List all forms |
| `get_form`             | Get a form by ID |
| `create_form`          | Create a new signup form |
| `update_form`          | Update a form |
| `delete_form`          | Delete a form |
| `submit_form`          | Submit a signup form on behalf of a contact |
 
  
 
### **Campaigns**
 
  
 
#### `list_campaigns`

List all email campaigns with optional filtering.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `status` | string | No | Filter by: draft/scheduled/sent/archived/paused |
| `q` | string | No | Search by subject (case-insensitive substring) |
 
  
 
#### `create_campaign`

Create a new email campaign.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `subject` | string | Yes | Campaign subject line |
| `body_type` | string | Yes | Body type: markdown/text/block/mjml |
| `text_body` | string | No | Plain text body |
| `preview_text` | string | No | Preview text for inbox |
| `sender_id` | string | No | Sender identity ID |
| `segment_id` | string | No | Target segment ID |
| `data` | object | No | Liquid template variables |
| `do_not_track` | boolean | No | Disable open/click tracking |
 
  
 
#### `get_campaign`

Get a single campaign by ID.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Campaign ID |
 
  
 
#### `update_campaign`

Update an existing campaign.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Campaign ID |
| `subject` | string | No | New subject line |
| `preview_text` | string | No | New preview text |
 
  
 
#### `delete_campaign`

Delete a campaign.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Campaign ID |
 
  
 
#### `send_campaign`

Send a campaign immediately.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Campaign ID |
| `sender_id` | string | No | Override sender identity |
 
  
 
#### `schedule_campaign`

Schedule a campaign for later delivery.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Campaign ID |
| `scheduled_for` | string | Yes | ISO 8601 datetime (e.g. 2026-06-01T09:00:00Z) |
 
  
 
### **Contacts**
 
  
 
#### `create_contact`

Create a new contact.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `email` | string | Yes | Email address |
| `first_name` | string | No | First name |
| `last_name` | string | No | Last name |
| `external_id` | string | No | External system ID |
| `status` | string | No | Status: active/inactive/bouncing/blocked/spam |
| `data` | object | No | Custom fields |
 
  
 
#### `get_contact`

Get a contact by ID, email, or external ID.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Contact identifier |
| `id_type` | string | No | Lookup type: id (default)/email/external_id |
 
  
 
#### `update_contact`

Update an existing contact.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Contact identifier |
| `email` | string | No | New email |
| `first_name` | string | No | New first name |
| `last_name` | string | No | New last name |
| `external_id` | string | No | New external ID |
| `data` | object | No | New custom fields |
| `id_type` | string | No | Lookup type: id (default)/email/external_id |
 
  
 
#### `delete_contact`

Delete a contact.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Contact identifier |
| `id_type` | string | No | Lookup type: id (default)/email/external_id |
 
  
 
#### `list_contacts`

List contacts with pagination and optional search.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `page` | integer | No | Page number (default: 0) |
| `page_size` | integer | No | Results per page (default: 50) |
| `q` | string | No | Search query |
 
  
 
### **Senders**
 
  
 
#### `list_senders`

List all sender identities.

No parameters.
 
  
 
### **Contact Data**

  
 
Custom data is a free-form JSON object attached to each contact. Use it to store any extra fields (e.g. `plan`, `score`, `tags`). Fields can be used as merge tags in campaigns via `{{ contact.data.my_field }}` and as segment filters. See [Keila — Segments and Custom Data](https://www.keila.io/segments-and-data/) and [Contacts API docs](https://www.keila.io/docs/contacts/).
 
  
 
#### `update_contact_data`
 
Merge new key/value pairs into a contact's custom data field. Keys not present in `data` are preserved.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Contact ID (or email/external_id when `id_type` set) |
| `data` | object | Yes | Key/value pairs to merge |
| `id_type` | string | No | `id` (default), `email`, or `external_id` |
 
  
 
#### `replace_contact_data`

Replace a contact's entire custom data field with the provided dict.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Contact ID (or email/external_id when `id_type` set) |
| `data` | object | Yes | New data dict (replaces existing) |
| `id_type` | string | No | `id` (default), `email`, or `external_id` |
 
  
 
### **Segments**
 
  
 
#### `create_segment`

Create a contact segment with a filter.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Segment name |
| `filter` | object | Yes | Keila filter expression |
 
  
 
#### `list_segments`

List all segments.

No parameters.
 
  
 
#### `get_segment`

Get a segment by ID.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Segment ID |
 
  
 
#### `delete_segment`

Delete a segment.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Segment ID |
 
  
 
#### `update_segment`

Update a segment's name and/or filter. At least one of `name` or `filter` must be provided.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Segment ID |
| `name` | string | No | New segment name |
| `filter` | object | No | New filter expression |
 
  
 
### **Forms**
 
  
 
#### `list_forms`

List all subscription forms.

No parameters.
 
  
 
#### `get_form`

Get a form by ID.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Form ID |
 
  
 
#### `create_form`

Create a new subscription form.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Form name |
| `sender_id` | string | No | Sender identity ID |
| `fields` | array | No | Form field definitions |
| `settings` | object | No | Form settings (double opt-in, redirect URLs, etc.) |
 
  
 
#### `delete_form`

Delete a form.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Form ID |
 
  
 
#### `update_form`

Update an existing signup form.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Form ID |
| `name` | string | No | New form name |
| `sender_id` | string | No | New sender identity ID |
| `fields` | array | No | Replacement field definitions |
| `settings` | object | No | Updated form settings |
 
  
 
#### `submit_form`

Submit a signup form on behalf of a contact. Returns the created/updated contact on success, or `{"data": {"double_opt_in_required": true}}` if the form has double opt-in enabled.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `form_id` | string | Yes | Form ID |
| `email` | string | Yes | Contact email address |
| `first_name` | string | No | Contact first name |
| `last_name` | string | No | Contact last name |
| `external_id` | string | No | External identifier |
| `status` | string | No | Contact status (e.g. `active`) |
| `data` | object | No | Custom data key/value pairs |

  

---

  

## **Development**

  

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

  

<div align="center">

© 2026 — [LICENSE AGPL-3.0](https://github.com/punkyard/keila-mcp/blob/main/LICENSE)

made with ⏳ by [punkyard](https://github.com/punkyard)

</div>
