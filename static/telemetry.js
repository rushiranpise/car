// Telemetry dashboard using Chart.js (on same page under controller)

const maxPoints = 600; // up to ~10 minutes at 1s per sample

// Helper to create a line chart
function createLineChart(ctx, label, color, minY, maxY) {
  return new Chart(ctx, {
    type: "line",
    data: {
      labels: [],
      datasets: [{
        label,
        data: [],
        borderColor: color,
        borderWidth: 1.5,
        pointRadius: 0,
        fill: false,
        tension: 0.15,
      }]
    },
    options: {
      responsive: true,
      animation: false,
      scales: {
        x: {
          display: false,
        },
        y: {
          min: minY,
          max: maxY,
          ticks: {
            color: "#9ca3c7",
            font: { size: 10 },
          },
          grid: {
            color: "rgba(80,90,130,0.4)",
          }
        }
      },
      plugins: {
        legend: {
          display: false
        }
      }
    }
  });
}

// Helper to create multi-line chart
function createMultiLineChart(ctx, labels, colors, minY, maxY) {
  const datasets = labels.map((label, i) => ({
    label,
    data: [],
    borderColor: colors[i],
    borderWidth: 1.2,
    pointRadius: 0,
    fill: false,
    tension: 0.15,
  }));
  return new Chart(ctx, {
    type: "line",
    data: {
      labels: [],
      datasets
    },
    options: {
      responsive: true,
      animation: false,
      scales: {
        x: { display: false },
        y: {
          min: minY,
          max: maxY,
          ticks: {
            color: "#9ca3c7",
            font: { size: 10 },
          },
          grid: {
            color: "rgba(80,90,130,0.4)",
          }
        }
      },
      plugins: {
        legend: {
          display: true,
          labels: {
            color: "#cfd4ff",
            font: { size: 10 },
          }
        }
      }
    }
  });
}

// Initialize charts
const speedChart   = createLineChart(
  document.getElementById("chart-speed"),
  "Speed (smoothed)",
  "#4f9cff",
  0, 100
);
const motorChart   = createLineChart(
  document.getElementById("chart-motor"),
  "Motor input",
  "#ffb347",
  0, 100
);
const cpuChart     = createLineChart(
  document.getElementById("chart-cpu"),
  "CPU temp (°C)",
  "#ff6b9b",
  20, 90
);
const distanceChart = createLineChart(
  document.getElementById("chart-distance"),
  "Distance (cm)",
  "#4ade80",
  0, 150
);
const lineChart    = createMultiLineChart(
  document.getElementById("chart-line"),
  ["Left", "Middle", "Right"],
  ["#f97373", "#facc15", "#38bdf8"],
  -0.1, 1.1
);
const modesChart   = createMultiLineChart(
  document.getElementById("chart-modes"),
  ["Line track", "Avoid obstacles", "Color follow", "Obstacle"],
  ["#6366f1", "#22c55e", "#f97316", "#ef4444"],
  -0.1, 1.1
);

let t = 0;

// Push new point, trim history
function pushPoint(chart, value) {
  const labels = chart.data.labels;
  const data = chart.data.datasets[0].data;
  labels.push(t);
  data.push(value);
  if (labels.length > maxPoints) {
    labels.shift();
    data.shift();
  }
}

// For multi-line chart
function pushPointMulti(chart, values) {
  const labels = chart.data.labels;
  labels.push(t);
  if (labels.length > maxPoints) {
    labels.shift();
  }
  chart.data.datasets.forEach((ds, i) => {
    ds.data.push(values[i]);
    if (ds.data.length > maxPoints) {
      ds.data.shift();
    }
  });
}

// Load history from DB (e.g. last 10 minutes)
function loadHistory(seconds = 600) {
  fetch(`/api/history?seconds=${seconds}`)
    .then(r => r.json())
    .then(data => {
      const history = data.history || [];

      // clear existing data
      [speedChart, motorChart, cpuChart, distanceChart, lineChart, modesChart].forEach(ch => {
        ch.data.labels = [];
        ch.data.datasets.forEach(ds => ds.data = []);
      });
      t = 0;

      history.forEach(sample => {
        const sp   = sample.speed || 0;
        const raw  = sample.raw_speed || 0;
        const dist = sample.distance || 0;
        const cpu  = sample.cpu_temp || 0;
        const line = sample.line || [0,0,0];
        const modes = sample.modes || {};
        const obstacle = sample.obstacle ? 1 : 0;

        const l = line[0] || 0;
        const m = line[1] || 0;
        const r = line[2] || 0;

        const ml = modes.line_track ? 1 : 0;
        const ma = modes.avoid_obstacles ? 1 : 0;
        const mf = modes.color_follow ? 1 : 0;

        t += 1;
        pushPoint(speedChart, sp);
        pushPoint(motorChart, raw);
        pushPoint(cpuChart, cpu);
        pushPoint(distanceChart, dist);
        pushPointMulti(lineChart, [l, m, r]);
        pushPointMulti(modesChart, [ml, ma, mf, obstacle]);
      });

      speedChart.update();
      motorChart.update();
      cpuChart.update();
      distanceChart.update();
      lineChart.update();
      modesChart.update();
    })
    .catch(() => {
      // ignore
    });
}

// Poll backend for live data (append on top of history)
function updateTelemetryCharts() {
  fetch("/api/status")
    .then(r => r.json())
    .then(d => {
      t += 1;

      const speed = d.speed || 0;
      const rawSpeed = d.raw_speed || 0;
      const dist = d.distance || 0;
      const cpu = d.cpu_temp || 0;
      const line = d.line || [0,0,0];
      const modes = d.modes || {};
      const obstacle = d.obstacle_detected ? 1 : 0;

      // Single-line charts
      pushPoint(speedChart, speed);
      pushPoint(motorChart, rawSpeed);
      pushPoint(cpuChart, cpu);
      pushPoint(distanceChart, dist);

      // Line sensors: 0/1
      const l = line[0] || 0;
      const m = line[1] || 0;
      const r = line[2] || 0;
      pushPointMulti(lineChart, [l, m, r]);

      // Modes: bool → 0/1
      const ml = modes.line_track ? 1 : 0;
      const ma = modes.avoid_obstacles ? 1 : 0;
      const mf = modes.color_follow ? 1 : 0;
      pushPointMulti(modesChart, [ml, ma, mf, obstacle]);

      speedChart.update();
      motorChart.update();
      cpuChart.update();
      distanceChart.update();
      lineChart.update();
      modesChart.update();
    })
    .catch(() => {
      // ignore errors
    });
}

// First load DB history, then start live polling
loadHistory(600);
setInterval(updateTelemetryCharts, 1000);  // 1 Hz live updates
