#!/usr/bin/env bash

DB_PATH="$HOME/BirdNET-Pi/scripts/birds.db"

echo "Checking database schema for updates"

# Check if the tables exist
DETECTIONS_TABLE_EXISTS=$(sqlite3 "$DB_PATH" "SELECT name FROM sqlite_master WHERE type='table' AND name='detections';")
SCRIPTS_MTD_TABLE_EXISTS=$(sqlite3 "$DB_PATH" "SELECT name FROM sqlite_master WHERE type='table' AND name='scripts_metadata';")

if [ -z "$DETECTIONS_TABLE_EXISTS" ]; then
    echo "Table 'detections' does not exist. Creating table..."
    sqlite3 "$DB_PATH" << EOF
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
    CREATE INDEX "detections_Date_Time" ON "detections" ("Date" DESC, "Time" DESC);
EOF
    echo "Table 'detections' created successfully."
elif [ -z "$SCRIPTS_MTD_TABLE_EXISTS" ]; then
    echo "Table 'scripts_metadata' does not exist. Creating table..."
    sqlite3 "$DB_PATH" << EOF
    CREATE TABLE IF NOT EXISTS scripts_metadata (
        script_name TEXT PRIMARY KEY,
        last_run DATETIME
    );
EOF
    echo "Table 'scripts_metadata' created successfully."
else
    echo "Tables 'detections' and 'scripts_metadata' already exist. No changes made."
fi

echo "Database schema update complete."
