"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "motion/react";
import {
  Users,
  Clock3,
  CalendarDays,
  Activity,
  Camera,
  Video,
  TriangleAlert,
  RefreshCcw,
  Upload,
  ChevronRight,
  TrendingUp,
  MapPin,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { fetchWaitingTime, analyserImage, analyserVideo, fetchStats } from "@/lib/api";

const SEUIL_ALERTE_MIN = 60;

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

type DureeParType = { type_rdv: string; avg_duree: number; nb: number };
type Stats = { total_today: number; avg_duree_globale: number; duree_par_type: DureeParType[] };
type VideoFrameResult = { frame: number; temps_secondes: number; occupied_count: number };
type VideoResult = { resultats: VideoFrameResult[]; moyenne_occupied: number; nb_frames_analysees: number };

function formatDuration(min: number) {
  if (min < 60) return `${Math.round(min)} min`;
  const h = Math.floor(min / 60);
  const m = Math.round(min % 60);
  return m > 0 ? `${h}h ${m}min` : `${h}h`;
}

export default function AttentePage() {
  const [data, setData]           = useState<WaitingTime | null>(null);
  const [stats, setStats]         = useState<Stats | null>(null);
  const [loading, setLoading]     = useState(true);
  const [countdown, setCountdown] = useState(30);
  const [lastUpdate, setLastUpdate] = useState("");
  const [refreshing, setRefreshing] = useState(false);

  const [yoloResult, setYoloResult]   = useState<WaitingTime | null>(null);
  const [yoloLoading, setYoloLoading] = useState(false);
  const [yoloError, setYoloError]     = useState<string | null>(null);
  const [preview, setPreview]         = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const [videoResult, setVideoResult]   = useState<VideoResult | null>(null);
  const [videoLoading, setVideoLoading] = useState(false);
  const [videoError, setVideoError]     = useState<string | null>(null);
  const [videoPreview, setVideoPreview] = useState<string | null>(null);
  const [intervalleFrames, setIntervalleFrames] = useState(30);
  const videoRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async (silent = false) => {
    if (silent) setRefreshing(true);
    try {
      const [waitingTime, statsData] = await Promise.all([fetchWaitingTime(), fetchStats()]);
      setData(waitingTime);
      setStats(statsData);
      setLastUpdate(new Date().toLocaleTimeString("fr-FR"));
    } catch {
      setData(null);
    } finally {
      setLoading(false);
      setRefreshing(false);
      setCountdown(30);
    }
  }, []);

  useEffect(() => {
    load();
    const interval = setInterval(() => load(true), 30000);
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
      setYoloResult(await analyserImage(file));
    } catch {
      setYoloError("Erreur lors de l'analyse. Vérifiez que le service YOLO est actif.");
    } finally {
      setYoloLoading(false);
    }
  };

  const handleVideo = async (file: File) => {
    setVideoPreview(URL.createObjectURL(file));
    setVideoResult(null);
    setVideoError(null);
    setVideoLoading(true);
    try {
      setVideoResult(await analyserVideo(file, intervalleFrames));
    } catch {
      setVideoError("Erreur lors de l'analyse vidéo. Vérifiez que le service YOLO est actif.");
    } finally {
      setVideoLoading(false);
    }
  };

  const alerte = data && data.temps_attente_min >= SEUIL_ALERTE_MIN;

  if (loading) {
    return (
      <div className="waiting-display flex flex-col gap-6">
        <Skeleton className="h-10 w-64 rounded-full" />
        <Skeleton className="h-[340px] w-full rounded-[28px]" />
        <div className="grid gap-4 sm:grid-cols-3">
          <Skeleton className="h-32 rounded-[24px]" />
          <Skeleton className="h-32 rounded-[24px]" />
          <Skeleton className="h-32 rounded-[24px]" />
        </div>
      </div>
    );
  }

  return (
    <main className="waiting-display flex flex-col gap-6">

      {/* Header */}
      <div className="page-header">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div className="space-y-3">
            <div className="page-eyebrow">
              <Activity className="h-4 w-4" />
              Salle d&apos;attente · SmartWaiting
            </div>
            <div>
              <h1 className="page-title text-balance">Votre temps d&apos;attente</h1>
              <p className="page-subtitle">
                Estimation en temps réel basée sur l&apos;occupation de la salle et l&apos;historique des consultations.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/webcam">
              <Button variant="outline" size="sm" className="gap-2">
                <Camera className="h-4 w-4" />
                Webcam live
              </Button>
            </Link>
            <Button variant="outline" size="sm" onClick={() => load(true)} disabled={refreshing} className="gap-2">
              <RefreshCcw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
              Actualiser
            </Button>
          </div>
        </div>
      </div>

      {!data ? (
        <Card className="card-modern">
          <CardContent className="flex flex-col items-center justify-center gap-4 py-16 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-destructive/10 text-destructive">
              <TriangleAlert className="h-8 w-8" />
            </div>
            <p className="text-lg font-semibold">Impossible de contacter le serveur</p>
            <p className="text-sm text-muted-foreground">Vérifiez que le backend est en ligne.</p>
            <Button onClick={() => load()} className="gap-2">
              <RefreshCcw className="h-4 w-4" />
              Réessayer
            </Button>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Alerte attente longue */}
          <AnimatePresence>
            {alerte && (
              <motion.div
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                className="flex items-start gap-3 rounded-2xl border border-destructive/30 bg-destructive/8 p-4"
              >
                <TriangleAlert className="mt-0.5 h-5 w-5 shrink-0 text-destructive" />
                <div>
                  <p className="font-semibold text-destructive">
                    Temps d&apos;attente élevé — {formatDuration(data.temps_attente_min)}
                  </p>
                  <p className="mt-0.5 text-sm text-destructive/80">
                    L&apos;attente dépasse {SEUIL_ALERTE_MIN} minutes. Passage estimé à {data.heure_passage ?? "—"}.
                  </p>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Hero — position + temps */}
          <div className="waiting-hero p-6 sm:p-10">
            <div className="flex flex-col items-center gap-6 text-center lg:flex-row lg:justify-between lg:text-left">
              <div>
                <p className="waiting-hero__label mb-3">Vous êtes en position</p>
                <div className="waiting-hero__big-number">
                  {data.patient_position ?? data.nb_personnes}
                </div>
                <p className="waiting-hero__sub mt-3">
                  {data.nb_personnes} personne{data.nb_personnes > 1 ? "s" : ""} en salle d&apos;attente
                </p>
              </div>

              <div className="grid w-full max-w-sm gap-4 sm:grid-cols-3 lg:max-w-none lg:w-auto lg:grid-cols-3">
                {[
                  { label: "Attente estimée", value: formatDuration(data.temps_attente_min), color: alerte ? "text-destructive" : "text-foreground" },
                  { label: "Passage estimé", value: data.heure_passage ?? "—", color: "text-success" },
                  { label: "Durée / patient", value: `${data.duree_par_patient} min`, color: "text-foreground" },
                ].map(({ label, value, color }) => (
                  <div key={label} className="soft-panel p-4 text-center">
                    <p className="mb-1 text-xs uppercase tracking-[0.14em] text-muted-foreground">{label}</p>
                    <p className={`text-2xl font-bold tabular-nums ${color}`}>{value}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="live-strip mt-6">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <span className="live-dot" />
                Mise à jour à {lastUpdate}
              </div>
              <span className="text-xs text-muted-foreground">
                Actualisation dans {countdown}s
              </span>
            </div>
          </div>

          {/* KPIs */}
          {stats && (
            <section className="metric-grid metric-grid--3">
              {[
                { label: "Patients aujourd'hui", value: stats.total_today, icon: CalendarDays, tone: "primary" },
                { label: "Durée moyenne globale", value: `${stats.avg_duree_globale} min`, icon: TrendingUp, tone: "success" },
                { label: "Source capteur", value: data.source_occupancy, icon: MapPin, tone: "warning" },
              ].map(({ label, value, icon: Icon, tone }) => (
                <div key={label} className="kpi-card">
                  <div className="mb-3 flex items-start justify-between gap-2">
                    <div>
                      <p className="kpi-card__label">{label}</p>
                      <p className="kpi-card__value capitalize">{value}</p>
                    </div>
                    <span className={`status-pill status-pill--${tone}`}>
                      <Icon className="h-3.5 w-3.5" />
                    </span>
                  </div>
                </div>
              ))}
            </section>
          )}

          {/* Contexte prédiction */}
          <Card className="card-modern">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Activity className="h-4 w-4 text-primary" />
                Contexte de la prédiction
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              <div className="flex flex-wrap gap-3">
                {[
                  { label: "Type RDV actif", value: data.type_rdv, tone: "primary" },
                  { label: "Jour", value: data.jour_semaine, tone: "primary" },
                  { label: "Saison", value: data.saison_annee, tone: "primary" },
                ].map(({ label, value, tone }) => (
                  <div key={label} className="soft-panel flex-1 min-w-[130px] p-3">
                    <p className="mb-1 text-xs text-muted-foreground">{label}</p>
                    <p className={`font-semibold status-pill--${tone} text-sm`}>{value}</p>
                  </div>
                ))}
              </div>
              <p className="rounded-2xl bg-muted/60 p-4 text-sm leading-7 text-muted-foreground">
                {data.message}
              </p>
            </CardContent>
          </Card>

          {/* Stats par type */}
          {stats && stats.duree_par_type.length > 0 && (
            <Card className="card-modern">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Clock3 className="h-4 w-4 text-primary" />
                  Durée moyenne par type de consultation
                </CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-3">
                {stats.duree_par_type.map(({ type_rdv, avg_duree, nb }) => (
                  <div key={type_rdv}>
                    <div className="mb-1 flex justify-between text-sm">
                      <span className="text-foreground">{type_rdv}</span>
                      <span className="text-muted-foreground tabular-nums">
                        {avg_duree} min <span className="text-xs">({nb} consultations)</span>
                      </span>
                    </div>
                    <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                      <div
                        className="h-full rounded-full bg-primary transition-all"
                        style={{ width: `${Math.min((avg_duree / 45) * 100, 100)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </>
      )}

      {/* Analyse image YOLO */}
      <Card className="card-modern">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Camera className="h-4 w-4 text-primary" />
            Analyse par photo (YOLO)
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <p className="text-sm text-muted-foreground">
            Uploadez une photo de la salle d&apos;attente — YOLO détecte les personnes et estime le temps d&apos;attente.
          </p>
          <div
            onDrop={(e) => { e.preventDefault(); const f = e.dataTransfer.files?.[0]; if (f) handleFile(f); }}
            onDragOver={(e) => e.preventDefault()}
            onClick={() => fileRef.current?.click()}
            className="soft-panel flex min-h-[140px] cursor-pointer flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed p-6 text-center transition-colors hover:border-primary/40 hover:bg-primary/5"
          >
            {preview ? (
              <img src={preview} alt="preview" className="max-h-[200px] max-w-full rounded-xl object-contain" />
            ) : (
              <>
                <Upload className="h-8 w-8 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">Glisser une photo ici ou cliquer</p>
              </>
            )}
          </div>
          <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }} />

          {yoloLoading && <p className="text-center text-sm text-muted-foreground">Analyse YOLO en cours...</p>}
          {yoloError && <p className="text-sm text-destructive">{yoloError}</p>}

          {yoloResult && (
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col gap-4">
              <div className="soft-panel p-5 text-center">
                <p className="mb-1 text-xs uppercase tracking-[0.14em] text-muted-foreground">Personnes détectées</p>
                <p className="text-5xl font-black text-success">{yoloResult.nb_personnes}</p>
              </div>
              <div className="grid grid-cols-3 gap-3">
                {[
                  { label: "Attente", value: formatDuration(yoloResult.temps_attente_min) },
                  { label: "Passage", value: yoloResult.heure_passage ?? "—" },
                  { label: "Durée/patient", value: `${yoloResult.duree_par_patient} min` },
                ].map(({ label, value }) => (
                  <div key={label} className="soft-panel p-3 text-center">
                    <p className="mb-1 text-xs text-muted-foreground">{label}</p>
                    <p className="font-bold tabular-nums">{value}</p>
                  </div>
                ))}
              </div>
            </motion.div>
          )}
        </CardContent>
      </Card>

      {/* Analyse vidéo YOLO */}
      <Card className="card-modern">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Video className="h-4 w-4 text-primary" />
            Analyse vidéo (YOLO)
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <p className="text-sm text-muted-foreground">
            Uploadez une vidéo — YOLO analyse chaque frame et retourne l&apos;occupation moyenne.
          </p>
          <div className="flex items-center gap-3">
            <label className="text-sm text-muted-foreground">1 frame toutes les</label>
            <input
              type="number" min={1} max={120} value={intervalleFrames}
              onChange={(e) => setIntervalleFrames(Math.max(1, Number(e.target.value)))}
              className="w-16 rounded-xl border border-input bg-background px-3 py-1.5 text-center text-sm"
            />
            <label className="text-sm text-muted-foreground">frames</label>
          </div>
          <div
            onDrop={(e) => { e.preventDefault(); const f = e.dataTransfer.files?.[0]; if (f) handleVideo(f); }}
            onDragOver={(e) => e.preventDefault()}
            onClick={() => videoRef.current?.click()}
            className="soft-panel flex min-h-[120px] cursor-pointer flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed p-6 text-center transition-colors hover:border-primary/40 hover:bg-primary/5"
          >
            {videoPreview ? (
              <video src={videoPreview} controls className="max-h-[180px] max-w-full rounded-xl" />
            ) : (
              <>
                <Video className="h-8 w-8 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">Glisser une vidéo (mp4, avi…) ou cliquer</p>
              </>
            )}
          </div>
          <input ref={videoRef} type="file" accept="video/*" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) handleVideo(f); }} />

          {videoLoading && <p className="text-center text-sm text-muted-foreground">Analyse en cours...</p>}
          {videoError && <p className="text-sm text-destructive">{videoError}</p>}

          {videoResult && (
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col gap-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="soft-panel p-4 text-center">
                  <p className="mb-1 text-xs text-muted-foreground">Occupation moyenne</p>
                  <p className="text-4xl font-black text-success">{videoResult.moyenne_occupied}</p>
                  <p className="text-xs text-muted-foreground">personnes</p>
                </div>
                <div className="soft-panel p-4 text-center">
                  <p className="mb-1 text-xs text-muted-foreground">Frames analysées</p>
                  <p className="text-4xl font-black text-primary">{videoResult.nb_frames_analysees}</p>
                </div>
              </div>
              <div className="table-shell max-h-[200px] overflow-y-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Frame</TableHead>
                      <TableHead>Temps (s)</TableHead>
                      <TableHead>Personnes</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {videoResult.resultats.map((r) => (
                      <TableRow key={r.frame}>
                        <TableCell className="tabular-nums">{r.frame}</TableCell>
                        <TableCell className="tabular-nums">{r.temps_secondes}s</TableCell>
                        <TableCell className="font-bold text-success tabular-nums">{r.occupied_count}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </motion.div>
          )}
        </CardContent>
      </Card>

      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>SmartWaiting · Salle d&apos;attente</span>
        <Link href="/" className="flex items-center gap-1 hover:text-foreground transition-colors">
          Interface médecin <ChevronRight className="h-3 w-3" />
        </Link>
      </div>
    </main>
  );
}
