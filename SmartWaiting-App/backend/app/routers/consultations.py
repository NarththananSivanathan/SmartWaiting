from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from typing import List

from ..database import get_db
from ..models import Consultation
from ..schemas import ConsultationStart, ConsultationSetType, ConsultationResponse, PaginatedConsultations, ConsultationStats, DureeParType

router = APIRouter(prefix="/consultations", tags=["consultations"])

JOURS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

SAISONS = {
    1: "Hiver", 2: "Hiver", 3: "Printemps", 4: "Printemps", 5: "Printemps",
    6: "Été", 7: "Été", 8: "Été",
    9: "Automne", 10: "Automne", 11: "Automne", 12: "Hiver",
}


def _derive_fields(dt: datetime) -> dict:
    return {
        "date": dt.date(),
        "jour_semaine": JOURS[dt.weekday()],
        "saison_annee": SAISONS[dt.month],
    }


@router.post("/start", response_model=ConsultationResponse, status_code=201)
def start_consultation(payload: ConsultationStart, db: Session = Depends(get_db)):
    now = datetime.now()
    consultation = Consultation(
        heure_arrivee=now,
        type_rdv=payload.type_rdv,
        **_derive_fields(now),
    )
    db.add(consultation)
    db.commit()
    db.refresh(consultation)
    return consultation


@router.patch("/{consultation_id}/end", response_model=ConsultationResponse)
def end_consultation(consultation_id: int, db: Session = Depends(get_db)):
    consultation = db.query(Consultation).filter(Consultation.id == consultation_id).first()
    if not consultation:
        raise HTTPException(status_code=404, detail="Consultation non trouvée")
    if consultation.heure_depart:
        raise HTTPException(status_code=400, detail="La consultation est déjà terminée")

    now = datetime.now()
    consultation.heure_depart = now
    delta = now - consultation.heure_arrivee
    consultation.duree_consultation = int(delta.total_seconds() // 60)
    db.commit()
    db.refresh(consultation)
    return consultation


@router.patch("/{consultation_id}/type", response_model=ConsultationResponse)
def set_type_rdv(consultation_id: int, payload: ConsultationSetType, db: Session = Depends(get_db)):
    consultation = db.query(Consultation).filter(Consultation.id == consultation_id).first()
    if not consultation:
        raise HTTPException(status_code=404, detail="Consultation non trouvée")

    consultation.type_rdv = payload.type_rdv
    db.commit()
    db.refresh(consultation)
    return consultation


@router.get("/", response_model=PaginatedConsultations)
def list_consultations(page: int = 1, size: int = 20, db: Session = Depends(get_db)):
    if page < 1:
        page = 1
    if size < 1 or size > 100:
        size = 20
    total = db.query(Consultation).count()
    pages = (total + size - 1) // size
    items = (
        db.query(Consultation)
        .order_by(Consultation.heure_arrivee.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    return PaginatedConsultations(total=total, page=page, size=size, pages=pages, data=items)


@router.get("/stats", response_model=ConsultationStats)
def get_stats(db: Session = Depends(get_db)):
    today = datetime.now().date()

    total_today = db.query(func.count(Consultation.id)).filter(
        Consultation.date == today
    ).scalar() or 0

    avg_globale = db.query(func.avg(Consultation.duree_consultation)).filter(
        Consultation.duree_consultation > 0
    ).scalar()

    rows = (
        db.query(
            Consultation.type_rdv,
            func.avg(Consultation.duree_consultation).label("avg_duree"),
            func.count(Consultation.id).label("nb"),
        )
        .filter(Consultation.duree_consultation > 0, Consultation.type_rdv.isnot(None))
        .group_by(Consultation.type_rdv)
        .order_by(func.avg(Consultation.duree_consultation).desc())
        .all()
    )

    return ConsultationStats(
        total_today=total_today,
        avg_duree_globale=round(float(avg_globale), 1) if avg_globale else 0.0,
        duree_par_type=[
            DureeParType(type_rdv=r.type_rdv, avg_duree=round(float(r.avg_duree), 1), nb=r.nb)
            for r in rows
        ],
    )


@router.get("/{consultation_id}", response_model=ConsultationResponse)
def get_consultation(consultation_id: int, db: Session = Depends(get_db)):
    consultation = db.query(Consultation).filter(Consultation.id == consultation_id).first()
    if not consultation:
        raise HTTPException(status_code=404, detail="Consultation non trouvée")
    return consultation
