/* Widgets of the dashboard (TASK-027).
   Homepage keeps ownership of cards, links, groups and layout (services.yaml, settings.yaml). This file adds
   what Homepage does not show natively, from one request to /api/snapshot (services/homepage/metrics):
   the header summary, the Proxmox node cards, the k3s and PostgreSQL cards, a status line per service, the
   TrueNAS, Plex and qBittorrent widgets, the state of the remote desktop machines and the background
   switcher. A card is found by its "id" in services.yaml; the tables below are the only place that names them. */
(function () {
  "use strict";

  if (window.__nithWidgets) return;
  window.__nithWidgets = true;

  var SVGNS = "http://www.w3.org/2000/svg";
  var REFRESH_MS = 10000;
  var BACKGROUNDS = ["/images/bg-1.jpg", "/images/bg-2.jpg", "/images/bg-3.webp"];
  var BACKGROUND_KEY = "nithBackgroundIndex";
  var DEFAULT_BACKGROUND = "/images/coffee-bg.jpg";

  /* card id -> key of snapshot.nodes */
  var NODE_CARDS = {
    "pve-management-service": "pve_management",
    "pve-core-service": "pve_core",
    "pve-infra-service": "pve_infra",
    "pve-lab-service": "pve_lab",
    "pve-compute-service": "pve_compute"
  };

  /* card id -> key of snapshot.services, for the one-line status */
  var HEALTH_CARDS = {
    "argocd-service": "argocd",
    "authentik-service": "authentik",
    "grafana-service": "grafana",
    "netbox-service": "netbox",
    "windmill-service": "windmill",
    "phase-service": "phase",
    "headlamp-service": "headlamp",
    "forgejo-service": "forgejo",
    "wiki-service": "wiki",
    "adguard-service": "adguard",
    "nextcloud-service": "nextcloud",
    "vaultwarden-service": "vaultwarden",
    "router-service": "router",
    "switch-service": "switch",
    "truenas-service": "truenas",
    "plex-service": "plex",
    "qbit-service": "qbit"
  };

  /* cards that hold a widget under their title: they are laid out as tall cards */
  var TALL_CARDS = ["k3s-service", "postgres-service", "truenas-service", "plex-service", "qbit-service"];
  var REMOTE_CARDS = ["win11-dev-service", "win11-game-service"];

  var ICONS = {
    cpu: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="7" y="7" width="10" height="10" rx="1"/><rect x="10" y="10" width="4" height="4" rx="0.5"/><path d="M9 3v2m6-2v2M9 19v2m6-2v2M3 9h2m-2 6h2m14-6h2m-2 6h2"/></svg>',
    ram: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="8" width="20" height="8" rx="1"/><path d="M6 16v2m4-2v2m4-2v2m4-2v2M6 11v2m4-2v2m4-2v2"/></svg>',
    storage: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="6.5" rx="1.5"/><rect x="3" y="13.5" width="18" height="6.5" rx="1.5"/><path d="M7 7.2h.01M7 16.7h.01"/></svg>'
  };

  /* ── formatting ─────────────────────────────────────────────────────────────────────────────────────── */

  function missing(n) {
    return n === null || n === undefined || isNaN(n);
  }

  function fmtBytes(n) {
    if (missing(n)) return "-";
    var units = ["B", "KB", "MB", "GB", "TB", "PB"];
    var value = Number(n);
    var i = 0;
    while (value >= 1024 && i < units.length - 1) {
      value /= 1024;
      i++;
    }
    return (value >= 100 ? value.toFixed(0) : value.toFixed(1)) + " " + units[i];
  }

  function fmtBps(n) {
    return missing(n) ? "-" : fmtBytes(n) + "/s";
  }

  function fmtPct(n) {
    return missing(n) ? "-" : Math.round(Number(n)) + "%";
  }

  function clampPct(n) {
    n = Number(n);
    return isNaN(n) ? 0 : Math.max(0, Math.min(100, n));
  }

  function fmtTime(ms) {
    if (!ms || ms < 0) return "0:00";
    var seconds = Math.floor(ms / 1000);
    var hours = Math.floor(seconds / 3600);
    seconds -= hours * 3600;
    var minutes = Math.floor(seconds / 60);
    seconds -= minutes * 60;
    var pad = function (x) { return (x < 10 ? "0" : "") + x; };
    return (hours > 0 ? hours + ":" + pad(minutes) : minutes) + ":" + pad(seconds);
  }

  function fmtUptime(seconds) {
    seconds = Number(seconds || 0);
    var days = Math.floor(seconds / 86400);
    var hours = Math.floor((seconds % 86400) / 3600);
    return days > 0 ? days + "d " + hours + "h" : hours + "h";
  }

  /* ── DOM helpers ────────────────────────────────────────────────────────────────────────────────────── */

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function icon(kind) {
    var span = el("span", "nith-ricon " + kind);
    span.innerHTML = ICONS[kind] || "";
    return span;
  }

  function findCard(id) {
    var root = document.getElementById(id);
    return root ? root.querySelector(".service-card") : null;
  }

  /* One container per widget, created once under the card's title and reused on every refresh. */
  function slot(card, key) {
    if (!card) return null;
    var existing = card.querySelector('[data-nith="' + key + '"]');
    if (existing) return existing;
    var node = el("div");
    node.setAttribute("data-nith", key);
    card.appendChild(node);
    return node;
  }

  function dropSlot(card, key) {
    var existing = card && card.querySelector('[data-nith="' + key + '"]');
    if (existing) existing.remove();
  }

  function progress(label, pct, value, kind) {
    var row = el("div", "nith-resource-row");
    row.appendChild(icon(kind));
    row.appendChild(el("span", "nith-rlabel", label));
    var bar = el("div", "nith-progress");
    bar.setAttribute("role", "progressbar");
    bar.setAttribute("aria-valuemin", "0");
    bar.setAttribute("aria-valuemax", "100");
    var fill = el("div", "nith-progress-fill " + (kind || ""));
    fill.style.width = clampPct(pct) + "%";
    bar.appendChild(fill);
    row.appendChild(bar);
    row.appendChild(el("span", "nith-rval", value));
    return row;
  }

  function setProgress(row, pct, value) {
    row.querySelector(".nith-progress").setAttribute("aria-valuenow", String(Math.round(clampPct(pct))));
    row.querySelector(".nith-progress-fill").style.width = clampPct(pct) + "%";
    row.querySelector(".nith-rval").textContent = value;
  }

  /* A row of small figures ("3 / 3" over "NODES"); built once for a given list of labels. */
  function statRow(box, className, labels) {
    var signature = labels.join("|");
    var row = box.querySelector("." + className.split(" ")[0]);
    if (row && row.dataset.labels === signature) return row;
    if (row) row.remove();
    row = el("div", className);
    row.dataset.labels = signature;
    row.style.setProperty("--nith-stats", String(labels.length));
    labels.forEach(function (label) {
      var stat = el("div", "nith-node-stat");
      stat.appendChild(el("span", "nith-node-stat-value", "-"));
      stat.appendChild(el("span", "nith-node-stat-label", label));
      row.appendChild(stat);
    });
    box.insertBefore(row, box.firstChild);
    return row;
  }

  function setStats(row, values) {
    var nodes = row.querySelectorAll(".nith-node-stat-value");
    values.forEach(function (value, index) {
      if (nodes[index]) nodes[index].textContent = value;
    });
  }

  function note(card, key, text) {
    var box = slot(card, key);
    if (!box) return;
    box.className = "nith-note";
    box.textContent = text;
  }

  /* ── header summary ─────────────────────────────────────────────────────────────────────────────────── */

  function ensureSummary() {
    var header = document.getElementById("information-widgets");
    if (!header) return null;
    var box = header.querySelector('[data-nith="summary"]');
    if (box) return box;
    box = el("div", "nith-summary");
    box.setAttribute("data-nith", "summary");
    header.insertBefore(box, header.firstChild);
    return box;
  }

  function summaryMetric(kind, valueA, labelA, valueB, labelB, pct) {
    var node = el("div", "nith-summary-metric");
    node.appendChild(icon(kind));
    var body = el("div", "nith-summary-body");
    var grid = el("div", "nith-summary-grid");
    [[valueA, labelA], [valueB, labelB]].forEach(function (item) {
      grid.appendChild(el("span", "nith-sv", item[0]));
      grid.appendChild(el("span", "nith-sl", item[1]));
    });
    var bar = el("div", "nith-progress");
    var fill = el("div", "nith-progress-fill " + kind);
    fill.style.width = clampPct(pct) + "%";
    bar.appendChild(fill);
    body.appendChild(grid);
    body.appendChild(bar);
    node.appendChild(body);
    return node;
  }

  function renderSummary(data) {
    var box = ensureSummary();
    if (!box) return;
    /* Without the read access to the cluster there is nothing to sum: dashes, not zeros. */
    var compute = data.compute && data.compute.cores ? data.compute : {};
    var storage = data.storage && data.storage.total_bytes ? data.storage : {};
    var load = missing(compute.cpu_load) ? "-" : Number(compute.cpu_load).toFixed(2);
    box.textContent = "";
    box.title = "The four nodes of the doku-lab cluster together";
    box.appendChild(summaryMetric("cpu", fmtPct(compute.cpu_percent), "CPU", load, "Load", compute.cpu_percent));
    box.appendChild(summaryMetric("ram", fmtBytes(compute.ram_free_bytes), "Free", fmtBytes(compute.ram_total_bytes), "Total", compute.ram_percent));
    box.appendChild(summaryMetric("storage", fmtBytes(storage.free_bytes), "Free", fmtBytes(storage.total_bytes), "Total", storage.percent));
  }

  /* ── Proxmox nodes ──────────────────────────────────────────────────────────────────────────────────── */

  function renderNode(card, node) {
    if (!card) return;
    if (!node || node.online === false) {
      dropSlot(card, "node");
      note(card, "node-note", node && node.error ? "Node unavailable · " + node.error : "Waiting for data");
      card.setAttribute("data-nith-state", "offline");
      return;
    }
    dropSlot(card, "node-note");
    card.setAttribute("data-nith-state", "online");
    var box = slot(card, "node");
    box.className = "nith-node-content";
    var stats = statRow(box, "nith-node-stats", ["VM", "LXC", "Load", "Uptime"]);
    var bars = box.querySelector(".nith-node-bars");
    if (!bars) {
      bars = el("div", "nith-node-bars");
      bars.appendChild(progress("CPU", 0, "-", "cpu"));
      bars.appendChild(progress("RAM", 0, "-", "ram"));
      bars.appendChild(progress("Disk", 0, "-", "storage"));
      box.appendChild(bars);
    }
    setStats(stats, [
      (node.vms_running || 0) + " / " + (node.vms_total || 0),
      (node.lxc_running || 0) + " / " + (node.lxc_total || 0),
      Number(node.load1 || 0).toFixed(2),
      fmtUptime(node.uptime_seconds)
    ]);
    var rows = bars.querySelectorAll(".nith-resource-row");
    setProgress(rows[0], node.cpu_percent, fmtPct(node.cpu_percent) + " · " + (node.cores || 0) + " threads");
    setProgress(rows[1], node.ram_percent, fmtBytes(node.ram_used_bytes) + " / " + fmtBytes(node.ram_total_bytes));
    setProgress(rows[2], node.storage_percent, fmtBytes(node.storage_used_bytes) + " / " + fmtBytes(node.storage_total_bytes));
  }

  /* ── k3s and PostgreSQL ─────────────────────────────────────────────────────────────────────────────── */

  function renderK3s(k3s) {
    var card = findCard("k3s-service");
    if (!card) return;
    if (!k3s || k3s.online === false) {
      dropSlot(card, "k3s");
      note(card, "k3s-note", k3s && k3s.error ? "No data · " + k3s.error : "Waiting for data");
      return;
    }
    dropSlot(card, "k3s-note");
    var box = slot(card, "k3s");
    box.className = "nith-node-content";
    setStats(statRow(box, "nith-node-stats", ["Servers", "Pods", "Workloads", "Restarts 24h"]), [
      k3s.nodes_ready + " / " + k3s.nodes_total,
      String(k3s.pods_running),
      k3s.workloads_ready + " / " + k3s.workloads_total,
      String(k3s.restarts_day)
    ]);
    var healthy = k3s.nodes_ready === k3s.nodes_total && k3s.workloads_ready === k3s.workloads_total && !k3s.pods_failing;
    var line = box.querySelector(".nith-service-health") || box.appendChild(el("div", "nith-service-health"));
    line.setAttribute("data-online", healthy ? "true" : "false");
    line.innerHTML = '<span class="nith-service-dot"></span><span class="nith-service-text"></span>';
    line.querySelector(".nith-service-text").textContent = healthy
      ? "Every server ready, every workload available"
      : (k3s.nodes_total - k3s.nodes_ready) + " server(s) not ready · " +
        (k3s.workloads_total - k3s.workloads_ready) + " workload(s) short · " + k3s.pods_failing + " pod(s) failing";
  }

  function renderPostgres(postgres) {
    var card = findCard("postgres-service");
    if (!card) return;
    if (!postgres || !postgres.members || !postgres.members.length) {
      dropSlot(card, "postgres");
      note(card, "postgres-note", postgres && postgres.error ? "No data · " + postgres.error : "Waiting for data");
      return;
    }
    dropSlot(card, "postgres-note");
    var box = slot(card, "postgres");
    box.className = "nith-node-content";
    var lag = Math.max.apply(null, postgres.members.map(function (m) { return m.lag_bytes || 0; }));
    setStats(statRow(box, "nith-node-stats", ["Leader", "Members", "Version", "Replica lag"]), [
      postgres.leader || "none",
      postgres.members_running + " / " + postgres.members_total,
      postgres.version || "-",
      fmtBytes(lag)
    ]);
    var healthy = postgres.online && postgres.members_running === postgres.members_total;
    var line = box.querySelector(".nith-service-health") || box.appendChild(el("div", "nith-service-health"));
    line.setAttribute("data-online", healthy ? "true" : "false");
    line.innerHTML = '<span class="nith-service-dot"></span><span class="nith-service-text"></span>';
    line.querySelector(".nith-service-text").textContent = postgres.members.map(function (m) {
      return m.name + " " + (m.running ? m.role : "down");
    }).join(" · ");
  }

  /* ── one status line per service ────────────────────────────────────────────────────────────────────── */

  function httpLabel(check) {
    if (!check) return "No data";
    if (check.online === false) return check.status_code ? "HTTP " + check.status_code : "Not answering";
    var code = check.status_code ? "HTTP " + check.status_code : "Online";
    return check.response_ms !== undefined ? code + " · " + check.response_ms + " ms" : code;
  }

  function healthLabel(key, check) {
    if (!check || check.online === false) return httpLabel(check);
    if (key === "forgejo" && check.version) {
      var parts = [check.version.replace("+gitea-", " · Gitea ")];
      if (!missing(check.public_orgs)) parts.push(check.public_orgs + " orgs");
      if (!missing(check.public_repos)) parts.push(check.public_repos + " public repos");
      return parts.join(" · ");
    }
    if (key === "nextcloud" && check.version) {
      return "Nextcloud " + check.version + (check.maintenance ? " · maintenance" : "");
    }
    if (check.version) return check.version + " · " + check.response_ms + " ms";
    return httpLabel(check);
  }

  function renderHealth(services) {
    Object.keys(HEALTH_CARDS).forEach(function (id) {
      var card = findCard(id);
      if (!card) return;
      var key = HEALTH_CARDS[id];
      var check = services[key];
      var box = slot(card, "service-health");
      var online = !!(check && check.online && !check.maintenance && !check.needs_db_upgrade);
      box.className = "nith-service-health";
      box.setAttribute("data-online", online ? "true" : "false");
      if (!box.firstChild) {
        box.appendChild(el("span", "nith-service-dot"));
        box.appendChild(el("span", "nith-service-text"));
      }
      box.querySelector(".nith-service-text").textContent = healthLabel(key, check);
    });
  }

  /* ── TrueNAS ────────────────────────────────────────────────────────────────────────────────────────── */

  function renderTruenas(data) {
    var card = findCard("truenas-service");
    if (!card) return;
    if (!data || !data.configured || data.online === false) {
      dropSlot(card, "storage");
      note(card, "storage-note", "No figures from the NAS" + (data && data.error ? " · " + data.error : ""));
      return;
    }
    dropSlot(card, "storage-note");
    var box = slot(card, "storage");
    box.className = "nith-truenas-content";
    var system = data.system || {};
    setStats(statRow(box, "nith-node-stats nith-truenas-system", ["Load", "Uptime", "Threads", "RAM"]), [
      Number(system.load1 || 0).toFixed(2),
      fmtUptime(system.uptime_seconds),
      missing(system.cores) ? "-" : String(system.cores),
      fmtBytes(system.ram_total_bytes)
    ]);
    var pools = Array.isArray(data.disks) ? data.disks : [];
    var signature = pools.map(function (pool) { return pool.label; }).join("|");
    var column = box.querySelector(".nith-truenas-pools");
    if (!column || column.dataset.pools !== signature) {
      if (column) column.remove();
      column = el("div", "nith-truenas-pools");
      column.dataset.pools = signature;
      column.appendChild(el("div", "nith-truenas-title", "ZFS pools"));
      pools.forEach(function () {
        var row = el("div", "nith-truenas-pool");
        var head = el("div", "nith-truenas-pool-head");
        var name = el("div", "nith-truenas-pool-name");
        name.appendChild(icon("storage"));
        name.appendChild(el("strong"));
        var figures = el("div", "nith-truenas-pool-values");
        ["free", "total"].forEach(function (kind) {
          var block = el("div", "nith-storage-figure " + kind);
          block.appendChild(el("span", "nith-storage-value"));
          block.appendChild(el("span", "nith-storage-caption", kind));
          figures.appendChild(block);
        });
        var meter = el("div", "nith-progress nith-truenas-meter");
        meter.appendChild(el("div", "nith-progress-fill storage"));
        head.appendChild(name);
        head.appendChild(figures);
        row.appendChild(head);
        row.appendChild(meter);
        column.appendChild(row);
      });
      box.appendChild(column);
    }
    var rows = column.querySelectorAll(".nith-truenas-pool");
    pools.forEach(function (pool, index) {
      var row = rows[index];
      if (!row) return;
      row.setAttribute("data-healthy", pool.healthy === false ? "false" : "true");
      row.querySelector("strong").textContent = pool.label || "Pool";
      row.querySelector(".free .nith-storage-value").textContent = fmtBytes(pool.free_bytes);
      row.querySelector(".total .nith-storage-value").textContent = fmtBytes(pool.total_bytes);
      row.querySelector(".nith-progress-fill").style.width = clampPct(pool.percent) + "%";
    });
  }

  /* ── qBittorrent ────────────────────────────────────────────────────────────────────────────────────── */

  function chartPath(series, key, w, h, max) {
    if (!series.length || !max) return "M0 " + h + " L" + w + " " + h;
    if (series.length === 1) {
      var onlyY = h - ((series[0][key] || 0) / max) * h;
      return "M0 " + onlyY.toFixed(1) + " L" + w + " " + onlyY.toFixed(1);
    }
    return series.map(function (point, index) {
      var x = (index / Math.max(1, series.length - 1)) * w;
      var y = h - ((point[key] || 0) / max) * h;
      return (index ? "L" : "M") + x.toFixed(1) + " " + y.toFixed(1);
    }).join(" ");
  }

  function ensureQbitChart(box) {
    var existing = box.querySelector("svg");
    if (existing) return existing;
    var chart = el("div", "nith-qbit-chart");
    var svg = document.createElementNS(SVGNS, "svg");
    svg.setAttribute("viewBox", "0 0 520 64");
    svg.setAttribute("preserveAspectRatio", "none");
    [16, 32, 48].forEach(function (y) {
      var line = document.createElementNS(SVGNS, "line");
      line.setAttribute("x1", "0");
      line.setAttribute("x2", "520");
      line.setAttribute("y1", String(y));
      line.setAttribute("y2", String(y));
      line.setAttribute("stroke", "rgba(255,255,255,.06)");
      svg.appendChild(line);
    });
    [["download_bps", "dl"], ["upload_bps", "ul"]].forEach(function (spec) {
      var path = document.createElementNS(SVGNS, "path");
      path.setAttribute("data-qbit-line", spec[0]);
      path.setAttribute("class", "nith-qline " + spec[1]);
      svg.appendChild(path);
    });
    var legend = el("div", "nith-qbit-legend");
    legend.innerHTML = '<span><i class="dot dl"></i>DL <b data-qbit-value="download_bps">0 B/s</b></span>' +
      '<span><i class="dot ul"></i>UL <b data-qbit-value="upload_bps">0 B/s</b></span>';
    chart.appendChild(svg);
    chart.appendChild(legend);
    box.appendChild(chart);
    return svg;
  }

  function renderQbit(data) {
    var card = findCard("qbit-service");
    if (!card) return;
    if (!data || !data.configured || data.online === false) {
      dropSlot(card, "qbit");
      note(card, "qbit-note", !data || !data.configured
        ? "Transfer chart appears once the qBittorrent login is in the secret store"
        : "qBittorrent API not answering" + (data.error ? " · " + data.error : ""));
      return;
    }
    dropSlot(card, "qbit-note");
    var box = slot(card, "qbit");
    box.className = "nith-node-content";
    var current = data.current || {};
    var series = (data.series || []).slice(-120);
    if (!series.length) series = [current];
    setStats(statRow(box, "nith-node-stats", ["Leech", "Download", "Seed", "Upload"]), [
      String(current.leech || 0), fmtBps(current.download_bps), String(current.seed || 0), fmtBps(current.upload_bps)
    ]);
    var max = Math.max.apply(null, series.map(function (p) {
      return Math.max(p.download_bps || 0, p.upload_bps || 0);
    })) || 1;
    var svg = ensureQbitChart(box);
    ["download_bps", "upload_bps"].forEach(function (key) {
      svg.querySelector('[data-qbit-line="' + key + '"]').setAttribute("d", chartPath(series, key, 520, 64, max));
      box.querySelector('[data-qbit-value="' + key + '"]').textContent = fmtBps(current[key]);
    });
  }

  /* ── Plex ───────────────────────────────────────────────────────────────────────────────────────────── */

  function renderPlex(data) {
    var card = findCard("plex-service");
    if (!card) return;
    if (!data || !data.configured || data.online === false) {
      dropSlot(card, "plex");
      note(card, "plex-note", !data || !data.configured
        ? "Streams and library figures appear once the Plex token is in the secret store"
        : "Plex API not answering" + (data.error ? " · " + data.error : ""));
      return;
    }
    dropSlot(card, "plex-note");
    var box = slot(card, "plex");
    box.className = "nith-node-content";
    var library = data.library || {};
    setStats(statRow(box, "nith-node-stats", ["Active streams", "Movies", "TV shows"]), [
      String(data.count || 0), String(library.movies || 0), String(library.shows || 0)
    ]);
    var list = box.querySelector(".nith-plex-list") || box.appendChild(el("div", "nith-plex-list"));
    list.textContent = "";
    var sessions = (data.sessions || []).slice(0, 2);
    if (!sessions.length) {
      list.appendChild(el("div", "nith-plex-empty", "Nothing playing"));
      return;
    }
    sessions.forEach(function (session) {
      var item = el("div", "nith-plex-session");
      var head = el("div", "nith-plex-head");
      var title = el("div", "nith-plex-title");
      title.appendChild(el("span", "nith-plex-media", session.title || "Playback"));
      title.appendChild(el("span", "nith-plex-device", session.player ? " - " + session.player : ""));
      head.appendChild(title);
      head.appendChild(el("div", "nith-plex-time", fmtTime(session.elapsed_ms) + " / " + fmtTime(session.duration_ms)));
      var bar = el("div", "nith-progress");
      var fill = el("div", "nith-progress-fill cpu");
      fill.style.width = clampPct(session.percent) + "%";
      bar.appendChild(fill);
      item.appendChild(head);
      item.appendChild(bar);
      list.appendChild(item);
    });
  }

  /* ── remote desktop machines ────────────────────────────────────────────────────────────────────────── */

  function renderRemote(data) {
    var services = (data && data.services) || {};
    REMOTE_CARDS.forEach(function (id) {
      var card = findCard(id);
      if (!card) return;
      var dot = card.querySelector(".nith-remote-dot") || card.appendChild(el("span", "nith-remote-dot"));
      var remote = services[id] || {};
      var state = remote.running ? "running" : (remote.status || "unknown");
      card.setAttribute("data-remote-state", state);
      dot.title = (remote.label || "VM") + " · " + state;
    });
  }

  /* ── background switcher ────────────────────────────────────────────────────────────────────────────── */

  function getBackgroundIndex() {
    var raw = window.localStorage.getItem(BACKGROUND_KEY);
    if (raw === null) return null;
    var saved = Number(raw);
    return isNaN(saved) ? null : Math.max(0, Math.min(BACKGROUNDS.length - 1, saved));
  }

  function setBackgroundImage(url) {
    var target = document.getElementById("background");
    if (!target) return;
    target.style.setProperty(
      "background-image",
      'linear-gradient(rgb(var(--bg-color) / 0.18), rgb(var(--bg-color) / 0.18)), url("' + url + '")'
    );
  }

  function loadBackground(index) {
    var image = new Image();
    image.onload = function () {
      setBackgroundImage(BACKGROUNDS[index]);
      window.localStorage.setItem(BACKGROUND_KEY, String(index));
    };
    image.onerror = function () {
      window.localStorage.removeItem(BACKGROUND_KEY);
      setBackgroundImage(DEFAULT_BACKGROUND);
    };
    image.src = BACKGROUNDS[index];
  }

  function ensureBackgroundSwitcher() {
    var bar = document.getElementById("style");
    if (!bar || bar.querySelector(".nith-bg-switcher")) return;
    var button = el("button", "nith-bg-switcher");
    button.type = "button";
    button.title = "Change background";
    button.setAttribute("aria-label", "Change background");
    button.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="2"></rect><circle cx="8.5" cy="10" r="1.5"></circle><path d="m5 17 4.5-4.5 3 3 2-2L19 18"></path></svg>';
    button.addEventListener("click", function () {
      var current = getBackgroundIndex();
      loadBackground((current === null ? 0 : current + 1) % BACKGROUNDS.length);
    });
    bar.insertBefore(button, bar.firstChild);
  }

  /* ── layout marks: CSS places cards by these attributes, never by position ──────────────────────────── */

  function markLayout() {
    Array.prototype.forEach.call(document.querySelectorAll(".services-group"), function (group) {
      var title = group.querySelector(".service-group-name");
      if (title) group.setAttribute("data-nith-group", title.textContent.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-"));
    });
    Object.keys(NODE_CARDS).forEach(function (id) {
      var item = document.getElementById(id);
      if (item) item.setAttribute("data-nith-card", "node");
    });
    TALL_CARDS.forEach(function (id) {
      var item = document.getElementById(id);
      if (item) item.setAttribute("data-nith-card", "tall");
    });
    REMOTE_CARDS.forEach(function (id) {
      var item = document.getElementById(id);
      if (item) item.setAttribute("data-nith-card", "remote");
    });
  }

  /* ── refresh loop ───────────────────────────────────────────────────────────────────────────────────── */

  function renderSnapshot(data) {
    data = data || {};
    markLayout();
    ensureBackgroundSwitcher();
    renderSummary(data.summary || {});
    var nodes = data.nodes || {};
    Object.keys(NODE_CARDS).forEach(function (id) {
      renderNode(findCard(id), nodes[NODE_CARDS[id]]);
    });
    renderK3s(data.k3s);
    renderPostgres(data.postgres);
    renderHealth(data.services || {});
    renderTruenas(data.truenas);
    renderQbit(data.qbit);
    renderPlex(data.plex);
    renderRemote(data.remote);
  }

  function refresh() {
    var controller = new AbortController();
    var timer = setTimeout(function () { controller.abort(); }, 8000);
    return fetch("/api/snapshot", { signal: controller.signal, cache: "no-store", credentials: "same-origin" })
      .then(function (response) {
        if (!response.ok) throw new Error("HTTP " + response.status);
        return response.json();
      })
      .then(renderSnapshot)
      .catch(function () { /* the next refresh tries again; the cards keep what they last showed */ })
      .finally(function () { clearTimeout(timer); });
  }

  function boot() {
    var saved = getBackgroundIndex();
    if (saved !== null) loadBackground(saved);
    /* Homepage draws the cards after its own data arrives: mark and fill them a few times early on. */
    [0, 400, 1200, 2500].forEach(function (delay) {
      setTimeout(function () {
        markLayout();
        ensureBackgroundSwitcher();
        refresh();
      }, delay);
    });
    setInterval(refresh, REFRESH_MS);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
  } else {
    boot();
  }
})();
