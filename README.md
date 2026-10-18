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

## Quick start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python3 maskarr.py
```

Then open `http://localhost:8888` to configure your first tracker.

## Documentation

- [Usage, configuration and REST API](docs/usage.md)
- [Deployment (systemd, Docker, CI/CD)](docs/deployment.md)

## License

GNU GPL v3.0

## Contributing

Pull requests welcome. For major changes, please open an issue first.
