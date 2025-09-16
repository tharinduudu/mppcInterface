#!/bin/bash
# Automatically runs ./main with a timestamped log filename

# Get current date and time in the format YYYY-MM-DD_HH-MM-SS
timestamp=$(date +"%Y-%m-%d_%H-%M-%S")

# Build filename
filename="Turkey_Obs_E5_${timestamp}.log"

# Run main script with generated filename
./main "$filename"
