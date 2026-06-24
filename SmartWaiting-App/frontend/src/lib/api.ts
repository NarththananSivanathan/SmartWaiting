const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function startConsultation(type_rdv?: string) {
  const res = await fetch(`${API_URL}/api/consultations/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ type_rdv }),
  });
  if (!res.ok) throw new Error("Erreur lors du démarrage de la consultation");
  return res.json();
}

export async function endConsultation(id: number) {
  const res = await fetch(`${API_URL}/api/consultations/${id}/end`, {
    method: "PATCH",
  });
  if (!res.ok) throw new Error("Erreur lors de la fin de la consultation");
  return res.json();
}

export async function setTypeRdv(id: number, type_rdv: string) {
  const res = await fetch(`${API_URL}/api/consultations/${id}/type`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ type_rdv }),
  });
  if (!res.ok) throw new Error("Erreur lors de la mise à jour du type");
  return res.json();
}

export async function fetchConsultations(page = 1, size = 20) {
  const res = await fetch(`${API_URL}/api/consultations/?page=${page}&size=${size}`);
  if (!res.ok) throw new Error("Erreur lors du chargement des consultations");
  return res.json();
}

export async function fetchWaitingTime() {
  const res = await fetch(`${API_URL}/api/occupancy/waiting-time`);
  if (!res.ok) throw new Error("Erreur lors du chargement du temps d'attente");
  return res.json();
}

export async function fetchStats() {
  const res = await fetch(`${API_URL}/api/consultations/stats`);
  if (!res.ok) throw new Error("Erreur lors du chargement des statistiques");
  return res.json();
}

export async function analyserImage(file: File) {
  const form = new FormData();
  form.append("image", file);
  const res = await fetch(`${API_URL}/api/occupancy/analyser`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error("Erreur lors de l'analyse de l'image");
  return res.json();
}

export async function sendSensorData(occupiedChairs: number, source: "sensor" | "camera" = "sensor", patientPosition?: number) {
  const res = await fetch(`${API_URL}/api/occupancy/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ occupied_chairs: occupiedChairs, source, patient_position: patientPosition }),
  });
  if (!res.ok) throw new Error("Erreur lors de l'envoi des données capteur");
  return res.json();
}

export async function fetchLatestOccupancy() {
  const res = await fetch(`${API_URL}/api/occupancy/latest`);
  if (!res.ok) throw new Error("Aucune donnée d'occupation disponible");
  return res.json();
}

export async function checkHealth() {
  const res = await fetch(`${API_URL}/health`);
  if (!res.ok) throw new Error("Backend indisponible");
  return res.json();
}
