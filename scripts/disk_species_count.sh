#!/bin/bash

# Get default values
source /etc/birdnet/birdnet.conf
base_dir="$(readlink -f "$HOME/BirdSongs/Extracted/By_Date")"
cd "$base_dir" || exit 1

# Function to format numbers to k if ≥1000
format_k() {
    local value=$1
    if [ "$value" -ge 1000 ]; then
        awk -v v="$value" 'BEGIN { printf "%.1fk", v/1000 }'
    else
        echo "$value"
    fi
}

# Get bird names from the database
bird_names=$(sqlite3 -readonly "$HOME"/BirdNET-Pi/scripts/birds.db <<EOF
.headers off
.mode list
SELECT DISTINCT Com_Name FROM detections;
EOF
)

# Sanitize names for folder matching
sanitized_names="$(echo "$bird_names" | tr ' ' '_' | tr -d "'" | grep '[[:alnum:]]')"
sanitized_names=$(echo "$sanitized_names" | sed 's/_*$//')

# Count species
species_count=$(echo "$sanitized_names" | wc -l)
total_file_count=0

# Temp files
data_file=$(mktemp)
output_file=$(mktemp)

# Loop through each species
while read -r species; do
    # Count total files
    total=$(find */"$species" -type f -name "*[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]*.*" \
        -not -iname "*.png" 2>/dev/null | wc -l)
    total_file_count=$((total_file_count + total))

    # Format total
    total_display=$(format_k "$total")

    # Clean species name for display
    species_display=$(echo "$species" | tr '_' ' ')

    # Save padded sort key + display line
    printf "%05d %s : %s\n" "$total" "$total_display" "$species_display" >> "$data_file"
done <<<"$sanitized_names"

# Avoid TERM error if not running in a terminal
[ -t 1 ] && clear

# Build final output
{
    echo "BirdSongs stored on your drive"
    echo " "
    echo "Location : $base_dir: "
    echo "Free space    : $(df -h "$base_dir" | awk 'NR==2 {print $4}' | sed 's/G/ GB/; s/M/ MB/; s/K/ KB/')"
    echo "Total species : $species_count"
    echo "Total files   : $(format_k "$total_file_count")"
    echo "Total size    : $(du -sh . | sed 's/G/ GB/; s/M/ MB/; s/K/ KB/' | cut -f1)"
    echo " "
    sort -r "$data_file" | sed 's/^[0-9]* //'
} > "$output_file"

# Show results
cat "$output_file"

# Clean up
rm -f "$data_file" "$output_file"
