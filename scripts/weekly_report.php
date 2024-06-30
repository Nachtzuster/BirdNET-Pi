<?php 
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);
error_reporting(E_ALL);
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

if(isset($_GET['ascii'])) {

	$db = new SQLite3('./scripts/birds.db', SQLITE3_OPEN_READONLY);
	$db->busyTimeout(1000);

	$statement1 = $db->prepare('SELECT DISTINCT(Com_Name), COUNT(*) FROM detections WHERE Date BETWEEN "'.date("Y-m-d",$startdate).'" AND "'.date("Y-m-d",$enddate).'" GROUP By Com_Name ORDER BY COUNT(*) DESC');
	ensure_db_ok($statement1);
	$result1 = $statement1->execute();

	$statement4 = $db->prepare('SELECT DISTINCT(Com_Name), COUNT(*) FROM detections WHERE Date BETWEEN "'.date("Y-m-d",$startdate).'" AND "'.date("Y-m-d",$enddate).'"');
	ensure_db_ok($statement4);
	$result4 = $statement4->execute();
	$totalcount = $result4->fetchArray(SQLITE3_ASSOC)['COUNT(*)'];

	$statement5 = $db->prepare('SELECT DISTINCT(Com_Name), COUNT(*) FROM detections WHERE Date BETWEEN "'.date("Y-m-d",$startdate- (7*86400)).'" AND "'.date("Y-m-d",$enddate- (7*86400)).'"');
	ensure_db_ok($statement5);
	$result5 = $statement5->execute();
	$priortotalcount = $result5->fetchArray(SQLITE3_ASSOC)['COUNT(*)'];

	$statement6 = $db->prepare('SELECT COUNT(DISTINCT(Com_Name)) FROM detections WHERE Date BETWEEN "'.date("Y-m-d",$startdate).'" AND "'.date("Y-m-d",$enddate).'"');
	ensure_db_ok($statement6);
	$result6 = $statement6->execute();
	$totalspeciestally = $result6->fetchArray(SQLITE3_ASSOC)['COUNT(DISTINCT(Com_Name))'];

	$statement7 = $db->prepare('SELECT COUNT(DISTINCT(Com_Name)) FROM detections WHERE Date BETWEEN "'.date("Y-m-d",$startdate- (7*86400)).'" AND "'.date("Y-m-d",$enddate- (7*86400)).'"');
	ensure_db_ok($statement7);
	$result7= $statement7->execute();
	$priortotalspeciestally = $result7->fetchArray(SQLITE3_ASSOC)['COUNT(DISTINCT(Com_Name))'];

	$percentagedifftotal = safe_percentage($totalcount, $priortotalcount);
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

	$detections = [];
	$i = 0;
	while($detection=$result1->fetchArray(SQLITE3_ASSOC))
	{
		$detections[$detection["Com_Name"]] = $detection["COUNT(*)"];
	}

	echo "# BirdNET-Pi: Week ".date('W', $enddate)." Report\n";

	echo "Total Detections: <b>".$totalcount."</b> (".$percentagedifftotal.")<br>";
	echo "Unique Species Detected: <b>".$totalspeciestally."</b> (".$percentagedifftotaldistinctspecies.")<br><br>";

	echo "= <b>Top 10 Species</b> =<br>";

	$i = 0;
	foreach($detections as $com_name=>$scount)
	{
		$i++;

		if($i <= 10) {
			$statement2 = $db->prepare('SELECT COUNT(*) FROM detections WHERE Com_Name == "'.$com_name.'" AND Date BETWEEN "'.date("Y-m-d",$startdate - (7*86400)).'" AND "'.date("Y-m-d",$enddate - (7*86400)).'"');
			ensure_db_ok($statement2);
			$result2 = $statement2->execute();
			$totalcount = $result2->fetchArray(SQLITE3_ASSOC);
			$priorweekcount = $totalcount['COUNT(*)'];

      // really percent changed
			$percentagediff = safe_percentage($scount, $priorweekcount);
                                if($percentagediff > 0) {
                                        $percentagediff = "<span style='color:green;font-size:small'>+".$percentagediff."%</span>";
                                } else {
                                        $percentagediff = "<span style='color:red;font-size:small'>-".abs($percentagediff)."%</span>";
                                }

                                echo $com_name." - ".$scount." (".$percentagediff.")<br>";
		}
	}

	echo "<br>= <b>Species Detected for the First Time</b> =<br>";

    $newspeciescount=0;
	foreach($detections as $com_name=>$scount)
	{
		$statement3 = $db->prepare('SELECT COUNT(*) FROM detections WHERE Com_Name == "'.$com_name.'" AND Date NOT BETWEEN "'.date("Y-m-d",$startdate).'" AND "'.date("Y-m-d",$enddate).'"');
		ensure_db_ok($statement3);
		$result3 = $statement3->execute();
		$totalcount = $result3->fetchArray(SQLITE3_ASSOC);
		$nonthisweekcount = $totalcount['COUNT(*)'];

		if($nonthisweekcount == 0) {
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
?></div><?php

$db = new SQLite3('./scripts/birds.db', SQLITE3_OPEN_READONLY);
$db->busyTimeout(1000);
if($debug == false){
$statement1 = $db->prepare('SELECT DISTINCT(Com_Name), COUNT(*) FROM detections WHERE Date BETWEEN "'.date("Y-m-d",$startdate).'" AND "'.date("Y-m-d",$enddate).'" GROUP By Com_Name ORDER BY COUNT(*) DESC');
} else {
	$statement1 = $db->prepare('SELECT DISTINCT(Com_Name), COUNT(*) FROM detections WHERE Date BETWEEN "'.date("Y-m-d",$startdate).'" AND "'.date("Y-m-d",$enddate).'" GROUP By Com_Name ORDER BY COUNT(*) ASC');
}
ensure_db_ok($statement1);
$result1 = $statement1->execute();

$detections = [];
$i = 0;
while($detection=$result1->fetchArray(SQLITE3_ASSOC))
{
	if($debug == true){
		if($i > 10) { 
			break;
		}
	}
	$i++;
	$detections[$detection["Com_Name"]] = $detection["COUNT(*)"];
	
}
?>
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
	foreach($detections as $com_name=>$scount)
	{
		$i++;
		if($i <= 10) {
			$statement2 = $db->prepare('SELECT COUNT(*) FROM detections WHERE Com_Name == "'.$com_name.'" AND Date BETWEEN "'.date("Y-m-d",$startdate - (7*86400)).'" AND "'.date("Y-m-d",$enddate - (7*86400)).'"');
			ensure_db_ok($statement2);
			$result2 = $statement2->execute();
			$totalcount = $result2->fetchArray(SQLITE3_ASSOC);
			$priorweekcount = $totalcount['COUNT(*)'];

			$percentagediff = safe_percentage($scount, $priorweekcount);
			if($percentagediff > 0) {
				$percentagediff = "<span style='color:green;font-size:small'>+".$percentagediff."%</span>";
			} else {
				$percentagediff = "<span style='color:red;font-size:small'>-".abs($percentagediff)."%</span>";
			}

			echo "<tr><td>".$com_name."<br><small style=\"font-size:small\">".$scount." (".$percentagediff.")</small><br></td></tr>";
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
	foreach($detections as $com_name=>$scount)
	{
		$statement3 = $db->prepare('SELECT COUNT(*) FROM detections WHERE Com_Name == "'.$com_name.'" AND Date NOT BETWEEN "'.date("Y-m-d",$startdate).'" AND "'.date("Y-m-d",$enddate).'"');
		ensure_db_ok($statement3);
		$result3 = $statement3->execute();
		$totalcount = $result3->fetchArray(SQLITE3_ASSOC);
		$nonthisweekcount = $totalcount['COUNT(*)'];

		if($nonthisweekcount == 0) {
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
