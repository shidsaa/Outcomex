import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class Preprocessor:
    def __init__(self):
        # Define expected sensor keys and their valid ranges
        self.expected_fields = {
            "pm2_5": (0, 500),
            "pm10": (0, 500),
            "dBA": (30, 200),  # Increased to accommodate generator's alert values
            "vibration": (0, 100)  # Vibration should not be negative
        }

    def validate_and_normalize(self, record: Dict) -> Optional[Dict]:
        try:
            cleaned = {
                "timestamp": record["timestamp"],
                "device_id": record["device_id"]
            }

            for key, (min_val, max_val) in self.expected_fields.items():
                if key not in record:
                    logger.warning(f"Missing field: {key}")
                    return None
                value = float(record[key])
                if not (min_val <= value <= max_val):
                    logger.warning(f"Out-of-range value for {key}: {value}")
                    return None
                cleaned[key] = round(value, 3)

            return cleaned
        except Exception as e:
            logger.error(f"Error during preprocessing: {e}")
            return None
