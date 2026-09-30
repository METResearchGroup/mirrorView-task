const data = JSON.parse(document.getElementById("page-data").textContent);

function table(rows, groupLabel) {
  const grouped = new Map();
  for (const row of rows) {
    const key = String(row.group);
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key).push(row);
  }
  const parts = [];
  for (const [group, items] of grouped) {
    const n = items[0].n_group_pairs;
    const body = items
      .slice()
      .sort((a, b) => a.rank - b.rank)
      .map((row) => `<tr><td class="num">${row.rank}</td><td>${row.name}</td><td class="num">${row.n_pairs.toLocaleString()}</td></tr>`)
      .join("");
    parts.push(
      `<h3>${groupLabel(group)} (${Number(n).toLocaleString()} pairs)</h3>` +
      `<table><thead><tr><th class="num">Rank</th><th>Feature</th><th class="num">Pairs</th></tr></thead><tbody>${body}</tbody></table>`
    );
  }
  return parts.join("");
}

document.getElementById("lean-slot").innerHTML = document.getElementById("lean-chart").outerHTML;
document.getElementById("toxicity-slot").innerHTML = document.getElementById("toxicity-chart").outerHTML;
document.getElementById("toxicity-lines-slot").innerHTML = document.getElementById("toxicity-lines").outerHTML;
document.getElementById("remove-lines-slot").innerHTML = document.getElementById("remove-lines").outerHTML;
document.getElementById("lean-tables").innerHTML = table(data.lean, (group) => group);
document.getElementById("toxicity-tables").innerHTML = table(data.toxicity, (group) => group);
document.getElementById("remove-tables").innerHTML = table(
  data.remove_votes,
  (group) => `${group} remove votes`
);

const featureRows = document.getElementById("feature-rows");
function drawFeatures(query) {
  const needle = query.trim().toLowerCase();
  const matches = data.features.filter((feature) => {
    if (!needle) return true;
    return feature.name.toLowerCase().includes(needle) || feature.description.toLowerCase().includes(needle);
  });
  featureRows.innerHTML = matches
    .map((feature) => `<tr><td>${feature.name}</td><td>${feature.description}</td></tr>`)
    .join("");
}
const search = document.getElementById("feature-search");
search.addEventListener("input", () => drawFeatures(search.value));
drawFeatures("");
