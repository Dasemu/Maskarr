#!/usr/bin/env python3
"""
Maskarr - Tracker Proxy for *arr apps
A proxy server to modify User-Agent and other headers for private trackers
"""

import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import requests
from datetime import datetime
import threading

CONFIG_FILE = os.getenv("CONFIG_PATH", "maskarr_config.json")
DEFAULT_CONFIG = {
    "trackers": {},
    "port": 8888,
    "log_requests": True
}

class ConfigManager:
    """Thread-safe configuration manager"""
    def __init__(self):
        self.lock = threading.Lock()
        self.config = self.load_config()

    def load_config(self):
        """Load configuration from file"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}, using defaults")
                return DEFAULT_CONFIG.copy()
        return DEFAULT_CONFIG.copy()

    def save_config(self):
        """Save configuration to file"""
        with self.lock:
            try:
                with open(CONFIG_FILE, 'w') as f:
                    json.dump(self.config, f, indent=2)
                return True
            except Exception as e:
                print(f"Error saving config: {e}")
                return False

    def get_tracker(self, tracker_id):
        """Get tracker configuration"""
        with self.lock:
            return self.config.get("trackers", {}).get(tracker_id)

    def add_tracker(self, tracker_id, config):
        """Add or update tracker configuration"""
        with self.lock:
            if "trackers" not in self.config:
                self.config["trackers"] = {}
            self.config["trackers"][tracker_id] = config
        return self.save_config()

    def delete_tracker(self, tracker_id):
        """Delete tracker configuration"""
        with self.lock:
            if tracker_id in self.config.get("trackers", {}):
                del self.config["trackers"][tracker_id]
        return self.save_config()

    def get_all_trackers(self):
        """Get all tracker configurations"""
        with self.lock:
            return self.config.get("trackers", {}).copy()


class MaskarrHandler(BaseHTTPRequestHandler):
    """HTTP request handler with proxy functionality"""

    config_manager = None  # Will be set by the server

    def log_message(self, format, *args):
        """Custom logging"""
        if self.config_manager.config.get("log_requests", True):
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] {self.address_string()} - {format%args}")

    def send_json_response(self, data, status=200):
        """Send JSON response"""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def send_html_response(self, html, status=200):
        """Send HTML response"""
        self.send_response(status)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode())

    def handle_proxy_request(self, tracker_id):
        """Handle proxy request to tracker"""
        tracker_config = self.config_manager.get_tracker(tracker_id)

        if not tracker_config:
            self.send_error(404, f"Tracker '{tracker_id}' not configured")
            return

        try:
            # Build target URL
            target_domain = tracker_config.get("domain", "")
            if not target_domain:
                self.send_error(500, "Tracker domain not configured")
                return

            # Remove the tracker prefix from path
            path = self.path.replace(f"/proxy/{tracker_id}", "", 1)
            if not path:
                path = "/"

            target_url = f"https://{target_domain}{path}"

            # Prepare headers
            headers = {}

            # Copy custom headers from config
            custom_headers = tracker_config.get("headers", {})
            for key, value in custom_headers.items():
                headers[key] = value

            # Override with specific headers
            if "user_agent" in tracker_config:
                headers["User-Agent"] = tracker_config["user_agent"]

            # Copy certain headers from original request if not in custom headers
            for header in ["Cookie", "Authorization", "Accept", "Accept-Language"]:
                if header.lower() not in [h.lower() for h in headers.keys()]:
                    value = self.headers.get(header)
                    if value:
                        headers[header] = value

            # Read body for POST/PUT/PATCH
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else None

            # Make the request
            response = requests.request(
                method=self.command,
                url=target_url,
                headers=headers,
                data=body,
                allow_redirects=False,
                timeout=tracker_config.get("timeout", 30),
                verify=tracker_config.get("verify_ssl", True)
            )

            # Send response back
            self.send_response(response.status_code)

            # Copy response headers (exclude problematic ones)
            excluded_headers = ['content-encoding', 'transfer-encoding', 'connection']
            for key, value in response.headers.items():
                if key.lower() not in excluded_headers:
                    self.send_header(key, value)

            self.end_headers()
            self.wfile.write(response.content)

        except requests.exceptions.Timeout:
            self.send_error(504, "Gateway Timeout")
        except requests.exceptions.ConnectionError as e:
            self.send_error(502, f"Bad Gateway: {str(e)}")
        except Exception as e:
            print(f"Proxy error: {e}")
            self.send_error(500, f"Proxy error: {str(e)}")

    def handle_api_request(self):
        """Handle API requests"""
        path = urlparse(self.path).path
        query = parse_qs(urlparse(self.path).query)

        if path == "/api/trackers" and self.command == "GET":
            # Get all trackers
            trackers = self.config_manager.get_all_trackers()
            self.send_json_response({"trackers": trackers})

        elif path == "/api/trackers" and self.command == "POST":
            # Add/update tracker
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length)
                data = json.loads(body.decode())

                tracker_id = data.get("id")
                if not tracker_id:
                    self.send_json_response({"error": "Tracker ID required"}, 400)
                    return

                tracker_config = {
                    "domain": data.get("domain", ""),
                    "user_agent": data.get("user_agent", ""),
                    "headers": data.get("headers", {}),
                    "timeout": data.get("timeout", 30),
                    "verify_ssl": data.get("verify_ssl", True)
                }

                if self.config_manager.add_tracker(tracker_id, tracker_config):
                    self.send_json_response({"success": True, "message": "Tracker saved"})
                else:
                    self.send_json_response({"error": "Failed to save tracker"}, 500)

            except json.JSONDecodeError:
                self.send_json_response({"error": "Invalid JSON"}, 400)
            except Exception as e:
                self.send_json_response({"error": str(e)}, 500)

        elif path.startswith("/api/trackers/") and self.command == "DELETE":
            # Delete tracker
            tracker_id = path.replace("/api/trackers/", "")
            if self.config_manager.delete_tracker(tracker_id):
                self.send_json_response({"success": True, "message": "Tracker deleted"})
            else:
                self.send_json_response({"error": "Failed to delete tracker"}, 500)

        else:
            self.send_error(404, "API endpoint not found")

    def do_GET(self):
        """Handle GET requests"""
        self._handle_request()

    def do_POST(self):
        """Handle POST requests"""
        self._handle_request()

    def do_PUT(self):
        """Handle PUT requests"""
        self._handle_request()

    def do_DELETE(self):
        """Handle DELETE requests"""
        self._handle_request()

    def do_PATCH(self):
        """Handle PATCH requests"""
        self._handle_request()

    def do_HEAD(self):
        """Handle HEAD requests"""
        self._handle_request()

    def do_OPTIONS(self):
        """Handle OPTIONS requests (CORS)"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, PATCH, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.end_headers()

    def _handle_request(self):
        """Main request router"""
        path = urlparse(self.path).path

        try:
            if path == "/" or path == "/index.html":
                self.send_html_response(get_index_html())

            elif path.startswith("/api/"):
                self.handle_api_request()

            elif path.startswith("/proxy/"):
                # Extract tracker ID
                parts = path.split("/")
                if len(parts) >= 3:
                    tracker_id = parts[2]
                    self.handle_proxy_request(tracker_id)
                else:
                    self.send_error(400, "Invalid proxy path")

            else:
                self.send_error(404, "Not Found")

        except Exception as e:
            print(f"Unhandled exception: {e}")
            import traceback
            traceback.print_exc()
            self.send_error(500, "Internal Server Error")


def get_index_html():
    """Generate the main HTML interface"""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Maskarr - Tracker Proxy</title>
    <link rel="icon" type="image/x-icon" href="https://git.dariosevilla.es/repo-avatars/902a4790cab6170ef514a5d9de8e477a581e536284d6e117b3a908aed04c7ed0">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #1e1e1e;
            color: #e0e0e0;
            line-height: 1.6;
        }

        .header {
            background: #282828;
            padding: 20px;
            border-bottom: 2px solid #ffa500;
            box-shadow: 0 2px 10px rgba(0,0,0,0.3);
            display: flex;
            align-items: center;
            gap: 15px;
        }

        .header img {
            width: 48px;
            height: 48px;
            border-radius: 8px;
        }

        .header-text {
            flex: 1;
        }

        .header h1 {
            color: #ffa500;
            font-size: 28px;
            font-weight: 600;
            margin: 0;
        }

        .header p {
            color: #b0b0b0;
            margin: 5px 0 0 0;
        }

        .container {
            max-width: 900px;
            margin: 0 auto;
            padding: 30px 20px;
        }

        .alert {
            padding: 12px 16px;
            border-radius: 4px;
            margin-bottom: 20px;
            display: none;
        }

        .alert.success {
            background: #2e7d32;
            color: white;
            border: 1px solid #4caf50;
        }

        .alert.error {
            background: #c62828;
            color: white;
            border: 1px solid #f44336;
        }

        .alert.show {
            display: block;
        }

        .tracker-card {
            background: #282828;
            border-radius: 8px;
            margin-bottom: 15px;
            border: 1px solid #383838;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            overflow: hidden;
        }

        .tracker-header {
            padding: 18px 20px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            user-select: none;
            transition: background 0.2s;
        }

        .tracker-header:hover {
            background: #2a2a2a;
        }

        .tracker-header-left {
            display: flex;
            align-items: center;
            gap: 12px;
            flex: 1;
        }

        .tracker-chevron {
            color: #ffa500;
            transition: transform 0.2s;
            font-size: 18px;
        }

        .tracker-chevron.expanded {
            transform: rotate(90deg);
        }

        .tracker-title {
            color: #ffa500;
            font-size: 16px;
            font-weight: 600;
        }

        .tracker-domain {
            color: #909090;
            font-size: 13px;
            margin-left: 15px;
        }

        .tracker-header-actions {
            display: flex;
            gap: 8px;
        }

        .tracker-body {
            display: none;
            padding: 0 20px 20px 20px;
            border-top: 1px solid #383838;
        }

        .tracker-body.expanded {
            display: block;
        }

        .proxy-url-box {
            background: #1e1e1e;
            padding: 12px;
            border-radius: 4px;
            margin: 15px 0;
            border: 1px solid #383838;
        }

        .proxy-url-label {
            color: #909090;
            font-size: 12px;
            margin-bottom: 6px;
        }

        .proxy-url {
            background: #161616;
            padding: 10px 12px;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            color: #4CAF50;
            border: 1px solid #2a2a2a;
            cursor: pointer;
            transition: background 0.2s;
            word-break: break-all;
        }

        .proxy-url:hover {
            background: #1a1a1a;
        }

        .form-group {
            margin-bottom: 18px;
        }

        label {
            display: block;
            margin-bottom: 6px;
            color: #c0c0c0;
            font-weight: 500;
            font-size: 14px;
        }

        input[type="text"],
        input[type="number"],
        textarea {
            width: 100%;
            padding: 10px 12px;
            background: #1e1e1e;
            border: 1px solid #484848;
            border-radius: 4px;
            color: #e0e0e0;
            font-size: 14px;
            transition: border-color 0.2s;
        }

        input:focus,
        textarea:focus {
            outline: none;
            border-color: #ffa500;
        }

        input.error {
            border-color: #d32f2f;
        }

        textarea {
            font-family: 'Courier New', monospace;
            min-height: 100px;
            resize: vertical;
        }

        .checkbox-group {
            display: flex;
            align-items: center;
        }

        input[type="checkbox"] {
            width: 18px;
            height: 18px;
            margin-right: 8px;
            cursor: pointer;
        }

        button {
            padding: 10px 20px;
            background: #ffa500;
            color: #1e1e1e;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-weight: 600;
            font-size: 14px;
            transition: background 0.2s;
        }

        button:hover {
            background: #ff8c00;
        }

        button.secondary {
            background: #484848;
            color: #e0e0e0;
        }

        button.secondary:hover {
            background: #585858;
        }

        button.danger {
            background: #d32f2f;
            color: white;
        }

        button.danger:hover {
            background: #b71c1c;
        }

        button.small {
            padding: 6px 12px;
            font-size: 12px;
        }

        .help-text {
            font-size: 12px;
            color: #909090;
            margin-top: 4px;
        }

        .help-text.error {
            color: #f44336;
        }

        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #707070;
        }

        .empty-state svg {
            width: 64px;
            height: 64px;
            margin-bottom: 15px;
            opacity: 0.5;
        }

        .form-actions {
            display: flex;
            gap: 10px;
            margin-top: 20px;
            padding-top: 15px;
            border-top: 1px solid #383838;
        }

        .new-tracker-hint {
            text-align: center;
            color: #909090;
            font-size: 14px;
            margin-bottom: 10px;
        }
    </style>
</head>
<body>
    <div class="header">
        <img src="https://git.dariosevilla.es/repo-avatars/902a4790cab6170ef514a5d9de8e477a581e536284d6e117b3a908aed04c7ed0" alt="Maskarr Logo">
        <div class="header-text">
            <h1>Maskarr</h1>
            <p>Tracker Proxy for *arr Applications</p>
        </div>
    </div>

    <div class="container">
        <div id="alert" class="alert"></div>
        <div id="trackersList"></div>
    </div>

    <script>
        let trackers = {};

        // Load trackers on page load
        loadTrackers();

        async function loadTrackers() {
            try {
                const response = await fetch('/api/trackers');
                const data = await response.json();
                trackers = data.trackers || {};
                renderTrackers();
            } catch (e) {
                showAlert('Failed to load trackers: ' + e.message, 'error');
            }
        }

        function renderTrackers() {
            const container = document.getElementById('trackersList');

            if (Object.keys(trackers).length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <svg fill="currentColor" viewBox="0 0 20 20">
                            <path d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z"/>
                        </svg>
                        <p>No trackers configured yet. Add your first tracker below.</p>
                    </div>
                `;
            } else {
                container.innerHTML = Object.entries(trackers).map(([id, config]) =>
                    renderTrackerCard(id, config)
                ).join('');
            }

            // Add new tracker card at the bottom
            container.innerHTML += renderNewTrackerCard();
        }

        function renderTrackerCard(id, config) {
            const proxyUrl = `${window.location.protocol}//${window.location.host}/proxy/${id}/`;
            return `
                <div class="tracker-card">
                    <div class="tracker-header" onclick="toggleTracker('${id}')">
                        <div class="tracker-header-left">
                            <span class="tracker-chevron" id="chevron-${id}">▶</span>
                            <span class="tracker-title">${escapeHtml(id)}</span>
                            <span class="tracker-domain">${escapeHtml(config.domain)}</span>
                        </div>
                        <div class="tracker-header-actions">
                            <button class="danger small" onclick="event.stopPropagation(); deleteTracker('${id}')">Delete</button>
                        </div>
                    </div>
                    <div class="tracker-body" id="body-${id}">
                        <div class="proxy-url-box">
                            <div class="proxy-url-label">Proxy URL (click to copy):</div>
                            <div class="proxy-url" onclick="copyToClipboard('${proxyUrl}')" title="Click to copy">
                                ${escapeHtml(proxyUrl)}
                            </div>
                        </div>
                        <form onsubmit="saveTracker(event, '${id}')">
                            <div class="form-group">
                                <label for="domain-${id}">Domain *</label>
                                <input type="text" id="domain-${id}" value="${escapeHtml(config.domain)}" required>
                                <div class="help-text">Target domain without protocol (https:// is assumed)</div>
                            </div>

                            <div class="form-group">
                                <label for="userAgent-${id}">User-Agent *</label>
                                <input type="text" id="userAgent-${id}" value="${escapeHtml(config.user_agent)}" required>
                                <div class="help-text">Browser user-agent string to use</div>
                            </div>

                            <div class="form-group">
                                <label for="headers-${id}">Additional Headers (JSON)</label>
                                <textarea id="headers-${id}">${escapeHtml(JSON.stringify(config.headers, null, 2))}</textarea>
                                <div class="help-text">Optional custom headers in JSON format</div>
                            </div>

                            <div class="form-group">
                                <label for="timeout-${id}">Timeout (seconds)</label>
                                <input type="number" id="timeout-${id}" value="${config.timeout || 30}" min="1" max="120">
                            </div>

                            <div class="form-group">
                                <div class="checkbox-group">
                                    <input type="checkbox" id="verifySSL-${id}" ${config.verify_ssl !== false ? 'checked' : ''}>
                                    <label for="verifySSL-${id}" style="margin-bottom: 0;">Verify SSL Certificate</label>
                                </div>
                            </div>

                            <div class="form-actions">
                                <button type="submit">Save Changes</button>
                            </div>
                        </form>
                    </div>
                </div>
            `;
        }

        function renderNewTrackerCard() {
            return `
                <div class="new-tracker-hint">➕ Add a new tracker</div>
                <div class="tracker-card">
                    <div class="tracker-header" onclick="toggleTracker('new')">
                        <div class="tracker-header-left">
                            <span class="tracker-chevron" id="chevron-new">▶</span>
                            <span class="tracker-title">New Tracker</span>
                        </div>
                    </div>
                    <div class="tracker-body" id="body-new">
                        <form onsubmit="saveTracker(event, 'new')">
                            <div class="form-group">
                                <label for="trackerId-new">Tracker ID *</label>
                                <input type="text" id="trackerId-new" placeholder="e.g., divteam" pattern="[a-z0-9_-]+" required>
                                <div class="help-text" id="help-trackerId-new">Unique identifier (lowercase letters, numbers, hyphens, underscores only)</div>
                            </div>

                            <div class="form-group">
                                <label for="domain-new">Domain *</label>
                                <input type="text" id="domain-new" placeholder="e.g., divteam.com" required>
                                <div class="help-text">Target domain without protocol (https:// is assumed)</div>
                            </div>

                            <div class="form-group">
                                <label for="userAgent-new">User-Agent *</label>
                                <input type="text" id="userAgent-new" placeholder="Mozilla/5.0 (X11; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0" required>
                                <div class="help-text">Browser user-agent string to use</div>
                            </div>

                            <div class="form-group">
                                <label for="headers-new">Additional Headers (JSON)</label>
                                <textarea id="headers-new" placeholder='{"Referer": "https://example.com"}'>{}</textarea>
                                <div class="help-text">Optional custom headers in JSON format</div>
                            </div>

                            <div class="form-group">
                                <label for="timeout-new">Timeout (seconds)</label>
                                <input type="number" id="timeout-new" value="30" min="1" max="120">
                            </div>

                            <div class="form-group">
                                <div class="checkbox-group">
                                    <input type="checkbox" id="verifySSL-new" checked>
                                    <label for="verifySSL-new" style="margin-bottom: 0;">Verify SSL Certificate</label>
                                </div>
                            </div>

                            <div class="form-actions">
                                <button type="submit">Create Tracker</button>
                                <button type="button" class="secondary" onclick="resetNewTracker()">Clear</button>
                            </div>
                        </form>
                    </div>
                </div>
            `;
        }

        function toggleTracker(id) {
            const body = document.getElementById(`body-${id}`);
            const chevron = document.getElementById(`chevron-${id}`);

            if (body.classList.contains('expanded')) {
                body.classList.remove('expanded');
                chevron.classList.remove('expanded');
            } else {
                body.classList.add('expanded');
                chevron.classList.add('expanded');
            }
        }

        async function saveTracker(event, trackerId) {
            event.preventDefault();

            let id;
            if (trackerId === 'new') {
                id = document.getElementById('trackerId-new').value.trim().toLowerCase();

                // Validate tracker ID format
                if (!/^[a-z0-9_-]+$/.test(id)) {
                    showAlert('Tracker ID must contain only lowercase letters, numbers, hyphens, and underscores', 'error');
                    document.getElementById('trackerId-new').classList.add('error');
                    document.getElementById('help-trackerId-new').classList.add('error');
                    return;
                }

                if (trackers[id]) {
                    showAlert(`Tracker "${id}" already exists. Please choose a different ID.`, 'error');
                    return;
                }
            } else {
                id = trackerId;
            }

            const domain = document.getElementById(`domain-${trackerId}`).value.trim();
            const userAgent = document.getElementById(`userAgent-${trackerId}`).value.trim();
            const headersText = document.getElementById(`headers-${trackerId}`).value.trim() || '{}';
            const timeout = parseInt(document.getElementById(`timeout-${trackerId}`).value);
            const verifySSL = document.getElementById(`verifySSL-${trackerId}`).checked;

            // Validate headers JSON
            let headers;
            try {
                headers = JSON.parse(headersText);
            } catch (e) {
                showAlert('Invalid JSON in headers field', 'error');
                return;
            }

            const data = {
                id: id,
                domain: domain,
                user_agent: userAgent,
                headers: headers,
                timeout: timeout,
                verify_ssl: verifySSL
            };

            try {
                const response = await fetch('/api/trackers', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });

                const result = await response.json();

                if (response.ok) {
                    showAlert(trackerId === 'new' ? 'Tracker created successfully!' : 'Tracker updated successfully!', 'success');
                    await loadTrackers();
                } else {
                    showAlert(result.error || 'Failed to save tracker', 'error');
                }
            } catch (e) {
                showAlert('Network error: ' + e.message, 'error');
            }
        }

        async function deleteTracker(id) {
            if (!confirm(`Delete tracker "${id}"?`)) return;

            try {
                const response = await fetch(`/api/trackers/${id}`, {method: 'DELETE'});
                const result = await response.json();

                if (response.ok) {
                    showAlert('Tracker deleted', 'success');
                    await loadTrackers();
                } else {
                    showAlert(result.error || 'Failed to delete tracker', 'error');
                }
            } catch (e) {
                showAlert('Network error: ' + e.message, 'error');
            }
        }

        function resetNewTracker() {
            document.getElementById('trackerId-new').value = '';
            document.getElementById('domain-new').value = '';
            document.getElementById('userAgent-new').value = '';
            document.getElementById('headers-new').value = '{}';
            document.getElementById('timeout-new').value = '30';
            document.getElementById('verifySSL-new').checked = true;
            document.getElementById('trackerId-new').classList.remove('error');
            document.getElementById('help-trackerId-new').classList.remove('error');
        }

        function showAlert(message, type) {
            const alert = document.getElementById('alert');
            alert.textContent = message;
            alert.className = `alert ${type} show`;

            setTimeout(() => {
                alert.classList.remove('show');
            }, 5000);
        }

        function copyToClipboard(text) {
            navigator.clipboard.writeText(text).then(() => {
                showAlert('URL copied to clipboard!', 'success');
            }).catch(() => {
                showAlert('Failed to copy URL', 'error');
            });
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Add real-time validation for tracker ID
        document.addEventListener('DOMContentLoaded', () => {
            setTimeout(() => {
                const trackerIdInput = document.getElementById('trackerId-new');
                if (trackerIdInput) {
                    trackerIdInput.addEventListener('input', (e) => {
                        const value = e.target.value;
                        const helpText = document.getElementById('help-trackerId-new');

                        // Auto-convert to lowercase
                        if (value !== value.toLowerCase()) {
                            e.target.value = value.toLowerCase();
                        }

                        if (value && !/^[a-z0-9_-]+$/.test(value)) {
                            e.target.classList.add('error');
                            helpText.classList.add('error');
                        } else {
                            e.target.classList.remove('error');
                            helpText.classList.remove('error');
                        }
                    });
                }
            }, 100);
        });
    </script>
</body>
</html>
"""


def main():
    """Main entry point"""
    config_manager = ConfigManager()
    port = config_manager.config.get("port", 8888)

    # Set config manager as class variable
    MaskarrHandler.config_manager = config_manager

    try:
        server = HTTPServer(('0.0.0.0', port), MaskarrHandler)
        print(f"🎭 Maskarr - Tracker Proxy Server")
        print(f"=" * 50)
        print(f"🌐 Server running on http://0.0.0.0:{port}")
        print(f"📊 Web UI: http://localhost:{port}")
        print(f"📝 Config file: {os.path.abspath(CONFIG_FILE)}")
        print(f"=" * 50)
        print(f"Press Ctrl+C to stop")
        print()

        server.serve_forever()

    except KeyboardInterrupt:
        print("\n\n👋 Shutting down gracefully...")
        server.shutdown()
        sys.exit(0)

    except PermissionError:
        print(f"❌ Error: Permission denied to bind to port {port}")
        print(f"Try using a port > 1024 or run with sudo")
        sys.exit(1)

    except OSError as e:
        print(f"❌ Error: {e}")
        print(f"Port {port} might be already in use")
        sys.exit(1)

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
