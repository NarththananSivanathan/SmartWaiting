"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { motion, AnimatePresence } from "motion/react";
import {
  Stethoscope,
  Clock3,
  LogOut,
  ListChecks,
  Timer,
  Activity,
  ChevronLeft,
  ChevronRight,
  CalendarDays,
  Sparkles,
  RefreshCcw,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  startConsultation,
  endConsultation,
  setTypeRdv,
  fetchConsultations,
} from "@/lib/api";

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

function formatElapsed(totalSeconds: number) {
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = totalSeconds % 60;

  if (h > 0) return `${h}h ${String(m).padStart(2, "0")}min`;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function formatDateLabel() {
  return new Intl.DateTimeFormat("fr-FR", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(new Date());
}

function formatTimeLabel() {
  return new Intl.DateTimeFormat("fr-FR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date());
}

function getStatusMeta(active: boolean) {
  if (active) {
    return {
      label: "En consultation",
      className: "status-pill status-pill--warning",
    };
  }

  return {
    label: "Disponible",
    className: "status-pill status-pill--success",
  };
}

function DoctorHeader({
  active,
  currentTime,
  onRefresh,
  refreshing,
}: {
  active: boolean;
  currentTime: string;
  onRefresh: () => void;
  refreshing: boolean;
}) {
  const status = getStatusMeta(active);

  return (
    <div className="page-header">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="space-y-3">
          <div className="page-eyebrow">
            <Stethoscope className="h-4 w-4" />
            Interface médecin · SmartWaiting
          </div>

          <div>
            <h1 className="page-title text-balance">Suivi des consultations</h1>
            <p className="page-subtitle text-pretty">
              Pilotez les consultations en cours, visualisez l&apos;activité du
              cabinet et gardez un historique clair des passages patients.
            </p>
          </div>
        </div>

        <div className="soft-panel flex flex-col gap-3 p-4 sm:min-w-[320px]">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                Statut du cabinet
              </p>
              <div className="mt-2">
                <span className={status.className}>
                  <Activity className="h-3.5 w-3.5" />
                  {status.label}
                </span>
              </div>
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={onRefresh}
              disabled={refreshing}
              className="gap-2"
            >
              <RefreshCcw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
              Actualiser
            </Button>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-2xl bg-muted/70 p-3">
              <p className="mb-1 text-xs text-muted-foreground">Date</p>
              <p className="font-medium capitalize text-foreground">{formatDateLabel()}</p>
            </div>
            <div className="rounded-2xl bg-muted/70 p-3">
              <p className="mb-1 text-xs text-muted-foreground">Heure locale</p>
              <p className="font-semibold tabular-nums text-foreground">{currentTime}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ActiveConsultationCard({
  active,
  elapsed,
  onStart,
  onEnd,
  onTypeChange,
  starting,
  ending,
}: {
  active: Consultation | null;
  elapsed: number;
  onStart: () => void;
  onEnd: () => void;
  onTypeChange: (value: string) => void;
  starting: boolean;
  ending: boolean;
}) {
  if (!active) {
    return (
      <Card className="card-modern card-modern--hero border-dashed">
        <CardContent className="flex flex-col items-center justify-center gap-5 px-6 py-12 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 text-primary shadow-sm">
            <Stethoscope className="h-8 w-8" />
          </div>

          <div className="space-y-2">
            <p className="text-xl font-semibold text-foreground">
              Aucune consultation en cours
            </p>
            <p className="mx-auto max-w-2xl text-sm leading-7 text-muted-foreground">
              Le cabinet est prêt pour le prochain patient. Lancez une nouvelle
              consultation dès que le patient entre dans le cabinet.
            </p>
          </div>

          <Button size="lg" disabled={starting} onClick={onStart} className="gap-2">
            <Sparkles className="h-4 w-4" />
            {starting ? "Démarrage..." : "Commencer la consultation"}
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28 }}
    >
      <Card className="card-modern card-modern--hero overflow-hidden border-primary/25">
        <CardHeader className="relative z-10 flex flex-col gap-4 pb-2 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-3">
            <div className="page-eyebrow">
              <span className="live-dot" />
              Consultation active
            </div>

            <div>
              <CardTitle className="text-2xl font-semibold tracking-tight">
                Patient actuellement en consultation
              </CardTitle>
              <p className="mt-2 text-sm leading-7 text-muted-foreground">
                Arrivée enregistrée à{" "}
                <span className="font-semibold text-foreground">
                  {new Date(active.heure_arrivee).toLocaleTimeString("fr-FR")}
                </span>
                . Gardez le type de rendez-vous à jour pour améliorer la qualité
                des statistiques et des prédictions.
              </p>
            </div>
          </div>

          <div className="rounded-2xl border border-primary/20 bg-primary/10 px-4 py-3 shadow-sm">
            <p className="mb-1 flex items-center gap-2 text-xs uppercase tracking-[0.18em] text-primary">
              <Clock3 className="h-3.5 w-3.5" />
              Temps écoulé
            </p>
            <p className="text-3xl font-black tracking-tight tabular-nums text-primary">
              {formatElapsed(elapsed)}
            </p>
          </div>
        </CardHeader>

        <CardContent className="relative z-10 grid gap-5 pt-4 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="soft-panel p-4">
              <p className="mb-1 text-xs uppercase tracking-[0.16em] text-muted-foreground">
                Heure d&apos;arrivée
              </p>
              <p className="text-lg font-semibold text-foreground">
                {new Date(active.heure_arrivee).toLocaleTimeString("fr-FR")}
              </p>
            </div>

            <div className="soft-panel p-4">
              <p className="mb-2 text-xs uppercase tracking-[0.16em] text-muted-foreground">
                Type de rendez-vous
              </p>

              <Select value={active.type_rdv || undefined} onValueChange={onTypeChange}>
                <SelectTrigger className="h-11 w-full text-sm">
                  <SelectValue placeholder="Choisir un type" />
                </SelectTrigger>
                <SelectContent>
                  {TYPES_RDV.map((type) => (
                    <SelectItem key={type} value={type}>
                      {type}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="soft-panel flex flex-col justify-between gap-4 p-4">
            <div>
              <p className="mb-1 text-xs uppercase tracking-[0.16em] text-muted-foreground">
                Action principale
              </p>
              <p className="text-sm leading-7 text-muted-foreground">
                Clôturez la consultation lorsque le patient quitte le cabinet
                afin de conserver un historique fiable et une durée correcte.
              </p>
            </div>

            <Button
              variant="destructive"
              disabled={ending}
              onClick={onEnd}
              className="h-11 gap-2"
            >
              <LogOut className="h-4 w-4" />
              {ending ? "Clôture..." : "Le patient quitte le cabinet"}
            </Button>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

function StatsSummary({
  total,
  avgDuration,
  isActive,
  completedCount,
}: {
  total: number;
  avgDuration: number | null;
  isActive: boolean;
  completedCount: number;
}) {
  const items = [
    {
      label: "Consultations enregistrées",
      value: total,
      hint: "Volume visible sur l’historique",
      icon: ListChecks,
      tone: "primary",
    },
    {
      label: "Durée moyenne",
      value: avgDuration ? `${avgDuration} min` : "—",
      hint: "Calculée sur les consultations terminées",
      icon: Timer,
      tone: "success",
    },
    {
      label: "Statut médecin",
      value: isActive ? "En consultation" : "Disponible",
      hint: "État opérationnel en temps réel",
      icon: Activity,
      tone: isActive ? "warning" : "success",
    },
    {
      label: "Consultations clôturées",
      value: completedCount,
      hint: "Sur la page actuellement chargée",
      icon: CalendarDays,
      tone: "primary",
    },
  ] as const;

  const toneMap: Record<string, string> = {
    primary: "status-pill status-pill--primary",
    success: "status-pill status-pill--success",
    warning: "status-pill status-pill--warning",
  };

  return (
    <section className="metric-grid metric-grid--4">
      {items.map(({ label, value, hint, icon: Icon, tone }) => (
        <Card key={label} className="kpi-card">
          <CardContent className="p-0">
            <div className="mb-4 flex items-start justify-between gap-3">
              <div>
                <p className="kpi-card__label">{label}</p>
                <p className="kpi-card__value">{value}</p>
              </div>

              <span className={toneMap[tone]}>
                <Icon className="h-3.5 w-3.5" />
              </span>
            </div>

            <p className="kpi-card__hint">{hint}</p>
          </CardContent>
        </Card>
      ))}
    </section>
  );
}

function ConsultationsTable({
  consultations,
  page,
  pages,
  total,
  onPageChange,
}: {
  consultations: Consultation[];
  page: number;
  pages: number;
  total: number;
  onPageChange: (page: number) => void;
}) {
  return (
    <section className="table-shell">
      <div className="flex flex-col gap-3 border-b border-border px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-foreground">
            Historique des consultations
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Consultez les passages récents et vérifiez les informations
            enregistrées.
          </p>
        </div>

        <div className="status-pill status-pill--primary">
          <ListChecks className="h-3.5 w-3.5" />
          {total} au total
        </div>
      </div>

      {consultations.length === 0 ? (
        <div className="px-5 py-14 text-center">
          <p className="text-base font-medium text-foreground">
            Aucune consultation enregistrée
          </p>
          <p className="mt-2 text-sm text-muted-foreground">
            Les nouvelles consultations apparaîtront ici au fur et à mesure.
          </p>
        </div>
      ) : (
        <>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Jour</TableHead>
                  <TableHead>Arrivée</TableHead>
                  <TableHead>Départ</TableHead>
                  <TableHead>Durée</TableHead>
                  <TableHead>Saison</TableHead>
                  <TableHead>Type RDV</TableHead>
                </TableRow>
              </TableHeader>

              <TableBody>
                <AnimatePresence initial={false}>
                  {consultations.map((consultation) => (
                    <motion.tr
                      key={consultation.id}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="border-b border-border transition-colors hover:bg-muted/50"
                    >
                      <TableCell className="font-medium">{consultation.date}</TableCell>
                      <TableCell className="capitalize">
                        {consultation.jour_semaine}
                      </TableCell>
                      <TableCell className="tabular-nums">
                        {new Date(consultation.heure_arrivee).toLocaleTimeString("fr-FR")}
                      </TableCell>
                      <TableCell className="tabular-nums">
                        {consultation.heure_depart ? (
                          new Date(consultation.heure_depart).toLocaleTimeString("fr-FR")
                        ) : (
                          <Badge
                            variant="outline"
                            className="border-warning/40 bg-warning/10 text-warning"
                          >
                            En cours
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell className="tabular-nums">
                        {consultation.duree_consultation != null
                          ? `${consultation.duree_consultation} min`
                          : "—"}
                      </TableCell>
                      <TableCell className="capitalize">
                        {consultation.saison_annee}
                      </TableCell>
                      <TableCell>{consultation.type_rdv ?? "—"}</TableCell>
                    </motion.tr>
                  ))}
                </AnimatePresence>
              </TableBody>
            </Table>
          </div>

          <div className="flex flex-col gap-3 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
            <Button
              variant="outline"
              size="sm"
              disabled={page === 1}
              onClick={() => onPageChange(page - 1)}
              className="gap-1"
            >
              <ChevronLeft className="h-4 w-4" />
              Précédent
            </Button>

            <span className="text-sm text-muted-foreground">
              Page {page} / {pages}
            </span>

            <Button
              variant="outline"
              size="sm"
              disabled={page === pages}
              onClick={() => onPageChange(page + 1)}
              className="gap-1"
            >
              Suivant
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </>
      )}
    </section>
  );
}

export default function Home() {
  const [consultations, setConsultations] = useState<Consultation[]>([]);
  const [active, setActive] = useState<Consultation | null>(null);
  const [page, setPage] = useState(1);
  const [meta, setMeta] = useState({ total: 0, pages: 1 });
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [starting, setStarting] = useState(false);
  const [ending, setEnding] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [currentTime, setCurrentTime] = useState(formatTimeLabel());

  const loadConsultations = useCallback(
    async (p: number, silent = false) => {
      if (silent) setRefreshing(true);
      else setLoading(true);

      try {
        const res: PaginatedResponse = await fetchConsultations(p, 20);
        setConsultations(res.data);
        setMeta({ total: res.total, pages: res.pages });
        setActive(res.data.find((c) => !c.heure_depart) ?? null);
      } catch {
        toast.error("Impossible de charger les consultations");
      } finally {
        if (silent) setRefreshing(false);
        else setLoading(false);
      }
    },
    []
  );

  useEffect(() => {
    loadConsultations(page);
  }, [page, loadConsultations]);

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(formatTimeLabel());
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!active?.heure_arrivee) {
      setElapsed(0);
      return;
    }

    const start = new Date(active.heure_arrivee).getTime();
    const tick = () =>
      setElapsed(Math.max(0, Math.floor((Date.now() - start) / 1000)));

    tick();
    const interval = setInterval(tick, 1000);

    return () => clearInterval(interval);
  }, [active?.heure_arrivee]);

  const handleStart = async () => {
    setStarting(true);
    try {
      const consultation = await startConsultation("Consultation générale");
      setActive(consultation);
      setConsultations((prev) => [consultation, ...prev]);
      setMeta((m) => ({ ...m, total: m.total + 1 }));
      toast.success("Consultation démarrée");
    } catch {
      toast.error("Erreur lors du démarrage");
    } finally {
      setStarting(false);
    }
  };

  const handleEnd = async () => {
    if (!active) return;

    setEnding(true);
    try {
      const updated = await endConsultation(active.id);
      setActive(null);
      setConsultations((prev) =>
        prev.map((c) => (c.id === updated.id ? updated : c))
      );
      toast.success("Consultation clôturée");
    } catch {
      toast.error("Erreur lors de la clôture");
    } finally {
      setEnding(false);
    }
  };

  const handleType = async (value: string) => {
    if (!active) return;

    try {
      const updated = await setTypeRdv(active.id, value);
      setActive(updated);
      setConsultations((prev) =>
        prev.map((c) => (c.id === updated.id ? updated : c))
      );
      toast.success("Type de rendez-vous mis à jour");
    } catch {
      toast.error("Erreur lors de la mise à jour du type");
    }
  };

  const avgDuration = useMemo(() => {
    const done = consultations.filter((c) => c.duree_consultation != null);
    if (done.length === 0) return null;

    return Math.round(
      done.reduce((acc, c) => acc + (c.duree_consultation ?? 0), 0) / done.length
    );
  }, [consultations]);

  const completedCount = useMemo(
    () => consultations.filter((c) => c.heure_depart).length,
    [consultations]
  );

  if (loading && consultations.length === 0) {
    return (
      <div className="page-shell page-shell--wide flex flex-col gap-6">
        <div className="space-y-3">
          <Skeleton className="h-7 w-44 rounded-full" />
          <Skeleton className="h-14 w-96 rounded-2xl" />
          <Skeleton className="h-5 w-[620px] max-w-full rounded-xl" />
        </div>

        <Skeleton className="h-[320px] w-full rounded-[28px]" />

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <Skeleton className="h-32 rounded-[24px]" />
          <Skeleton className="h-32 rounded-[24px]" />
          <Skeleton className="h-32 rounded-[24px]" />
          <Skeleton className="h-32 rounded-[24px]" />
        </div>

        <Skeleton className="h-[420px] w-full rounded-[28px]" />
      </div>
    );
  }

  return (
    <main className="page-shell page-shell--wide flex flex-col gap-6">
      <DoctorHeader
        active={!!active}
        currentTime={currentTime}
        onRefresh={() => loadConsultations(page, true)}
        refreshing={refreshing}
      />

      <ActiveConsultationCard
        active={active}
        elapsed={elapsed}
        onStart={handleStart}
        onEnd={handleEnd}
        onTypeChange={handleType}
        starting={starting}
        ending={ending}
      />

      <StatsSummary
        total={meta.total}
        avgDuration={avgDuration}
        isActive={!!active}
        completedCount={completedCount}
      />

      <ConsultationsTable
        consultations={consultations}
        page={page}
        pages={meta.pages}
        total={meta.total}
        onPageChange={setPage}
      />
    </main>
  );
}