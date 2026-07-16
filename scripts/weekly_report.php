<?php
/* error_reporting is process-global and this file is include()d by views.php, so
   E_ALL + display_errors here sprayed notices (and absolute filesystem paths)
   into the rendered page for the rest of the request. Match every other view. */
ini_set('display_errors', 0);
error_reporting(E_ERROR);
require_once 'scripts/common.php';

$startdate = strtotime('last sunday') - (7*86400);
$enddate = strtotime('last sunday') - (1*86400);

$debug = false;

function safe_percentage($count, $prior_count) {
	if ($prior_count !== 0) {
		$percentagediff = round((($count - $prior_count) / $prior_count) * 100);
	} else {
		if ($count > 0) {
			$percentagediff = INF;
		} else {
			$percentagediff = 0;
		}
	}
	return $percentagediff;
}

$db = new SQLite3('./scripts/birds.db', SQLITE3_OPEN_READONLY);
$db->busyTimeout(1000);

$this_start = date("Y-m-d", $startdate);
$this_end   = date("Y-m-d", $enddate);
$prev_start = date("Y-m-d", $startdate - (7 * 86400));
$prev_end   = date("Y-m-d", $enddate - (7 * 86400));

/* This was 1 + 2N queries: the prior-week count and the first-seen check each
   ran once PER SPECIES inside the loop below (~100 species => ~200 extra
   prepared statements per report). Pre-aggregate each into a lookup instead, so
   the whole report costs 3 grouped queries regardless of species count.
   Values are bound rather than interpolated while we're here. */

# prior week counts, grouped once
$prior = [];
$statement2 = $db->prepare('SELECT Sci_Name, COUNT(*) AS Count FROM detections WHERE Date BETWEEN :ps AND :pe GROUP BY Sci_Name');
ensure_db_ok($statement2);
$statement2->bindValue(':ps', $prev_start, SQLITE3_TEXT);
$statement2->bindValue(':pe', $prev_end, SQLITE3_TEXT);
$result2 = $statement2->execute();
while ($row = $result2->fetchArray(SQLITE3_ASSOC)) {
  $prior[$row['Sci_Name']] = $row['Count'];
}

# first/last detection date per species, grouped once. A species is "first seen"
# when it has no detection outside this week - i.e. its whole range sits inside
# it. Equivalent to the old per-species "COUNT(*) outside the week == 0".
$span = [];
$statement3 = $db->prepare('SELECT Sci_Name, MIN(Date) AS mn, MAX(Date) AS mx FROM detections GROUP BY Sci_Name');
ensure_db_ok($statement3);
$result3 = $statement3->execute();
while ($row = $result3->fetchArray(SQLITE3_ASSOC)) {
  $span[$row['Sci_Name']] = $row;
}

$statement1 = $db->prepare('SELECT Sci_Name, Com_Name, COUNT(*) AS Count FROM detections WHERE Date BETWEEN :s AND :e GROUP BY Sci_Name ORDER BY COUNT(*) DESC');
ensure_db_ok($statement1);
$statement1->bindValue(':s', $this_start, SQLITE3_TEXT);
$statement1->bindValue(':e', $this_end, SQLITE3_TEXT);
$result1 = $statement1->execute();
$detections = [];
while ($detection = $result1->fetchArray(SQLITE3_ASSOC)) {
  $com_name = $detection["Com_Name"];
  $sci_name = $detection["Sci_Name"];
  $scount = $detection["Count"];

  $priorweekcount = $prior[$sci_name] ?? 0;
  $percentagediff = safe_percentage($scount, $priorweekcount);

  $is_first_seen = isset($span[$sci_name])
    && $span[$sci_name]['mn'] >= $this_start
    && $span[$sci_name]['mx'] <= $this_end;

  $detections[$com_name] = ["count" => $scount, "percentagediff" => $percentagediff, "is_first_seen" => $is_first_seen];
}

$statement4 = $db->prepare('SELECT COUNT(*) AS Count FROM detections WHERE Date BETWEEN :s AND :e');
ensure_db_ok($statement4);
$statement4->bindValue(':s', $this_start, SQLITE3_TEXT);
$statement4->bindValue(':e', $this_end, SQLITE3_TEXT);
$result4 = $statement4->execute();
$totalcount = $result4->fetchArray(SQLITE3_ASSOC)['Count'];

$statement5 = $db->prepare('SELECT COUNT(*) AS Count FROM detections WHERE Date BETWEEN :ps AND :pe');
ensure_db_ok($statement5);
$statement5->bindValue(':ps', $prev_start, SQLITE3_TEXT);
$statement5->bindValue(':pe', $prev_end, SQLITE3_TEXT);
$result5 = $statement5->execute();
$priortotalcount = $result5->fetchArray(SQLITE3_ASSOC)['Count'];

$statement6 = $db->prepare('SELECT COUNT(DISTINCT(Sci_Name)) FROM detections WHERE Date BETWEEN "'.date("Y-m-d",$startdate).'" AND "'.date("Y-m-d",$enddate).'"');
ensure_db_ok($statement6);
$result6 = $statement6->execute();
$totalspeciestally = $result6->fetchArray(SQLITE3_ASSOC)['COUNT(DISTINCT(Sci_Name))'];

$statement7 = $db->prepare('SELECT COUNT(DISTINCT(Sci_Name)) FROM detections WHERE Date BETWEEN "'.date("Y-m-d",$startdate- (7*86400)).'" AND "'.date("Y-m-d",$enddate- (7*86400)).'"');
ensure_db_ok($statement7);
$result7= $statement7->execute();
$priortotalspeciestally = $result7->fetchArray(SQLITE3_ASSOC)['COUNT(DISTINCT(Sci_Name))'];

$percentagedifftotal = safe_percentage($totalcount, $priortotalcount);

if(isset($_GET['ascii'])) {
	if($percentagedifftotal > 0) {
		$percentagedifftotal = "<span style='color:green;font-size:small'>+".$percentagedifftotal."%</span>";
	} else {
		$percentagedifftotal = "<span style='color:red;font-size:small'>-".abs($percentagedifftotal)."%</span>";
	}

	$percentagedifftotaldistinctspecies = safe_percentage($totalspeciestally, $priortotalspeciestally);
	if($percentagedifftotaldistinctspecies > 0) {
		$percentagedifftotaldistinctspecies = "<span style='color:green;font-size:small'>+".$percentagedifftotaldistinctspecies."%</span>";
	} else {
		$percentagedifftotaldistinctspecies = "<span style='color:red;font-size:small'>-".abs($percentagedifftotaldistinctspecies)."%</span>";
	}

	echo "# BirdNET-Pi: Week ".date('W', $enddate)." Report\n";

	echo "Total Detections: <b>".$totalcount."</b> (".$percentagedifftotal.")<br>";
	echo "Unique Species Detected: <b>".$totalspeciestally."</b> (".$percentagedifftotaldistinctspecies.")<br><br>";

	echo "= <b>Top 10 Species</b> =<br>";

	$i = 0;
	foreach($detections as $com_name=>$stats)
	{
    $count = $stats["count"];
    $percentagediff = $stats["percentagediff"];
		$i++;
		if($i <= 10) {
      if($percentagediff > 0) {
              $percentagediff = "<span style='color:green;font-size:small'>+".$percentagediff."%</span>";
      } else {
              $percentagediff = "<span style='color:red;font-size:small'>-".abs($percentagediff)."%</span>";
      }

      echo $com_name." - ".$count." (".$percentagediff.")<br>";
		}
	}

	echo "<br>= <b>Species Detected for the First Time</b> =<br>";

  $newspeciescount=0;
	foreach($detections as $com_name=>$stats)
	{
		if($stats["is_first_seen"]) {
			$newspeciescount++;
			echo $com_name." - ".$scount."<br>";
		}
	}
	if($newspeciescount == 0) {
		echo "No new species were seen this week.";
	}

  $prevweek = date('W', $enddate) - 1;
  if($prevweek < 1) { $prevweek = 52; }

	echo "<hr><span style='font-size:small'>* data from ".date('Y-m-d', $startdate)." — ".date('Y-m-d',$enddate).".</span><br>";
	echo "<span style='font-size:small'>* percentages are calculated relative to week ".($prevweek).".</span>";

	die();
}

?>
<div class="brbanner"> <?php
echo "<h1>Week ".date('W', $enddate)." Report</h1>".date('F jS, Y',$startdate)." — ".date('F jS, Y',$enddate)."<br>";
?>
</div>
<br>
<?php // TODO: fix the box shadows, maybe make them a bit smaller on the tr ?>
<table align="center" style="box-shadow:unset"><tr><td style="background-color:transparent">
	<table>
	<thead>
		<tr>
			<th><?php echo "Top 10 Species: <br>"; ?></th>
		</tr>
	</thead>
	<tbody>
	<?php

	$i = 0;
	foreach($detections as $com_name=>$stats)
	{
		$i++;
		if($i <= 10) {
        $count = $stats["count"];
        $percentagediff = $stats["percentagediff"];
			if($percentagediff > 0) {
				$percentagediff = "<span style='color:green;font-size:small'>+".$percentagediff."%</span>";
			} else {
				$percentagediff = "<span style='color:red;font-size:small'>-".abs($percentagediff)."%</span>";
			}

			echo "<tr><td>".$com_name."<br><small style=\"font-size:small\">".$count." (".$percentagediff.")</small><br></td></tr>";
		}
	}
	?>
	</tbody>
	</table>
	</td><td style="background-color:transparent">

	<table >
	<thead>
		<tr>
			<th><?php echo "Species Detected for the First Time: <br>"; ?></th>
		</tr>
	</thead>
	<tbody>
	<?php 

  $newspeciescount=0;
	foreach($detections as $com_name=>$stats)
	{
		if($stats["is_first_seen"]) {
			$newspeciescount++;
			echo "<tr><td>".$com_name."<br><small style=\"font-size:small\">".$scount."</small><br></td></tr>";
		}
	}
	if($newspeciescount == 0) {
		echo "<tr><td>No new species were seen this week.</td></tr>";
	}
	?>
	</tbody>
	</table>
	</td></tr></table>


<br>
<div style="text-align:center">
	<hr><small style="font-size:small">* percentages are calculated relative to week <?php echo date('W', $enddate) - 1; ?></small>
</div>
