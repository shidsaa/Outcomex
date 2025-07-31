import logging
import os
from typing import Dict, Optional
from openai import OpenAI


logger = logging.getLogger(__name__)

class LLMReasoner:
    def __init__(self, model: str = "gpt-4o", temperature: float = 0.3):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("No OpenAI API key found. Skipping LLM reasoning.")
            self.client = None
        else:
            self.client = OpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature
        # TODO: This is a placeholder for the device mapper. We will need to implement this.
        # For example we can make different decisions for different devices.
        self.device_mapper = {
            "sensor-1": "sensor-1",
            "sensor-2": "sensor-2",
            "sensor-3": "sensor-3",
        }

    def reason_about_anomaly(self, record: Dict, detections: Optional[str] = "") -> Optional[str]:
        if not self.client:
            return None

        prompt = f"""
A sensor located in '{self.device_mapper[record['device_id']]}' reported the following readings:
PM2.5 = {record['pm2_5']}, PM10 = {record['pm10']}, dBA = {record['dBA']}, Vibration = {record['vibration']}.
Additional notes: {detections if detections else "No prior flags"}.

Does this seem like a true alert situation or a random anomaly? Justify briefly.
Respond in one line.
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                messages=[
                    {"role": "system", "content": "You are a smart environmental alert analyst."},
                    {"role": "user", "content": prompt}
                ]
            )
            decision = response.choices[0].message.content.strip()
            return decision
        except Exception as e:
            logger.error(f"LLM reasoning failed: {e}")
            return None
