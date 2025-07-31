import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy import create_engine, text, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

Base = declarative_base()

class SensorData(Base):
    __tablename__ = 'sensor_data'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False)
    device_id = Column(String(50), nullable=False)
    pm2_5 = Column(Float)
    pm10 = Column(Float)
    dba = Column('dba', Float)
    vibration = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

class Anomaly(Base):
    __tablename__ = 'anomalies'
    
    id = Column(Integer, primary_key=True)
    sensor_data_id = Column(Integer)
    device_id = Column(String(50), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    anomaly_type = Column(String(50), nullable=False)
    sensor_field = Column(String(20), nullable=False)
    value = Column(Float)
    threshold = Column(Float)
    severity = Column(String(20), default='medium')
    llm_decision = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class SystemMetric(Base):
    __tablename__ = 'system_metrics'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False)
    service_name = Column(String(50), nullable=False)
    metric_name = Column(String(50), nullable=False)
    metric_value = Column(Float)
    metric_unit = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)

class DatabaseManager:
    def __init__(self):
        self.engine = None
        self.session_local = None
        self.connected = False
        
        self.db_host = os.environ.get("DB_HOST", "postgres")
        self.db_port = int(os.environ.get("DB_PORT", "5432"))
        self.db_name = os.environ.get("DB_NAME", "smartsensor")
        self.db_user = os.environ.get("DB_USER", "user")
        self.db_password = os.environ.get("DB_PASSWORD", "user123")
        
        logger.info(f"Database configuration: {self.db_host}:{self.db_port}/{self.db_name}")
    
    def connect(self) -> bool:
        try:
            database_url = f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
            
            self.engine = create_engine(
                database_url,
                pool_pre_ping=True,
                pool_recycle=300,
                echo=False
            )
            
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            self.session_local = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            
            Base.metadata.create_all(bind=self.engine)
            
            self.connected = True
            logger.info("Successfully connected to PostgreSQL database")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            self.connected = False
            return False
    
    def get_session(self) -> Optional[Session]:
        if not self.connected or not self.session_local:
            return None
        return self.session_local()
    
    def store_sensor_data(self, data: Dict[str, Any]) -> Optional[int]:
        if not self.connected:
            return None
        
        try:
            session = self.get_session()
            if not session:
                return None
            
            sensor_record = SensorData(
                timestamp=datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00')),
                device_id=data['device_id'],
                pm2_5=data.get('pm2_5'),
                pm10=data.get('pm10'),
                dba=data.get('dBA'),
                vibration=data.get('vibration')
            )
            
            session.add(sensor_record)
            session.commit()
            session.refresh(sensor_record)
            
            logger.debug(f"Stored sensor data: ID {sensor_record.id} for device {data['device_id']}")
            return sensor_record.id
            
        except SQLAlchemyError as e:
            logger.error(f"Database error storing sensor data: {e}")
            if session:
                session.rollback()
            return None
        except Exception as e:
            logger.error(f"Error storing sensor data: {e}")
            if session:
                session.rollback()
            return None
        finally:
            if session:
                session.close()
    
    def store_anomaly(self, sensor_data_id: int, device_id: str, timestamp: str, 
                     anomaly_type: str, sensor_field: str, value: float, 
                     threshold: float, severity: str = 'medium', 
                     llm_decision: str = None) -> bool:
        if not self.connected:
            return False
        
        try:
            session = self.get_session()
            if not session:
                return False
            
            anomaly_record = Anomaly(
                sensor_data_id=sensor_data_id,
                device_id=device_id,
                timestamp=datetime.fromisoformat(timestamp.replace('Z', '+00:00')),
                anomaly_type=anomaly_type,
                sensor_field=sensor_field,
                value=value,
                threshold=threshold,
                severity=severity,
                llm_decision=llm_decision
            )
            
            session.add(anomaly_record)
            session.commit()
            
            logger.info(f"Stored anomaly: {anomaly_type} for {device_id} - {sensor_field}: {value}")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"Database error storing anomaly: {e}")
            if session:
                session.rollback()
            return False
        except Exception as e:
            logger.error(f"Error storing anomaly: {e}")
            if session:
                session.rollback()
            return False
        finally:
            if session:
                session.close()
    
    def store_metric(self, service_name: str, metric_name: str, 
                    metric_value: float, metric_unit: str = None) -> bool:
        if not self.connected:
            return False
        
        try:
            session = self.get_session()
            if not session:
                return False
            
            metric_record = SystemMetric(
                timestamp=datetime.utcnow(),
                service_name=service_name,
                metric_name=metric_name,
                metric_value=metric_value,
                metric_unit=metric_unit
            )
            
            session.add(metric_record)
            session.commit()
            
            logger.debug(f"Stored metric: {service_name}.{metric_name} = {metric_value}")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"Database error storing metric: {e}")
            if session:
                session.rollback()
            return False
        except Exception as e:
            logger.error(f"Error storing metric: {e}")
            if session:
                session.rollback()
            return False
        finally:
            if session:
                session.close()
    
    def get_recent_sensor_data(self, limit: int = 100, device_id: str = None, hours: int = None) -> List[Dict]:
        if not self.connected:
            return []
        
        try:
            session = self.get_session()
            if not session:
                return []
            
            query = session.query(SensorData).order_by(SensorData.timestamp.desc())
            
            if device_id:
                query = query.filter(SensorData.device_id == device_id)
            
            if hours is not None:
                from datetime import timedelta
                cutoff_time = datetime.utcnow() - timedelta(hours=hours)
                query = query.filter(SensorData.timestamp >= cutoff_time)
            
            records = query.limit(limit).all()
            
            result = []
            for record in records:
                result.append({
                    'id': record.id,
                    'timestamp': record.timestamp.isoformat(),
                    'device_id': record.device_id,
                    'pm2_5': record.pm2_5,
                    'pm10': record.pm10,
                    'dBA': record.dba,
                    'vibration': record.vibration,
                    'created_at': record.created_at.isoformat()
                })
            
            return result
            
        except SQLAlchemyError as e:
            logger.error(f"Database error getting sensor data: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting sensor data: {e}")
            return []
        finally:
            if session:
                session.close()
    
    def get_recent_anomalies(self, limit: int = 50, device_id: str = None) -> List[Dict]:
        if not self.connected:
            return []
        
        try:
            session = self.get_session()
            if not session:
                return []
            
            query = session.query(Anomaly).order_by(Anomaly.timestamp.desc())
            
            if device_id:
                query = query.filter(Anomaly.device_id == device_id)
            
            records = query.limit(limit).all()
            
            result = []
            for record in records:
                result.append({
                    'id': record.id,
                    'device_id': record.device_id,
                    'timestamp': record.timestamp.isoformat(),
                    'anomaly_type': record.anomaly_type,
                    'sensor_field': record.sensor_field,
                    'value': record.value,
                    'threshold': record.threshold,
                    'severity': record.severity,
                    'llm_decision': record.llm_decision,
                    'created_at': record.created_at.isoformat()
                })
            
            return result
            
        except SQLAlchemyError as e:
            logger.error(f"Database error getting anomalies: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting anomalies: {e}")
            return []
        finally:
            if session:
                session.close()
    
    def close(self):
        if self.engine:
            self.engine.dispose()
            logger.info("Database connection closed") 
