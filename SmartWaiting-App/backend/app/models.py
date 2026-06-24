from sqlalchemy import Column, Integer, String, DateTime, Date
from datetime import datetime
from .database import Base


class Consultation(Base):
    __tablename__ = "consultations"

    id = Column(Integer, primary_key=True, index=True)
    heure_arrivee = Column(DateTime, nullable=False)
    heure_depart = Column(DateTime, nullable=True)
    date = Column(Date, nullable=False)
    duree_consultation = Column(Integer, nullable=True)  # en minutes
    jour_semaine = Column(String(20), nullable=False)
    saison_annee = Column(String(20), nullable=False)
    type_rdv = Column(String(100), nullable=True)


class OccupancyReading(Base):
    __tablename__ = "occupancy_readings"

    id = Column(Integer, primary_key=True, index=True)
    occupied_count = Column(Integer, nullable=False)
    patient_position = Column(Integer, nullable=True)
    source = Column(String(20), nullable=False)  # "sensor", "camera", "yolo"
    timestamp = Column(DateTime, default=datetime.now)
