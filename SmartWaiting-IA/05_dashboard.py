"""
SmartWaiting — Dashboard interactif
====================================
Lancer : python 05_dashboard.py
Ouvre  : http://localhost:5050
"""

from flask import Flask, request, jsonify, render_template_string
import joblib, json, pandas as pd, numpy as np
from datetime import datetime, timedelta
import os, webbrowser, threading
from utils import JOURS_FR, get_saison

# ── Chargement modèle ─────────────────────────────────────────────────────────
BASE = os.path.dirname(os.path.abspath(__file__))

model     = joblib.load(os.path.join(BASE, "models/model_smartwaiting.pkl"))
le_jour   = joblib.load(os.path.join(BASE, "models/le_jour.pkl"))
le_saison = joblib.load(os.path.join(BASE, "models/le_saison.pkl"))
le_type   = joblib.load(os.path.join(BASE, "models/le_type.pkl"))

with open(os.path.join(BASE, "models/features.json"), encoding="utf-8") as f:
    meta = json.load(f)

FEATURES        = meta["features"]
TYPES_VALIDES   = meta["types_valides"]
JOURS_VALIDES   = meta["jours_valides"]
SAISONS_VALIDES = meta["saisons_valides"]

# ── Helpers ───────────────────────────────────────────────────────────────────
def predire(heure_dec, minute, mois, jour, saison, type_rdv):
    X = pd.DataFrame([[
        heure_dec, minute, mois,
        le_jour.transform([jour])[0],
        le_saison.transform([saison])[0],
        le_type.transform([type_rdv])[0]
    ]], columns=FEATURES)
    return float(model.predict(X)[0])

def courbe_journee(jour, saison, type_rdv):
    """Retourne la durée prédite pour chaque heure de 8h à 19h."""
    points = []
    for h in range(8, 19):
        for m in [0, 30]:
            hd = h + m/60
            d  = max(5, round(predire(hd, m, 6, jour, saison, type_rdv)))
            points.append({"heure": f"{h:02d}h{m:02d}", "duree": d})
    return points

def stats_par_type(jour, saison):
    """Durée moyenne prédite pour chaque type à 10h un jour donné."""
    return [
        {"type": t, "duree": round(max(5, predire(10, 0, 6, jour, saison, t)))}
        for t in TYPES_VALIDES
    ]

# ── HTML ──────────────────────────────────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SmartWaiting — Dashboard</title>
<style>
  :root {
    --bg:       #0f1117;
    --surface:  #1a1d27;
    --card:     #21253a;
    --border:   #2e3350;
    --accent:   #6c8fff;
    --accent2:  #4ade80;
    --warn:     #f59e0b;
    --danger:   #f87171;
    --text:     #e2e8f0;
    --muted:    #8892b0;
    --radius:   12px;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font-family: 'Inter', system-ui, sans-serif; min-height: 100vh; }

  /* ── Layout ── */
  .shell { display: grid; grid-template-columns: 280px 1fr; min-height: 100vh; }
  .sidebar { background: var(--surface); border-right: 1px solid var(--border); padding: 2rem 1.5rem; display: flex; flex-direction: column; gap: 1.5rem; }
  .main { padding: 2rem; display: flex; flex-direction: column; gap: 1.5rem; }

  /* ── Logo ── */
  .logo { display: flex; align-items: center; gap: 10px; margin-bottom: .5rem; }
  .logo-dot { width: 10px; height: 10px; border-radius: 50%; background: var(--accent); box-shadow: 0 0 8px var(--accent); animation: pulse 2s infinite; }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }
  .logo h1 { font-size: 1.1rem; font-weight: 700; letter-spacing: -.3px; }
  .logo span { color: var(--accent); }

  /* ── Form ── */
  .section-label { font-size: .7rem; font-weight: 600; letter-spacing: .08em; color: var(--muted); text-transform: uppercase; margin-bottom: .5rem; }
  .field { display: flex; flex-direction: column; gap: 6px; }
  label { font-size: .8rem; color: var(--muted); }
  input, select {
    background: var(--card); border: 1px solid var(--border); border-radius: 8px;
    color: var(--text); font-size: .9rem; padding: 9px 12px; width: 100%;
    transition: border-color .2s;
  }
  input:focus, select:focus { outline: none; border-color: var(--accent); }
  input[type=range] { padding: 4px 0; cursor: pointer; accent-color: var(--accent); }
  .range-row { display: flex; align-items: center; gap: 10px; }
  .range-row input { flex: 1; }
  .badge-pos { background: var(--accent); color: #fff; border-radius: 6px; padding: 3px 10px; font-weight: 700; font-size: .9rem; min-width: 36px; text-align: center; }

  /* ── Boutons ── */
  .btn { border: none; border-radius: 8px; padding: 11px; font-size: .95rem; font-weight: 600; cursor: pointer; transition: all .15s; width: 100%; }
  .btn-primary { background: var(--accent); color: #fff; }
  .btn-primary:hover { filter: brightness(1.15); }
  .btn-auto { background: var(--card); color: var(--text); border: 1px solid var(--border); margin-top: -6px; }
  .btn-auto:hover { border-color: var(--accent); color: var(--accent); }

  /* ── Cards résultat ── */
  .cards-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; }
  .card { background: var(--card); border: 1px solid var(--border); border-radius: var(--radius); padding: 1.25rem 1.5rem; }
  .card.accent { border-color: var(--accent); }
  .card-label { font-size: .75rem; color: var(--muted); margin-bottom: .4rem; }
  .card-value { font-size: 2rem; font-weight: 700; }
  .card-sub { font-size: .8rem; color: var(--muted); margin-top: .3rem; }
  .card-value.green { color: var(--accent2); }
  .card-value.amber { color: var(--warn); }
  .card-value.red   { color: var(--danger); }

  /* ── Message résultat ── */
  .result-banner { background: var(--card); border: 1px solid var(--accent); border-radius: var(--radius); padding: 1.25rem 1.5rem; display: flex; align-items: center; gap: 1rem; display: none; }
  .result-banner.show { display: flex; }
  .clock-icon { font-size: 2.5rem; }
  .result-text h2 { font-size: 1.1rem; font-weight: 600; }
  .result-text p  { color: var(--muted); font-size: .9rem; margin-top: 4px; }

  /* ── Graphiques ── */
  .charts-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
  .chart-card { background: var(--card); border: 1px solid var(--border); border-radius: var(--radius); padding: 1.25rem; }
  .chart-title { font-size: .85rem; font-weight: 600; color: var(--muted); margin-bottom: 1rem; }
  canvas { width: 100% !important; }

  /* ── Timeline ── */
  .timeline { display: flex; flex-direction: column; gap: 8px; margin-top: .5rem; }
  .tl-item { display: flex; align-items: center; gap: 10px; font-size: .85rem; }
  .tl-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
  .tl-dot.done  { background: var(--accent2); }
  .tl-dot.now   { background: var(--accent); box-shadow: 0 0 6px var(--accent); }
  .tl-dot.later { background: var(--border); }
  .tl-line { width: 1px; height: 16px; background: var(--border); margin-left: 3.5px; }
  .tl-label { color: var(--muted); }
  .tl-time  { margin-left: auto; font-weight: 600; }

  /* ── Spinner ── */
  .spinner { display: none; width: 18px; height: 18px; border: 2px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin .6s linear infinite; margin: 0 auto; }
  @keyframes spin { to { transform: rotate(360deg); } }
  .spinner.show { display: block; }

  /* ── Responsive ── */
  @media (max-width: 860px) {
    .shell { grid-template-columns: 1fr; }
    .sidebar { border-right: none; border-bottom: 1px solid var(--border); }
    .cards-row, .charts-grid { grid-template-columns: 1fr; }
  }

  .empty-state { text-align: center; color: var(--muted); padding: 3rem; font-size: .95rem; }
  .tag { display: inline-block; background: var(--surface); border: 1px solid var(--border); border-radius: 20px; font-size: .75rem; padding: 3px 10px; color: var(--muted); }
  hr.sep { border: none; border-top: 1px solid var(--border); }
  .now-info { font-size: .78rem; color: var(--muted); text-align: center; }
</style>
</head>
<body>
<div class="shell">

  <!-- ══ SIDEBAR ══ -->
  <aside class="sidebar">
    <div>
      <div class="logo">
        <div class="logo-dot"></div>
        <h1>Smart<span>Waiting</span></h1>
      </div>
      <div class="tag">IA — Prédiction temps d'attente</div>
    </div>

    <hr class="sep">

    <!-- Position -->
    <div class="field">
      <p class="section-label">Votre position</p>
      <div class="range-row">
        <input type="range" id="position" min="1" max="30" value="5" oninput="document.getElementById('pos-val').textContent=this.value">
        <span class="badge-pos" id="pos-val">5</span>
      </div>
      <label>Numéro dans la file d'attente</label>
    </div>

    <!-- Type de consultation -->
    <div class="field">
      <p class="section-label">Type de consultation</p>
      <select id="type_rdv">
        {% for t in types %}
        <option value="{{ t }}">{{ t }}</option>
        {% endfor %}
      </select>
    </div>

    <!-- Heure -->
    <div class="field">
      <p class="section-label">Heure d'arrivée</p>
      <input type="time" id="heure" value="10:00" min="08:00" max="19:00">
    </div>

    <!-- Jour -->
    <div class="field">
      <p class="section-label">Jour de la semaine</p>
      <select id="jour">
        {% for j in jours %}
        <option value="{{ j }}">{{ j }}</option>
        {% endfor %}
      </select>
    </div>

    <!-- Saison -->
    <div class="field">
      <p class="section-label">Saison</p>
      <select id="saison">
        {% for s in saisons %}
        <option value="{{ s }}">{{ s }}</option>
        {% endfor %}
      </select>
    </div>

    <div style="display:flex;flex-direction:column;gap:8px;margin-top:auto">
      <button class="btn btn-auto" onclick="remplirAuto()">⟳ Remplir avec l'heure actuelle</button>
      <button class="btn btn-primary" onclick="predict()">Estimer mon attente →</button>
      <div class="spinner" id="spinner"></div>
    </div>
  </aside>

  <!-- ══ MAIN ══ -->
  <main class="main">

    <!-- Bandeau résultat -->
    <div class="result-banner" id="result-banner">
      <div class="clock-icon">⏱</div>
      <div class="result-text">
        <h2 id="res-msg">—</h2>
        <p id="res-sub">—</p>
      </div>
    </div>

    <!-- KPI cards -->
    <div class="cards-row">
      <div class="card">
        <div class="card-label">Temps d'attente estimé</div>
        <div class="card-value" id="kpi-attente">—</div>
        <div class="card-sub">minutes avant votre tour</div>
      </div>
      <div class="card accent">
        <div class="card-label">Heure de passage estimée</div>
        <div class="card-value green" id="kpi-passage">—</div>
        <div class="card-sub">heure approximative</div>
      </div>
      <div class="card">
        <div class="card-label">Durée moy. par patient</div>
        <div class="card-value amber" id="kpi-duree">—</div>
        <div class="card-sub">pour ce type de consultation</div>
      </div>
    </div>

    <!-- Timeline + Graphiques -->
    <div class="charts-grid">

      <!-- Timeline -->
      <div class="chart-card">
        <div class="chart-title">DÉROULÉ DE VOTRE ATTENTE</div>
        <div class="timeline" id="timeline">
          <div class="empty-state">Lancez une estimation pour voir la timeline</div>
        </div>
      </div>

      <!-- Durée selon le type -->
      <div class="chart-card">
        <div class="chart-title">DURÉE ESTIMÉE SELON LE TYPE DE CONSULTATION</div>
        <canvas id="chart-types" height="220"></canvas>
      </div>

      <!-- Courbe journée -->
      <div class="chart-card" style="grid-column: span 2">
        <div class="chart-title">DURÉE PRÉDITE SUR LA JOURNÉE — <span id="chart-courbe-label">ce jour / cette saison</span></div>
        <canvas id="chart-courbe" height="160"></canvas>
      </div>

    </div>

    <p class="now-info" id="now-info"></p>
  </main>
</div>

<!-- Chart.js -->
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script>
const ACCENT  = '#6c8fff';
const ACCENT2 = '#4ade80';
const WARN    = '#f59e0b';
const DANGER  = '#f87171';
const MUTED   = '#8892b0';
const GRIDCLR = 'rgba(255,255,255,0.06)';

const chartDefaults = {
  responsive: true,
  plugins: { legend: { display: false }, tooltip: { backgroundColor: '#21253a', titleColor: '#e2e8f0', bodyColor: '#8892b0', borderColor: '#2e3350', borderWidth: 1 } },
  scales: {
    x: { grid: { color: GRIDCLR }, ticks: { color: MUTED, font: { size: 11 } } },
    y: { grid: { color: GRIDCLR }, ticks: { color: MUTED, font: { size: 11 } }, beginAtZero: true }
  }
};

let chartTypes  = null;
let chartCourbe = null;

function initCharts() {
  chartTypes = new Chart(document.getElementById('chart-types'), {
    type: 'bar',
    data: { labels: [], datasets: [{ data: [], backgroundColor: ACCENT + '99', borderColor: ACCENT, borderWidth: 1, borderRadius: 6 }] },
    options: { ...chartDefaults, indexAxis: 'y' }
  });

  chartCourbe = new Chart(document.getElementById('chart-courbe'), {
    type: 'line',
    data: { labels: [], datasets: [{
      data: [], borderColor: ACCENT2, backgroundColor: ACCENT2 + '22',
      fill: true, tension: 0.4, pointRadius: 3, pointBackgroundColor: ACCENT2
    }] },
    options: {
      ...chartDefaults,
      plugins: { ...chartDefaults.plugins, annotation: {} }
    }
  });
}

function updateChartsTypes(data) {
  const colors = data.map(d =>
    d.duree >= 35 ? DANGER + 'CC' :
    d.duree >= 25 ? WARN   + 'CC' : ACCENT + 'CC'
  );
  chartTypes.data.labels   = data.map(d => d.type);
  chartTypes.data.datasets[0].data            = data.map(d => d.duree);
  chartTypes.data.datasets[0].backgroundColor = colors;
  chartTypes.data.datasets[0].borderColor     = colors.map(c => c.slice(0,7));
  chartTypes.update();
}

function updateChartCourbe(data, heureActuelle) {
  chartCourbe.data.labels                = data.map(d => d.heure);
  chartCourbe.data.datasets[0].data      = data.map(d => d.duree);
  chartCourbe.update();
}

function couleurKpi(val, seuil1, seuil2) {
  if (val <= seuil1) return 'green';
  if (val <= seuil2) return 'amber';
  return 'red';
}

async function predict() {
  const position  = parseInt(document.getElementById('position').value);
  const type_rdv  = document.getElementById('type_rdv').value;
  const heure_str = document.getElementById('heure').value;      // "HH:MM"
  const jour      = document.getElementById('jour').value;
  const saison    = document.getElementById('saison').value;

  document.getElementById('spinner').classList.add('show');
  document.querySelector('.btn-primary').disabled = true;

  try {
    const res  = await fetch('/api/predict', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ position, type_rdv, heure_arrivee: heure_str, jour_semaine: jour, saison_annee: saison })
    });
    const data = await res.json();
    if (data.error) { alert('Erreur : ' + data.error); return; }

    // KPIs
    const att = Math.round(data.temps_attente_min);
    document.getElementById('kpi-attente').textContent = att + ' min';
    document.getElementById('kpi-attente').className   = 'card-value ' + couleurKpi(att, 20, 60);
    document.getElementById('kpi-passage').textContent = data.heure_passage;
    document.getElementById('kpi-duree').textContent   = Math.round(data.duree_par_patient) + ' min';

    // Bandeau
    document.getElementById('res-msg').textContent = `Vous êtes en position ${position} — passage estimé à ${data.heure_passage}`;
    document.getElementById('res-sub').textContent = `Attente : ${att} min · ${Math.round(data.duree_par_patient)} min par patient · ${type_rdv}`;
    document.getElementById('result-banner').classList.add('show');

    // Timeline
    buildTimeline(heure_str, data.duree_par_patient, position, data.heure_passage);

    // Graphiques
    document.getElementById('chart-courbe-label').textContent = `${jour} · ${saison}`;

    const [resTypes, resCourbe] = await Promise.all([
      fetch('/api/stats/types', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({jour, saison}) }),
      fetch('/api/stats/courbe', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({jour, saison, type_rdv}) })
    ]);
    updateChartsTypes(await resTypes.json());
    updateChartCourbe(await resCourbe.json(), heure_str);

  } catch(e) { console.error(e); alert('Impossible de contacter le serveur.'); }
  finally {
    document.getElementById('spinner').classList.remove('show');
    document.querySelector('.btn-primary').disabled = false;
  }
}

function buildTimeline(heure_str, duree_par_patient, position, heure_passage) {
  const [h, m] = heure_str.split(':').map(Number);
  const arrivee = new Date(); arrivee.setHours(h, m, 0, 0);
  const fmt = d => `${String(d.getHours()).padStart(2,'0')}h${String(d.getMinutes()).padStart(2,'0')}`;

  const items = [{ label: 'Arrivée en salle d\'attente', time: fmt(arrivee), state: 'done' }];

  // Étapes intermédiaires toutes les ~2 patients
  for (let i = 2; i < position; i += Math.max(1, Math.floor(position / 4))) {
    const t = new Date(arrivee.getTime() + i * duree_par_patient * 60000);
    items.push({ label: `Patient ${i} vu`, time: fmt(t), state: 'now' });
  }

  items.push({ label: 'Votre tour — entrée en consultation', time: heure_passage, state: 'later' });

  const container = document.getElementById('timeline');
  container.innerHTML = '';
  items.forEach((it, idx) => {
    const row = document.createElement('div');
    row.className = 'tl-item';
    row.innerHTML = `<div class="tl-dot ${it.state}"></div><span class="tl-label">${it.label}</span><span class="tl-time">${it.time}</span>`;
    container.appendChild(row);
    if (idx < items.length - 1) {
      const line = document.createElement('div'); line.className = 'tl-line';
      container.appendChild(line);
    }
  });
}

function remplirAuto() {
  const now   = new Date();
  const hh    = String(now.getHours()).padStart(2,'0');
  const mm    = String(now.getMinutes()).padStart(2,'0');
  const jours = ['Lundi','Mardi','Mercredi','Jeudi','Vendredi','Samedi','Dimanche'];
  const saisons = { 12:'Hiver',1:'Hiver',2:'Hiver',3:'Printemps',4:'Printemps',5:'Printemps',6:'Été',7:'Été',8:'Été',9:'Automne',10:'Automne',11:'Automne' };

  document.getElementById('heure').value = `${hh}:${mm}`;

  const jourStr  = jours[now.getDay() === 0 ? 6 : now.getDay() - 1];
  const saisonSt = saisons[now.getMonth() + 1];
  const jourSel  = document.getElementById('jour');
  const saisonSel= document.getElementById('saison');
  for (let o of jourSel.options)   if (o.value === jourStr)  o.selected = true;
  for (let o of saisonSel.options) if (o.value === saisonSt) o.selected = true;

  document.getElementById('now-info').textContent = `Heure actuelle : ${hh}h${mm} · ${jourStr} · ${saisonSt}`;
}

// Init
window.onload = () => { initCharts(); remplirAuto(); };
</script>
</body>
</html>"""

# ── Flask app ─────────────────────────────────────────────────────────────────
app = Flask(__name__)

@app.route("/")
def index():
    return render_template_string(HTML,
        types=TYPES_VALIDES,
        jours=JOURS_VALIDES,
        saisons=SAISONS_VALIDES
    )

@app.route("/api/predict", methods=["POST"])
def api_predict():
    try:
        d        = request.get_json()
        position = int(d.get("position", 1))
        type_rdv = d.get("type_rdv", TYPES_VALIDES[0])
        heure_str= d.get("heure_arrivee", "10:00")
        jour     = d.get("jour_semaine", "Lundi")
        saison   = d.get("saison_annee", "Printemps")

        h, m     = map(int, heure_str.split(":"))
        hd       = h + m / 60
        mois     = {"Hiver":1,"Printemps":4,"Été":7,"Automne":10}.get(saison, 6)

        duree         = round(max(5.0, predire(hd, m, mois, jour, saison, type_rdv)), 1)
        attente       = round(position * duree, 1)
        base          = datetime.now().replace(hour=h, minute=m, second=0, microsecond=0)
        heure_passage = (base + timedelta(minutes=attente)).strftime("%Hh%M")

        return jsonify({
            "position": position, "duree_par_patient": duree,
            "temps_attente_min": attente, "heure_passage": heure_passage
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/stats/types", methods=["POST"])
def api_stats_types():
    d = request.get_json()
    return jsonify(stats_par_type(d.get("jour","Lundi"), d.get("saison","Printemps")))

@app.route("/api/stats/courbe", methods=["POST"])
def api_stats_courbe():
    d = request.get_json()
    return jsonify(courbe_journee(d.get("jour","Lundi"), d.get("saison","Printemps"), d.get("type_rdv", TYPES_VALIDES[0])))

# ── Lancement ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "="*52)
    print("  🏥  SmartWaiting — Dashboard interactif")
    print("="*52)
    print("  ▶  http://localhost:5050")
    print("  Ctrl+C pour arrêter\n")
    threading.Timer(1.2, lambda: webbrowser.open("http://localhost:5050")).start()
    app.run(debug=False, host="0.0.0.0", port=5050)