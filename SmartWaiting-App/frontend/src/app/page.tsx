"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { startConsultation, endConsultation, setTypeRdv, fetchConsultations } from "@/lib/api";

const TYPES_RDV = [
  "Consultation générale",
  "Consultation de suivi",
  "Urgence",
  "Vaccination",
  "Bilan de santé",
  "Autre",
];

type Consultation = {
  id: number;
  heure_arrivee: string;
  heure_depart: string | null;
  date: string;
  duree_consultation: number | null;
  jour_semaine: string;
  saison_annee: string;
  type_rdv: string | null;
};

type PaginatedResponse = {
  total: number;
  page: number;
  size: number;
  pages: number;
  data: Consultation[];
};

export default function Home() {
  const [consultations, setConsultations] = useState<Consultation[]>([]);
  const [active, setActive] = useState<Consultation | null>(null);
  const [page, setPage] = useState(1);
  const [meta, setMeta] = useState({ total: 0, pages: 1 });

  const loadConsultations = (p: number) => {
    fetchConsultations(p, 20).then((res: PaginatedResponse) => {
      setConsultations(res.data);
      setMeta({ total: res.total, pages: res.pages });
      const enCours = res.data.find((c: Consultation) => !c.heure_depart);
      if (enCours) setActive(enCours);
    });
  };

  useEffect(() => { loadConsultations(page); }, [page]);

  const handleStart = async () => {
    const c = await startConsultation("Consultation générale");
    setActive(c);
    setConsultations((prev) => [c, ...prev]);
  };

  const handleEnd = async () => {
    if (!active) return;
    const updated = await endConsultation(active.id);
    setActive(null);
    setConsultations((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
  };

  const handleType = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    if (!active) return;
    const updated = await setTypeRdv(active.id, e.target.value);
    setActive(updated);
    setConsultations((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
  };

  return (
    <div className="container">
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1.5rem" }}>
        <h1 style={{ margin: 0 }}>SmartWaiting — Consultations</h1>
        <div style={{ display: "flex", gap: "0.75rem" }}>
          <Link href="/attente" style={{ background: "#0070f3", color: "white", padding: "0.5rem 1.2rem", borderRadius: "6px", textDecoration: "none", fontSize: "0.95rem" }}>
            Voir la salle d&apos;attente →
          </Link>
          <Link href="/test" style={{ background: "#6b7280", color: "white", padding: "0.5rem 1.2rem", borderRadius: "6px", textDecoration: "none", fontSize: "0.95rem" }}>
            Tests API
          </Link>
        </div>
      </div>

      <div className="card">
        <h2>Consultation en cours</h2>
        {!active ? (
          <button className="btn-primary" onClick={handleStart}>
            Commencer la consultation
          </button>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            <p>Patient arrivé à <strong>{new Date(active.heure_arrivee).toLocaleTimeString("fr-FR")}</strong></p>
            <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
              <label>Type de rendez-vous :</label>
              <select
                value={active.type_rdv || ""}
                onChange={handleType}
                style={{ padding: "0.5rem", borderRadius: "6px", border: "1px solid #d1d5db" }}
              >
                {TYPES_RDV.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>
            <button className="btn-danger" onClick={handleEnd} style={{ width: "fit-content" }}>
              Le patient quitte le cabinet
            </button>
          </div>
        )}
      </div>

      <div className="card">
        <h2>Historique des consultations <span style={{ fontSize: "0.9rem", color: "#6b7280" }}>({meta.total} total)</span></h2>
        {consultations.length === 0 ? (
          <p style={{ color: "#6b7280" }}>Aucune consultation enregistrée.</p>
        ) : (
          <>
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Jour</th>
                  <th>Arrivée</th>
                  <th>Départ</th>
                  <th>Durée (min)</th>
                  <th>Saison</th>
                  <th>Type RDV</th>
                </tr>
              </thead>
              <tbody>
                {consultations.map((c) => (
                  <tr key={c.id}>
                    <td>{c.date}</td>
                    <td>{c.jour_semaine}</td>
                    <td>{new Date(c.heure_arrivee).toLocaleTimeString("fr-FR")}</td>
                    <td>{c.heure_depart ? new Date(c.heure_depart).toLocaleTimeString("fr-FR") : <span className="badge badge-waiting">En cours</span>}</td>
                    <td>{c.duree_consultation ?? "—"}</td>
                    <td>{c.saison_annee}</td>
                    <td>{c.type_rdv ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div style={{ display: "flex", alignItems: "center", gap: "1rem", marginTop: "1rem" }}>
              <button className="btn-primary" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}>
                &larr; Précédent
              </button>
              <span style={{ color: "#6b7280" }}>Page {page} / {meta.pages}</span>
              <button className="btn-primary" onClick={() => setPage((p) => Math.min(meta.pages, p + 1))} disabled={page === meta.pages}>
                Suivant &rarr;
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
