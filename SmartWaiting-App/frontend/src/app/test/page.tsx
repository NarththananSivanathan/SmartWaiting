"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  checkHealth,
  sendSensorData,
  fetchLatestOccupancy,
  fetchWaitingTime,
  analyserImage,
  startConsultation,
  endConsultation,
} from "@/lib/api";

type Result = { ok: boolean; data: unknown };

function ResultBox({ result }: { result: Result | null }) {
  if (!result) return null;
  return (
    <pre
      style={{
        marginTop: "0.75rem",
        padding: "0.75rem",
        background: result.ok ? "#f0fdf4" : "#fef2f2",
        border: `1px solid ${result.ok ? "#86efac" : "#fca5a5"}`,
        borderRadius: "6px",
        fontSize: "0.8rem",
        overflowX: "auto",
        color: result.ok ? "#166534" : "#b91c1c",
        whiteSpace: "pre-wrap",
        wordBreak: "break-all",
      }}
    >
      {JSON.stringify(result.data, null, 2)}
    </pre>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="card">
      <h2 style={{ marginBottom: "1rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
        {title}
      </h2>
      {children}
    </div>
  );
}

export default function TestPage() {
  const [healthResult, setHealthResult] = useState<Result | null>(null);

  // Sensor
  const [sensorCount, setSensorCount] = useState(3);
  const [sensorSource, setSensorSource] = useState<"sensor" | "camera">("sensor");
  const [sensorPosition, setSensorPosition] = useState<number | undefined>(undefined);
  const [sensorResult, setSensorResult] = useState<Result | null>(null);

  // Latest
  const [latestResult, setLatestResult] = useState<Result | null>(null);

  // Waiting time
  const [waitResult, setWaitResult] = useState<Result | null>(null);

  // YOLO
  const [yoloFile, setYoloFile] = useState<File | null>(null);
  const [yoloPreview, setYoloPreview] = useState<string | null>(null);
  const [yoloResult, setYoloResult] = useState<Result | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  // Consultation
  const [consultResult, setConsultResult] = useState<Result | null>(null);
  const [activeConsultId, setActiveConsultId] = useState<number | null>(null);

  // Auto health check on mount
  useEffect(() => {
    checkHealth()
      .then((d) => setHealthResult({ ok: true, data: d }))
      .catch((e) => setHealthResult({ ok: false, data: { error: e.message } }));
  }, []);

  const run = async (fn: () => Promise<unknown>, setState: (r: Result) => void) => {
    try {
      const data = await fn();
      setState({ ok: true, data });
    } catch (e: unknown) {
      setState({ ok: false, data: { error: e instanceof Error ? e.message : String(e) } });
    }
  };

  const handleYoloFile = (file: File) => {
    setYoloFile(file);
    setYoloPreview(URL.createObjectURL(file));
    setYoloResult(null);
  };

  return (
    <div className="container">
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1.5rem" }}>
        <h1 style={{ margin: 0 }}>SmartWaiting — Page de test</h1>
        <div style={{ display: "flex", gap: "0.75rem" }}>
          <Link href="/" style={{ color: "#0070f3", textDecoration: "none", fontSize: "0.9rem" }}>
            Consultations
          </Link>
          <Link href="/attente" style={{ color: "#0070f3", textDecoration: "none", fontSize: "0.9rem" }}>
            Salle d&apos;attente
          </Link>
        </div>
      </div>

      {/* Health */}
      <Section title="1. Santé du backend — GET /health">
        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          <button
            className="btn-primary"
            onClick={() => run(checkHealth, setHealthResult)}
          >
            Tester /health
          </button>
          {healthResult && (
            <span style={{ fontSize: "0.9rem", color: healthResult.ok ? "#10b981" : "#ef4444", fontWeight: 600 }}>
              {healthResult.ok ? "Backend en ligne" : "Backend inaccessible"}
            </span>
          )}
        </div>
        <ResultBox result={healthResult} />
      </Section>

      {/* Sensor */}
      <Section title="2. Envoyer des données capteur — POST /api/occupancy/">
        <div style={{ display: "flex", flexWrap: "wrap", gap: "1rem", alignItems: "flex-end" }}>
          <div>
            <label style={{ display: "block", fontSize: "0.85rem", color: "#6b7280", marginBottom: "0.3rem" }}>
              Personnes occupées
            </label>
            <input
              type="number"
              min={0}
              max={50}
              value={sensorCount}
              onChange={(e) => setSensorCount(Number(e.target.value))}
              style={{ padding: "0.5rem", borderRadius: "6px", border: "1px solid #d1d5db", width: "80px" }}
            />
          </div>
          <div>
            <label style={{ display: "block", fontSize: "0.85rem", color: "#6b7280", marginBottom: "0.3rem" }}>
              Source
            </label>
            <select
              value={sensorSource}
              onChange={(e) => setSensorSource(e.target.value as "sensor" | "camera")}
              style={{ padding: "0.5rem", borderRadius: "6px", border: "1px solid #d1d5db" }}
            >
              <option value="sensor">sensor (IoT)</option>
              <option value="camera">camera (script YOLO)</option>
            </select>
          </div>
          <div>
            <label style={{ display: "block", fontSize: "0.85rem", color: "#6b7280", marginBottom: "0.3rem" }}>
              Position patient (optionnel)
            </label>
            <input
              type="number"
              min={1}
              placeholder="—"
              value={sensorPosition ?? ""}
              onChange={(e) => setSensorPosition(e.target.value ? Number(e.target.value) : undefined)}
              style={{ padding: "0.5rem", borderRadius: "6px", border: "1px solid #d1d5db", width: "80px" }}
            />
          </div>
          <button
            className="btn-primary"
            onClick={() => run(() => sendSensorData(sensorCount, sensorSource, sensorPosition), setSensorResult)}
          >
            Envoyer
          </button>
        </div>
        <ResultBox result={sensorResult} />
      </Section>

      {/* Latest */}
      <Section title="3. Dernière lecture d'occupation — GET /api/occupancy/latest">
        <button
          className="btn-primary"
          onClick={() => run(fetchLatestOccupancy, setLatestResult)}
        >
          Récupérer
        </button>
        <ResultBox result={latestResult} />
      </Section>

      {/* Waiting time */}
      <Section title="4. Temps d'attente estimé — GET /api/occupancy/waiting-time">
        <p style={{ fontSize: "0.85rem", color: "#6b7280", marginBottom: "0.75rem" }}>
          Nécessite au moins une donnée d&apos;occupation en base et le service IA actif.
        </p>
        <button
          className="btn-primary"
          onClick={() => run(fetchWaitingTime, setWaitResult)}
        >
          Calculer le temps d&apos;attente
        </button>
        <ResultBox result={waitResult} />
      </Section>

      {/* YOLO */}
      <Section title="5. Analyse YOLO — POST /api/occupancy/analyser">
        <p style={{ fontSize: "0.85rem", color: "#6b7280", marginBottom: "0.75rem" }}>
          Envoie une image au service YOLO (port 8001) via le backend. Nécessite le service YOLO actif.
        </p>
        <div
          onDrop={(e) => { e.preventDefault(); const f = e.dataTransfer.files?.[0]; if (f) handleYoloFile(f); }}
          onDragOver={(e) => e.preventDefault()}
          onClick={() => fileRef.current?.click()}
          style={{
            border: "2px dashed #d1d5db", borderRadius: "8px", padding: "1.5rem",
            textAlign: "center", cursor: "pointer", background: "#f9fafb",
            minHeight: "120px", display: "flex", alignItems: "center",
            justifyContent: "center", flexDirection: "column", gap: "0.4rem",
          }}
        >
          {yoloPreview ? (
            <img src={yoloPreview} alt="preview" style={{ maxHeight: "160px", maxWidth: "100%", borderRadius: "6px" }} />
          ) : (
            <>
              <p style={{ color: "#6b7280", margin: 0 }}>Glisser une photo ici</p>
              <p style={{ color: "#9ca3af", fontSize: "0.8rem", margin: 0 }}>ou cliquer pour sélectionner</p>
            </>
          )}
        </div>
        <input ref={fileRef} type="file" accept="image/*" style={{ display: "none" }} onChange={(e) => { const f = e.target.files?.[0]; if (f) handleYoloFile(f); }} />
        {yoloFile && (
          <button
            className="btn-success"
            style={{ marginTop: "0.75rem" }}
            onClick={() => run(() => analyserImage(yoloFile!), setYoloResult)}
          >
            Analyser avec YOLO
          </button>
        )}
        <ResultBox result={yoloResult} />
      </Section>

      {/* Consultation */}
      <Section title="6. Consultations — POST /start & PATCH /end">
        <div style={{ display: "flex", gap: "1rem", alignItems: "center", flexWrap: "wrap" }}>
          <button
            className="btn-success"
            disabled={!!activeConsultId}
            onClick={() =>
              run(() => startConsultation("Consultation générale"), (r) => {
                setConsultResult(r);
                if (r.ok) setActiveConsultId((r.data as { id: number }).id);
              })
            }
          >
            Commencer consultation
          </button>
          <button
            className="btn-danger"
            disabled={!activeConsultId}
            onClick={() =>
              run(() => endConsultation(activeConsultId!), (r) => {
                setConsultResult(r);
                if (r.ok) setActiveConsultId(null);
              })
            }
          >
            Terminer consultation {activeConsultId ? `#${activeConsultId}` : ""}
          </button>
          {activeConsultId && (
            <span style={{ fontSize: "0.85rem", color: "#6b7280" }}>
              Consultation #{activeConsultId} en cours
            </span>
          )}
        </div>
        <ResultBox result={consultResult} />
      </Section>

      <div style={{ textAlign: "center", color: "#9ca3af", fontSize: "0.8rem", marginTop: "1rem", marginBottom: "2rem" }}>
        Backend : {process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}
      </div>
    </div>
  );
}
