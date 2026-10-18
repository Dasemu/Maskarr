# Usage

## 1. Start the server

```bash
python3 maskarr.py
```

You'll see something like:
```
Maskarr - Tracker Proxy Server
==================================================
Server running on http://0.0.0.0:8888
Web UI: http://localhost:8888
Config file: /path/to/maskarr_config.json
==================================================
Press Ctrl+C to stop
```

## 2. Configure a tracker

1. Open your browser at `http://localhost:8888`
2. Fill in the form:
   - **Tracker ID**: Unique identifier (e.g., `mytracker`)
   - **Domain**: Tracker domain (e.g., `mytracker.com`)
   - **User-Agent**: Browser user-agent you want to use
   - **Additional headers**: JSON with extra headers (optional)
   - **Timeout**: Timeout in seconds (default: 30)
   - **Verify SSL**: Verify SSL certificate (recommended: enabled)

3. Click **Save Tracker**

## 3. Use the proxy in Prowlarr/Jackett

Each configured tracker will have a unique proxy URL:

```
http://localhost:8888/proxy/{tracker_id}/
```

For example, if you configured `mytracker`:
```
http://localhost:8888/proxy/mytracker/
```

You will have to create a custom definition for the indexer, copying one which has been
created already, and modifying its `base_url` to:
`http://localhost:8888/proxy/mytracker`

## Configuration examples

### Tracker without custom headers

```json
{
  "id": "mytracker",
  "domain": "mytracker.com",
  "user_agent": "Mozilla/5.0 (X11; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0",
  "headers": {},
  "timeout": 30,
  "verify_ssl": true
}
```

### Tracker with custom headers

```json
{
  "id": "mytracker",
  "domain": "tracker.example.com",
  "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
  "headers": {
    "Referer": "https://tracker.example.com",
    "X-Requested-With": "XMLHttpRequest"
  },
  "timeout": 45,
  "verify_ssl": true
}
```

## REST API

### GET /api/trackers
Get all configured trackers.

**Response:**
```json
{
  "trackers": {
    "mytracker": {
      "domain": "mytracker.com",
      "user_agent": "Mozilla/5.0...",
      "headers": {},
      "timeout": 30,
      "verify_ssl": true
    }
  }
}
```

### POST /api/trackers
Add or update a tracker.

**Body:**
```json
{
  "id": "mytracker",
  "domain": "mytracker.com",
  "user_agent": "Mozilla/5.0...",
  "headers": {},
  "timeout": 30,
  "verify_ssl": true
}
```

### DELETE /api/trackers/{tracker_id}
Delete a tracker.

## Advanced configuration

### Change the port

Edit `maskarr_config.json`:
```json
{
  "port": 9999,
  "log_requests": true,
  "trackers": {}
}
```

### Disable request logging

In `maskarr_config.json`:
```json
{
  "log_requests": false
}
```

## Troubleshooting

### Port in use
```
Error: Port 8888 might be already in use
```
Change the port in `maskarr_config.json` or close the application using port 8888.

### Permission denied
```
Error: Permission denied to bind to port 8888
```
Use a port > 1024 or run with privileges (not recommended).

### SSL certificate verify failed
If the tracker uses a self-signed certificate, disable "Verify SSL" in the tracker configuration.

### Request timeout
Increase the "Timeout" value in the tracker configuration.

## Security

- **Don't expose the server to the internet**: it's designed for local use.
- **Use HTTPS if exposing**: consider a reverse proxy (nginx, Caddy).
- **Protect your cookies**: cookies are passed through the proxy.
- **Check the logs**: enable `log_requests` for debugging.
