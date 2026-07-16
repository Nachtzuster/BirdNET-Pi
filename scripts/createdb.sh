#!/usr/bin/env bash
source /etc/birdnet/birdnet.conf
sqlite3 $HOME/BirdNET-Pi/scripts/birds.db << EOF
DROP TABLE IF EXISTS detections;
CREATE TABLE IF NOT EXISTS detections (
  Date DATE,
  Time TIME,
  Sci_Name VARCHAR(100) NOT NULL,
  Com_Name VARCHAR(100) NOT NULL,
  Confidence FLOAT,
  Lat FLOAT,
  Lon FLOAT,
  Cutoff FLOAT,
  Week INT,
  Sens FLOAT,
  Overlap FLOAT,
  File_Name VARCHAR(100) NOT NULL);
CREATE INDEX "detections_Com_Name" ON "detections" ("Com_Name");
CREATE INDEX "detections_Sci_Name" ON "detections" ("Sci_Name");
CREATE INDEX "detections_Date_Time" ON "detections" ("Date" DESC, "Time" DESC);
-- Composite (Sci_Name, Date): overview.php - the default landing page - runs two
-- correlated subqueries filtering on BOTH columns. With only the Sci_Name index
-- each probe scans every historical row for that species; this makes them index
-- seeks instead.
CREATE INDEX IF NOT EXISTS "detections_Sci_Date" ON "detections" ("Sci_Name", "Date");
EOF
chown $USER:$USER $HOME/BirdNET-Pi/scripts/birds.db
chmod g+w $HOME/BirdNET-Pi/scripts/birds.db
