# Deployment

## Run as a service (systemd)

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

## Docker

### Using Docker Compose (recommended)

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

### Using Docker directly

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

## CI/CD - automatic Docker image publishing

The GitHub Actions workflow `.github/workflows/docker-publish.yml` publishes the Docker image to
**GitHub Container Registry** (`ghcr.io`) on each push to `main`/`master` or tag `v*.*.*`.
CI and versioning run on Gitea Actions (`.gitea/workflows/` (CI also runs on GitHub)).
Every push to `main` creates a `vX.Y.Z` tag and release on both Gitea (`version.yml`, after the version bump) and GitHub (`release` job in `ci.yml`).

### Using published images

```bash
docker pull ghcr.io/dasemu/maskarr:latest
```
