import psycopg2
import time
from flask import Flask, jsonify, render_template_string, request

# ===== PostgreSQL config (must match the Pi-side PG_CONFIG) =====
PG_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "postgres",
    "user": "postgres",
    "password": "2710",
}

app = Flask(__name__)


def get_pg_conn():
    return psycopg2.connect(**PG_CONFIG)


INDEX_HTML = r"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>IntelliCart Factory Dashboard</title>
  <style>
    * { box-sizing:border-box; margin:0; padding:0; }
    body {
      font-family: system-ui;
      background: #050814;
      color: #f5f6ff;
    }
    .top-nav {
      width: 100%;
      padding: 8px 14px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      background: #050814;
      border-bottom: 1px solid #191e32;
      position: sticky;
      top: 0;
      z-index: 20;
    }
    .nav-title {
      font-weight: 600;
      letter-spacing: 0.06em;
      font-size: 14px;
      text-transform: uppercase;
      color: #9aa3ff;
    }
    .page {
      max-width: 1200px;
      margin: 0 auto;
      padding: 14px;
    }
    h1 {
      font-size: 22px;
      margin-bottom: 6px;
    }
    .subtitle {
      font-size: 13px;
      opacity: 0.8;
      margin-bottom: 12px;
    }

    .vehicles-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 10px;
    }
    .card {
      background: #121627;
      border-radius: 12px;
      padding: 10px 12px;
      box-shadow: 0 8px 18px rgba(0,0,0,0.5);
      border: 1px solid rgba(85,110,200,0.6);
      cursor: pointer;
      transition: transform 0.08s ease-out, box-shadow 0.08s ease-out, border-color 0.08s ease-out;
    }
    .card:hover {
      transform: translateY(-2px);
      box-shadow: 0 12px 26px rgba(0,0,0,0.7);
      border-color: rgba(130,160,255,0.9);
    }
    .card-selected {
      border-color: #2e63ff;
      box-shadow: 0 14px 30px rgba(46,99,255,0.7);
    }
    .vehicle-id {
      font-size: 15px;
      font-weight: 600;
      margin-bottom: 4px;
    }
    .status-line {
      font-size: 13px;
      margin: 2px 0;
    }
    .badge-row {
      margin-top: 6px;
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
    }
    .badge {
      padding: 2px 6px;
      border-radius: 999px;
      font-size: 11px;
      background: #1f2438;
      border: 1px solid rgba(140,160,255,0.6);
    }
    .badge-active {
      background: #2e63ff;
      border-color: #2e63ff;
      color: #ffffff;
    }
    .badge-danger {
      background: #ff3b63;
      border-color: #ff3b63;
      color: #ffffff;
    }
    .last-seen {
      font-size: 11px;
      opacity: 0.7;
      margin-top: 4px;
    }

    /* Graphs section */
    #graphs {
      margin-top: 20px;
      display: none;
    }
    #graphs h2 {
      font-size: 18px;
      margin-bottom: 4px;
    }
    #graphs .graphs-note {
      font-size: 12px;
      opacity: 0.75;
      margin-bottom: 10px;
    }

    .graph-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 10px;
    }
    .graph-card {
      background: #14182a;
      border-radius: 10px;
      padding: 8px;
      border: 1px solid rgba(90,110,200,0.7);
      box-shadow: 0 8px 18px rgba(0,0,0,0.6);
    }
    .graph-card h3 {
      font-size: 13px;
      margin-bottom: 4px;
    }
    .graph-card canvas {
      width: 100%;
      height: 170px;
    }

    @media (max-width: 700px) {
      .graph-card canvas {
        height: 150px;
      }
    }
  </style>
</head>
<body>
  <div class="top-nav">
    <div class="nav-title">IntelliCart Factory Dashboard</div>
  </div>
  <div class="page">
    <h1>Vehicle Status</h1>
    <div class="subtitle">
      Central view of all IntelliCart vehicles. Click one vehicle to see its graphs (speed, distance, CPU temp, modes & obstacles).
    </div>

    <div id="vehicles" class="vehicles-grid">
      <!-- Filled by JS -->
    </div>

    <!-- Graphs for selected vehicle -->
    <div id="graphs">
      <h2>History: <span id="graphs-vid"></span></h2>
      <div class="graphs-note">
        Showing recent data (last 10 minutes if available) from PostgreSQL.
      </div>
      <div class="graph-grid">
        <div class="graph-card">
          <h3>Speed (smoothed)</h3>
          <canvas id="g-speed"></canvas>
        </div>
        <div class="graph-card">
          <h3>Distance (cm)</h3>
          <canvas id="g-distance"></canvas>
        </div>
        <div class="graph-card">
          <h3>CPU Temperature (°C)</h3>
          <canvas id="g-cpu"></canvas>
        </div>
        <div class="graph-card">
          <h3>Modes & Obstacles</h3>
          <canvas id="g-modes"></canvas>
        </div>
      </div>
    </div>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <script>
    // ===== Vehicle list + selection =====
    let selectedVehicleId = null;

    function formatAgo(ts) {
      if(!ts) return "Unknown";
      const now = Date.now() / 1000;
      const diff = Math.max(0, now - ts);
      if(diff < 5) return "just now";
      if(diff < 60) return Math.round(diff) + " s ago";
      const m = diff / 60;
      if(m < 60) return Math.round(m) + " min ago";
      const h = m / 60;
      return Math.round(h) + " h ago";
    }

    function selectVehicle(vid) {
      selectedVehicleId = vid;
      // Highlight card
      document.querySelectorAll(".card").forEach(c => {
        if(c.dataset.vehicleId === vid) c.classList.add("card-selected");
        else c.classList.remove("card-selected");
      });
      // Load graphs for this vehicle
      loadVehicleHistory(vid);
    }

    function updateVehicles() {
      fetch("/api/vehicles")
        .then(r => r.json())
        .then(d => {
          const cont = document.getElementById("vehicles");
          const list = d.vehicles || [];
          if(!list.length){
            cont.innerHTML = "<div class='status-line'>No data yet. Waiting for vehicles to report...</div>";
            return;
          }
          cont.innerHTML = "";
          list.forEach(v => {
            const card = document.createElement("div");
            card.className = "card";
            card.dataset.vehicleId = v.vehicle_id;

            const motion = v.motion || "stop";
            const obstacle = v.obstacle ? true : false;
            const modes = v.modes || {};
            const line = v.line || [0,0,0];

            let html = "";
            html += "<div class='vehicle-id'>" + (v.vehicle_id || "Unknown vehicle") + "</div>";
            html += "<div class='status-line'>Motion: <b>" + motion + "</b>, Speed: <b>" + (v.speed||0).toFixed(1) + "</b></div>";
            html += "<div class='status-line'>Distance: " + (v.distance||0).toFixed(1) + " cm, CPU: " + (v.cpu_temp||0).toFixed(1) + " °C</div>";
            html += "<div class='status-line'>Line sensors: [" + line.join(", ") + "]</div>";

            html += "<div class='badge-row'>";
            if(modes.line_track)      html += "<span class='badge badge-active'>Line</span>";
            if(modes.avoid_obstacles) html += "<span class='badge badge-active'>Avoid</span>";
            if(modes.color_follow)    html += "<span class='badge badge-active'>Follow</span>";
            if(modes.color_detect)    html += "<span class='badge'>Color detect</span>";
            if(modes.face_detect)     html += "<span class='badge'>Face</span>";
            if(obstacle)              html += "<span class='badge badge-danger'>Obstacle</span>";
            html += "</div>";

            html += "<div class='last-seen'>Last update: " + formatAgo(v.ts) + "</div>";

            card.innerHTML = html;
            card.onclick = () => selectVehicle(v.vehicle_id);

            cont.appendChild(card);
          });

          // If nothing selected yet, auto-select the first
          if(!selectedVehicleId && list.length > 0) {
            selectVehicle(list[0].vehicle_id);
          }
        })
        .catch(() => {
          // ignore for now
        });
    }

    updateVehicles();
    setInterval(updateVehicles, 2000);

    // ===== Charts setup =====
    let speedChart = null;
    let distanceChart = null;
    let cpuChart = null;
    let modesChart = null;
    let tCounter = 0;

    function ensureCharts() {
      const speedCtx = document.getElementById("g-speed").getContext("2d");
      const distanceCtx = document.getElementById("g-distance").getContext("2d");
      const cpuCtx = document.getElementById("g-cpu").getContext("2d");
      const modesCtx = document.getElementById("g-modes").getContext("2d");

      if(!speedChart) {
        speedChart = new Chart(speedCtx, {
          type: "line",
          data: { labels: [], datasets: [{ label:"Speed", data: [], borderWidth:1.5, tension:0.15, pointRadius:0 }] },
          options: {
            responsive:true,
            animation:false,
            scales:{
              x:{ display:false },
              y:{
                min:0, max:100,
                ticks:{ color:"#9ca3c7", font:{size:10} },
                grid:{ color:"rgba(80,90,130,0.4)" }
              }
            },
            plugins:{ legend:{ display:false } }
          }
        });
      }
      if(!distanceChart) {
        distanceChart = new Chart(distanceCtx, {
          type: "line",
          data: { labels: [], datasets: [{ label:"Distance", data: [], borderWidth:1.5, tension:0.15, pointRadius:0 }] },
          options: {
            responsive:true,
            animation:false,
            scales:{
              x:{ display:false },
              y:{
                min:0, max:150,
                ticks:{ color:"#9ca3c7", font:{size:10} },
                grid:{ color:"rgba(80,90,130,0.4)" }
              }
            },
            plugins:{ legend:{ display:false } }
          }
        });
      }
      if(!cpuChart) {
        cpuChart = new Chart(cpuCtx, {
          type: "line",
          data: { labels: [], datasets: [{ label:"CPU", data: [], borderWidth:1.5, tension:0.15, pointRadius:0 }] },
          options: {
            responsive:true,
            animation:false,
            scales:{
              x:{ display:false },
              y:{
                min:20, max:90,
                ticks:{ color:"#9ca3c7", font:{size:10} },
                grid:{ color:"rgba(80,90,130,0.4)" }
              }
            },
            plugins:{ legend:{ display:false } }
          }
        });
      }
      if(!modesChart) {
        modesChart = new Chart(modesCtx, {
          type: "line",
          data: {
            labels: [],
            datasets: [
              { label:"Line track",      data: [], borderWidth:1.2, tension:0.1, pointRadius:0 },
              { label:"Avoid obstacles", data: [], borderWidth:1.2, tension:0.1, pointRadius:0 },
              { label:"Color follow",    data: [], borderWidth:1.2, tension:0.1, pointRadius:0 },
              { label:"Obstacle",        data: [], borderWidth:1.2, tension:0.1, pointRadius:0 },
            ]
          },
          options: {
            responsive:true,
            animation:false,
            scales:{
              x:{ display:false },
              y:{
                min:-0.1, max:1.1,
                ticks:{ color:"#9ca3c7", font:{size:10} },
                grid:{ color:"rgba(80,90,130,0.4)" }
              }
            },
            plugins:{
              legend:{
                display:true,
                labels:{ color:"#cfd4ff", font:{size:10} }
              }
            }
          }
        });
      }
    }

    function loadVehicleHistory(vehicleId) {
      if(!vehicleId) return;
      document.getElementById("graphs-vid").textContent = vehicleId;
      document.getElementById("graphs").style.display = "block";

      // Load last 10 minutes from central DB
      fetch("/api/history?vehicle_id=" + encodeURIComponent(vehicleId) + "&seconds=600")
        .then(r => r.json())
        .then(d => {
          const history = d.history || [];
          ensureCharts();
          tCounter = 0;

          const labels = [];
          const speedData = [];
          const distanceData = [];
          const cpuData = [];
          const lt = [];
          const av = [];
          const cf = [];
          const obs = [];

          history.forEach((s, i) => {
            labels.push(i);
            speedData.push(s.speed || 0);
            distanceData.push(s.distance || 0);
            cpuData.push(s.cpu_temp || 0);

            const modes = s.modes || {};
            lt.push(modes.line_track ? 1 : 0);
            av.push(modes.avoid_obstacles ? 1 : 0);
            cf.push(modes.color_follow ? 1 : 0);
            obs.push(s.obstacle ? 1 : 0);
          });

          speedChart.data.labels = labels;
          speedChart.data.datasets[0].data = speedData;
          speedChart.update();

          distanceChart.data.labels = labels;
          distanceChart.data.datasets[0].data = distanceData;
          distanceChart.update();

          cpuChart.data.labels = labels;
          cpuChart.data.datasets[0].data = cpuData;
          cpuChart.update();

          modesChart.data.labels = labels;
          modesChart.data.datasets[0].data = lt;
          modesChart.data.datasets[1].data = av;
          modesChart.data.datasets[2].data = cf;
          modesChart.data.datasets[3].data = obs;
          modesChart.update();
        })
        .catch(() => {
          // ignore
        });
    }
  </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(INDEX_HTML)


@app.route("/api/vehicles")
def api_vehicles():
    """
    Returns latest status per vehicle_id from vehicle_telemetry.
    Used for the cards at the top of the dashboard.
    """
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT DISTINCT ON (vehicle_id)
                    vehicle_id, ts, speed, raw_speed, distance,
                    line_l, line_m, line_r,
                    motion, line_state, obstacle, cpu_temp,
                    line_track, avoid_obstacles, color_follow, color_detect, face_detect
                FROM vehicle_telemetry
                ORDER BY vehicle_id, ts DESC;
            """)
            rows = cur.fetchall()
    except Exception as e:
        print("PostgreSQL /api/vehicles error:", e)
        return jsonify({"vehicles": []})

    vehicles = []
    for row in rows:
        vehicles.append({
            "vehicle_id": row[0],
            "ts": row[1],
            "speed": row[2],
            "raw_speed": row[3],
            "distance": row[4],
            "line": [row[5], row[6], row[7]],
            "motion": row[8],
            "line_state": row[9],
            "obstacle": bool(row[10]),
            "cpu_temp": row[11],
            "modes": {
                "line_track": bool(row[12]),
                "avoid_obstacles": bool(row[13]),
                "color_follow": bool(row[14]),
                "color_detect": bool(row[15]),
                "face_detect": bool(row[16]),
            }
        })
    return jsonify({"vehicles": vehicles})


@app.route("/api/history")
def api_history():
    """
    Return recent telemetry history for a single vehicle from PostgreSQL.
    Query params:
      - vehicle_id (required)
      - seconds (optional, default 600)
    """
    vehicle_id = request.args.get("vehicle_id")
    if not vehicle_id:
        return jsonify({"error": "vehicle_id is required"}), 400

    secs = request.args.get("seconds", default=600, type=int)
    if secs <= 0:
        secs = 600
    if secs > 86400:
        secs = 86400  # max 24h

    cutoff = time.time() - secs

    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT ts, speed, raw_speed, distance,
                       line_l, line_m, line_r,
                       motion, line_state, obstacle, cpu_temp,
                       line_track, avoid_obstacles, color_follow, color_detect, face_detect
                FROM vehicle_telemetry
                WHERE vehicle_id = %s AND ts >= %s
                ORDER BY ts ASC
            """, (vehicle_id, cutoff))
            rows = cur.fetchall()
    except Exception as e:
        print("PostgreSQL /api/history error:", e)
        return jsonify({"vehicle_id": vehicle_id, "history": []})

    history = []
    for r in rows:
        history.append({
            "ts": r[0],
            "speed": r[1],
            "raw_speed": r[2],
            "distance": r[3],
            "line": [r[4], r[5], r[6]],
            "motion": r[7],
            "line_state": r[8],
            "obstacle": bool(r[9]),
            "cpu_temp": r[10],
            "modes": {
                "line_track": bool(r[11]),
                "avoid_obstacles": bool(r[12]),
                "color_follow": bool(r[13]),
                "color_detect": bool(r[14]),
                "face_detect": bool(r[15]),
            }
        })

    return jsonify({"vehicle_id": vehicle_id, "history": history})


if __name__ == "__main__":
    print("IntelliCart central dashboard at http://0.0.0.0:8000")
    app.run(host="0.0.0.0", port=8000, debug=False)
