<?php
error_reporting(E_ERROR);
ini_set('display_errors', 1);

session_start();
require_once "scripts/common.php";
$user = get_user();
$home = get_home();

ensure_authenticated();

// Handle form submission
$message = '';
$message_type = '';

if (isset($_GET['action'])) {
    switch ($_GET['action']) {
        case 'configure':
            exec('sudo /usr/local/bin/configure_wifi_roaming.sh configure 2>&1', $output, $return_code);
            if ($return_code === 0) {
                $message = "WiFi roaming configured successfully!";
                $message_type = "success";
            } else {
                $message = "Error configuring WiFi roaming: " . implode("\n", $output);
                $message_type = "error";
            }
            break;
        
        case 'restore':
            if (isset($_GET['file']) && !empty($_GET['file'])) {
                // Sanitize the file path to prevent directory traversal
                $backup_file = basename($_GET['file']);
                $full_path = '/etc/wpa_supplicant/' . $backup_file;
                
                // Verify the file exists and has the correct prefix
                if (strpos($backup_file, 'wpa_supplicant.conf.backup.') === 0 && file_exists($full_path)) {
                    exec('sudo /usr/local/bin/configure_wifi_roaming.sh restore ' . escapeshellarg($full_path) . ' 2>&1', $output, $return_code);
                    if ($return_code === 0) {
                        $message = "Configuration restored successfully!";
                        $message_type = "success";
                    } else {
                        $message = "Error restoring configuration: " . implode("\n", $output);
                        $message_type = "error";
                    }
                } else {
                    $message = "Invalid backup file selected.";
                    $message_type = "error";
                }
            }
            break;
        
        case 'status':
            // Get status info
            exec('sudo /usr/local/bin/configure_wifi_roaming.sh status 2>&1', $output, $return_code);
            break;
    }
}

// Get current WiFi status
exec('iwconfig 2>&1 | grep -A 10 "wlan0"', $wifi_status);
$wifi_connected = !empty($wifi_status);

// Check if roaming is configured
exec('grep -E "ap_scan=1|fast_reauth=1|bgscan=" /etc/wpa_supplicant/wpa_supplicant.conf 2>&1', $roaming_check);
$roaming_configured = count($roaming_check) >= 2;

// Get available backups
exec('ls -1t /etc/wpa_supplicant/wpa_supplicant.conf.backup.* 2>/dev/null', $backups);

?>
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>WiFi Roaming Configuration - BirdNET-Pi</title>
    <style>
        .wifi-container {
            max-width: 800px;
            margin: 20px auto;
            padding: 20px;
        }
        .status-box {
            background: #f0f0f0;
            border-radius: 5px;
            padding: 15px;
            margin: 15px 0;
        }
        .status-box.active {
            background: #d4edda;
            border: 1px solid #c3e6cb;
        }
        .status-box.inactive {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
        }
        .message {
            padding: 15px;
            margin: 15px 0;
            border-radius: 5px;
        }
        .message.success {
            background: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
        }
        .message.error {
            background: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
        }
        .button {
            background: #007bff;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            margin: 5px;
            text-decoration: none;
            display: inline-block;
        }
        .button:hover {
            background: #0056b3;
        }
        .button.secondary {
            background: #6c757d;
        }
        .button.secondary:hover {
            background: #545b62;
        }
        .button.danger {
            background: #dc3545;
        }
        .button.danger:hover {
            background: #c82333;
        }
        .info-section {
            background: #e7f3ff;
            border-left: 4px solid #007bff;
            padding: 15px;
            margin: 15px 0;
        }
        pre {
            background: #2d2d2d;
            color: #f8f8f2;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            font-size: 12px;
        }
        h1, h2 {
            color: #333;
        }
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 5px;
        }
        .status-indicator.on {
            background: #28a745;
        }
        .status-indicator.off {
            background: #dc3545;
        }
        .backup-list {
            max-height: 200px;
            overflow-y: auto;
            background: #f8f9fa;
            padding: 10px;
            border-radius: 5px;
        }
    </style>
</head>
<body>
<div class="wifi-container">
    <h1>WiFi Roaming Configuration</h1>
    
    <?php if ($message): ?>
        <div class="message <?php echo $message_type; ?>">
            <?php echo nl2br(htmlspecialchars($message)); ?>
        </div>
    <?php endif; ?>

    <div class="status-box <?php echo $roaming_configured ? 'active' : 'inactive'; ?>">
        <h2>
            <span class="status-indicator <?php echo $roaming_configured ? 'on' : 'off'; ?>"></span>
            Roaming Status: <?php echo $roaming_configured ? 'Configured' : 'Not Configured'; ?>
        </h2>
        <?php if ($wifi_connected): ?>
            <p><strong>WiFi Connection:</strong> Connected</p>
            <pre><?php echo htmlspecialchars(implode("\n", $wifi_status)); ?></pre>
        <?php else: ?>
            <p><strong>WiFi Connection:</strong> Not detected or not active</p>
        <?php endif; ?>
    </div>

    <div class="info-section">
        <h3>What is WiFi Roaming?</h3>
        <p>WiFi roaming allows your Raspberry Pi to automatically switch between multiple WiFi access points 
        with the same SSID (network name) based on signal strength. This ensures the best possible connection 
        for SSH access and the web interface.</p>
        
        <p><strong>Requirements:</strong></p>
        <ul>
            <li>Multiple WiFi access points with the same SSID</li>
            <li>Same password and security settings on all access points</li>
            <li>Overlapping coverage areas</li>
        </ul>
    </div>

    <?php if ($roaming_configured): ?>
        <div class="status-box active">
            <h3>Current Configuration</h3>
            <p>WiFi roaming is enabled with the following settings:</p>
            <pre><?php echo htmlspecialchars(implode("\n", $roaming_check)); ?></pre>
            
            <p><strong>Configuration Details:</strong></p>
            <ul>
                <li><code>ap_scan=1</code>: Active scanning for the best access point</li>
                <li><code>fast_reauth=1</code>: Fast re-authentication when switching APs</li>
                <li><code>bgscan="simple:30:-45:300"</code>: Scan every 30s, switch if signal &lt; -45dBm</li>
            </ul>
        </div>
    <?php else: ?>
        <div class="info-section">
            <h3>Configure WiFi Roaming</h3>
            <p>Click the button below to enable automatic WiFi roaming. This will:</p>
            <ol>
                <li>Backup your current WiFi configuration</li>
                <li>Add roaming parameters to wpa_supplicant</li>
                <li>Restart the WiFi service</li>
            </ol>
            <p><strong>Note:</strong> Your WiFi connection may briefly disconnect during configuration.</p>
        </div>
    <?php endif; ?>

    <div style="margin: 20px 0;">
        <?php if (!$roaming_configured): ?>
            <a href="?action=configure" class="button" onclick="return confirm('This will modify your WiFi configuration and restart the WiFi service. Continue?')">
                Enable WiFi Roaming
            </a>
        <?php endif; ?>
        
        <a href="?action=status" class="button secondary">Refresh Status</a>
        
        <a href="../docs/wifi_roaming.md" class="button secondary" target="_blank">View Documentation</a>
    </div>

    <?php if (!empty($backups)): ?>
        <div class="status-box">
            <h3>Configuration Backups</h3>
            <p>Previous WiFi configurations are backed up automatically. You can restore them if needed:</p>
            <div class="backup-list">
                <?php foreach ($backups as $backup): ?>
                    <div>
                        📄 <?php echo basename($backup); ?>
                        <a href="?action=restore&file=<?php echo urlencode(basename($backup)); ?>" 
                           class="button danger" 
                           style="font-size: 11px; padding: 3px 8px;"
                           onclick="return confirm('Restore this backup? This will replace your current configuration.')">
                            Restore
                        </a>
                    </div>
                <?php endforeach; ?>
            </div>
        </div>
    <?php endif; ?>

    <div class="info-section">
        <h3>Advanced Configuration</h3>
        <p>For advanced users, you can manually edit the WiFi configuration:</p>
        <pre>sudo nano /etc/wpa_supplicant/wpa_supplicant.conf</pre>
        <p>After editing, restart the WiFi service:</p>
        <pre>sudo systemctl restart wpa_supplicant.service</pre>
        
        <p>For detailed information and troubleshooting, see the 
        <a href="../docs/wifi_roaming.md" target="_blank">complete documentation</a>.</p>
    </div>

    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center;">
        <a href="index.php" class="button secondary">Back to Main Page</a>
    </div>
</div>
</body>
</html>
