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

	$weekly_species_counts = get_weekly_report_species_detection_counts();

	ensure_db_ok($weekly_species_counts['detections']['success']);
	$result1 = $weekly_species_counts['detections']['data'];

	ensure_db_ok($weekly_species_counts['totalcount']['success']);
	$totalcount = $weekly_species_counts['totalcount']['data']['COUNT(*)'];

	ensure_db_ok($weekly_species_counts['priortotalcount']['success']);
	$priortotalcount = $weekly_species_counts['priortotalcount']['data']['COUNT(*)'];

	$weekly_species_talley = get_weekly_report_species_talley();

	ensure_db_ok($weekly_species_talley['totalspeciestally']['success']);
	$totalspeciestally = $weekly_species_talley['totalspeciestally']['data']['COUNT(DISTINCT(Com_Name))'];

	ensure_db_ok($weekly_species_talley['priortotalspeciestally']['success']);
	$priortotalspeciestally = $weekly_species_talley['priortotalspeciestally']['data']['COUNT(DISTINCT(Com_Name))'];

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
	foreach ($result1 as $detection)
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
			$statement2 = get_weekly_report_species_detection($com_name);
			ensure_db_ok($statement2['success']);
			$priorweekcount = $statement2['data']['COUNT(*)'];

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
		$statement3 = get_weekly_report_species_detection($com_name,false);
		ensure_db_ok($statement3['success']);
		$nonthisweekcount = $statement3['data']['COUNT(*)'];

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

if($debug == false){
	$weekly_species_counts = get_weekly_report_species_detection_counts();
	$result1 = $weekly_species_counts['detections']['data'];
	ensure_db_ok($weekly_species_counts['detections']['success']);
} else {
	$weekly_species_counts = get_weekly_report_species_detection_counts(false);
	$result1 = $weekly_species_counts['detections']['data'];
	ensure_db_ok($weekly_species_counts['detections']['success']);
}

$detections = [];
$i = 0;
foreach ($result1 as $detection)
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
<table align="center" style="box-shadow:unset"><tr><td style="background-color:#77c487">
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
			$statement2 = get_weekly_report_species_detection($com_name);
			ensure_db_ok($statement2['success']);
			$priorweekcount = $statement2['data']['COUNT(*)'];

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
	</td><td style="background-color:#77c487">

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
		$statement3 = get_weekly_report_species_detection($com_name,false);
		ensure_db_ok($statement3['success']);
		$nonthisweekcount = $statement3['data']['COUNT(*)'];

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
