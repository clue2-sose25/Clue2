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

# Build the -f arguments for Locust carrying locust files
LOCUST_FILE_ARGS=""
IFS=',' read -ra FILES <<< "$LOCUST_FILE"
for i in "${FILES[@]}"; do
  LOCUST_FILE_ARGS+=" -f $i"
done

locust $LOCUST_FILE_ARGS --csv $SUT_NAME --csv-full-history --headless --only-summary 1>/dev/null 2>erros.log && tar zcf - ${SUT_NAME}_stats.csv ${SUT_NAME}_failures.csv ${SUT_NAME}_stats_history.csv erros.log | base64 -w 0