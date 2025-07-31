import logging
import json
import aiohttp
from typing import Dict, List, Optional
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

logger = logging.getLogger(__name__)

class ActionHandler:
    def __init__(self):
        self.action_history = []
        self.escalation_levels = {
            "low": ["log"],
            "medium": ["log", "alert"],
            "high": ["log", "alert", "escalate"],
            "critical": ["log", "alert", "escalate", "emergency"]
        }
        
        # Action configurations
        self.config = {
            "email_enabled": False,
            "email_recipients": [],
            "slack_webhook": None,
            "log_file": "anomaly_actions.log",
            "n8n_webhook_url": "http://n8n:5678/webhook/smartsensor-alert",
            "telegram_enabled": True,
            # LLM Configuration
            "llm_enabled": os.getenv("LLM_ENABLED", "false").lower() == "true",
            "llm_api_key": os.getenv("LLM_API_KEY", ""),
            "llm_model": os.getenv("LLM_MODEL", "gpt-3.5-turbo"),
            "llm_max_tokens": int(os.getenv("LLM_MAX_TOKENS", "150"))
        }
        
        # Initialize LLM client if enabled
        self.llm_client = None
        if self.config["llm_enabled"] and self.config["llm_api_key"]:
            self._init_llm_client()

    def _init_llm_client(self):
        """Initialize LLM client for AI insights"""
        try:
            from openai import AsyncOpenAI
            self.llm_client = AsyncOpenAI(api_key=self.config["llm_api_key"])
            logger.info("LLM client initialized successfully")
        except ImportError:
            logger.warning("OpenAI library not installed. LLM features disabled.")
            self.config["llm_enabled"] = False
        except Exception as e:
            logger.error(f"Failed to initialize LLM client: {e}")
            self.config["llm_enabled"] = False

    async def _get_llm_insights(self, record: Dict, anomalies: List[Dict]) -> Optional[Dict]:
        """Get AI insights for the anomaly situation"""
        if not self.llm_client or not self.config["llm_enabled"]:
            return None
        
        try:
            # Prepare context for LLM
            context = self._prepare_llm_context(record, anomalies)
            
            # Create prompt for LLM
            prompt = f"""
You are an AI assistant analyzing environmental sensor data anomalies. 

Context:
{context}

Please provide:
1. A brief analysis of what might be causing this anomaly
2. Recommended immediate actions
3. Potential risks if not addressed
4. Confidence level in your assessment (0-100%)

Keep your response concise and actionable. Focus on practical insights for sensor monitoring.
"""

            # Call LLM
            response = await self._call_llm(prompt)
            
            if response:
                return {
                    "analysis": response.get("analysis", ""),
                    "recommended_actions": response.get("recommended_actions", ""),
                    "potential_risks": response.get("potential_risks", ""),
                    "confidence_level": response.get("confidence_level", 0),
                    "ai_generated": True
                }
            
        except Exception as e:
            logger.error(f"Failed to get LLM insights: {e}")
        
        return None

    def _prepare_llm_context(self, record: Dict, anomalies: List[Dict]) -> str:
        """Prepare context string for LLM analysis"""
        device_id = record.get("device_id", "Unknown")
        timestamp = record.get("timestamp", "Unknown")
        
        # Sensor readings
        readings = f"""
Device: {device_id}
Timestamp: {timestamp}
Current Readings:
- PM2.5: {record.get('pm2_5', 'N/A')} µg/m³
- PM10: {record.get('pm10', 'N/A')} µg/m³
- dBA: {record.get('dBA', 'N/A')} dB
- Vibration: {record.get('vibration', 'N/A')} g
"""
        
        # Anomaly details
        anomaly_details = []
        for anomaly in anomalies:
            details = f"""
Anomaly Type: {anomaly.get('type', 'Unknown')}
Severity: {anomaly.get('severity', 'Unknown')}
Reason: {anomaly.get('reason', 'Unknown')}
Confidence: {anomaly.get('confidence', 'Unknown')}
"""
            anomaly_details.append(details)
        
        return readings + "\n".join(anomaly_details)

    async def _call_llm(self, prompt: str) -> Optional[Dict]:
        """Call LLM API"""
        try:
            from openai import AsyncOpenAI
            
            client = AsyncOpenAI(api_key=self.config["llm_api_key"])
            
            response = await client.chat.completions.create(
                model=self.config["llm_model"],
                messages=[
                    {"role": "system", "content": "You are an AI assistant specializing in environmental sensor monitoring and anomaly analysis."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.config["llm_max_tokens"],
                temperature=0.3
            )
            
            content = response.choices[0].message.content
            
            # Parse the response into structured format
            return self._parse_llm_response(content)
            
        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            return None

    def _parse_llm_response(self, content: str) -> Dict:
        """Parse LLM response into structured format"""
        try:
            # Simple parsing - extract key insights
            lines = content.split('\n')
            analysis = ""
            recommended_actions = ""
            potential_risks = ""
            confidence_level = 50  # Default
            
            for line in lines:
                line = line.strip()
                if "analysis" in line.lower() or "causing" in line.lower():
                    analysis += line + " "
                elif "action" in line.lower() or "recommend" in line.lower():
                    recommended_actions += line + " "
                elif "risk" in line.lower() or "danger" in line.lower():
                    potential_risks += line + " "
                elif "confidence" in line.lower():
                    # Try to extract confidence number
                    import re
                    match = re.search(r'(\d+)', line)
                    if match:
                        confidence_level = int(match.group(1))
            
            return {
                "analysis": analysis.strip() or "AI analysis unavailable",
                "recommended_actions": recommended_actions.strip() or "Monitor closely",
                "potential_risks": potential_risks.strip() or "Standard monitoring required",
                "confidence_level": confidence_level
            }
            
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return {
                "analysis": "AI analysis unavailable",
                "recommended_actions": "Monitor closely",
                "potential_risks": "Standard monitoring required",
                "confidence_level": 50
            }

    async def handle_anomalies(self, anomalies: List[Dict], record: Dict) -> List[Dict]:
        """
        Handle detected anomalies by taking appropriate actions
        """
        actions_taken = []
        
        for anomaly in anomalies:
            severity = anomaly.get("severity", "medium")
            actions = self.escalation_levels.get(severity, ["log"])
            
            for action_type in actions:
                action_result = await self._execute_action(action_type, anomaly, record)
                if action_result:
                    actions_taken.append(action_result)
        
        return actions_taken

    async def _execute_action(self, action_type: str, anomaly: Dict, record: Dict) -> Optional[Dict]:
        """Execute a specific action"""
        try:
            if action_type == "log":
                return self._log_anomaly(anomaly, record)
            elif action_type == "alert":
                return await self._send_alert(anomaly, record)
            elif action_type == "escalate":
                return self._escalate_anomaly(anomaly, record)
            elif action_type == "emergency":
                return self._emergency_action(anomaly, record)
            else:
                logger.warning(f"Unknown action type: {action_type}")
                return None
        except Exception as e:
            logger.error(f"Error executing action {action_type}: {e}")
            return None

    def _log_anomaly(self, anomaly: Dict, record: Dict) -> Dict:
        """Log anomaly details for audit trail"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": "log",
            "anomaly": anomaly,
            "device_id": record.get("device_id"),
            "sensor_data": {k: v for k, v in record.items() if k in ["pm2_5", "pm10", "dBA", "vibration"]}
        }
        
        # Log to file
        try:
            with open(self.config["log_file"], "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to write to log file: {e}")
        
        # Log to console
        logger.warning(f"ANOMALY DETECTED: {anomaly.get('reason', 'Unknown reason')} "
                      f"for device {record.get('device_id')}")
        
        self.action_history.append(log_entry)
        return log_entry

    async def _send_alert(self, anomaly: Dict, record: Dict) -> Dict:
        """Send alert via N8N webhook to Telegram with optional LLM insights"""
        alert_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": "alert",
            "anomaly": anomaly,
            "device_id": record.get("device_id"),
            "message": self._format_alert_message(anomaly, record)
        }
        
        # Get LLM insights if enabled
        if self.config["llm_enabled"]:
            try:
                llm_insights = await self._get_llm_insights(record, [anomaly])
                if llm_insights:
                    alert_entry["llm_insights"] = llm_insights
                    # Enhance message with AI insights
                    alert_entry["message"] = self._enhance_message_with_ai(alert_entry["message"], llm_insights)
                    logger.info(f"LLM insights added to alert for device {record.get('device_id')}")
            except Exception as e:
                logger.error(f"Failed to get LLM insights: {e}")
        
        # Send to N8N webhook for Telegram
        if self.config["telegram_enabled"]:
            try:
                await self._send_n8n_webhook(alert_entry)
                logger.info(f"Alert sent via N8N webhook for device {record.get('device_id')}")
            except Exception as e:
                logger.error(f"Failed to send N8N webhook: {e}")
        
        # Send email if configured
        if self.config["email_enabled"]:
            self._send_email_alert(alert_entry)
        
        self.action_history.append(alert_entry)
        return alert_entry

    def _enhance_message_with_ai(self, original_message: str, llm_insights: Dict) -> str:
        """Enhance alert message with AI insights"""
        ai_section = f"""

🤖 AI ANALYSIS:
{llm_insights.get('analysis', 'Analysis unavailable')}

💡 RECOMMENDED ACTIONS:
{llm_insights.get('recommended_actions', 'Monitor closely')}

⚠️ POTENTIAL RISKS:
{llm_insights.get('potential_risks', 'Standard monitoring required')}

🎯 CONFIDENCE: {llm_insights.get('confidence_level', 50)}%
        """
        
        return original_message + ai_section

    async def _send_n8n_webhook(self, alert_entry: Dict):
        """Send alert to N8N webhook for Telegram delivery"""
        try:
            webhook_data = {
                "device_id": alert_entry["device_id"],
                "anomaly_type": alert_entry["anomaly"].get("type", "unknown"),
                "severity": alert_entry["anomaly"].get("severity", "medium"),
                "reason": alert_entry["anomaly"].get("reason", "Unknown anomaly"),
                "sensor_data": alert_entry["anomaly"].get("sensor_data", {}),
                "timestamp": alert_entry["timestamp"],
                "message": alert_entry["message"]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.config["n8n_webhook_url"],
                    json=webhook_data,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        logger.info("N8N webhook sent successfully")
                    else:
                        logger.error(f"N8N webhook failed: {response.status}")
                        
        except Exception as e:
            logger.error(f"Error sending N8N webhook: {e}")
            raise

    def _escalate_anomaly(self, anomaly: Dict, record: Dict) -> Dict:
        """Escalate anomaly to higher level"""
        escalation_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": "escalate",
            "anomaly": anomaly,
            "device_id": record.get("device_id"),
            "escalation_level": anomaly.get("severity", "medium")
        }
        
        # Log escalation
        logger.warning(f"ESCALATING ANOMALY: {anomaly.get('reason')} "
                      f"for device {record.get('device_id')} to level {anomaly.get('severity')}")
        
        # Could trigger additional actions like:
        # - Send to management
        # - Create incident ticket
        # - Trigger emergency protocols
        
        self.action_history.append(escalation_entry)
        return escalation_entry

    def _emergency_action(self, anomaly: Dict, record: Dict) -> Dict:
        """Take emergency actions for critical anomalies"""
        emergency_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": "emergency",
            "anomaly": anomaly,
            "device_id": record.get("device_id"),
            "emergency_level": "critical"
        }
        
        # Immediate actions for critical situations
        logger.critical(f"EMERGENCY ACTION REQUIRED: {anomaly.get('reason')} "
                       f"for device {record.get('device_id')}")
        
        # Could trigger system shutdown, emergency protocols, etc.
        self._trigger_emergency_protocols(anomaly, record)
        
        self.action_history.append(emergency_entry)
        return emergency_entry

    def _format_alert_message(self, anomaly: Dict, record: Dict) -> str:
        """Format alert message for notifications"""
        device_id = record.get("device_id", "Unknown")
        reason = anomaly.get("reason", "Unknown anomaly")
        severity = anomaly.get("severity", "medium")
        anomaly_type = anomaly.get("type", "unknown")
        
        message = f"""
🚨 SMART SENSOR ALERT 🚨

Device: {device_id}
Severity: {severity.upper()}
Type: {anomaly_type}
Reason: {reason}

Current Readings:
- PM2.5: {record.get('pm2_5', 'N/A')} µg/m³
- PM10: {record.get('pm10', 'N/A')} µg/m³  
- dBA: {record.get('dBA', 'N/A')} dB
- Vibration: {record.get('vibration', 'N/A')} g

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        return message.strip()

    def _send_email_alert(self, alert_entry: Dict):
        """Send email alert (placeholder implementation)"""
        try:
            # This would be implemented with actual email sending logic
            logger.info(f"Email alert would be sent: {alert_entry['message'][:100]}...")
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")

    def _trigger_emergency_protocols(self, anomaly: Dict, record: Dict):
        """Trigger emergency protocols for critical situations"""
        logger.critical("EMERGENCY PROTOCOLS ACTIVATED")
        # Implement emergency actions like:
        # - System shutdown
        # - Emergency notifications
        # - Safety protocols
        pass

    def get_action_history(self) -> List[Dict]:
        """Get history of all actions taken"""
        return self.action_history.copy()

    def get_stats(self) -> Dict:
        """Get action statistics"""
        stats = {
            "total_actions": len(self.action_history),
            "actions_by_type": {},
            "recent_actions": self.action_history[-10:] if self.action_history else []
        }
        
        # Count actions by type
        for action in self.action_history:
            action_type = action.get("action", "unknown")
            stats["actions_by_type"][action_type] = stats["actions_by_type"].get(action_type, 0) + 1
        
        return stats
