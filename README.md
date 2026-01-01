# Maskarr - Tracker Proxy for *arr Apps

An HTTP proxy server that allows modifying User-Agent and headers to access private trackers from Prowlarr, Jackett, or other *arr stack applications.

## Features

- **Multi-tracker**: Configure multiple trackers from a web interface
- **Full HTTP methods**: Supports GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS
- **Web UI in -arr style**: Modern UI matching Radarr/Sonarr design
- **Persistent configuration**: Saves configuration in JSON
- **Thread-safe**: Safe configuration handling across multiple requests
- **No crashes**: Robust exception and error handling
- **Logging**: Detailed request logging (optional)

## Requirements

```bash
pip install requests
```

## Installation

1. Clone or download the repository:
```bash
git clone <repo-url>
cd maskarr
```

2. Install dependencies:
```bash
pip install requests
```

3. Run the server:
```bash
python3 maskarr.py
```

Or make it executable:
```bash
chmod +x maskarr.py
./maskarr.py
```

## Usage

### 1. Start the server

```bash
python3 maskarr.py
```

You'll see something like:
```
🎭 Maskarr - Tracker Proxy Server
==================================================
🌐 Server running on http://0.0.0.0:8888
📊 Web UI: http://localhost:8888
📝 Config file: /path/to/maskarr_config.json
==================================================
Press Ctrl+C to stop
```

### 2. Configure a tracker

1. Open your browser at `http://localhost:8888`
2. Fill in the form:
   - **Tracker ID**: Unique identifier (e.g., `divteam`)
   - **Domain**: Tracker domain (e.g., `divteam.com`)
   - **User-Agent**: Browser user-agent you want to use
   - **Additional headers**: JSON with extra headers (optional)
   - **Timeout**: Timeout in seconds (default: 30)
   - **Verify SSL**: Verify SSL certificate (recommended: enabled)

3. Click **Save Tracker**

### 3. Use the proxy in Prowlarr/Jackett

Each configured tracker will have a unique proxy URL:

```
http://localhost:8888/proxy/{tracker_id}/
```

For example, if you configured `divteam`:
```
http://localhost:8888/proxy/divteam/
```

In Prowlarr:
1. Go to Settings → Indexers
2. Add the indexer manually
3. In "Base URL", use: `http://localhost:8888/proxy/divteam`
4. Configure the rest of the parameters normally

## Configuration Examples

### DivTeam

```json
{
  "id": "divteam",
  "domain": "divteam.com",
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
    "divteam": {
      "domain": "divteam.com",
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
  "id": "divteam",
  "domain": "divteam.com",
  "user_agent": "Mozilla/5.0...",
  "headers": {},
  "timeout": 30,
  "verify_ssl": true
}
```

### DELETE /api/trackers/{tracker_id}
Delete a tracker.

## Advanced Configuration

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

### Run as a service (systemd)

Create `/etc/systemd/system/maskarr.service`:

```ini
[Unit]
Description=Maskarr Tracker Proxy
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/maskarr
ExecStart=/usr/bin/python3 /path/to/maskarr/maskarr.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable maskarr
sudo systemctl start maskarr
sudo systemctl status maskarr
```

### Docker

#### Using Docker Compose (recommended)

```bash
# Download docker-compose.yml
wget https://raw.githubusercontent.com/yourusername/maskarr/main/docker-compose.yml

# Create config directory
mkdir -p config

# Start the service
docker-compose up -d

# View logs
docker-compose logs -f
```

#### Using Docker directly

From GitHub Container Registry:
```bash
docker run -d \
  --name maskarr \
  -p 8888:8888 \
  -v $(pwd)/config:/app/config \
  --restart unless-stopped \
  ghcr.io/yourusername/maskarr:latest
```

Or build the image locally:
```bash
# Clone the repository
git clone https://github.com/yourusername/maskarr.git
cd maskarr

# Build the image
docker build -t maskarr .

# Run the container
docker run -d \
  --name maskarr \
  -p 8888:8888 \
  -v $(pwd)/config:/app/config \
  --restart unless-stopped \
  maskarr:latest
```

#### Multi-architecture

Images support multiple architectures:
- `linux/amd64` (x86_64)
- `linux/arm64` (ARM 64-bit, Raspberry Pi 4, Apple Silicon)
- `linux/arm/v7` (ARM 32-bit, Raspberry Pi 3)

## CI/CD - Automatic Docker Image Publishing

The project includes workflows for **GitHub Actions** and **Gitea Actions** that automatically publish Docker images.

### Supported Registries

Each push to `main`/`master` or tag `v*.*.*` will publish to:

1. **GitHub Container Registry** (`ghcr.io`) - Primary and most reliable ⭐
2. **Gitea Container Registry** (your private instance)

### Quick Setup

**📖 [Read the complete setup guide: SETUP_CI.md](SETUP_CI.md)**

The guide includes:
- Step-by-step configuration for GitHub and Gitea
- How to create access tokens
- How to configure secrets
- Common troubleshooting
- Usage examples

### Quick Start

#### GitHub:
1. Upload code to GitHub
2. Push or create a tag → Image builds automatically
3. Make the package public to allow `docker pull` without authentication

#### Gitea:
1. Enable Actions and Container Registry on your instance
2. Configure the secret `PACKAGE_TOKEN` with `write:package` permissions
3. Push or create a tag → Image builds automatically

### Using Published Images

```bash
# From GitHub Container Registry (recommended)
docker pull ghcr.io/your-username/maskarr:latest

# From Gitea
docker pull gitea.yourdomain.com/your-username/maskarr:latest
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

### SSL Certificate Verify Failed
If the tracker uses a self-signed certificate, disable "Verify SSL" in the tracker configuration.

### Request timeout
Increase the "Timeout" value in the tracker configuration.

## Security

- **Don't expose the server to the internet**: It's designed for local use
- **Use HTTPS if exposing**: Consider a reverse proxy (nginx, Caddy)
- **Protect your cookies**: Cookies are passed through the proxy
- **Check the logs**: Enable `log_requests` for debugging

## Roadmap

- [ ] Basic authentication for the UI
- [ ] Proxy chain support
- [ ] Usage statistics per tracker
- [ ] Rate limiting per tracker
- [ ] Configuration import/export
- [ ] User-Agent rotation support

## License

GNU GPL V3.0

## Contributing

Pull requests welcome. For major changes, please open an issue first.

## Author

Created to facilitate the use of private trackers with *arr applications.
