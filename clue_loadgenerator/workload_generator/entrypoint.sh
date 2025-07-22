#!/bin/bash

# Check if LOCUST_FILE is provided
if [ -z "$LOCUST_FILE" ]; then
  echo "Error: LOCUST_FILE environment variable is not set."
  exit 1
fi

# Check if SUT_NAME is provided
if [ -z "$SUT_NAME" ]; then
  echo "Error: SUT_NAME environment variable is not set."
  exit 1
fi

# Check if LOCUST_RUN_TIME is provided
if [ -z "$LOCUST_RUN_TIME" ]; then
  echo "Error: LOCUST_RUN_TIME environment variable is not set."
  exit 1
fi

# Build the -f arguments for Locust carrying all locust files
LOCUST_FILE_ARGS=""
ALL_LOCUST_FILES=""
IFS=',' read -ra FILES <<< "$LOCUST_FILE"
for i in "${FILES[@]}"; do
  if [ -z "$ALL_LOCUST_FILES" ]; then
    ALL_LOCUST_FILES="$(basename $i)"
  else
    ALL_LOCUST_FILES+=",$(basename $i)"
  fi
done
LOCUST_FILE_ARGS="-f $ALL_LOCUST_FILES"

# Ensure the locustfiles directory exists
mkdir -p /app/locustfiles/
cd /app/locustfiles/

locust $LOCUST_FILE_ARGS --csv $SUT_NAME --csv-full-history --headless --only-summary --run-time $LOCUST_RUN_TIME --host $LOCUST_HOST 2>errors.log

SANITIZED_SUT_NAME=$(echo "$SUT_NAME" | sed 's/-/_/g')

# Try to find the actual files and use them
if ls ${SUT_NAME}_stats.csv 1> /dev/null 2>&1; then
    # Using original SUT name for files
    FILE_PREFIX="$SUT_NAME"
elif ls ${SANITIZED_SUT_NAME}_stats.csv 1> /dev/null 2>&1; then
    # Using sanitized SUT name for files
    FILE_PREFIX="$SANITIZED_SUT_NAME"
else
    # No stats files found, creating empty tar
    echo "No results generated" > no_results.txt
    tar zcf - no_results.txt errors.log | base64 -w 0
    exit 0
fi

# Tar and base64 encode the results so they can get pulled by the deployer with prefix: $FILE_PREFIX"
tar zcf - ${FILE_PREFIX}_stats.csv ${FILE_PREFIX}_failures.csv ${FILE_PREFIX}_stats_history.csv errors.log | base64 -w 0