"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import Link from "next/link";
import { fetchWaitingTime, analyserImage, fetchStats } from "@/lib/api";

type WaitingTime = {
  nb_personnes: number;
  patient_position: number | null;
  duree_par_patient: number;
  temps_attente_min: number;
  heure_passage: string | null;
  message: string;
  type_rdv: string;
  jour_semaine: string;
  saison_annee: string;
  source_occupancy: string;
};

type DureeParType = {
  type_rdv: string;
  avg_duree: number;
  nb: number;
};

type Stats = {
  total_today: number;
  avg_duree_globale: number;
  duree_par_type: DureeParType[];
};

const SEUIL_ALERTE_MIN = 60;

function formatDuration(min: number) {
  if (min < 60) return `${Math.round(min)} min`;
  const h = Math.floor(min / 60);
  const m = Math.round(min % 60);
  return m > 0 ? `${h}h ${m}min` : `${h}h`;
}

export default function AttentePage() {
  const [data, setData] = useState<WaitingTime | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [countdown, setCountdown] = useState(30);
  const [lastUpdate, setLastUpdate] = useState("");

  const [yoloResult, setYoloResult] = useState<WaitingTime | null>(null);
  const [yoloLoading, setYoloLoading] = useState(false);
  const [yoloError, setYoloError] = useState<string | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    try {
      const [waitingTime, statsData] = await Promise.all([
        fetchWaitingTime(),
        fetchStats(),
      ]);
      setData(waitingTime);
      setStats(statsData);
      setLastUpdate(new Date().toLocaleTimeString("fr-FR"));
    } catch {
      setData(null);
    } finally {
      setLoading(false);
      setCountdown(30);
    }
  }, []);

  useEffect(() => {
    load();
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, [load]);

  useEffect(() => {
    const timer = setInterval(() => setCountdown((c) => (c > 0 ? c - 1 : 30)), 1000);
    return () => clearInterval(timer);
  }, []);

  const handleFile = async (file: File) => {
    setPreview(URL.createObjectURL(file));
    setYoloResult(null);
    setYoloError(null);
    setYoloLoading(true);
    try {
      const result = await analyserImage(file);
      setYoloResult(result);
    } catch {
      setYoloError("Erreur lors de l'analyse. Vérifiez que le service YOLO est actif.");
    } finally {
      setYoloLoading(false);
    }
  };

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file) handleFile(file);
  };

  const alerteActive = data && data.temps_attente_min >= SEUIL_ALERTE_MIN;

  return (
    <div className="container">
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1.5rem" }}>
        <h1>Salle d&apos;attente</h1>
        <Link href="/" style={{ color: "#0070f3", textDecoration: "none", fontSize: "0.9rem" }}>
          ← Retour
        </Link>
      </div>

      {loading ? (
        <div className="card" style={{ textAlign: "center", color: "#6b7280" }}>Chargement...</div>
      ) : !data ? (
        <div className="card" style={{ textAlign: "center", color: "#ef4444" }}>Impossible de contacter le serveur</div>
      ) : (
        <>
          {/* Alerte attente longue */}
          {alerteActive && (
            <div style={{
              background: "#fef2f2", border: "1px solid #fca5a5", borderRadius: "8px",
              padding: "1rem 1.5rem", marginBottom: "1.5rem",
              display: "flex", alignItems: "center", gap: "0.75rem",
            }}>
              <span style={{ fontSize: "1.4rem" }}>⚠️</span>
              <div>
                <p style={{ fontWeight: "700", color: "#b91c1c", margin: 0 }}>
                  Temps d&apos;attente élevé — {formatDuration(data.temps_attente_min)}
                </p>
                <p style={{ color: "#ef4444", fontSize: "0.85rem", margin: 0 }}>
                  L&apos;attente dépasse {SEUIL_ALERTE_MIN} minutes. Passage estimé à {data.heure_passage ?? "—"}.
                </p>
              </div>
            </div>
          )}

          {/* Position + temps d'attente */}
          <div className="card" style={{ textAlign: "center", padding: "2.5rem" }}>
            <p style={{ color: "#6b7280", marginBottom: "0.5rem", fontSize: "0.95rem" }}>Vous êtes en position</p>
            <div style={{ fontSize: "5rem", fontWeight: "800", color: "#0070f3", lineHeight: 1 }}>
              {data.patient_position ?? data.nb_personnes}
            </div>
            <p style={{ color: "#6b7280", marginTop: "0.5rem" }}>
              {data.nb_personnes} personne{data.nb_personnes > 1 ? "s" : ""} en salle d&apos;attente
            </p>
            <div style={{ margin: "2rem 0", borderTop: "1px solid #e5e7eb", paddingTop: "2rem", display: "flex", justifyContent: "center", gap: "4rem", flexWrap: "wrap" }}>
              <div>
                <p style={{ color: "#6b7280", fontSize: "0.85rem", marginBottom: "0.3rem" }}>Temps d&apos;attente estimé</p>
                <p style={{ fontSize: "2rem", fontWeight: "700", color: alerteActive ? "#ef4444" : "#111" }}>
                  {formatDuration(data.temps_attente_min)}
                </p>
              </div>
              <div>
                <p style={{ color: "#6b7280", fontSize: "0.85rem", marginBottom: "0.3rem" }}>Passage estimé</p>
                <p style={{ fontSize: "2rem", fontWeight: "700", color: "#10b981" }}>{data.heure_passage ?? "—"}</p>
              </div>
              <div>
                <p style={{ color: "#6b7280", fontSize: "0.85rem", marginBottom: "0.3rem" }}>Durée / patient</p>
                <p style={{ fontSize: "2rem", fontWeight: "700", color: "#111" }}>{data.duree_par_patient} min</p>
              </div>
            </div>
          </div>

          {/* Statistiques */}
          {stats && (
            <div className="card">
              <h2 style={{ marginBottom: "1.25rem" }}>Statistiques</h2>

              {/* KPIs globaux */}
              <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", marginBottom: "1.5rem" }}>
                <div style={{ flex: 1, minWidth: "140px", background: "#eff6ff", borderRadius: "8px", padding: "1rem", textAlign: "center" }}>
                  <p style={{ fontSize: "0.75rem", color: "#1e40af", marginBottom: "0.3rem" }}>Patients aujourd&apos;hui</p>
                  <p style={{ fontSize: "1.8rem", fontWeight: "700", color: "#1e40af" }}>{stats.total_today}</p>
                </div>
                <div style={{ flex: 1, minWidth: "140px", background: "#f0fdf4", borderRadius: "8px", padding: "1rem", textAlign: "center" }}>
                  <p style={{ fontSize: "0.75rem", color: "#166534", marginBottom: "0.3rem" }}>Durée moyenne globale</p>
                  <p style={{ fontSize: "1.8rem", fontWeight: "700", color: "#166534" }}>{stats.avg_duree_globale} min</p>
                </div>
                <div style={{ flex: 1, minWidth: "140px", background: "#fefce8", borderRadius: "8px", padding: "1rem", textAlign: "center" }}>
                  <p style={{ fontSize: "0.75rem", color: "#854d0e", marginBottom: "0.3rem" }}>Source capteur</p>
                  <p style={{ fontSize: "1rem", fontWeight: "700", color: "#854d0e", textTransform: "capitalize" }}>{data.source_occupancy}</p>
                </div>
              </div>

              {/* Durée par type */}
              {stats.duree_par_type.length > 0 && (
                <>
                  <p style={{ fontSize: "0.8rem", color: "#6b7280", marginBottom: "0.75rem", fontWeight: "600", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                    Durée moyenne par type de consultation
                  </p>
                  <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                    {stats.duree_par_type.map(({ type_rdv, avg_duree, nb }) => {
                      const pct = Math.round((avg_duree / 45) * 100);
                      return (
                        <div key={type_rdv}>
                          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.2rem" }}>
                            <span style={{ fontSize: "0.85rem", color: "#374151" }}>{type_rdv}</span>
                            <span style={{ fontSize: "0.85rem", color: "#6b7280" }}>{avg_duree} min <span style={{ fontSize: "0.75rem" }}>({nb} consultations)</span></span>
                          </div>
                          <div style={{ background: "#e5e7eb", borderRadius: "4px", height: "6px" }}>
                            <div style={{ background: "#0070f3", borderRadius: "4px", height: "6px", width: `${Math.min(pct, 100)}%` }} />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </>
              )}
            </div>
          )}

          {/* Contexte de la prédiction */}
          <div className="card">
            <h2>Contexte de la prédiction</h2>
            <div style={{ display: "flex", gap: "1rem", marginTop: "1rem", flexWrap: "wrap" }}>
              {[
                { label: "Type de RDV actif", value: data.type_rdv, bg: "#dbeafe", color: "#1e40af" },
                { label: "Jour", value: data.jour_semaine, bg: "#f3f4f6", color: "#374151" },
                { label: "Saison", value: data.saison_annee, bg: "#f3f4f6", color: "#374151" },
                { label: "Source capteur", value: data.source_occupancy, bg: "#dcfce7", color: "#166534" },
              ].map(({ label, value, bg, color }) => (
                <div key={label} style={{ flex: 1, minWidth: "140px", background: bg, borderRadius: "8px", padding: "1rem", textAlign: "center" }}>
                  <p style={{ fontSize: "0.75rem", color, marginBottom: "0.3rem" }}>{label}</p>
                  <p style={{ fontWeight: "700", color }}>{value}</p>
                </div>
              ))}
            </div>
            <p style={{ marginTop: "1.5rem", padding: "1rem", background: "#f9fafb", borderRadius: "8px", color: "#374151", fontSize: "0.9rem", lineHeight: "1.6" }}>
              {data.message}
            </p>
          </div>

          <div style={{ textAlign: "center", color: "#9ca3af", fontSize: "0.8rem", marginTop: "0.5rem" }}>
            Dernière mise à jour : {lastUpdate} — Actualisation dans {countdown}s
          </div>
        </>
      )}

      {/* YOLO */}
      <div className="card" style={{ marginTop: "2rem" }}>
        <h2 style={{ marginBottom: "1rem" }}>Analyse par caméra (YOLO)</h2>
        <p style={{ color: "#6b7280", fontSize: "0.9rem", marginBottom: "1rem" }}>
          Uploadez une photo de la salle d&apos;attente — YOLO détecte le nombre de personnes et estime le temps d&apos;attente.
        </p>

        <div
          onDrop={onDrop}
          onDragOver={(e) => e.preventDefault()}
          onClick={() => fileRef.current?.click()}
          style={{
            border: "2px dashed #d1d5db", borderRadius: "8px", padding: "2rem",
            textAlign: "center", cursor: "pointer", background: "#f9fafb",
            minHeight: "140px", display: "flex", alignItems: "center",
            justifyContent: "center", flexDirection: "column", gap: "0.5rem",
          }}
        >
          {preview ? (
            <img src={preview} alt="preview" style={{ maxHeight: "200px", maxWidth: "100%", borderRadius: "6px" }} />
          ) : (
            <>
              <p style={{ color: "#6b7280", margin: 0, fontSize: "1rem" }}>Glisser une photo ici</p>
              <p style={{ color: "#9ca3af", fontSize: "0.85rem", margin: 0 }}>ou cliquer pour sélectionner</p>
            </>
          )}
        </div>
        <input ref={fileRef} type="file" accept="image/*" style={{ display: "none" }} onChange={onFileChange} />

        {yoloLoading && (
          <p style={{ color: "#6b7280", textAlign: "center", marginTop: "1rem" }}>Analyse YOLO en cours...</p>
        )}
        {yoloError && (
          <p style={{ color: "#ef4444", marginTop: "1rem" }}>{yoloError}</p>
        )}

        {yoloResult && (
          <div style={{ marginTop: "1.5rem" }}>
            <div style={{ textAlign: "center", padding: "1.5rem", background: "#f0fdf4", borderRadius: "8px", marginBottom: "1rem" }}>
              <p style={{ color: "#6b7280", fontSize: "0.9rem", marginBottom: "0.3rem" }}>Personnes détectées par YOLO</p>
              <div style={{ fontSize: "3.5rem", fontWeight: "800", color: "#10b981", lineHeight: 1 }}>
                {yoloResult.nb_personnes}
              </div>
            </div>
            <div style={{ display: "flex", justifyContent: "center", gap: "4rem", flexWrap: "wrap", borderTop: "1px solid #e5e7eb", paddingTop: "1.5rem" }}>
              <div style={{ textAlign: "center" }}>
                <p style={{ color: "#6b7280", fontSize: "0.85rem", marginBottom: "0.3rem" }}>Temps d&apos;attente</p>
                <p style={{ fontSize: "2rem", fontWeight: "700", color: "#111" }}>{formatDuration(yoloResult.temps_attente_min)}</p>
              </div>
              <div style={{ textAlign: "center" }}>
                <p style={{ color: "#6b7280", fontSize: "0.85rem", marginBottom: "0.3rem" }}>Passage estimé</p>
                <p style={{ fontSize: "2rem", fontWeight: "700", color: "#10b981" }}>{yoloResult.heure_passage ?? "—"}</p>
              </div>
              <div style={{ textAlign: "center" }}>
                <p style={{ color: "#6b7280", fontSize: "0.85rem", marginBottom: "0.3rem" }}>Durée / patient</p>
                <p style={{ fontSize: "2rem", fontWeight: "700", color: "#111" }}>{yoloResult.duree_par_patient} min</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}