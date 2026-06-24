from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from typing import Optional
import httpx

from ..database import get_db
from ..models import OccupancyReading, Consultation
from ..schemas import OccupancyInput, OccupancyReadingResponse, WaitingTimeResponse
from ..config import settings

router = APIRouter(prefix="/occupancy", tags=["occupancy"])


async def _call_ia(position: int, type_rdv: str) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            response = await client.post(
                f"{settings.IA_API_URL}/predict/auto",
                json={"type_rdv": type_rdv, "position": position},
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Erreur service IA : {str(e)}")
    return response.json()


def _latest_reading(db: Session, source: Optional[str] = None) -> Optional[OccupancyReading]:
    q = db.query(OccupancyReading)
    if source:
        q = q.filter(OccupancyReading.source == source)
    return q.order_by(OccupancyReading.timestamp.desc()).first()


def _active_type_rdv(db: Session) -> str:
    active = db.query(Consultation).filter(
        Consultation.heure_depart == None,
        Consultation.type_rdv != None,
    ).order_by(Consultation.heure_arrivee.desc()).first()
    return active.type_rdv if active else "Consultation générale"


@router.post("/", response_model=OccupancyReadingResponse, status_code=201)
def receive_sensor(payload: OccupancyInput, db: Session = Depends(get_db)):
    reading = OccupancyReading(
        occupied_count=payload.occupied_chairs,
        patient_position=payload.patient_position,
        source=payload.source or "sensor",
        timestamp=datetime.now(),
    )
    db.add(reading)
    db.commit()
    db.refresh(reading)
    return reading


@router.post("/analyser", response_model=WaitingTimeResponse, status_code=201)
async def analyser_image_yolo(image: UploadFile = File(...), db: Session = Depends(get_db)):
    contenu = await image.read()

    # 1. Envoyer l'image au service YOLO → obtenir occupied_count
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.post(
                f"{settings.YOLO_API_URL}/analyser",
                files={"image": (image.filename, contenu, image.content_type)},
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Erreur service YOLO : {str(e)}")

    yolo_data = response.json()
    occupied_count = yolo_data["occupied_count"]

    # 2. Stocker la lecture YOLO
    reading = OccupancyReading(
        occupied_count=occupied_count,
        patient_position=None,
        source="yolo",
        timestamp=datetime.now(),
    )
    db.add(reading)
    db.commit()
    db.refresh(reading)

    # 3. Appeler le service IA avec occupied_count comme position
    type_rdv = _active_type_rdv(db)
    ia = await _call_ia(occupied_count, type_rdv)

    return WaitingTimeResponse(
        nb_personnes=occupied_count,
        patient_position=None,
        duree_par_patient=ia["duree_par_patient"],
        temps_attente_min=ia["temps_attente_min"],
        heure_passage=ia.get("heure_passage"),
        message=ia["message"],
        type_rdv=ia["type_rdv"],
        jour_semaine=ia["jour_semaine"],
        saison_annee=ia["saison_annee"],
        source_occupancy="yolo",
        timestamp=reading.timestamp,
    )


@router.get("/waiting-time", response_model=WaitingTimeResponse)
async def get_waiting_time(db: Session = Depends(get_db)):
    latest = _latest_reading(db)
    if not latest:
        raise HTTPException(status_code=404, detail="Aucune donnée d'occupation disponible")

    position = latest.patient_position if latest.patient_position is not None else latest.occupied_count
    type_rdv = _active_type_rdv(db)
    ia = await _call_ia(position, type_rdv)

    return WaitingTimeResponse(
        nb_personnes=latest.occupied_count,
        patient_position=latest.patient_position,
        duree_par_patient=ia["duree_par_patient"],
        temps_attente_min=ia["temps_attente_min"],
        heure_passage=ia.get("heure_passage"),
        message=ia["message"],
        type_rdv=ia["type_rdv"],
        jour_semaine=ia["jour_semaine"],
        saison_annee=ia["saison_annee"],
        source_occupancy=latest.source,
        timestamp=latest.timestamp,
    )


@router.get("/latest", response_model=OccupancyReadingResponse)
def get_latest(db: Session = Depends(get_db)):
    reading = _latest_reading(db)
    if not reading:
        raise HTTPException(status_code=404, detail="Aucune donnée d'occupation disponible")
    return reading
