# Keyla MCP

MCP server for [Keila](https://keila.io/) email campaign API.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install .
```

## Configuration

```bash
export KEILA_URL="https://your-keila-instance.com"
export KEILA_API_KEY="your-api-key"
```

## Usage

### Stdio (default, for MCP clients)

```bash
python src/mcp_server.py
```

### HTTP (for testing)

```bash
python src/mcp_server.py --http
```

## Tools

### `list_campaigns`

List all email campaigns with optional filtering.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `status` | string | No | Filter by: draft/scheduled/sent/archived/paused |
| `q` | string | No | Search by subject (case-insensitive substring) |

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
```
