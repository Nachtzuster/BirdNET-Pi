#!/usr/bin/env bash
# Web-based WiFi Setup for BirdNET-Pi
# Creates a temporary web interface for WiFi configuration before main installation
set -e

WIFI_SETUP_DIR="/tmp/birdnet-wifi-setup"
WIFI_SETUP_PORT=8080

echo "Setting up web-based WiFi configuration..."

# Create temporary directory
mkdir -p $WIFI_SETUP_DIR

# Create the WiFi setup web interface
cat > $WIFI_SETUP_DIR/index.html << 'EOF'
<!DOCTYPE html>
<html lang="nl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BirdNET-Pi WiFi Configuratie</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 600px;
            width: 100%;
            padding: 40px;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .logo {
            width: 80px;
            height: 80px;
            margin: 0 auto 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 40px;
        }
        h1 {
            color: #333;
            font-size: 28px;
            margin-bottom: 10px;
        }
        .subtitle {
            color: #666;
            font-size: 14px;
        }
        .network-list {
            margin: 20px 0;
            max-height: 400px;
            overflow-y: auto;
        }
        .network-item {
            padding: 15px;
            margin: 10px 0;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .network-item:hover {
            border-color: #667eea;
            background: #f8f9ff;
        }
        .network-item.selected {
            border-color: #667eea;
            background: #667eea;
            color: white;
        }
        .network-name {
            font-weight: 600;
            font-size: 16px;
        }
        .signal-strength {
            display: flex;
            gap: 3px;
            align-items: flex-end;
        }
        .signal-bar {
            width: 6px;
            background: #ccc;
            border-radius: 2px;
        }
        .network-item.selected .signal-bar {
            background: white;
        }
        .bar1 { height: 8px; }
        .bar2 { height: 12px; }
        .bar3 { height: 16px; }
        .bar4 { height: 20px; }
        .bar5 { height: 24px; }
        .signal-bar.active {
            background: #4CAF50;
        }
        .network-item.selected .signal-bar.active {
            background: white;
        }
        .password-section {
            margin: 20px 0;
            display: none;
        }
        .password-section.show {
            display: block;
            animation: fadeIn 0.3s;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .input-group {
            margin: 15px 0;
        }
        label {
            display: block;
            margin-bottom: 8px;
            color: #555;
            font-weight: 500;
        }
        input[type="text"],
        input[type="password"] {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        input:focus {
            outline: none;
            border-color: #667eea;
        }
        .button {
            width: 100%;
            padding: 15px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s;
            margin-top: 20px;
        }
        .button:hover {
            transform: translateY(-2px);
        }
        .button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }
        .loading {
            text-align: center;
            padding: 40px;
        }
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .message {
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
            display: none;
        }
        .message.show {
            display: block;
            animation: fadeIn 0.3s;
        }
        .message.error {
            background: #ffebee;
            color: #c62828;
            border: 1px solid #ef5350;
        }
        .message.success {
            background: #e8f5e9;
            color: #2e7d32;
            border: 1px solid #66bb6a;
        }
        .refresh-button {
            background: #f5f5f5;
            color: #666;
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            margin-bottom: 15px;
        }
        .refresh-button:hover {
            background: #e0e0e0;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">🐦</div>
            <h1>BirdNET-Pi</h1>
            <p class="subtitle">WiFi Netwerk Configuratie</p>
        </div>

        <div id="loading" class="loading">
            <div class="spinner"></div>
            <p>Netwerken scannen...</p>
        </div>

        <div id="content" style="display: none;">
            <button class="refresh-button" onclick="scanNetworks()">🔄 Opnieuw scannen</button>
            
            <div id="message" class="message"></div>
            
            <div class="network-list" id="networkList"></div>
            
            <div id="passwordSection" class="password-section">
                <div class="input-group">
                    <label for="ssid">Netwerk Naam (SSID)</label>
                    <input type="text" id="ssid" readonly>
                </div>
                <div class="input-group">
                    <label for="password">Wachtwoord</label>
                    <input type="password" id="password" placeholder="Voer wachtwoord in">
                </div>
                <button class="button" onclick="connectNetwork()">Verbinden</button>
            </div>
        </div>
    </div>

    <script>
        let selectedNetwork = null;

        async function scanNetworks() {
            document.getElementById('loading').style.display = 'block';
            document.getElementById('content').style.display = 'none';
            
            try {
                const response = await fetch('/scan');
                const networks = await response.json();
                
                document.getElementById('loading').style.display = 'none';
                document.getElementById('content').style.display = 'block';
                
                displayNetworks(networks);
            } catch (error) {
                showMessage('Fout bij scannen van netwerken: ' + error.message, 'error');
                document.getElementById('loading').style.display = 'none';
                document.getElementById('content').style.display = 'block';
            }
        }

        function displayNetworks(networks) {
            const listDiv = document.getElementById('networkList');
            listDiv.innerHTML = '';
            
            if (networks.length === 0) {
                listDiv.innerHTML = '<p style="text-align: center; color: #999;">Geen netwerken gevonden</p>';
                return;
            }
            
            networks.forEach(network => {
                const item = document.createElement('div');
                item.className = 'network-item';
                item.onclick = () => selectNetwork(network.ssid, item);
                
                const nameDiv = document.createElement('div');
                nameDiv.className = 'network-name';
                nameDiv.textContent = network.ssid;
                
                const signalDiv = document.createElement('div');
                signalDiv.className = 'signal-strength';
                
                const signal = parseInt(network.signal);
                const bars = signal > -50 ? 5 : signal > -60 ? 4 : signal > -70 ? 3 : signal > -80 ? 2 : 1;
                
                for (let i = 1; i <= 5; i++) {
                    const bar = document.createElement('div');
                    bar.className = 'signal-bar bar' + i;
                    if (i <= bars) bar.classList.add('active');
                    signalDiv.appendChild(bar);
                }
                
                item.appendChild(nameDiv);
                item.appendChild(signalDiv);
                listDiv.appendChild(item);
            });
        }

        function selectNetwork(ssid, element) {
            selectedNetwork = ssid;
            
            // Remove selection from all items
            document.querySelectorAll('.network-item').forEach(item => {
                item.classList.remove('selected');
            });
            
            // Add selection to clicked item
            element.classList.add('selected');
            
            // Show password section
            document.getElementById('ssid').value = ssid;
            document.getElementById('password').value = '';
            document.getElementById('passwordSection').classList.add('show');
        }

        async function connectNetwork() {
            const ssid = document.getElementById('ssid').value;
            const password = document.getElementById('password').value;
            
            if (!ssid) {
                showMessage('Selecteer eerst een netwerk', 'error');
                return;
            }
            
            const button = event.target;
            button.disabled = true;
            button.textContent = 'Verbinden...';
            
            try {
                const response = await fetch('/connect', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ssid, password })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showMessage('Succesvol verbonden! BirdNET-Pi wordt nu geïnstalleerd...', 'success');
                    setTimeout(() => {
                        window.location.href = '/complete';
                    }, 3000);
                } else {
                    showMessage('Verbinding mislukt: ' + result.message, 'error');
                    button.disabled = false;
                    button.textContent = 'Verbinden';
                }
            } catch (error) {
                showMessage('Fout bij verbinden: ' + error.message, 'error');
                button.disabled = false;
                button.textContent = 'Verbinden';
            }
        }

        function showMessage(text, type) {
            const msg = document.getElementById('message');
            msg.textContent = text;
            msg.className = 'message ' + type + ' show';
            setTimeout(() => msg.classList.remove('show'), 5000);
        }

        // Start scanning on page load
        window.onload = scanNetworks;
    </script>
</body>
</html>
EOF

# Create the Python backend server
cat > $WIFI_SETUP_DIR/wifi_server.py << 'EOF'
#!/usr/bin/env python3
import os
import sys
import json
import subprocess
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs

class WiFiSetupHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress default logging
    
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            with open('/tmp/birdnet-wifi-setup/index.html', 'rb') as f:
                self.wfile.write(f.read())
        
        elif self.path == '/scan':
            networks = self.scan_networks()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(networks).encode())
        
        elif self.path == '/complete':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            html = """
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body { font-family: Arial; text-align: center; padding: 50px; background: #667eea; color: white; }
                    h1 { font-size: 48px; }
                </style>
            </head>
            <body>
                <h1>✓ WiFi Geconfigureerd!</h1>
                <p>BirdNET-Pi installatie wordt voortgezet...</p>
                <p>Deze pagina sluit automatisch.</p>
            </body>
            </html>
            """
            self.wfile.write(html.encode())
            # Signal completion
            open('/tmp/birdnet-wifi-setup/complete', 'w').close()
        
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        if self.path == '/connect':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode())
            
            success = self.configure_wifi(data['ssid'], data.get('password', ''))
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            if success:
                self.wfile.write(json.dumps({'success': True}).encode())
            else:
                self.wfile.write(json.dumps({
                    'success': False, 
                    'message': 'Kon niet verbinden. Controleer uw wachtwoord.'
                }).encode())
    
    def scan_networks(self):
        try:
            # Get WiFi interface
            result = subprocess.run(['iw', 'dev'], capture_output=True, text=True)
            interface = None
            for line in result.stdout.split('\n'):
                if 'Interface' in line:
                    interface = line.split()[1]
                    break
            
            if not interface:
                return []
            
            # Scan networks
            subprocess.run(['sudo', 'ifconfig', interface, 'up'], stderr=subprocess.DEVNULL)
            time.sleep(1)
            
            result = subprocess.run(['sudo', 'iw', 'dev', interface, 'scan'], 
                                  capture_output=True, text=True, timeout=10)
            
            networks = {}
            current_ssid = None
            current_signal = None
            
            for line in result.stdout.split('\n'):
                line = line.strip()
                if line.startswith('SSID:'):
                    current_ssid = line.split('SSID:', 1)[1].strip()
                elif 'signal:' in line:
                    signal = line.split('signal:')[1].strip().split()[0]
                    current_signal = signal
                    
                    if current_ssid and current_ssid not in networks:
                        networks[current_ssid] = current_signal
            
            # Convert to list and sort by signal strength
            network_list = [{'ssid': ssid, 'signal': signal} 
                          for ssid, signal in networks.items() if ssid]
            network_list.sort(key=lambda x: float(x['signal']), reverse=True)
            
            return network_list
        except Exception as e:
            print(f"Scan error: {e}", file=sys.stderr)
            return []
    
    def configure_wifi(self, ssid, password):
        try:
            # Backup existing config
            if os.path.exists('/etc/wpa_supplicant/wpa_supplicant.conf'):
                timestamp = time.strftime('%Y%m%d_%H%M%S')
                subprocess.run(['sudo', 'cp', '/etc/wpa_supplicant/wpa_supplicant.conf',
                              f'/etc/wpa_supplicant/wpa_supplicant.conf.backup.{timestamp}'])
            
            # Get country code
            country = 'NL'
            try:
                with open('/etc/wpa_supplicant/wpa_supplicant.conf', 'r') as f:
                    for line in f:
                        if line.startswith('country='):
                            country = line.split('=')[1].strip()
                            break
            except:
                pass
            
            # Create new config
            if password:
                config = f"""ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country={country}

network={{
    ssid="{ssid}"
    psk="{password}"
    key_mgmt=WPA-PSK
}}
"""
            else:
                config = f"""ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country={country}

network={{
    ssid="{ssid}"
    key_mgmt=NONE
}}
"""
            
            # Write config
            with open('/tmp/wpa_supplicant.conf.tmp', 'w') as f:
                f.write(config)
            
            subprocess.run(['sudo', 'cp', '/tmp/wpa_supplicant.conf.tmp', 
                          '/etc/wpa_supplicant/wpa_supplicant.conf'])
            os.remove('/tmp/wpa_supplicant.conf.tmp')
            
            # Restart networking
            subprocess.run(['sudo', 'systemctl', 'restart', 'dhcpcd'], 
                         stderr=subprocess.DEVNULL)
            time.sleep(2)
            
            # Get WiFi interface
            result = subprocess.run(['iw', 'dev'], capture_output=True, text=True)
            interface = None
            for line in result.stdout.split('\n'):
                if 'Interface' in line:
                    interface = line.split()[1]
                    break
            
            if interface:
                subprocess.run(['sudo', 'wpa_cli', '-i', interface, 'reconfigure'], 
                             stderr=subprocess.DEVNULL)
            
            # Check connection
            for _ in range(15):
                time.sleep(1)
                result = subprocess.run(['iwconfig', interface], 
                                      capture_output=True, text=True)
                if f'ESSID:"{ssid}"' in result.stdout:
                    return True
            
            return False
        except Exception as e:
            print(f"Config error: {e}", file=sys.stderr)
            return False

def run_server():
    server = HTTPServer(('0.0.0.0', 8080), WiFiSetupHandler)
    print('WiFi setup server started on http://birdnetpi.local:8080')
    print('Or access via IP address on port 8080')
    server.serve_forever()

if __name__ == '__main__':
    run_server()
EOF

chmod +x $WIFI_SETUP_DIR/wifi_server.py

echo "Web-based WiFi setup created at $WIFI_SETUP_DIR"
