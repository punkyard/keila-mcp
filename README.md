# Keyla MCP

MCP server for [Keila](https://keila.io/) email campaign API.
https://github.com/punkyard/keila-mcp

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
export KEYLA_MCP_HTTP_PORT=8325  # optional, default stdio
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

### Campaigns

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

### Contacts

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

### Senders

#### `list_senders`

List all sender identities.

No parameters.

### Segments

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

### Forms

#### `list_forms`

List all subscription forms.

No parameters.

#### `get_form`

Get a form by ID.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Form ID |

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
```
