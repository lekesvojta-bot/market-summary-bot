/* Dashboard: načte docs/data/*.json a vykreslí karty akcií, grafy a sekce. */

let history = [];
const charts = [];

function fmtPct(value) {
  if (value === null || value === undefined) return null;
  return (value >= 0 ? "+" : "") + value.toFixed(2) + " %";
}

function pctClass(value) {
  if (value > 0.15) return "up";
  if (value < -0.15) return "down";
  return "flat";
}

function fmtPragueTime(isoString) {
  return new Date(isoString).toLocaleString("cs-CZ", {
    timeZone: "Europe/Prague",
    day: "numeric", month: "numeric", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function daysUntil(dateString) {
  const target = new Date(dateString + "T00:00:00Z");
  return Math.ceil((target - new Date()) / 86400000);
}

function renderStockCard(stock) {
  const card = el("article", "card");
  const title = el("h2");
  title.append(el("span", null, stock.symbol));

  if (stock.quote) {
    title.append(el("span", "price", stock.quote.price.toFixed(2) + " USD"));
    const chg = el("span", "chg " + pctClass(stock.quote.change_pct), fmtPct(stock.quote.change_pct));
    title.append(chg);
  } else {
    title.append(el("span", "chg flat", "cena nedostupná"));
  }
  card.append(title);

  const badges = el("div", "badges");
  if (stock.week_change_pct !== null && stock.week_change_pct !== undefined) {
    badges.append(el("span", "badge", "7 dní: " + fmtPct(stock.week_change_pct)));
  }
  if (stock.quote) {
    badges.append(el("span", "badge",
      "rozpětí " + stock.quote.day_low + "–" + stock.quote.day_high + " USD"));
  }
  if (stock.earnings_date) {
    const days = daysUntil(stock.earnings_date);
    badges.append(el("span", "badge earnings",
      "⚠️ výsledky " + new Date(stock.earnings_date).toLocaleDateString("cs-CZ") +
      (days >= 0 ? ` (za ${days} d.)` : "")));
  }
  if (badges.children.length) card.append(badges);

  // Graf vývoje ceny z historie (jen pokud máme aspoň 2 body).
  const points = history
    .filter((rec) => rec.prices[stock.symbol])
    .map((rec) => ({ x: fmtPragueTime(rec.timestamp), y: rec.prices[stock.symbol].price }));
  if (points.length >= 2) {
    const wrap = el("div", "chart-wrap");
    const canvas = document.createElement("canvas");
    wrap.append(canvas);
    card.append(wrap);
    charts.push(new Chart(canvas, {
      type: "line",
      data: {
        labels: points.map((p) => p.x),
        datasets: [{
          data: points.map((p) => p.y),
          borderColor: "#5b9dff",
          backgroundColor: "rgba(91,157,255,0.12)",
          fill: true,
          tension: 0.25,
          pointRadius: points.length > 30 ? 0 : 2,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { display: false },
          y: { ticks: { color: "#93a0b8", font: { size: 10 } }, grid: { color: "#2b3550" } },
        },
      },
    }));
  }

  card.append(el("p", "analysis", stock.analysis || "(analýza není k dispozici)"));

  if (stock.note) card.append(el("p", "note", stock.note));

  if (stock.news && stock.news.length) {
    const details = el("details");
    details.append(el("summary", null, `Novinky (${stock.news.length})`));
    const list = el("ul", "news-list");
    for (const item of stock.news) {
      const li = el("li");
      if (item.url) {
        const link = el("a", null, item.headline);
        link.href = item.url;
        link.target = "_blank";
        link.rel = "noopener";
        li.append(link);
      } else {
        li.append(el("b", null, item.headline));
      }
      if (item.summary) li.append(document.createTextNode(" — " + item.summary));
      list.append(li);
    }
    details.append(list);
    card.append(details);
  }

  return card;
}

function renderRun(run) {
  document.getElementById("last-update").textContent =
    "Stav k " + fmtPragueTime(run.timestamp);

  for (const chart of charts.splice(0)) chart.destroy();
  const stocksSection = document.getElementById("stocks");
  stocksSection.replaceChildren();
  for (const stock of run.stocks) stocksSection.append(renderStockCard(stock));

  document.getElementById("macro-analysis").textContent = run.macro_analysis || "";
  const macroList = document.getElementById("macro-news");
  macroList.replaceChildren();
  for (const item of run.macro_news || []) {
    const li = el("li");
    if (item.url) {
      const link = el("a", null, item.headline);
      link.href = item.url;
      link.target = "_blank";
      link.rel = "noopener";
      li.append(link);
    } else {
      li.append(el("b", null, item.headline));
    }
    macroList.append(li);
  }

  const tips = document.getElementById("tips");
  tips.replaceChildren();
  for (const tip of run.tips || []) {
    const li = el("li");
    li.append(el("b", null, tip.ticker + ": "));
    li.append(document.createTextNode(tip.reason));
    tips.append(li);
  }

  if (run.glossary) {
    document.getElementById("glossary-term").textContent = run.glossary.term;
    document.getElementById("glossary-explanation").textContent = run.glossary.explanation;
  }

  const recap = document.getElementById("weekly-recap");
  if (run.weekly_recap) {
    document.getElementById("weekly-recap-text").textContent = run.weekly_recap;
    recap.classList.remove("hidden");
  } else {
    recap.classList.add("hidden");
  }
}

async function loadJson(path) {
  const response = await fetch(path, { cache: "no-store" });
  if (!response.ok) throw new Error(`Nelze načíst ${path} (${response.status})`);
  return response.json();
}

async function init() {
  try {
    const [latest, hist, archiveIndex] = await Promise.all([
      loadJson("data/latest.json"),
      loadJson("data/history.json"),
      loadJson("data/archive/index.json").catch(() => []),
    ]);
    history = hist;

    const select = document.getElementById("archive-select");
    select.append(new Option("Nejnovější", "latest"));
    for (const name of archiveIndex) {
      const label = name.replace(".json", "").replace(/-(\d{2})(\d{2})$/, " $1:$2 UTC");
      select.append(new Option(label, name));
    }
    select.addEventListener("change", async () => {
      const value = select.value;
      const run = value === "latest"
        ? await loadJson("data/latest.json")
        : await loadJson("data/archive/" + value);
      renderRun(run);
    });

    renderRun(latest);
  } catch (error) {
    document.getElementById("last-update").textContent =
      "Data se nepodařilo načíst: " + error.message;
  }
}

init();
