"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "motion/react";
import {
  Activity,
  Send,
  Eye,
  Clock3,
  Camera,
  Video,
  Stethoscope,
  CheckCircle2,
  XCircle,
  Loader2,
  Upload,
  FlaskConical,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  checkHealth,
  sendSensorData,
  fetchLatestOccupancy,
  fetchWaitingTime,
  analyserImage,
  analyserVideo,
  startConsultation,
  endConsultation,
} from "@/lib/api";

type Result = { ok: boolean; data: unknown };

function ResultBox({ result }: { result: Result | null }) {
  if (!result) return null;
  return (
    <AnimatePresence>
      <motion.pre
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        className={`mt-3 overflow-x-auto rounded-2xl border p-4 text-xs leading-6 ${
          result.ok
            ? "border-success/30 bg-success/8 text-success"
            : "border-destructive/30 bg-destructive/8 text-destructive"
        }`}
        style={{ whiteSpace: "pre-wrap", wordBreak: "break-all" }}
      >
        {JSON.stringify(result.data, null, 2)}
      </motion.pre>
    </AnimatePresence>
  );
}

function Section({
  icon: Icon,
  title,
  index,
  children,
}: {
  icon: React.ElementType;
  title: string;
  index: number;
  children: React.ReactNode;
}) {
  return (
    <Card className="card-modern">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-3 text-base">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-primary text-sm font-bold">
            {index}
          </div>
          <Icon className="h-4 w-4 text-primary" />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

export default function TestPage() {
  const [healthResult, setHealthResult] = useState<Result | null>(null);
  const [sensorCount, setSensorCount]   = useState(3);
  const [sensorSource, setSensorSource] = useState<"sensor" | "camera">("sensor");
  const [sensorPosition, setSensorPosition] = useState<number | undefined>(undefined);
  const [sensorResult, setSensorResult] = useState<Result | null>(null);
  const [latestResult, setLatestResult] = useState<Result | null>(null);
  const [waitResult, setWaitResult]     = useState<Result | null>(null);
  const [yoloFile, setYoloFile]         = useState<File | null>(null);
  const [yoloPreview, setYoloPreview]   = useState<string | null>(null);
  const [yoloResult, setYoloResult]     = useState<Result | null>(null);
  const [videoFile, setVideoFile]       = useState<File | null>(null);
  const [videoPreview, setVideoPreview] = useState<string | null>(null);
  const [videoResult, setVideoResult]   = useState<Result | null>(null);
  const [intervalleFrames, setIntervalleFrames] = useState(30);
  const [consultResult, setConsultResult] = useState<Result | null>(null);
  const [activeConsultId, setActiveConsultId] = useState<number | null>(null);
  const [loading, setLoading]           = useState<string | null>(null);
  const fileRef  = useRef<HTMLInputElement>(null);
  const videoRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    run("health", checkHealth, setHealthResult);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const run = async (key: string, fn: () => Promise<unknown>, setState: (r: Result) => void) => {
    setLoading(key);
    try {
      setState({ ok: true, data: await fn() });
    } catch (e: unknown) {
      setState({ ok: false, data: { error: e instanceof Error ? e.message : String(e) } });
    } finally {
      setLoading(null);
    }
  };

  const Btn = ({ k, onClick, children }: { k: string; onClick: () => void; children: React.ReactNode }) => (
    <Button onClick={onClick} disabled={loading === k} className="gap-2">
      {loading === k ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
      {children}
    </Button>
  );

  return (
    <main className="page-shell flex flex-col gap-6">

      {/* Header */}
      <div className="page-header">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div className="space-y-3">
            <div className="page-eyebrow">
              <FlaskConical className="h-4 w-4" />
              Tests API · SmartWaiting
            </div>
            <div>
              <h1 className="page-title text-balance">Page de test</h1>
              <p className="page-subtitle">
                Testez tous les endpoints de l&apos;API directement depuis le navigateur.
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            <Link href="/"><Button variant="outline" size="sm">← Accueil</Button></Link>
            <Link href="/attente"><Button variant="outline" size="sm">Salle d&apos;attente</Button></Link>
          </div>
        </div>
      </div>

      {/* Status global */}
      <div className="live-strip">
        <div className="flex items-center gap-2 text-sm">
          {healthResult ? (
            healthResult.ok ? (
              <><CheckCircle2 className="h-4 w-4 text-success" /><span className="text-success font-medium">Backend en ligne</span></>
            ) : (
              <><XCircle className="h-4 w-4 text-destructive" /><span className="text-destructive font-medium">Backend inaccessible</span></>
            )
          ) : (
            <><Loader2 className="h-4 w-4 animate-spin text-muted-foreground" /><span className="text-muted-foreground">Vérification...</span></>
          )}
        </div>
        <span className="text-xs text-muted-foreground">
          {process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}
        </span>
      </div>

      {/* 1. Health */}
      <Section icon={Activity} title="Santé du backend — GET /health" index={1}>
        <Btn k="health" onClick={() => run("health", checkHealth, setHealthResult)}>
          <Activity className="h-4 w-4" />
          Tester /health
        </Btn>
        <ResultBox result={healthResult} />
      </Section>

      {/* 2. Sensor */}
      <Section icon={Send} title="Envoyer données capteur — POST /api/occupancy/" index={2}>
        <div className="flex flex-wrap items-end gap-4">
          <div>
            <p className="mb-1.5 text-xs text-muted-foreground">Personnes occupées</p>
            <input type="number" min={0} max={50} value={sensorCount}
              onChange={(e) => setSensorCount(Number(e.target.value))}
              className="w-20 rounded-xl border border-input bg-background px-3 py-2 text-center text-sm"
            />
          </div>
          <div>
            <p className="mb-1.5 text-xs text-muted-foreground">Source</p>
            <select value={sensorSource} onChange={(e) => setSensorSource(e.target.value as "sensor" | "camera")}
              className="rounded-xl border border-input bg-background px-3 py-2 text-sm"
            >
              <option value="sensor">sensor (IoT)</option>
              <option value="camera">camera (script YOLO)</option>
            </select>
          </div>
          <div>
            <p className="mb-1.5 text-xs text-muted-foreground">Position (optionnel)</p>
            <input type="number" min={1} placeholder="—" value={sensorPosition ?? ""}
              onChange={(e) => setSensorPosition(e.target.value ? Number(e.target.value) : undefined)}
              className="w-20 rounded-xl border border-input bg-background px-3 py-2 text-center text-sm"
            />
          </div>
          <Btn k="sensor" onClick={() => run("sensor", () => sendSensorData(sensorCount, sensorSource, sensorPosition), setSensorResult)}>
            <Send className="h-4 w-4" />
            Envoyer
          </Btn>
        </div>
        <ResultBox result={sensorResult} />
      </Section>

      {/* 3. Latest */}
      <Section icon={Eye} title="Dernière lecture — GET /api/occupancy/latest" index={3}>
        <Btn k="latest" onClick={() => run("latest", fetchLatestOccupancy, setLatestResult)}>
          <Eye className="h-4 w-4" />
          Récupérer
        </Btn>
        <ResultBox result={latestResult} />
      </Section>

      {/* 4. Waiting time */}
      <Section icon={Clock3} title="Temps d'attente — GET /api/occupancy/waiting-time" index={4}>
        <p className="mb-3 text-sm text-muted-foreground">Nécessite au moins une donnée d&apos;occupation et le service IA actif.</p>
        <Btn k="wait" onClick={() => run("wait", fetchWaitingTime, setWaitResult)}>
          <Clock3 className="h-4 w-4" />
          Calculer le temps d&apos;attente
        </Btn>
        <ResultBox result={waitResult} />
      </Section>

      {/* 5. YOLO image */}
      <Section icon={Camera} title="Analyse image YOLO — POST /api/occupancy/analyser" index={5}>
        <p className="mb-3 text-sm text-muted-foreground">Envoie une image au service YOLO (port 8001). Nécessite le service YOLO actif.</p>
        <div
          onDrop={(e) => { e.preventDefault(); const f = e.dataTransfer.files?.[0]; if (f) { setYoloFile(f); setYoloPreview(URL.createObjectURL(f)); setYoloResult(null); } }}
          onDragOver={(e) => e.preventDefault()}
          onClick={() => fileRef.current?.click()}
          className="soft-panel mb-3 flex min-h-[120px] cursor-pointer flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed p-4 text-center transition-colors hover:border-primary/40 hover:bg-primary/5"
        >
          {yoloPreview
            ? <img src={yoloPreview} alt="preview" className="max-h-[160px] max-w-full rounded-xl object-contain" />
            : <><Upload className="h-6 w-6 text-muted-foreground" /><p className="text-sm text-muted-foreground">Glisser une image ou cliquer</p></>
          }
        </div>
        <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) { setYoloFile(f); setYoloPreview(URL.createObjectURL(f)); setYoloResult(null); } }} />
        {yoloFile && (
          <Btn k="yolo" onClick={() => run("yolo", () => analyserImage(yoloFile!), setYoloResult)}>
            <Camera className="h-4 w-4" />
            Analyser avec YOLO
          </Btn>
        )}
        <ResultBox result={yoloResult} />
      </Section>

      {/* 6. YOLO vidéo */}
      <Section icon={Video} title="Analyse vidéo YOLO — POST /api/occupancy/analyser-video" index={6}>
        <div className="mb-3 flex items-center gap-3">
          <label className="text-sm text-muted-foreground">1 frame /</label>
          <input type="number" min={1} max={120} value={intervalleFrames}
            onChange={(e) => setIntervalleFrames(Number(e.target.value))}
            className="w-16 rounded-xl border border-input bg-background px-2 py-1.5 text-center text-sm"
          />
          <label className="text-sm text-muted-foreground">frames</label>
        </div>
        <div
          onDrop={(e) => { e.preventDefault(); const f = e.dataTransfer.files?.[0]; if (f) { setVideoFile(f); setVideoPreview(URL.createObjectURL(f)); setVideoResult(null); } }}
          onDragOver={(e) => e.preventDefault()}
          onClick={() => videoRef.current?.click()}
          className="soft-panel mb-3 flex min-h-[100px] cursor-pointer flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed p-4 text-center transition-colors hover:border-primary/40 hover:bg-primary/5"
        >
          {videoPreview
            ? <video src={videoPreview} controls className="max-h-[140px] max-w-full rounded-xl" />
            : <><Video className="h-6 w-6 text-muted-foreground" /><p className="text-sm text-muted-foreground">Glisser une vidéo (mp4, avi…) ou cliquer</p></>
          }
        </div>
        <input ref={videoRef} type="file" accept="video/*" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) { setVideoFile(f); setVideoPreview(URL.createObjectURL(f)); setVideoResult(null); } }} />
        {videoFile && (
          <Btn k="video" onClick={() => run("video", () => analyserVideo(videoFile!, intervalleFrames), setVideoResult)}>
            <Video className="h-4 w-4" />
            Analyser la vidéo
          </Btn>
        )}
        <ResultBox result={videoResult} />
      </Section>

      {/* 7. Consultation */}
      <Section icon={Stethoscope} title="Consultations — POST /start & PATCH /end" index={7}>
        <div className="flex flex-wrap items-center gap-3">
          <Button
            variant="default"
            disabled={!!activeConsultId || loading === "start"}
            onClick={() => run("start", () => startConsultation("Consultation générale"), (r) => {
              setConsultResult(r);
              if (r.ok) setActiveConsultId((r.data as { id: number }).id);
            })}
            className="gap-2"
          >
            {loading === "start" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Stethoscope className="h-4 w-4" />}
            Commencer consultation
          </Button>
          <Button
            variant="destructive"
            disabled={!activeConsultId || loading === "end"}
            onClick={() => run("end", () => endConsultation(activeConsultId!), (r) => {
              setConsultResult(r);
              if (r.ok) setActiveConsultId(null);
            })}
            className="gap-2"
          >
            {loading === "end" ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            Terminer {activeConsultId ? `#${activeConsultId}` : ""}
          </Button>
          {activeConsultId && (
            <span className="status-pill status-pill--warning">
              <Activity className="h-3.5 w-3.5" />
              Consultation #{activeConsultId} en cours
            </span>
          )}
        </div>
        <ResultBox result={consultResult} />
      </Section>
    </main>
  );
}
