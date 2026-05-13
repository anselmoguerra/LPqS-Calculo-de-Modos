const EXAMPLES = {
  small: { length: 3.0, width: 3.6, height: 2.4, maxFrequency: 300 },
  studio: { length: 5.2, width: 7.1, height: 3.1, maxFrequency: 300 },
  concert: { length: 18.0, width: 28.0, height: 11.0, maxFrequency: 160 },
};

const BANDS = [25, 31.5, 40, 50, 63, 80, 100, 125, 160, 200, 250];

const COLORS = {
  axial: "#b84a4a",
  tangential: "#3f78a9",
  oblique: "#4f955f",
};

const LABELS = {
  axial: "axial",
  tangential: "tangencial",
  oblique: "oblíquo",
};

const MODAL_DENSITY_WEIGHTS = {
  axial: 1,
  tangential: 0.5,
  oblique: 0.25,
};

const form = document.querySelector("#roomForm");
const inputs = {
  length: document.querySelector("#length"),
  width: document.querySelector("#width"),
  height: document.querySelector("#height"),
  temperature: document.querySelector("#temperature"),
  maxFrequency: document.querySelector("#maxFrequency"),
};

let currentModes = [];
let currentRoom = null;

function speedOfSound(temperatureC) {
  return 20.06 * Math.sqrt(temperatureC + 273);
}

function classifyMode(p, q, r) {
  const nonZero = [p, q, r].filter((value) => value > 0).length;
  if (nonZero === 1) return "axial";
  if (nonZero === 2) return "tangential";
  return "oblique";
}

function modalFrequency(room, p, q, r) {
  return room.speed / 2 * Math.sqrt(
    (p / room.length) ** 2 +
    (q / room.width) ** 2 +
    (r / room.height) ** 2
  );
}

function maxIndex(dimension, maxFrequency, speed) {
  return Math.ceil((2 * maxFrequency * dimension) / speed);
}

function calculateModes(room) {
  const maxP = maxIndex(room.length, room.maxFrequency, room.speed);
  const maxQ = maxIndex(room.width, room.maxFrequency, room.speed);
  const maxR = maxIndex(room.height, room.maxFrequency, room.speed);
  const modes = [];

  for (let p = 0; p <= maxP; p += 1) {
    for (let q = 0; q <= maxQ; q += 1) {
      for (let r = 0; r <= maxR; r += 1) {
        if (p === 0 && q === 0 && r === 0) continue;
        const frequency = modalFrequency(room, p, q, r);
        if (frequency <= room.maxFrequency) {
          modes.push({
            p,
            q,
            r,
            frequency,
            rounded: Math.round(frequency),
            type: classifyMode(p, q, r),
          });
        }
      }
    }
  }

  return modes.sort((a, b) => a.frequency - b.frequency || a.type.localeCompare(b.type));
}

function roomRatio(room) {
  const sorted = [room.length, room.width, room.height].sort((a, b) => a - b);
  return [1, sorted[1] / sorted[0], sorted[2] / sorted[0]];
}

function countBy(items, keyFn) {
  const map = new Map();
  items.forEach((item) => {
    const key = keyFn(item);
    map.set(key, (map.get(key) || 0) + 1);
  });
  return map;
}

function countsByFrequency(modes) {
  const counts = new Map();
  modes.forEach((mode) => {
    if (!counts.has(mode.rounded)) {
      counts.set(mode.rounded, { axial: 0, tangential: 0, oblique: 0 });
    }
    counts.get(mode.rounded)[mode.type] += 1;
  });
  return new Map([...counts.entries()].sort((a, b) => a[0] - b[0]));
}

function bandEdges(centerFrequency) {
  const ratio = 2 ** (1 / 6);
  return [centerFrequency / ratio, centerFrequency * ratio];
}

function countsByBand(modes) {
  return BANDS.map((band) => {
    const [low, high] = bandEdges(band);
    const counts = { axial: 0, tangential: 0, oblique: 0 };
    modes.forEach((mode) => {
      if (mode.frequency >= low && mode.frequency < high) {
        counts[mode.type] += 1;
      }
    });
    const total = counts.axial + counts.tangential + counts.oblique;
    return { band, counts, total, density: total / band };
  });
}

function weightedDensityByBand(modes) {
  return BANDS.map((band) => {
    const [low, high] = bandEdges(band);
    let weightedTotal = 0;

    modes.forEach((mode) => {
      if (mode.frequency >= low && mode.frequency < high) {
        // A ponderação reduz a influência dos modos tangenciais e oblíquos,
        // aproximando a densidade modal do comportamento da planilha original.
        weightedTotal += MODAL_DENSITY_WEIGHTS[mode.type];
      }
    });

    return { band, weightedTotal, density: weightedTotal / band };
  });
}

function modalDensityTickStep(maxDensity) {
  if (maxDensity <= 0.5) return 0.05;
  if (maxDensity <= 1) return 0.1;
  if (maxDensity <= 2) return 0.2;
  if (maxDensity <= 5) return 0.5;
  return Math.ceil(maxDensity / 8);
}

function modeCountTickStep(maxCount) {
  if (maxCount <= 6) return 1;
  if (maxCount <= 12) return 2;
  if (maxCount <= 30) return 5;
  if (maxCount <= 60) return 10;
  return Math.ceil(maxCount / 6 / 10) * 10;
}

function bandRangeLabel(centerFrequency) {
  const [low, high] = bandEdges(centerFrequency);
  const format = (value) => value < 10 ? value.toFixed(1) : String(Math.round(value));
  return `${format(low)}-${format(high)}`;
}

function ratioWarnings(room, modes) {
  const warnings = [];
  const dims = [
    ["comprimento", room.length],
    ["largura", room.width],
    ["altura", room.height],
  ];

  for (let i = 0; i < dims.length; i += 1) {
    for (let j = i + 1; j < dims.length; j += 1) {
      const [nameA, valueA] = dims[i];
      const [nameB, valueB] = dims[j];
      const ratio = Math.max(valueA, valueB) / Math.min(valueA, valueB);
      if (Math.abs(ratio - 1) <= 0.05) {
        warnings.push({ severity: "alto", message: `${nameA} e ${nameB} são quase iguais. Salas quase cúbicas concentram modos nas mesmas frequências.` });
      }
      [2, 3].forEach((integerRatio) => {
        if (Math.abs(ratio - integerRatio) / integerRatio <= 0.03) {
          warnings.push({ severity: "alto", message: `${nameA} e ${nameB} estão perto de uma proporção ${integerRatio}:1. Isso pode reforçar cancelamentos e ressonâncias.` });
        }
      });
    }
  }

  const axialModes = modes.filter((mode) => mode.type === "axial");
  const axialCounts = countBy(axialModes, (mode) => mode.rounded);
  const coincident = [...axialCounts.entries()].filter(([, count]) => count > 1).map(([frequency]) => frequency);
  if (coincident.length) {
    warnings.push({ severity: "alto", message: `Há modos axiais coincidentes ou quase coincidentes em ${coincident.slice(0, 8).join(", ")} Hz.` });
  }

  const firstAxials = axialModes.map((mode) => mode.frequency).sort((a, b) => a - b).slice(0, 6);
  for (let i = 0; i < firstAxials.length - 1; i += 1) {
    const gap = firstAxials[i + 1] - firstAxials[i];
    if (gap < 5) {
      warnings.push({ severity: "medio", message: `Dois dos primeiros modos axiais estão separados por apenas ${gap.toFixed(1)} Hz (${firstAxials[i].toFixed(1)} e ${firstAxials[i + 1].toFixed(1)} Hz).` });
      break;
    }
  }

  const [, middle, longest] = roomRatio(room);
  if (middle < 1.1 || longest < 1.4) {
    warnings.push({ severity: "medio", message: `A proporção normalizada 1:${middle.toFixed(2)}:${longest.toFixed(2)} é pouco espalhada. Dimensões mais diferentes distribuem melhor os modos.` });
  }

  return warnings.length ? warnings : [{ severity: "ok", message: "Nenhum problema simples de proporção foi detectado. Confirme sempre com medição real da sala." }];
}

function frequencyRegionIndex(frequency) {
  if (frequency < 80) return 0;
  if (frequency < 250) return 1;
  if (frequency < 700) return 2;
  return 3;
}

function groupFrequencies(frequencies, maxGap, splitRegions = false) {
  if (!frequencies.length) return [];
  const groups = [[frequencies[0]]];
  for (let i = 1; i < frequencies.length; i += 1) {
    const current = frequencies[i];
    const previous = groups[groups.length - 1][groups[groups.length - 1].length - 1];
    const sameRegion = !splitRegions || frequencyRegionIndex(current) === frequencyRegionIndex(previous);
    if (sameRegion && current - previous <= maxGap) {
      groups[groups.length - 1].push(current);
    } else {
      groups.push([current]);
    }
  }
  return groups;
}

function formatFrequencyGroup(group) {
  if (group.length === 1) return `${Math.round(group[0])} Hz`;
  return `${Math.round(group[0])}-${Math.round(group[group.length - 1])} Hz`;
}

function modesInRange(modes, start, end) {
  return modes.filter((mode) => mode.frequency >= start && mode.frequency <= end);
}

function dominantModeType(modes) {
  if (!modes.length) return "não identificado";
  const counts = { axial: 0, tangential: 0, oblique: 0 };
  modes.forEach((mode) => { counts[mode.type] += 1; });
  return LABELS[Object.entries(counts).sort((a, b) => b[1] - a[1])[0][0]];
}

function treatmentForFrequency(frequency, issue) {
  if (frequency < 80) return "Armadilhas de grave espessas, cantos e teste de posição de caixas/ouvintes";
  if (frequency < 250) {
    if (issue === "gap") return "Reposicionamento e absorção banda larga com cuidado";
    return "Absorção banda larga profunda; tratamento sintonizado só após medição";
  }
  if (frequency < 700) return "Absorção de primeiras reflexões, posicionamento e análise por medição";
  return "Difusão e controle de reflexões, não correção modal pura";
}

function cautionForFrequency(frequency) {
  if (frequency < 250) return "Confirmar com sweep/IR; depende muito da posição";
  if (frequency < 700) return "Verificar RT/IR; região de transição";
  return "Avaliar reflexões, difusão e tempo de reverberação";
}

function acousticRecommendations(room, modes) {
  const recommendations = [];
  const frequencyCounts = countsByFrequency(modes);
  const clustered = [...frequencyCounts.entries()]
    .filter(([, counts]) => counts.axial + counts.tangential + counts.oblique >= 4)
    .map(([frequency]) => frequency);

  groupFrequencies(clustered, 8, true).forEach((group) => {
    const start = group[0];
    const end = group[group.length - 1];
    const matches = modesInRange(modes, start - 0.5, end + 0.5);
    const center = (start + end) / 2;
    const highCount = Math.max(...group.map((frequency) => {
      const counts = frequencyCounts.get(frequency);
      return counts.axial + counts.tangential + counts.oblique;
    }));
    recommendations.push({
      frequency: formatFrequencyGroup(group),
      type: dominantModeType(matches),
      severity: matches.some((mode) => mode.type === "axial") || highCount >= 6 ? "alta" : "média",
      effect: "Agrupamento modal: notas podem soar fortes, longas ou emboladas",
      treatment: treatmentForFrequency(center, "cluster"),
      caution: cautionForFrequency(center),
    });
  });

  const axialModes = modes.filter((mode) => mode.type === "axial");
  const lowAxials = axialModes.filter((mode) => mode.frequency < 80).map((mode) => mode.frequency).sort((a, b) => a - b);
  groupFrequencies(lowAxials, 6).forEach((group) => {
    const center = group.reduce((sum, value) => sum + value, 0) / group.length;
    recommendations.push({
      frequency: formatFrequencyGroup(group),
      type: "axial",
      severity: center < 60 ? "alta" : "média",
      effect: "Modo axial baixo: pode dominar notas graves próximas",
      treatment: treatmentForFrequency(center, "low"),
      caution: cautionForFrequency(center),
    });
  });

  const lowModes = modes.filter((mode) => mode.frequency < 80);
  if (lowModes.length >= 8) {
    recommendations.push({
      frequency: "< 80 Hz",
      type: dominantModeType(lowModes),
      severity: "alta",
      effect: "Acúmulo de energia no grave profundo",
      treatment: "Priorizar armadilhas de grave e testar posição de caixas/ouvintes",
      caution: "Medir em várias posições antes de escolher solução sintonizada",
    });
  }

  const uniqueFreqs = [...new Set(modes.map((mode) => mode.frequency).filter((frequency) => frequency <= 300))].sort((a, b) => a - b);
  for (let i = 0; i < uniqueFreqs.length - 1; i += 1) {
    const lower = uniqueFreqs[i];
    const upper = uniqueFreqs[i + 1];
    const gap = upper - lower;
    if (lower < 250 && gap >= 18) {
      const center = (lower + upper) / 2;
      recommendations.push({
        frequency: `${lower.toFixed(1)}-${upper.toFixed(1)} Hz`,
        type: "lacuna",
        severity: gap < 30 ? "média" : "alta",
        effect: "Faixa com poucos modos: resposta pode variar entre notas vizinhas",
        treatment: treatmentForFrequency(center, "gap"),
        caution: "Confirmar com fonte e posição de escuta reais",
      });
    }
  }

  const [, middle, longest] = roomRatio(room);
  ratioWarnings(room, modes).forEach((warning) => {
    if (warning.severity === "alto" || warning.severity === "medio") {
      recommendations.push({
        frequency: `1:${middle.toFixed(2)}:${longest.toFixed(2)}`,
        type: "geometria",
        severity: warning.severity === "alto" ? "alta" : "média",
        effect: warning.message,
        treatment: "Reposicionamento, tratamento de graves e absorção conforme medição",
        caution: "Proporção ruim não se corrige só com material fino",
      });
    }
  });

  const seen = new Set();
  const severityOrder = { alta: 0, média: 1, baixa: 2 };
  return recommendations
    .filter((item) => {
      const key = `${item.frequency}-${item.effect}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .sort((a, b) => (severityOrder[a.severity] - severityOrder[b.severity]) || parseFloat(a.frequency) - parseFloat(b.frequency))
    .slice(0, 14);
}

function buildRoomFromInputs() {
  const room = {
    length: Number(inputs.length.value),
    width: Number(inputs.width.value),
    height: Number(inputs.height.value),
    temperature: Number(inputs.temperature.value),
    maxFrequency: Number(inputs.maxFrequency.value),
  };
  room.speed = speedOfSound(room.temperature);
  room.volume = room.length * room.width * room.height;
  room.surfaceArea = 2 * (room.length * room.width + room.length * room.height + room.width * room.height);
  return room;
}

function setText(selector, value) {
  document.querySelector(selector).textContent = value;
}

function updateMetrics(room, modes) {
  const ratio = roomRatio(room);
  setText("#volume", `${room.volume.toFixed(2)} m³`);
  setText("#surfaceArea", `${room.surfaceArea.toFixed(2)} m²`);
  setText("#speed", `${room.speed.toFixed(1)} m/s`);
  setText("#ratio", `1:${ratio[1].toFixed(2)}:${ratio[2].toFixed(2)}`);
  setText("#modeCount", `${modes.length}`);
}

function renderWarnings(warnings) {
  const container = document.querySelector("#warnings");
  container.innerHTML = `<div class="warning-list">${warnings.map((warning) => (
    `<div class="warning-item ${warning.severity}"><strong>${warning.severity.toUpperCase()}</strong> ${warning.message}</div>`
  )).join("")}</div>`;
}

function renderTables(modes, recommendations) {
  document.querySelector("#modeRows").innerHTML = modes.slice(0, 32).map((mode) => `
    <tr>
      <td>${mode.p}</td>
      <td>${mode.q}</td>
      <td>${mode.r}</td>
      <td>${mode.frequency.toFixed(2)}</td>
      <td><span class="badge ${mode.type}">${LABELS[mode.type]}</span></td>
    </tr>
  `).join("");

  document.querySelector("#recommendationRows").innerHTML = recommendations.map((item) => `
    <tr>
      <td>${item.frequency}</td>
      <td>${item.type}</td>
      <td>${item.severity}</td>
      <td>${item.effect}</td>
      <td>${item.treatment}</td>
      <td>${item.caution}</td>
    </tr>
  `).join("");
}

function svgElement(name, attrs = {}) {
  const element = document.createElementNS("http://www.w3.org/2000/svg", name);
  Object.entries(attrs).forEach(([key, value]) => element.setAttribute(key, value));
  return element;
}

function drawAxes(svg, width, height, margin, maxX, maxY) {
  for (let i = 0; i <= 5; i += 1) {
    const y = margin.top + (height - margin.top - margin.bottom) * (i / 5);
    svg.appendChild(svgElement("line", { x1: margin.left, y1: y, x2: width - margin.right, y2: y, class: "grid-line" }));
    const label = Math.round(maxY * (1 - i / 5));
    svg.appendChild(svgElement("text", { x: 10, y: y + 4, class: "plot-label" })).textContent = label;
  }
  for (let i = 0; i <= 6; i += 1) {
    const x = margin.left + (width - margin.left - margin.right) * (i / 6);
    const label = Math.round(maxX * (i / 6));
    svg.appendChild(svgElement("text", { x: x - 12, y: height - 12, class: "plot-label" })).textContent = label;
  }
  svg.appendChild(svgElement("line", { x1: margin.left, y1: height - margin.bottom, x2: width - margin.right, y2: height - margin.bottom, stroke: "#66736a" }));
  svg.appendChild(svgElement("line", { x1: margin.left, y1: margin.top, x2: margin.left, y2: height - margin.bottom, stroke: "#66736a" }));
}

function renderFrequencyPlot(modes, maxFrequency) {
  const svg = document.querySelector("#frequencyPlot");
  svg.innerHTML = "";
  const width = 900;
  const height = 360;
  const margin = { top: 22, right: 24, bottom: 42, left: 42 };
  const counts = countsByFrequency(modes);
  const maxY = Math.max(1, ...[...counts.values()].flatMap((count) => [count.axial, count.tangential, count.oblique]));
  const xScale = (frequency) => margin.left + (frequency / maxFrequency) * (width - margin.left - margin.right);
  const yScale = (value) => height - margin.bottom - (value / maxY) * (height - margin.top - margin.bottom);
  drawAxes(svg, width, height, margin, maxFrequency, maxY);

  ["axial", "tangential", "oblique"].forEach((type) => {
    const points = [...counts.entries()].map(([frequency, count]) => `${xScale(frequency)},${yScale(count[type])}`).join(" ");
    svg.appendChild(svgElement("polyline", { points, fill: "none", stroke: COLORS[type], "stroke-width": 2.4 }));
  });

  const legend = svgElement("g", { transform: "translate(665 24)" });
  ["axial", "tangential", "oblique"].forEach((type, index) => {
    legend.appendChild(svgElement("rect", { x: 0, y: index * 22, width: 12, height: 12, fill: COLORS[type] }));
    const text = svgElement("text", { x: 18, y: index * 22 + 11, class: "plot-label" });
    text.textContent = LABELS[type];
    legend.appendChild(text);
  });
  svg.appendChild(legend);
}

function renderDistributionPlot(modes, maxFrequency) {
  const svg = document.querySelector("#distributionPlot");
  svg.innerHTML = "";
  const width = 900;
  const height = 300;
  const margin = { top: 18, right: 24, bottom: 38, left: 92 };
  const yMap = { axial: 70, tangential: 145, oblique: 220 };
  const xScale = (frequency) => margin.left + (frequency / maxFrequency) * (width - margin.left - margin.right);

  Object.entries(yMap).forEach(([type, y]) => {
    svg.appendChild(svgElement("line", { x1: margin.left, y1: y, x2: width - margin.right, y2: y, stroke: "#d8dfd9" }));
    svg.appendChild(svgElement("text", { x: 18, y: y + 4, class: "plot-label" })).textContent = LABELS[type];
  });
  for (let i = 0; i <= 6; i += 1) {
    const x = margin.left + (width - margin.left - margin.right) * (i / 6);
    svg.appendChild(svgElement("text", { x: x - 12, y: height - 12, class: "plot-label" })).textContent = Math.round(maxFrequency * i / 6);
  }
  modes.forEach((mode) => {
    svg.appendChild(svgElement("circle", {
      cx: xScale(mode.frequency),
      cy: yMap[mode.type],
      r: mode.type === "axial" ? 4.5 : 3.2,
      fill: COLORS[mode.type],
      opacity: 0.72,
    }));
  });
}

function renderBandPlot(modes) {
  const svg = document.querySelector("#bandPlot");
  svg.innerHTML = "";
  const width = 900;
  const height = 320;
  const margin = { top: 24, right: 130, bottom: 56, left: 48 };
  const bandData = countsByBand(modes);
  const maxCount = Math.max(1, ...bandData.map((item) => item.total));
  const tickStep = modeCountTickStep(maxCount);
  const yMax = Math.max(tickStep, Math.ceil(maxCount / tickStep) * tickStep);
  const tickCount = Math.round(yMax / tickStep);
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;
  const xStep = plotWidth / bandData.length;
  const barWidth = Math.min(46, xStep * 0.62);
  const yScale = (value) => height - margin.bottom - (value / yMax) * plotHeight;

  for (let i = 0; i <= tickCount; i += 1) {
    const value = i * tickStep;
    const y = yScale(value);
    svg.appendChild(svgElement("line", { x1: margin.left, y1: y, x2: width - margin.right, y2: y, class: "grid-line" }));
    svg.appendChild(svgElement("text", { x: 12, y: y + 4, class: "plot-label" })).textContent = String(value);
  }

  bandData.forEach((item, index) => {
    const xCenter = margin.left + xStep * index + xStep / 2;
    let base = 0;

    ["axial", "tangential", "oblique"].forEach((type) => {
      const value = item.counts[type];
      const y = yScale(base + value);
      const barHeight = yScale(base) - y;
      svg.appendChild(svgElement("rect", {
        x: xCenter - barWidth / 2,
        y,
        width: barWidth,
        height: barHeight,
        fill: COLORS[type],
      }));
      base += value;
    });

    svg.appendChild(svgElement("text", {
      x: xCenter,
      y: yScale(item.total) - 6,
      class: "plot-label",
      "text-anchor": "middle",
    })).textContent = String(item.total);
    svg.appendChild(svgElement("text", {
      x: xCenter,
      y: height - 18,
      class: "plot-label",
      "text-anchor": "middle",
    })).textContent = bandRangeLabel(item.band);
  });

  svg.appendChild(svgElement("line", { x1: margin.left, y1: height - margin.bottom, x2: width - margin.right, y2: height - margin.bottom, stroke: "#66736a" }));
  svg.appendChild(svgElement("line", { x1: margin.left, y1: margin.top, x2: margin.left, y2: height - margin.bottom, stroke: "#66736a" }));

  const legend = svgElement("g", { transform: `translate(${width - 112} 28)` });
  ["axial", "tangential", "oblique"].forEach((type, index) => {
    legend.appendChild(svgElement("rect", { x: 0, y: index * 22, width: 12, height: 12, fill: COLORS[type] }));
    const text = svgElement("text", { x: 18, y: index * 22 + 11, class: "plot-label" });
    text.textContent = LABELS[type];
    legend.appendChild(text);
  });
  svg.appendChild(legend);

  svg.appendChild(svgElement("text", { x: width - 212, y: height - 18, class: "plot-label" })).textContent = "banda (Hz)";
  svg.appendChild(svgElement("text", { x: 10, y: 18, class: "plot-label" })).textContent = "modos";
}

function renderDensityPlot(modes) {
  const svg = document.querySelector("#densityPlot");
  svg.innerHTML = "";
  const width = 900;
  const height = 320;
  const margin = { top: 24, right: 28, bottom: 48, left: 56 };
  const bandData = weightedDensityByBand(modes);
  const maxDensity = Math.max(0.01, ...bandData.map((item) => item.density));
  const tickStep = modalDensityTickStep(maxDensity);
  const yMax = Math.max(tickStep, Math.ceil(maxDensity / tickStep) * tickStep);
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;
  const xStep = plotWidth / Math.max(1, bandData.length - 1);
  const xScale = (index) => margin.left + index * xStep;
  const yScale = (value) => height - margin.bottom - (value / yMax) * plotHeight;

  const tickCount = Math.round(yMax / tickStep);
  for (let i = 0; i <= tickCount; i += 1) {
    const value = i * tickStep;
    const y = yScale(value);
    svg.appendChild(svgElement("line", { x1: margin.left, y1: y, x2: width - margin.right, y2: y, class: "grid-line" }));
    const label = value.toFixed(2);
    svg.appendChild(svgElement("text", { x: 10, y: y + 4, class: "plot-label" })).textContent = label;
  }

  bandData.forEach((item, index) => {
    const x = xScale(index);
    svg.appendChild(svgElement("text", {
      x: x - 14,
      y: height - 16,
      class: "plot-label",
    })).textContent = String(item.band);
  });

  svg.appendChild(svgElement("line", { x1: margin.left, y1: height - margin.bottom, x2: width - margin.right, y2: height - margin.bottom, stroke: "#66736a" }));
  svg.appendChild(svgElement("line", { x1: margin.left, y1: margin.top, x2: margin.left, y2: height - margin.bottom, stroke: "#66736a" }));

  const points = bandData.map((item, index) => `${xScale(index)},${yScale(item.density)}`).join(" ");
  svg.appendChild(svgElement("polyline", {
    points,
    fill: "none",
    stroke: "#8b5a9f",
    "stroke-width": 2.6,
  }));

  bandData.forEach((item, index) => {
    svg.appendChild(svgElement("circle", {
      cx: xScale(index),
      cy: yScale(item.density),
      r: 4.2,
      fill: "#8b5a9f",
    }));
  });

  svg.appendChild(svgElement("text", { x: width - 238, y: 24, class: "plot-label" })).textContent = "modos ponderados / Hz de banda";
}

function csvEscape(value) {
  const text = String(value);
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function exportCsv() {
  const header = ["p", "q", "r", "frequency_hz", "rounded_hz", "classification"];
  const rows = currentModes.map((mode) => [mode.p, mode.q, mode.r, mode.frequency.toFixed(6), mode.rounded, LABELS[mode.type]]);
  const csv = [header, ...rows].map((row) => row.map(csvEscape).join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "modes.csv";
  link.click();
  URL.revokeObjectURL(url);
}

function recalculate() {
  currentRoom = buildRoomFromInputs();
  currentModes = calculateModes(currentRoom);
  const warnings = ratioWarnings(currentRoom, currentModes);
  const recommendations = acousticRecommendations(currentRoom, currentModes);

  updateMetrics(currentRoom, currentModes);
  renderWarnings(warnings);
  renderTables(currentModes, recommendations);
  renderFrequencyPlot(currentModes, currentRoom.maxFrequency);
  renderDistributionPlot(currentModes, currentRoom.maxFrequency);
  renderBandPlot(currentModes);
  renderDensityPlot(currentModes);
}

form.addEventListener("input", recalculate);
document.querySelector("#exportCsv").addEventListener("click", exportCsv);
document.querySelectorAll("[data-example]").forEach((button) => {
  button.addEventListener("click", () => {
    const example = EXAMPLES[button.dataset.example];
    inputs.length.value = example.length;
    inputs.width.value = example.width;
    inputs.height.value = example.height;
    inputs.maxFrequency.value = example.maxFrequency;
    recalculate();
  });
});

recalculate();
