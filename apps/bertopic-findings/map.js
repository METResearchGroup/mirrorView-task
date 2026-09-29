(function () {
  const canvas = document.getElementById("map-canvas");
  if (!canvas) return;

  const statusEl = document.getElementById("map-status");
  const emptyEl = document.getElementById("map-empty");
  const detailEl = document.getElementById("map-detail");
  const typeEl = document.getElementById("map-type");
  const textEl = document.getElementById("map-text");
  const topicEl = document.getElementById("map-topic");
  const resetButton = document.getElementById("map-reset");
  const countButtons = Array.from(document.querySelectorAll("[data-map-count]"));

  const BLUE = "#2563eb";
  const RED = "#dc2626";
  const GRAY = "#94a3b8";
  const ctx = canvas.getContext("2d");

  let data = null;
  let grid = null;
  let circles = [];
  let circleCount = 10;
  let selected = -1;
  let view = null;
  let home = null;
  let dragging = null;
  let textRequest = 0;

  function setStatus(message) {
    statusEl.hidden = !message;
    statusEl.textContent = message || "";
  }

  function colorFor(lean, solid) {
    if (lean === 0) return solid ? BLUE : "rgba(37, 99, 235, 0.5)";
    if (lean === 1) return solid ? RED : "rgba(220, 38, 38, 0.5)";
    return solid ? GRAY : "rgba(148, 163, 184, 0.5)";
  }

  function fitHome() {
    const xs = data.x;
    const ys = data.y;
    let minX = Infinity;
    let maxX = -Infinity;
    let minY = Infinity;
    let maxY = -Infinity;
    for (let i = 0; i < xs.length; i += 1) {
      if (xs[i] < minX) minX = xs[i];
      if (xs[i] > maxX) maxX = xs[i];
      if (ys[i] < minY) minY = ys[i];
      if (ys[i] > maxY) maxY = ys[i];
    }
    const pad = 0.06;
    const width = Math.max(maxX - minX, 0.01);
    const height = Math.max(maxY - minY, 0.01);
    const span = Math.max(width, height) * (1 + pad * 2);
    home = {
      x0: (minX + maxX) / 2 - span / 2,
      y0: (minY + maxY) / 2 - span / 2,
      span: span,
    };
    view = { x0: home.x0, y0: home.y0, span: home.span };
  }

  function buildGrid() {
    const cell = home.span / 48;
    const cells = new Map();
    for (let i = 0; i < data.x.length; i += 1) {
      const key = `${Math.floor(data.x[i] / cell)},${Math.floor(data.y[i] / cell)}`;
      let bucket = cells.get(key);
      if (!bucket) {
        bucket = [];
        cells.set(key, bucket);
      }
      bucket.push(i);
    }
    grid = { cell: cell, cells: cells };
  }

  function topicCounts() {
    const counts = new Map();
    for (let i = 0; i < data.topic.length; i += 1) {
      const topic = data.topic[i];
      if (topic < 0) continue;
      counts.set(topic, (counts.get(topic) || 0) + 1);
    }
    return Array.from(counts.entries()).sort(function (a, b) {
      return b[1] - a[1] || a[0] - b[0];
    });
  }

  function circleFor(topicId) {
    let sumX = 0;
    let sumY = 0;
    let n = 0;
    for (let i = 0; i < data.topic.length; i += 1) {
      if (data.topic[i] !== topicId) continue;
      sumX += data.x[i];
      sumY += data.y[i];
      n += 1;
    }
    if (!n) return null;
    const cx = sumX / n;
    const cy = sumY / n;
    const distances = [];
    for (let i = 0; i < data.topic.length; i += 1) {
      if (data.topic[i] !== topicId) continue;
      const dx = data.x[i] - cx;
      const dy = data.y[i] - cy;
      distances.push(Math.sqrt(dx * dx + dy * dy));
    }
    distances.sort(function (a, b) {
      return a - b;
    });
    const rank = (distances.length - 1) * 0.75;
    const low = Math.floor(rank);
    const high = Math.ceil(rank);
    const radius = low === high ? distances[low] : distances[low] + (distances[high] - distances[low]) * (rank - low);
    return {
      topic: topicId,
      label: data.labels[String(topicId)] || "Ungrouped",
      cx: cx,
      cy: cy,
      radius: Math.max(radius, home.span * 0.012),
    };
  }

  function refreshCircles() {
    circles = topicCounts()
      .slice(0, circleCount)
      .map(function (entry) {
        return circleFor(entry[0]);
      })
      .filter(Boolean);
  }

  function cssSize() {
    const rect = canvas.getBoundingClientRect();
    return { width: rect.width, height: rect.height };
  }

  function resize() {
    const rect = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    canvas.width = Math.max(1, Math.round(rect.width * dpr));
    canvas.height = Math.max(1, Math.round(rect.height * dpr));
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    draw();
  }

  function frame() {
    const size = cssSize();
    const scale = Math.min(size.width, size.height) / view.span;
    return {
      size: size,
      scale: scale,
      offsetX: (size.width - view.span * scale) / 2,
      offsetY: (size.height - view.span * scale) / 2,
    };
  }

  function toScreen(x, y) {
    const box = frame();
    return [
      box.offsetX + (x - view.x0) * box.scale,
      box.offsetY + (view.y0 + view.span - y) * box.scale,
    ];
  }

  function toData(px, py) {
    const box = frame();
    return [
      view.x0 + (px - box.offsetX) / box.scale,
      view.y0 + view.span - (py - box.offsetY) / box.scale,
    ];
  }

  function wrapLabel(label) {
    const words = label.split(/\s+/);
    const lines = [];
    let current = "";
    words.forEach(function (word) {
      const next = current ? `${current} ${word}` : word;
      if (next.length > 28 && current) {
        lines.push(current);
        current = word;
      } else {
        current = next;
      }
    });
    if (current) lines.push(current);
    return lines.slice(0, 3);
  }

  function drawDots() {
    const box = frame();
    const size = box.size;
    const scale = box.scale;
    const radius = Math.max(1.1, Math.min(3.2, 1.5 * Math.sqrt(scale / 40)));
    ctx.save();
    ctx.beginPath();
    ctx.rect(0, 0, size.width, size.height);
    ctx.clip();
    for (let lean = 0; lean < 3; lean += 1) {
      ctx.fillStyle = colorFor(lean, false);
      ctx.beginPath();
      for (let i = 0; i < data.x.length; i += 1) {
        if (data.lean[i] !== lean) continue;
        if (i === selected || i === data.pair[selected]) continue;
        const point = toScreen(data.x[i], data.y[i]);
        ctx.moveTo(point[0] + radius, point[1]);
        ctx.arc(point[0], point[1], radius, 0, Math.PI * 2);
      }
      ctx.fill();
    }
    ctx.restore();
  }

  function drawCircles() {
    const box = frame();
    const size = box.size;
    const scale = box.scale;
    ctx.save();
    ctx.beginPath();
    ctx.rect(0, 0, size.width, size.height);
    ctx.clip();
    ctx.strokeStyle = "#64748b";
    ctx.lineWidth = 1.25;
    ctx.font = "600 12px system-ui, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "bottom";
    circles.forEach(function (circle) {
      const center = toScreen(circle.cx, circle.cy);
      const pixelRadius = circle.radius * scale;
      ctx.beginPath();
      ctx.arc(center[0], center[1], pixelRadius, 0, Math.PI * 2);
      ctx.stroke();
      const lines = wrapLabel(circle.label);
      let y = center[1] - pixelRadius - 6;
      if (y - lines.length * 14 < 8) y = center[1] + pixelRadius + 16;
      lines.forEach(function (line, index) {
        const lineY = y + index * 14;
        ctx.lineWidth = 4;
        ctx.strokeStyle = "#ffffff";
        ctx.strokeText(line, center[0], lineY);
        ctx.fillStyle = "#1a1a1a";
        ctx.fillText(line, center[0], lineY);
        ctx.strokeStyle = "#64748b";
        ctx.lineWidth = 1.25;
      });
    });
    ctx.restore();
  }

  function drawHighlight() {
    if (selected < 0) return;
    const pair = data.pair[selected];
    const a = toScreen(data.x[selected], data.y[selected]);
    const b = toScreen(data.x[pair], data.y[pair]);
    ctx.save();
    ctx.strokeStyle = "#525252";
    ctx.lineWidth = 1.25;
    ctx.beginPath();
    ctx.moveTo(a[0], a[1]);
    ctx.lineTo(b[0], b[1]);
    ctx.stroke();
    [selected, pair].forEach(function (index) {
      const point = index === selected ? a : b;
      ctx.beginPath();
      ctx.arc(point[0], point[1], 6.5, 0, Math.PI * 2);
      ctx.fillStyle = colorFor(data.lean[index], true);
      ctx.fill();
      ctx.lineWidth = 2;
      ctx.strokeStyle = "#ffffff";
      ctx.stroke();
      ctx.lineWidth = 1;
      ctx.strokeStyle = "#111111";
      ctx.stroke();
    });
    ctx.restore();
  }

  function draw() {
    if (!data || !view) return;
    const size = cssSize();
    ctx.clearRect(0, 0, size.width, size.height);
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, size.width, size.height);
    drawDots();
    drawCircles();
    drawHighlight();
  }

  function nearest(px, py) {
    const spot = toData(px, py);
    const reach = 10 / frame().scale;
    const cell = grid.cell;
    const cx = Math.floor(spot[0] / cell);
    const cy = Math.floor(spot[1] / cell);
    const windowCells = Math.ceil(reach / cell) + 1;
    let best = -1;
    let bestDistance = 10 * 10;
    for (let ix = cx - windowCells; ix <= cx + windowCells; ix += 1) {
      for (let iy = cy - windowCells; iy <= cy + windowCells; iy += 1) {
        const bucket = grid.cells.get(`${ix},${iy}`);
        if (!bucket) continue;
        for (let k = 0; k < bucket.length; k += 1) {
          const index = bucket[k];
          const point = toScreen(data.x[index], data.y[index]);
          const dx = point[0] - px;
          const dy = point[1] - py;
          const distance = dx * dx + dy * dy;
          if (distance < bestDistance) {
            bestDistance = distance;
            best = index;
          }
        }
      }
    }
    return best;
  }

  function showEmpty() {
    emptyEl.hidden = false;
    detailEl.hidden = true;
    emptyEl.textContent = "Click a dot.";
  }

  async function showSelection(index) {
    const request = ++textRequest;
    selected = index;
    draw();
    emptyEl.hidden = true;
    detailEl.hidden = false;
    typeEl.textContent = data.role[index] === 1 ? "mirror" : "original";
    topicEl.textContent = data.labels[String(data.topic[index])] || "Ungrouped";
    textEl.textContent = "Loading the post.";
    try {
      const response = await fetch(`/api/map?kind=text&i=${index}`);
      if (!response.ok) throw new Error("text");
      const payload = await response.json();
      if (request !== textRequest) return;
      textEl.textContent = payload.text || "";
    } catch (error) {
      if (request !== textRequest) return;
      textEl.textContent = "The post text could not be loaded.";
    }
  }

  function clearSelection() {
    textRequest += 1;
    selected = -1;
    showEmpty();
    draw();
  }

  canvas.addEventListener("pointerdown", function (event) {
    if (!data) return;
    canvas.setPointerCapture(event.pointerId);
    dragging = { x: event.offsetX, y: event.offsetY, moved: false, view: { ...view } };
  });

  canvas.addEventListener("pointermove", function (event) {
    if (!dragging) return;
    const dx = event.offsetX - dragging.x;
    const dy = event.offsetY - dragging.y;
    if (dx * dx + dy * dy > 16) dragging.moved = true;
    if (!dragging.moved) return;
    const scale = Math.min(cssSize().width, cssSize().height) / dragging.view.span;
    view = {
      x0: dragging.view.x0 - dx / scale,
      y0: dragging.view.y0 + dy / scale,
      span: dragging.view.span,
    };
    draw();
  });

  function endDrag(event) {
    if (!dragging) return;
    const moved = dragging.moved;
    dragging = null;
    if (moved) return;
    const hit = nearest(event.offsetX, event.offsetY);
    if (hit < 0) clearSelection();
    else showSelection(hit);
  }

  canvas.addEventListener("pointerup", endDrag);
  canvas.addEventListener("pointercancel", function () {
    dragging = null;
  });

  canvas.addEventListener(
    "wheel",
    function (event) {
      if (!data) return;
      event.preventDefault();
      const factor = event.deltaY > 0 ? 1.12 : 1 / 1.12;
      const nextSpan = Math.min(home.span * 1.2, Math.max(home.span / 40, view.span * factor));
      const before = toData(event.offsetX, event.offsetY);
      view = { x0: view.x0, y0: view.y0, span: nextSpan };
      const after = toData(event.offsetX, event.offsetY);
      view.x0 += before[0] - after[0];
      view.y0 += before[1] - after[1];
      draw();
    },
    { passive: false }
  );

  countButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      circleCount = Number(button.getAttribute("data-map-count"));
      countButtons.forEach(function (other) {
        other.setAttribute("aria-pressed", other === button ? "true" : "false");
      });
      refreshCircles();
      draw();
    });
  });

  resetButton.addEventListener("click", function () {
    view = { x0: home.x0, y0: home.y0, span: home.span };
    draw();
  });

  window.addEventListener("resize", resize);

  fetch("/api/map?kind=points")
    .then(function (response) {
      if (!response.ok) throw new Error("points");
      return response.json();
    })
    .then(function (payload) {
      data = payload;
      fitHome();
      buildGrid();
      refreshCircles();
      setStatus("");
      resize();
    })
    .catch(function () {
      setStatus("The map could not be loaded.");
    });
})();
