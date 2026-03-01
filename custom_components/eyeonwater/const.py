"""Constants for the EyeOnWater integration."""

from datetime import timedelta

from aiohttp import ClientTimeout

SCAN_INTERVAL = timedelta(minutes=15)
DEBOUNCE_COOLDOWN = 60 * 60  # Seconds

# API client timeout configuration
CLIENT_TIMEOUT = ClientTimeout(total=30, connect=10, sock_read=20)

DATA_COORDINATOR = "coordinator"
DATA_SMART_METER = "smart_meter_data"

DOMAIN = "eyeonwater"
WATER_METER_NAME = "Water Meter"

COST_STAT_SUFFIX = "_cost"

IMPORT_HISTORICAL_DATA_SERVICE_NAME = "import_historical_data"
IMPORT_HISTORICAL_DATA_DAYS_NAME = "days"
IMPORT_HISTORICAL_DATA_DAYS_DEFAULT = 365

# Statistics validation limits
STATISTICS_VALIDATION_BATCH_SIZE = 1000  # Rows per database query batch
MAX_VIOLATION_LOG_DISPLAY = 10  # Maximum violations to log before truncating
