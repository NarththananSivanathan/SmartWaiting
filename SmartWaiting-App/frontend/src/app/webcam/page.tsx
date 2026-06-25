"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { motion } from "motion/react";
import {
  Camera,
  CameraOff,
  Play,
  Square,
  Zap,
  Users,
  Clock3,
  Timer,
  Activity,
  ChevronRight,
  RefreshCcw,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { analyserImage } from "@/lib/api";

type WaitingTime = {
  nb_personnes: number;
  temps_attente_min: number;
  heure_passage: string | null;
  duree_par_patient: number;
  message: string;
  type_rdv: string;
  source_occupancy: string;
};

type HistoryEntry = { heure: string; nb_personnes: number };

function formatDuration(min: number) {
  if (min < 60) return `${Math.round(min)} min`;
  const h = Math.floor(min / 60);
  const m = Math.round(min % 60);
  return m > 0 ? `${h}h ${m}min` : `${h}h`;
}

export default function WebcamPage() {
  const videoRef    = useRef<HTMLVideoElement>(null);
  const canvasRef   = useRef<HTMLCanvasElement>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const countdownRef= useRef<ReturnType<typeof setInterval> | null>(null);

  const [stream, setStream]           = useState<MediaStream | null>(null);
  const [active, setActive]           = useState(false);
  const [intervalle, setIntervalle]   = useState(5);
  const [result, setResult]           = useState<WaitingTime | null>(null);
  const [history, setHistory]         = useState<HistoryEntry[]>([]);
  const [loading, setLoading]         = useState(false);
  const [erreurCamera, setErreurCamera] = useState<string | null>(null);
  const [erreurAnalyse, setErreurAnalyse] = useState<string | null>(null);
  const [countdown, setCountdown]     = useState(0);

  useEffect(() => {
    if (stream && videoRef.current) {
      videoRef.current.srcObject = stream;
      videoRef.current.play().catch(() => {});
    }
  }, [stream]);

  const demarrerWebcam = async () => {
    setErreurCamera(null);
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user", width: { ideal: 1280 }, height: { ideal: 720 } },
      });
      setStream(mediaStream);
    } catch {
      setErreurCamera("Impossible d'accéder à la caméra. Vérifiez les permissions du navigateur.");
    }
  };

  const arreterWebcam = useCallback(() => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    if (countdownRef.current) clearInterval(countdownRef.current);
    setActive(false);
    setCountdown(0);
    if (stream) { stream.getTracks().forEach((t) => t.stop()); setStream(null); }
  }, [stream]);

  const capturerEtAnalyser = useCallback(async () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || video.readyState < 2) return;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d")?.drawImage(video, 0, 0);
    canvas.toBlob(async (blob) => {
      if (!blob) return;
      setLoading(true);
      setErreurAnalyse(null);
      try {
        const fichier = new File([blob], "webcam_frame.jpg", { type: "image/jpeg" });
        const data: WaitingTime = await analyserImage(fichier);
        setResult(data);
        setHistory((prev) => [{ heure: new Date().toLocaleTimeString("fr-FR"), nb_personnes: data.nb_personnes }, ...prev].slice(0, 30));
      } catch (e: unknown) {
        setErreurAnalyse(e instanceof Error ? e.message : "Erreur lors de l'analyse YOLO");
      } finally {
        setLoading(false);
      }
    }, "image/jpeg", 0.85);
  }, []);

  const demarrerAnalyse = useCallback(() => {
    setActive(true);
    setCountdown(intervalle);
    capturerEtAnalyser();
    intervalRef.current = setInterval(() => { capturerEtAnalyser(); setCountdown(intervalle); }, intervalle * 1000);
    countdownRef.current = setInterval(() => setCountdown((c) => (c > 0 ? c - 1 : intervalle)), 1000);
  }, [intervalle, capturerEtAnalyser]);

  const arreterAnalyse = () => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    if (countdownRef.current) clearInterval(countdownRef.current);
    setActive(false);
    setCountdown(0);
  };

  useEffect(() => () => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    if (countdownRef.current) clearInterval(countdownRef.current);
    if (stream) stream.getTracks().forEach((t) => t.stop());
  }, [stream]);

  const maxPersonnes = history.length > 0 ? Math.max(...history.map((h) => h.nb_personnes), 1) : 1;

  return (
    <main className="page-shell page-shell--wide flex flex-col gap-6">

      {/* Header */}
      <div className="page-header">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div className="space-y-3">
            <div className="page-eyebrow">
              <Camera className="h-4 w-4" />
              Détection en direct · SmartWaiting
            </div>
            <div>
              <h1 className="page-title text-balance">Webcam live</h1>
              <p className="page-subtitle">
                Analysez le flux caméra en temps réel avec YOLO pour estimer l&apos;occupation de la salle d&apos;attente.
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            <Link href="/attente"><Button variant="outline" size="sm">Salle d&apos;attente</Button></Link>
            <Link href="/"><Button variant="outline" size="sm">← Accueil</Button></Link>
          </div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">

        {/* Flux vidéo */}
        <div className="flex flex-col gap-4">
          <Card className="card-modern overflow-hidden">
            <div className="relative bg-black" style={{ aspectRatio: "16/9" }}>
              {stream ? (
                <>
                  <video ref={videoRef} autoPlay playsInline muted className="h-full w-full object-cover" />
                  {/* Overlay status */}
                  <div className="absolute left-3 top-3 flex items-center gap-2">
                    {active ? (
                      <span className="status-pill status-pill--success text-xs">
                        <span className="live-dot" /> En direct
                      </span>
                    ) : (
                      <span className="status-pill status-pill--primary text-xs">
                        <Camera className="h-3 w-3" /> Caméra active
                      </span>
                    )}
                  </div>
                  {/* Overlay résultat */}
                  {result && (
                    <div className="absolute bottom-3 left-3 rounded-2xl bg-black/70 px-4 py-2 backdrop-blur-sm">
                      <span className="text-3xl font-black text-green-400">{result.nb_personnes}</span>
                      <span className="ml-2 text-sm text-white/80">personne{result.nb_personnes > 1 ? "s" : ""}</span>
                    </div>
                  )}
                  {/* Countdown */}
                  {active && countdown > 0 && !loading && (
                    <div className="absolute right-3 top-3 rounded-full bg-black/60 px-3 py-1 text-xs text-white backdrop-blur-sm">
                      {countdown}s
                    </div>
                  )}
                  {loading && (
                    <div className="absolute right-3 top-3 rounded-full bg-primary/80 px-3 py-1 text-xs text-white backdrop-blur-sm">
                      Analyse...
                    </div>
                  )}
                </>
              ) : (
                <div className="flex h-full min-h-[240px] flex-col items-center justify-center gap-3 text-white/40">
                  <CameraOff className="h-12 w-12" />
                  <p className="text-sm">Caméra inactive</p>
                </div>
              )}
            </div>
            <canvas ref={canvasRef} className="hidden" />

            <CardContent className="flex flex-col gap-4 pt-4">
              {erreurCamera && (
                <p className="rounded-xl bg-destructive/10 p-3 text-sm text-destructive">{erreurCamera}</p>
              )}
              {erreurAnalyse && (
                <p className="rounded-xl bg-warning/10 p-3 text-sm text-warning">⚠ {erreurAnalyse}</p>
              )}

              <div className="flex flex-wrap items-center gap-3">
                {!stream ? (
                  <Button onClick={demarrerWebcam} className="gap-2">
                    <Camera className="h-4 w-4" />
                    Démarrer la caméra
                  </Button>
                ) : (
                  <>
                    {!active ? (
                      <Button onClick={demarrerAnalyse} className="gap-2">
                        <Play className="h-4 w-4" />
                        Lancer la détection
                      </Button>
                    ) : (
                      <Button variant="destructive" onClick={arreterAnalyse} className="gap-2">
                        <Square className="h-4 w-4" />
                        Arrêter
                      </Button>
                    )}
                    <Button variant="outline" onClick={capturerEtAnalyser} className="gap-2">
                      <Zap className="h-4 w-4" />
                      Capturer maintenant
                    </Button>
                    <Button variant="outline" onClick={arreterWebcam} className="ml-auto gap-2">
                      <CameraOff className="h-4 w-4" />
                      Éteindre
                    </Button>
                  </>
                )}

                <div className="flex items-center gap-2">
                  <label className="text-sm text-muted-foreground">Intervalle :</label>
                  <input
                    type="number" min={1} max={60} value={intervalle} disabled={active}
                    onChange={(e) => setIntervalle(Math.max(1, Number(e.target.value)))}
                    className="w-14 rounded-xl border border-input bg-background px-2 py-1.5 text-center text-sm"
                  />
                  <span className="text-sm text-muted-foreground">s</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Graphique historique */}
          {history.length > 0 && (
            <Card className="card-modern">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Activity className="h-4 w-4 text-primary" />
                  Historique des détections
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-end gap-1" style={{ height: 80 }}>
                  {[...history].reverse().map((h, i) => (
                    <div key={i} className="flex flex-1 flex-col items-center gap-1">
                      <div
                        className="w-full rounded-t-sm bg-primary transition-all"
                        style={{ height: `${Math.round((h.nb_personnes / maxPersonnes) * 68) + 4}px`, minHeight: 4 }}
                        title={`${h.heure} — ${h.nb_personnes} pers.`}
                      />
                    </div>
                  ))}
                </div>
                <div className="mt-1 flex justify-between text-xs text-muted-foreground">
                  <span>{[...history].reverse()[0]?.heure}</span>
                  <span>{history[0]?.heure}</span>
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Résultats */}
        <div className="flex flex-col gap-4">
          {result ? (
            <>
              <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
                <Card className="card-modern card-modern--hero text-center">
                  <CardContent className="pt-6">
                    <p className="page-eyebrow mx-auto mb-3 w-fit">
                      <Users className="h-4 w-4" />
                      Personnes détectées
                    </p>
                    <div className="waiting-hero__big-number">{result.nb_personnes}</div>
                    <p className="mt-2 text-sm text-muted-foreground capitalize">{result.source_occupancy}</p>
                  </CardContent>
                </Card>
              </motion.div>

              <Card className="card-modern">
                <CardContent className="pt-4 flex flex-col gap-3">
                  {[
                    { icon: Clock3, label: "Attente estimée", value: formatDuration(result.temps_attente_min) },
                    { icon: ChevronRight, label: "Passage estimé", value: result.heure_passage ?? "—" },
                    { icon: Timer, label: "Durée / patient", value: `${result.duree_par_patient} min` },
                  ].map(({ icon: Icon, label, value }) => (
                    <div key={label} className="soft-panel flex items-center justify-between p-3">
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Icon className="h-4 w-4" />
                        {label}
                      </div>
                      <span className="font-bold tabular-nums">{value}</span>
                    </div>
                  ))}
                </CardContent>
              </Card>

              <Card className="card-modern">
                <CardContent className="pt-4">
                  <p className="mb-2 text-xs uppercase tracking-[0.14em] text-muted-foreground">Type de RDV</p>
                  <p className="mb-3 font-semibold text-primary">{result.type_rdv}</p>
                  <p className="text-sm leading-7 text-muted-foreground">{result.message}</p>
                </CardContent>
              </Card>

              {history.length > 1 && (
                <Card className="card-modern">
                  <CardHeader>
                    <CardTitle className="text-sm">Dernières captures</CardTitle>
                  </CardHeader>
                  <CardContent className="max-h-[200px] overflow-y-auto flex flex-col gap-1 pt-0">
                    {history.map((h, i) => (
                      <div key={i} className="flex justify-between border-b border-border py-2 text-sm last:border-0">
                        <span className="text-muted-foreground tabular-nums">{h.heure}</span>
                        <span className="font-semibold text-primary tabular-nums">{h.nb_personnes} pers.</span>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              )}
            </>
          ) : (
            <Card className="card-modern">
              <CardContent className="flex flex-col items-center justify-center gap-3 py-16 text-center">
                <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted text-muted-foreground">
                  <Camera className="h-8 w-8" />
                </div>
                <p className="font-medium">Lance la caméra</p>
                <p className="text-sm text-muted-foreground">Les résultats apparaîtront ici après la première capture.</p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </main>
  );
}