<?php
// scripts/species.php

require_once 'scripts/common.php';
$config = get_config();

// Get filter parameters
$time_period = isset($_GET['time_period']) ? $_GET['time_period'] : 'all';
$sort_by = isset($_GET['sort_by']) ? $_GET['sort_by'] : 'detections';
$search = isset($_GET['search']) ? $_GET['search'] : '';
$debug_mode = isset($_GET['debug']) && $_GET['debug'] == '1';

$db = get_db();

// Build WHERE clause for time period
$where_clauses = [];
if ($time_period !== 'all') {
    switch ($time_period) {
        case '24h': $where_clauses[] = "Date >= date('now', '-1 day')"; break;
        case '7d':  $where_clauses[] = "Date >= date('now', '-7 days')"; break;
        case '30d': $where_clauses[] = "Date >= date('now', '-30 days')"; break;
        case '90d': $where_clauses[] = "Date >= date('now', '-90 days')"; break;
        case '1y':  $where_clauses[] = "Date >= date('now', '-1 year')"; break;
    }
}
if (!empty($search)) {
    $where_clauses[] = "(Com_Name LIKE :search OR Sci_Name LIKE :search)";
}

$where_sql = !empty($where_clauses) ? "WHERE " . implode(" AND ", $where_clauses) : "";

// KPI Data
$kpi_stmt = $db->prepare("SELECT COUNT(DISTINCT Sci_Name) as unique_species, COUNT(*) as total_detections, AVG(Confidence) as avg_conf FROM detections $where_sql");
if (!empty($search)) {
    $kpi_stmt->bindValue(':search', '%' . $search . '%', SQLITE3_TEXT);
}
$kpi_res = $kpi_stmt->execute()->fetchArray(SQLITE3_ASSOC);

// Species List Data
$order_by = "COUNT(*) DESC";
switch ($sort_by) {
    case 'sci_name': $order_by = "Sci_Name ASC"; break;
    case 'com_name': $order_by = "Com_Name ASC"; break;
    case 'confidence': $order_by = "MAX(Confidence) DESC"; break;
}

$list_stmt = $db->prepare("SELECT Com_Name, Sci_Name, COUNT(*) as Count, MAX(Confidence) as MaxConf, MIN(Date) as FirstDate, File_Name FROM detections $where_sql GROUP BY Sci_Name ORDER BY $order_by");
if (!empty($search)) {
    $list_stmt->bindValue(':search', '%' . $search . '%', SQLITE3_TEXT);
}
$list_res = $list_stmt->execute();

$species_list = [];
while ($row = $list_res->fetchArray(SQLITE3_ASSOC)) {
    $species_list[] = $row;
}

// Image fetching logic
$flickr = new Flickr();
$wikipedia = new Wikipedia();

if (isset($config['IMAGE_PROVIDER']) && strtolower($config['IMAGE_PROVIDER']) == 'flickr') {
    $image_provider = $flickr;
    $fallback_provider = $wikipedia;
} else {
    $image_provider = $wikipedia;
    $fallback_provider = $flickr;
}

if ($image_provider && $image_provider->is_reset()) {
    $_SESSION['species_portal_v3_cache'] = [];
}


?>

<style>
/* Reusing styles from analytics.php and adding species-specific ones */
.species-dashboard {
    padding: 20px 40px;
    width: 100%;
    max-width: none !important;
    margin: 0;
    box-sizing: border-box;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}
.dashboard-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; }
.header-text h1 { font-size: 1.8rem; margin: 0; color: var(--text-heading); }
.header-text p { margin: 4px 0 0 0; color: var(--text-muted, #64748b); }

.kpi-row { display: flex; gap: 20px; align-items: stretch; }
.kpi-card {
    background: var(--bg-card);
    padding: 20px 24px;
    border-radius: 12px;
    border: 1px solid var(--border-light, #f1f5f9);
    display: flex;
    align-items: center;
    gap: 16px;
    min-width: 200px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.kpi-icon {
    width: 48px; height: 48px;
    border-radius: 50%;
    background: #eff6ff;
    color: #3b82f6;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.4rem;
}
.kpi-info { display: flex; flex-direction: column; }
.kpi-label { font-size: 0.9rem; font-weight: 600; color: var(--text-heading); }
.kpi-value { font-size: 1.6rem; font-weight: 700; color: var(--text-primary); line-height: 1; margin: 4px 0; }
.kpi-sub { font-size: 0.75rem; color: var(--text-muted); }

/* Filters */
.filter-section {
    background: var(--bg-card);
    padding: 24px;
    border-radius: 12px;
    margin-bottom: 32px;
    border: 1px solid var(--border-light, #f1f5f9);
}
.filter-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 24px;
    align-items: end;
}
.filter-group { display: flex; flex-direction: column; gap: 8px; }
.filter-group label { font-size: 0.85rem; font-weight: 600; color: var(--text-muted); }
.styled-select, .styled-input {
    padding: 10px 12px;
    border-radius: 8px;
    border: 1px solid var(--border);
    background: var(--bg-input, #fff);
    color: var(--text-primary);
    outline: none;
    font-size: 0.9rem;
}
.search-group { grid-column: 1 / -1; }
.filter-footer { display: flex; justify-content: space-between; align-items: center; margin-top: 20px; }
.results-count { font-size: 0.85rem; color: var(--text-muted); }
.filter-actions { display: flex; gap: 12px; }

/* Grid */
.species-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 24px;
}
.bird-card {
    background: var(--bg-card);
    border-radius: 16px;
    overflow: hidden;
    border: 1px solid var(--border-light, #f1f5f9);
    transition: transform 0.2s, box-shadow 0.2s;
    display: flex;
    flex-direction: column;
}
.bird-card:hover { 
    transform: translateY(-4px);
    box-shadow: 0 12px 20px -8px rgba(0,0,0,0.1);
}
.bird-image-container {
    height: 200px;
    background: #f8fafc;
    position: relative;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
}
.bird-image {
    width: 100%;
    height: 100%;
    object-fit: contain;
}
.card-content { padding: 20px; }
.bird-name { font-size: 1.1rem; font-weight: 700; color: var(--text-heading); margin-bottom: 2px; }
.bird-sci { font-size: 0.85rem; font-style: italic; color: var(--text-muted); margin-bottom: 16px; display: block; }
.stats-table { width: 100%; font-size: 0.85rem; }
.stats-table tr td:first-child { color: var(--text-muted); padding-bottom: 4px; }
.stats-table tr td:last-child { text-align: right; font-weight: 600; color: var(--text-primary); padding-bottom: 4px; }

</style>

<div class="species-dashboard">
    <div class="dashboard-header">
        <div class="header-text">
            <h1>Species</h1>
            <p>Comprehensive list of all bird species that have been detected</p>
        </div>
        <div class="kpi-row">
            <div class="kpi-card">
                <div class="kpi-icon">📋</div>
                <div class="kpi-info">
                    <span class="kpi-label">Total Species</span>
                    <span class="kpi-value"><?php echo number_format($kpi_res['unique_species']); ?></span>
                    <span class="kpi-sub"><?php echo number_format($kpi_res['total_detections']); ?> detections</span>
                </div>
            </div>
            <div class="kpi-card">
                <div class="kpi-icon">🎯</div>
                <div class="kpi-info">
                    <span class="kpi-label">Avg. Confidence</span>
                    <span class="kpi-value"><?php echo round($kpi_res['avg_conf'] * 100, 1); ?>%</span>
                    <span class="kpi-sub">Overall average</span>
                </div>
            </div>
        </div>
    </div>

    <div class="filter-section">
        <form action="" method="GET" id="species-filters">
            <input type="hidden" name="view" value="Species">
            <div class="filter-grid">
                <div class="filter-group">
                    <label>Time Period</label>
                    <select name="time_period" class="styled-select" onchange="this.form.submit()">
                        <option value="all" <?php echo $time_period == 'all' ? 'selected' : ''; ?>>All Time</option>
                        <option value="24h" <?php echo $time_period == '24h' ? 'selected' : ''; ?>>Last 24 Hours</option>
                        <option value="7d" <?php echo $time_period == '7d' ? 'selected' : ''; ?>>Last 7 Days</option>
                        <option value="30d" <?php echo $time_period == '30d' ? 'selected' : ''; ?>>Last 30 Days</option>
                        <option value="90d" <?php echo $time_period == '90d' ? 'selected' : ''; ?>>Last 90 Days</option>
                        <option value="1y" <?php echo $time_period == '1y' ? 'selected' : ''; ?>>Last Year</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label>Sort By</label>
                    <select name="sort_by" class="styled-select" onchange="this.form.submit()">
                        <option value="detections" <?php echo $sort_by == 'detections' ? 'selected' : ''; ?>>Most Detections</option>
                        <option value="com_name" <?php echo $sort_by == 'com_name' ? 'selected' : ''; ?>>Common Name</option>
                        <option value="sci_name" <?php echo $sort_by == 'sci_name' ? 'selected' : ''; ?>>Scientific Name</option>
                        <option value="confidence" <?php echo $sort_by == 'confidence' ? 'selected' : ''; ?>>Highest Confidence</option>
                    </select>
                </div>
                <div class="filter-group search-group">
                    <label>Search Species</label>
                    <input type="text" name="search" class="styled-input" placeholder="Search by name..." value="<?php echo htmlspecialchars($search); ?>">
                </div>
            </div>
            <div class="filter-footer">
                <span class="results-count"><?php echo count($species_list); ?> species</span>
                <div class="filter-actions">
                    <a href="?view=Species" class="btn-reset">Reset</a>
                    <button type="submit" class="btn-apply text-white">Apply Filters</button>
                    <button type="submit" name="export" value="csv" class="btn-apply" style="background: #475569 !important;">📥 Export CSV</button>
                </div>
            </div>
        </form>
    </div>

    <div class="species-grid">
        <?php foreach ($species_list as $bird): 
            $com_name = $bird['Com_Name'];
            $sci_name = $bird['Sci_Name'];
            
            // Get image
            $image_url = 'images/bird.png';
            $image = false;
            $debug_msg = "No Provider";

            if ($image_provider) {
                if (!isset($_SESSION['species_portal_v3_cache'])) {
                    $_SESSION['species_portal_v3_cache'] = [];
                }
                
                $search_name = trim($com_name);
                $key = array_search($search_name, array_column($_SESSION['species_portal_v3_cache'], 0));
                
                if ($key !== false) {
                    $image = $_SESSION['species_portal_v3_cache'][$key];
                    $debug_msg = "Session Match. URL: " . (empty($image[1]) ? "EMPTY" : "OK") . " | Source: " . ($image[1] ?? 'N/A');
                } else {
                    $cached_image = $image_provider->get_image($sci_name, $fallback_provider);
                    if ($cached_image && !empty($cached_image["image_url"])) {
                        $debug_msg = "Fetched Fresh. URL: " . $cached_image["image_url"];
                        $image_data = array($search_name, $cached_image["image_url"], $cached_image["title"], $cached_image["photos_url"], $cached_image["author_url"], $cached_image["license_url"]);
                        array_push($_SESSION["species_portal_v3_cache"], $image_data);
                        $image = $image_data;
                    } else {
                        $debug_msg = "Fetch Failed. Scientific name: " . $sci_name;
                        // Cache the failure with an empty URL so we don't retry every time
                        $image_data = array($search_name, "", "Not Found", "", "", "");
                        array_push($_SESSION["species_portal_v3_cache"], $image_data);
                        $image = $image_data;
                    }
                }
                $image_url = ($image && !empty($image[1])) ? $image[1] : 'images/bird.png';
            }
        ?>
            <!-- DEBUG: <?php echo $sci_name; ?> | <?php echo $debug_msg; ?> -->
            <div class="bird-card">
                <?php if ($debug_mode): ?>
                    <div style="font-size: 10px; padding: 5px; background: rgba(0,0,0,0.5); color: #fff; word-break: break-all; max-height: 60px; overflow: auto; position: absolute; z-index: 10; width: 100%;">
                        <?php echo $debug_msg; ?>
                    </div>
                <?php endif; ?>
                <div class="bird-name-debug" style="display:none"><?php echo $sci_name; ?> | <?php echo $debug_msg; ?></div>
                <div class="bird-image-container">
                    <img src="<?php echo $image_url; ?>" alt="<?php echo $com_name; ?>" class="bird-image" onerror="this.onerror=null; this.src='images/bird.png'">
                </div>
                <div class="card-content">
                    <span class="bird-name"><?php echo $com_name; ?></span>
                    <span class="bird-sci"><?php echo $sci_name; ?></span>
                    <table class="stats-table">
                        <tr><td>Detections:</td><td><?php echo number_format($bird['Count']); ?></td></tr>
                        <tr><td>Confidence:</td><td><?php echo round($bird['MaxConf'] * 100, 1); ?>%</td></tr>
                        <tr><td>First:</td><td><?php echo date('n/j/Y', strtotime($bird['FirstDate'])); ?></td></tr>
                    </table>
                </div>
            </div>
        <?php endforeach; ?>
    </div>
</div>

<?php
// Handle CSV export
if (isset($_GET['export']) && $_GET['export'] == 'csv') {
    ob_end_clean();
    header('Content-Type: text/csv');
    header('Content-Disposition: attachment; filename="species_list.csv"');
    $output = fopen('php://output', 'w');
    fputcsv($output, ['Common Name', 'Scientific Name', 'Detections', 'Max Confidence', 'First Detected']);
    foreach ($species_list as $bird) {
        fputcsv($output, [
            $bird['Com_Name'],
            $bird['Sci_Name'],
            $bird['Count'],
            round($bird['MaxConf'] * 100, 1) . '%',
            $bird['FirstDate']
        ]);
    }
    fclose($output);
    exit();
}
?>
