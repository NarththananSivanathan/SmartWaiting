from pydantic import BaseModel, ConfigDict
from datetime import datetime, date
from typing import Optional, List


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ConsultationStart(BaseModel):
    type_rdv: Optional[str] = None

class ConsultationSetType(BaseModel):
    type_rdv: str

class ConsultationResponse(ORMBase):
    id: int
    heure_arrivee: datetime
    heure_depart: Optional[datetime] = None
    date: date
    duree_consultation: Optional[int] = None
    jour_semaine: str
    saison_annee: str
    type_rdv: Optional[str] = None

class PaginatedConsultations(BaseModel):
    total: int
    page: int
    size: int
    pages: int
    data: List[ConsultationResponse]


class OccupancyInput(BaseModel):
    room_id: Optional[str] = None
    timestamp: Optional[str] = None
    total_chairs: Optional[int] = None
    occupied_chairs: int
    free_chairs: Optional[int] = None
    occupancy_rate: Optional[float] = None
    patient_position: Optional[int] = None
    source: Optional[str] = None  # "sensor", "camera", "yolo" — "sensor" par défaut

class OccupancyReadingResponse(ORMBase):
    id: int
    occupied_count: int
    patient_position: Optional[int] = None
    source: str
    timestamp: datetime

class DureeParType(BaseModel):
    type_rdv: str
    avg_duree: float
    nb: int

class ConsultationStats(BaseModel):
    total_today: int
    avg_duree_globale: float
    duree_par_type: List[DureeParType]


class WaitingTimeResponse(BaseModel):
    nb_personnes: int
    patient_position: Optional[int] = None
    duree_par_patient: float
    temps_attente_min: float
    heure_passage: Optional[str] = None
    message: str
    type_rdv: str
    jour_semaine: str
    saison_annee: str
    source_occupancy: str
    timestamp: datetime


class VideoFrameResult(BaseModel):
    frame: int
    temps_secondes: float
    occupied_count: int

class VideoAnalysisResponse(BaseModel):
    resultats: List[VideoFrameResult]
    moyenne_occupied: float
    nb_frames_analysees: int
    timestamp: datetime
    source_occupancy: str = "yolo-video"
