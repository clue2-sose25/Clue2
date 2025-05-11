import os


DEFAULT_DAILY_USERS: int = 1000

DEFAULT_STAGE_DURATION: int = 3600

DEFAULT_USE_CURRENT_TIME: bool = True

DEFAULT_ENDPOINT: str = "Vanilla"

max_daily_users = int(os.environ.get("LOADGENERATOR_MAX_DAILY_USERS", DEFAULT_DAILY_USERS))

stage_duration = int(os.environ.get("LOADGENERATOR_STAGE_DURATION", DEFAULT_STAGE_DURATION))

try:
    use_real_time = os.environ.get("LOADGENERATOR_USE_CURRENTTIME", DEFAULT_USE_CURRENT_TIME).lower() in ["true", "yes", "1", "y"]
except:
    use_real_time = False

endpoint_name = str(os.environ.get("LOADGENERATOR_ENDPOINT_NAME", DEFAULT_ENDPOINT))

print("Config", flush=True)
print("Max Daily Users:", max_daily_users, flush=True)
print("Stage Duration:", stage_duration, flush=True)
print("Use Real Time:", use_real_time, flush=True)
print("Endpoint Name:", endpoint_name, flush=True)