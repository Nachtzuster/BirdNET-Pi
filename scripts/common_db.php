<?php
//Reference to database connection
$DB_CONN = null;

/**
 * Connects to the bird.db SQLite3 database
 * @return SQLite3
 */
function connect_to_birdsdb($Open_ReadWrite=false)
{
	global $DB_CONN, $api_incl;

	//Initially check to see if the DB is already connected, it will not be null if it has
	if ($DB_CONN == null) {
		try {
			$flags = SQLITE3_OPEN_READONLY;
			if ($Open_ReadWrite) {
				$flags = SQLITE3_OPEN_READWRITE;
				debug_log("db_execute_query:: Opening DB as ReadWrite as query will modify the DB.");
			}

			$DB_CONN = new SQLite3(get_home() . "/BirdNET-Pi/scripts/birds.db", $flags);
			$DB_CONN->busyTimeout(1000);

			if ($DB_CONN == false) {
				debug_log("connect_to_birdsdb:: birds.db database is busy");
			}
		} catch (Exception $sql_exec) {
			debug_log("connect_to_birdsdb:: Exception occurred while trying to open birds.db - " . $sql_exec->getMessage());
		}
	}

	return $DB_CONN;
}

/**
 * Disconnects the database
 *
 * @return void
 */
function disconnect_from_birdsdb()
{
	global $DB_CONN;

	if ($DB_CONN != null) {
		return $DB_CONN->close();
	}
}

/**
 * Executes the supplied query and returns all results
 *
 * @param $query string The query to execute
 * @param $bind_params string Any values that should be bound into the query
 * @param $fetchAllRecords bool Any values that should be bound into the query
 * @param $fetchMode string Controls how result data is returned, default is @->default('SQLITE3_ASSOC') Associative Array;
 * @return array
 */
function db_execute_query($query, $bind_params = [], $fetchAllRecords = false, $fetchMode = SQLITE3_ASSOC)
{
	global $DB_CONN;
	$success = false;
	$message = '';
	$data_to_return = null;
	$Open_ReadWrite = false;

	//Open the database as RW if query intends to modify it
	if((strpos($query,"DELETE") !== false) || (strpos($query,"UPDATE") !== false))
	{
		$Open_ReadWrite = true;
	}

	//Connect to the DB
	connect_to_birdsdb($Open_ReadWrite);
	try {
		$stmt = $DB_CONN->prepare($query);
		//
		if (!empty($bind_params)) {
			//Loop over the bind values and add them
			foreach ($bind_params as $bind_key => $bind_value) {
				$stmt->bindValue($bind_key, $bind_value);
			}
		}

		if ($stmt == false) {
			//get caller's function name
			$caller_func_name = debug_backtrace(DEBUG_BACKTRACE_IGNORE_ARGS, 2)[1]['function'];
			$error_msg = "$caller_func_name => db_execute_query:: birds.db database is busy or a query error occurred";
			//
			$success = false;
			$message = $error_msg;
			$data_to_return = null;

			//Log the error message
			debug_log($error_msg);
		} else {
			$result = $stmt->execute();
			//Initial result collection
			$resultArray = $result->fetchArray($fetchMode);

			if ($fetchAllRecords) {
				$multiArray = array(); //array to store all rows
				//Loop over the results to collect them all
				while ($resultArray !== false) {
					array_push($multiArray, $resultArray); //insert all rows to $multiArray
					$resultArray = $result->fetchArray($fetchMode);
				}
				unset($resultArray); //unset temporary variable

				$data_to_return = $multiArray;
			} else {
				$data_to_return = $resultArray;
			}

			//
			$success = true;
			$message = 'Ok';
		}
	} catch (Exception $sql_exec) {
		$caller_func_name = debug_backtrace(DEBUG_BACKTRACE_IGNORE_ARGS, 2)[1]['function'];
		$error_msg = "$caller_func_name => db_execute_query:: Exception occurred while executing query - " . $sql_exec->getMessage();
		//
		$success = false;
		$message = $error_msg;
		$data_to_return = null;

		debug_log($error_msg);
	}

	return array('success' => $success, 'message' => $message, 'data' => $data_to_return);
}

/**
 * Returns a count of detections in the database
 * @return array
 */
function get_detection_count_all()
{
	return db_execute_query('SELECT COUNT(*) FROM detections');
}

/**
 * Returns today's count of detections in the database
 * @return array
 */
function get_detection_count_today()
{
	return db_execute_query('SELECT COUNT(*) FROM detections WHERE Date == DATE(\'now\', \'localtime\')');
}

/**
 * Returns detection info for the most recent detection today
 * @return array
 */
function get_most_recent_detection_today()
{
	return db_execute_query('SELECT * FROM detections WHERE Date == DATE(\'now\', \'localtime\') ORDER BY TIME DESC LIMIT 1', [], true);
}

/**
 * Returns a count of detections in the past hour
 * @return array
 */
function get_detection_count_last_hour()
{
	return db_execute_query('SELECT COUNT(*) FROM detections WHERE Date == Date(\'now\', \'localtime\') AND TIME >= TIME(\'now\', \'localtime\', \'-1 hour\')');
}

/**
 * Returns the most recent detection
 * @return array|string
 */
function get_most_recent_detection($limit = 1)
{
	return db_execute_query('SELECT Com_Name, Sci_Name, Date, Time, Confidence, File_Name  FROM detections ORDER BY Date DESC, Time DESC LIMIT :limit', [':limit' => $limit], true);
}

/**
 * Returns a talley for todays detected species, optionally
 * @param $range string Switch for what to get a species talley for, 'today' -> Today's Talley, 'custom' -> Talley all species from the specified $start_date param, 'range' -> Talley species within the $start_date and $end_date range
 * @param $start_date string Optional: Date filter for species talley from
 * @param $end_date string Optional: Date filter for species talley until
 * @return array
 */
function get_species_talley($range = "today", $start_date = null, $end_date = null)
{
	$range = strtolower($range);

	if ($range == "today") {
		$result = db_execute_query('SELECT COUNT(DISTINCT(Com_Name)) FROM detections WHERE Date == Date(\'now\', \'localtime\')');
	} else if ($range == "range") {
		$result = db_execute_query('SELECT COUNT(DISTINCT(Com_Name)) FROM detections WHERE Date BETWEEN :start_date AND :end_date', [':start_date' => $start_date, ':end_date' => $end_date]);
	}

	return $result;
}

/**
 * Returns a species talley from ALL detections
 * @return array
 */
function get_species_talley_all()
{
	return db_execute_query('SELECT COUNT(DISTINCT(Com_Name)) FROM detections');
}

/**
 * Returns the number of detections on the specified date
 *
 * @param $date string Date to count detections for
 * @return array
 */
function get_detection_count_by_date($date, $date_range = false)
{
	return db_execute_query("SELECT COUNT(*) FROM detections WHERE Date == :date", [':date' => $date], false);
}

/**
 * Returns detections and counts for the specified date and start & finish times
 *
 * @param $date string Date to count detections for
 * @param $starttime string Search for detections after this time
 * @param $endtime string And detections up to this time
 * @return array
 */
function get_detection_breakdown_by_time($date, $starttime, $endtime)
{
	return db_execute_query('SELECT DISTINCT(Com_Name), COUNT(*) FROM detections WHERE Date == :date AND Time > :start_time AND Time < :end_time AND Confidence > 0.75 GROUP By Com_Name ORDER BY COUNT(*) DESC',
		[
			':date' => $date,
			':start_time' => $starttime,
			':end_time' => $endtime
		],
		true);
}


/**
 * Returns the detection count for a specified bird
 * @param $birdName string Species Name to get stats for
 * @return array
 */
function get_detection_stats_last_30_days($birdName)
{
	//Cleanup the bird/species name
	$birdName = str_replace("_", " ", $birdName);

	$birdDetections = db_execute_query('SELECT Date, COUNT(*) AS Detections FROM detections WHERE Com_Name = :com_name AND Date BETWEEN DATE("now", "-30 days") AND DATE("now") GROUP BY Date', [':com_name' => $birdName], true);

	// Fetch the result set as an associative array
	$data = array();
	foreach ($birdDetections['data'] as $birdDetection) {
		$data[$birdDetection['Date']] = $birdDetection['Detections'];
	}

	// Create an array of all dates in the last 14 days
	$last14Days = array();
	for ($i = 0; $i < 31; $i++) {
		$last14Days[] = date('Y-m-d', strtotime("-$i days"));
	}

	// Merge the data array with the last14Days array
	$data = array_merge(array_fill_keys($last14Days, 0), $data);

	// Sort the data by date in ascending order
	ksort($data);

	// Convert the data to an array of objects
	$data = array_map(function ($date, $count) {
		return array('date' => $date, 'count' => $count);
	}, array_keys($data), $data);

	// Return the data as JSON - overwrite the result data
	$birdDetections['data'] = json_encode($data);

	return $birdDetections;
}

/**
 * Returns detection info for the specified
 * @param $birdName string Species name to get detection info on
 * @param $date string OPTIONAL - The date on which to list species on
 * @param $sort string OPTIONAL - Whether to sort the species by confidence value (so species ranked by detection accuracy/confidence)
 * @return array|string
 */
function get_species_detection_info($birdName, $date = null, $sort = null)
{
	//If no date is supplied, then list a unique list of detection dates in the DB, sorted descending
	if ($date == null) {
		//No date set so automatically search by date and time if no sort value is set
		if (isset($sort) && $sort == "confidence") {
			$detectionInfo = db_execute_query("SELECT * FROM detections where Com_Name == :birdname ORDER BY Confidence DESC", [':birdname' => $birdName], true);
		} else {
			$detectionInfo = db_execute_query("SELECT * FROM detections where Com_Name == :birdname ORDER BY Date DESC, Time DESC", [':birdname' => $birdName], true);
		}
	} else {
		//Date set so use that to filter the results depending on the sort value
		if (isset($sort) && $sort == "confidence") {
			$detectionInfo = db_execute_query("SELECT * FROM detections where Com_Name == :birdname AND Date == :date ORDER BY Confidence DESC", [':birdname' => $birdName, ':date' => $date], true);
		} else {
			$detectionInfo = db_execute_query("SELECT * FROM detections where Com_Name == :birdname AND Date == :date ORDER BY Time DESC", [':birdname' => $birdName, ':date' => $date], true);
		}
	}

	return $detectionInfo;
}

/**
 * Returns the detections for a specified filename
 *
 * @param $filename string The filename on which to get detections for
 * @return array|string
 */
function get_detections_by_filename($filename)
{
	return db_execute_query("SELECT * FROM detections where File_name == :filename ORDER BY Date DESC, Time DESC", [':filename' => $filename], true);
}

/**
 * Returns a list of specie names on a specified date if supplied, else lists valid dates which can be passed again for specific list of species on that date
 *
 * @param $date string OPTIONAL - The date on which to list species on
 * @param $sort string OPTIONAL - Whether to sort the species by occurrence (so species ranked by number of detections)
 * @return array|string
 */
function get_detections_by_date($date = null, $sort = null)
{

	//If no date is supplied, then list a unique list of species in the DB
	if ($date == null) {
		$detectionsByDateResult = db_execute_query('SELECT DISTINCT(Date) FROM detections GROUP BY Date ORDER BY Date DESC', null, true);
	} else {
		//Else a date was supplied, first check the sort order if any
		if (isset($sort) && $sort == "occurrences") {
			$detectionsByDateResult = db_execute_query("SELECT DISTINCT(Com_Name) FROM detections WHERE Date == :date GROUP BY Com_Name ORDER BY COUNT(*) DESC", [':date' => $date], true);
		} else {
			$detectionsByDateResult = db_execute_query("SELECT DISTINCT(Com_Name) FROM detections WHERE Date == :date ORDER BY Com_Name", [':date' => $date], true);
		}
	}

	return $detectionsByDateResult;
}

/**
 * Returns a list detections for a species if supplied, else lists all detected species by name
 *
 * @param $species_name string OPTIONAL - List detections for this specific species
 * @param $sort string OPTIONAL - Whether to sort the species by occurrence (so species ranked by number of detections)
 * @return array
 */
function get_detections_by_species($species_name = null, $sort = null)
{
	//If no species is  is supplied, then list all species
	if (!isset($species_name)) {
		if (isset($sort) && $sort == "occurrences") {
			//Sort by occurrences
			$speciesDetections = db_execute_query('SELECT DISTINCT(Com_Name) FROM detections GROUP BY Com_Name ORDER BY COUNT(*) DESC', null, true);
		} else {
			//Don't sort by occurrences
			$speciesDetections = db_execute_query('SELECT DISTINCT(Com_Name) FROM detections ORDER BY Com_Name ASC', null, true);
		}
	} else {
		//Else a species name was supplied, first check the sort order if any
		$speciesDetections = db_execute_query("SELECT * FROM detections WHERE Com_Name == :species_name ORDER BY Com_Name", [':species_name' => $species_name], true);
		//Also get the highest confidence record for this species
		$speciesDetections_MaxConf = db_execute_query("SELECT Date, Time, Sci_Name, MAX(Confidence), File_Name FROM detections WHERE Com_Name == :species_name ORDER BY Com_Name", [':species_name' => $species_name], true);
	}

	//Rearrange data
	$newReturnData = [];
	$newReturnData['species'] = $speciesDetections['data'];
	//Check to see if we have to get max confidence results for the species also
	if (isset($speciesDetections_MaxConf)) {
		$newReturnData['species_MaxConf'] = $speciesDetections_MaxConf['data'];
	}

	$speciesDetections['data'] = $newReturnData;

	return $speciesDetections;
}

/**
 * Returns a list of species either ordered alphabetically (default) or ordered by the number of detections the species has
 *
 * @param $sort string OPTIONAL - Sort result alphabetically (supply null) or by number of occurrences (supply "occurrences"
 * @return array
 */
function get_species_best_recording_list($sort = null)
{
	if (isset($sort) && $sort == "occurrences") {
		//Sort by occurrences
		$speciesBestRecording = db_execute_query('SELECT Date, Time, File_Name, Com_Name, COUNT(*), MAX(Confidence) FROM detections GROUP BY Com_Name ORDER BY COUNT(*) DESC', null, true);

	} else {
		//Don't sort by occurrences, sort by alphabetical
		$speciesBestRecording = db_execute_query('SELECT Date, Time, File_Name, Com_Name, COUNT(*), MAX(Confidence) FROM detections GROUP BY Com_Name ORDER BY Com_Name ASC', null, true);
	}

	return $speciesBestRecording;
}

/**
 * Returns a list of best recordings for a supplied species
 *
 * @param $species_name string Name of the species
 * @return array
 */
function get_best_recordings_for_species($species_name)
{
	return db_execute_query("SELECT Com_Name, Sci_Name, COUNT(*), MAX(Confidence), File_Name, Date, Time from detections WHERE Com_Name = :species_name", [':species_name' => $species_name], true);
}

/**
 * Get a list of todays detections
 *
 * @param $display_limit string Number of results to return
 * @param $search_term string OPTIONAL: Return results that match the supplied term
 * @param $hard_limit string OPTIONAL: Return a fix number of results
 * @return array
 */
function get_todays_detections($display_limit, $search_term = null, $hard_limit = null)
{
	$bind_params = [];

	if (isset($search_term)) {
		if (strtolower(explode(" ", $search_term)[0]) == "not") {
			$not = "NOT ";
			$operator = "AND";
			$search_term = str_replace("not ", "", $search_term);
			$search_term = str_replace("NOT ", "", $search_term);
		} else {
			$not = "";
			$operator = "OR";
		}
		$searchquery = "AND (Com_name " . $not . "LIKE :search_term " .
			$operator . " Sci_name " . $not . "LIKE :search_term " .
			$operator . " Confidence " . $not . "LIKE :search_term " .
			$operator . " File_Name " . $not . "LIKE :search_term " .
			$operator . " Time " . $not . "LIKE :search_term)";

		$bind_params = [':search_term' => '%' . $search_term . '%'];
	} else {
		$searchquery = "";
	}

	if (isset($display_limit) && is_numeric($display_limit)) {
		$bind_params[':display_limit'] = (intval($display_limit) - 40);
		$result = db_execute_query('SELECT Date, Time, Com_Name, Sci_Name, Confidence, File_Name FROM detections WHERE Date == Date(\'now\', \'localtime\') ' . $searchquery . ' ORDER BY Time DESC LIMIT :display_limit,40', $bind_params, true);
	} else {
		// legacy mode
		if (isset($hard_limit) && is_numeric($hard_limit)) {
			$bind_params[':hard_limit'] = $hard_limit;
			$result = db_execute_query('SELECT Date, Time, Com_Name, Sci_Name, Confidence, File_Name FROM detections WHERE Date == Date(\'now\', \'localtime\') ' . $searchquery . ' ORDER BY Time DESC LIMIT :hard_limit', $bind_params, true);
		} else {
			$result = db_execute_query('SELECT Date, Time, Com_Name, Sci_Name, Confidence, File_Name FROM detections WHERE Date == Date(\'now\', \'localtime\') ' . $searchquery . ' ORDER BY Time DESC', $bind_params, true);
		}
	}

	return $result;
}

/**
 * Returns the species talley for last week and the week prior to that
 *
 * @return array[]
 */
function get_weekly_report_species_talley()
{
	$last_week_dates = get_last_weeks_dates();
	$startdate = $last_week_dates['start_date'];
	$enddate = $last_week_dates['end_date'];


	$totalspeciestally = get_species_talley('range', date("Y-m-d", $startdate), date("Y-m-d", $enddate));
	$priortotalspeciestally = get_species_talley('range', date("Y-m-d", $startdate - (7 * 86400)), date("Y-m-d", $enddate - (7 * 86400)));

	return ['totalspeciestally' => $totalspeciestally, 'priortotalspeciestally' => $priortotalspeciestally];
}

/**
 * Returns the species talley for last week and the week prior
 *
 * @return array[]
 */
function get_weekly_report_species_detection_counts($detections_asc = false)
{
	$last_week_dates = get_last_weeks_dates();
	$startdate = $last_week_dates['start_date'];
	$enddate = $last_week_dates['end_date'];


	$sort_order = $detections_asc ? 'ASC' : 'DESC';

	$detections = db_execute_query('SELECT DISTINCT(Com_Name), COUNT(*) FROM detections WHERE Date BETWEEN :start_date AND :end_date GROUP By Com_Name ORDER BY COUNT(*) ' . $sort_order, [':start_date' => date("Y-m-d", $startdate), ':end_date' => date("Y-m-d", $enddate)], true);
	$totalcount = db_execute_query('SELECT DISTINCT(Com_Name), COUNT(*) FROM detections WHERE Date BETWEEN :start_date AND :end_date', [':start_date' => date("Y-m-d", $startdate), ':end_date' => date("Y-m-d", $enddate)], false);
	$priortotalcount = db_execute_query('SELECT DISTINCT(Com_Name), COUNT(*) FROM detections WHERE Date BETWEEN :start_date AND :end_date', [':start_date' => date("Y-m-d", strtotime(date("Y-m-d", $startdate - (7 * 86400)))), ':end_date' => date("Y-m-d", strtotime(date("Y-m-d", $enddate - (7 * 86400))))], false);

	return ['detections' => $detections, 'totalcount' => $totalcount, 'priortotalcount' => $priortotalcount];
}

/**
 * Returns last weeks detection count for the specified species
 *
 * @param string $species_name Species to get last weeks detection count for
 * @param bool $this_week Whether to find detections in or outside last week
 * @return array
 */
function get_weekly_report_species_detection($species_name, $this_week = true)
{
	$last_week_dates = get_last_weeks_dates();
	$startdate = $last_week_dates['start_date'];
	$enddate = $last_week_dates['end_date'];

	if ($this_week) {
		$result = db_execute_query('SELECT COUNT(*) FROM detections WHERE Com_Name == :species_name AND Date BETWEEN :start_date AND :end_date', [':species_name' => $species_name, ':start_date' => date("Y-m-d", $startdate - (7 * 86400)), ':end_date' => date("Y-m-d", $enddate - (7 * 86400))], false);
	} else {
		$result = db_execute_query('SELECT COUNT(*) FROM detections WHERE Com_Name == :species_name AND Date NOT BETWEEN :start_date AND :end_date', [':species_name' => $species_name, ':start_date' => date("Y-m-d", $startdate), ':end_date' => date("Y-m-d", $enddate)], false);
	}

	return $result;
}

/**
 * Deletes a specified detection by filename
 *
 * @param $filename string The filename of the detection e.g 2023-04-25/Pacific_Koel/Pacific_Koel-76-2023-04-25-birdnet-RTSP_2-16:24:05.mp3
 * @return array
 */
function delete_detection_by_filename($filename)
{
	$message = '';

	$filename_exploded = explode("/", $filename);
	$actual_filename = $filename_exploded[2];

	$statement = db_execute_query('DELETE FROM detections WHERE File_Name = :filename LIMIT 1', [':filename' => $actual_filename]);

	//
	$success = $statement['success'];
	//Message set above
	$data_to_return = $statement;

	return array('success' => $success, 'message' => $message, 'data' => $data_to_return);
}



register_shutdown_function('disconnect_from_birdsdb');