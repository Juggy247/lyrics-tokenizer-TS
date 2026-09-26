const IS_LOCAL_LIVE_SERVER = ["localhost", "127.0.0.1"].includes(window.location.hostname)
  && window.location.port === "5500";
const API_BASE = window.location.protocol === "file:" || IS_LOCAL_LIVE_SERVER
  ? "http://127.0.0.1:8000"
  : "";

document.getElementById("checkButton").addEventListener("click", async () => {
  const text = document.getElementById("textInput").value;
  const errorDiv = document.getElementById("error");
  const resultDiv = document.getElementById("result");

  errorDiv.textContent = "";
  resultDiv.style.display = "none";

  if (!text.trim()) {
    errorDiv.textContent = "Please enter some text.";
    return;
  }

  try {
    const response = await fetch(API_BASE + "/swiftian-score", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: text }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      errorDiv.textContent = "Error: " + JSON.stringify(errorData.detail || errorData);
      return;
    }

    const data = await response.json();

    document.getElementById("score").textContent = data.swiftian_score + "%";
    document.getElementById("verdict").textContent = data.verdict;
    document.getElementById("compression").textContent = data.compression_ratio;
    document.getElementById("familiarity").textContent = data.familiarity_score;

    const tokensDiv = document.getElementById("tokens");
    tokensDiv.innerHTML = "";
    data.tokens.forEach((tok, i) => {
      const span = document.createElement("span");
      span.className = "token token-" + (i % 6);
      span.textContent = tok.replace(/^ /, "·");
      tokensDiv.appendChild(span);
    });

    resultDiv.style.display = "block";

  } catch (err) {
    errorDiv.textContent = "Could not reach the API. Is the backend running?";
    console.error(err);
  }
});


async function loadEraChart() {
  try {
    const response = await fetch(API_BASE + "/stats/eras");
    if (!response.ok) {
      console.error("Failed to load era stats");
      return;
    }
    const data = await response.json();
    const albums = data.major_albums;

    const labels = albums.map(a => a.era);
    const compressions = albums.map(a => a.compression_ratio);

    const palette = [
      "#f87171", "#fb923c", "#fbbf24", "#a3e635", "#34d399",
      "#22d3ee", "#60a5fa", "#818cf8", "#a78bfa", "#f472b6",
      "#fb7185", "#facc15", "#4ade80",
    ];

    const barColors = albums.map((_, i) => palette[i % palette.length]);

    const ctx = document.getElementById("eraChart").getContext("2d");
    new Chart(ctx, {
      type: "bar",
      data: {
        labels: labels,
        datasets: [{
          label: "Compression ratio",
          data: compressions,
          backgroundColor: barColors,
        }],
      },
      options: {
        plugins: {
          title: {
            display: true,
            text: "SwiftBPE Compression Ratio by Album Era",
            font: { size: 18, weight: "bold" },
          },
          legend: { display: false },
        },
        scales: {
          x: {
            ticks: {
              font: { weight: "bold" },
              autoSkip: false,
              maxRotation: 45,
              minRotation: 45,
            },
          },
          y: { beginAtZero: false },
        },
      },
    });
  } catch (err) {
    console.error("Could not load era chart", err);
  }
}

loadEraChart();