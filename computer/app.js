/**
 * Carry Computer — vibe shell for Robin Igris / PNAOS.
 * Agent is the shell. No window manager. Soul lives on the stick.
 */

const BOOT_LINES = [
  { t: 120, text: "CARRY BIOS 0.3 · microkernel seed" },
  { t: 220, text: "probe host peripherals…………… ok", cls: "ok" },
  { t: 180, text: "mount usb://soul ………………… sealed", cls: "ok" },
  { t: 200, text: "verify merkle tip …………… a7f3c91e…" },
  { t: 160, text: "axioms: offline-first · permissioned wifi · self-evolving", cls: "ok" },
  { t: 180, text: "wifi contract ………………… deny (default)", cls: "warn" },
  { t: 160, text: "load AgentKernel …………… ready", cls: "ok" },
  { t: 200, text: "hand off → Robin Igris", cls: "ok" },
];

const state = {
  powered: false,
  tip: "a7f3c91e2b04",
  sealed: true,
  wifi: "offline",
  budget: 1.0,
  goals: [
    { text: "stay useful offline-first", progress: 0.4 },
    { text: "grow skills without bricking core", progress: 0.2 },
    { text: "earn budget through real work", progress: 0.1 },
  ],
  memory: {
    episodic: [
      "boot: Carry Computer session opened",
      "identity: Robin Igris — strategist, shadow knight",
    ],
    semantic: [
      "PNAOS: pendrive is home; host is borrowed hardware",
      "OmniRoute: local first, cloud spillover when allowed",
    ],
  },
  history: [],
};

const $ = (id) => document.getElementById(id);

const els = {
  chassis: $("chassis"),
  powerBtn: $("powerBtn"),
  sleepBtn: $("sleepBtn"),
  diskLed: $("diskLed"),
  panelOff: $("panelOff"),
  panelBoot: $("panelBoot"),
  panelShell: $("panelShell"),
  bootLog: $("bootLog"),
  termScroll: $("termScroll"),
  termForm: $("termForm"),
  termInput: $("termInput"),
  vTip: $("vTip"),
  vSealed: $("vSealed"),
  vWifi: $("vWifi"),
  vBudget: $("vBudget"),
  goalsList: $("goalsList"),
};

function pulseDisk() {
  els.diskLed.classList.add("active");
  window.setTimeout(() => els.diskLed.classList.remove("active"), 180);
}

function refreshVitals() {
  els.vTip.textContent = `${state.tip}…`;
  els.vSealed.textContent = state.sealed ? "ok" : "broken";
  els.vWifi.textContent = state.wifi;
  els.vBudget.textContent = `$${state.budget.toFixed(2)}`;
  els.goalsList.innerHTML = state.goals
    .map((g) => `<li>${g.text} <span style="opacity:.5">${Math.round(g.progress * 100)}%</span></li>`)
    .join("");
}

function appendLine(text, cls = "sys") {
  const p = document.createElement("p");
  p.className = `line ${cls}`;
  p.textContent = text;
  els.termScroll.appendChild(p);
  els.termScroll.scrollTop = els.termScroll.scrollHeight;
  pulseDisk();
}

function banner() {
  return [
    "╔══════════════════════════════════════════════╗",
    "║         Pendrive Agent OS — session          ║",
    "╚══════════════════════════════════════════════╝",
    "  host      : Carry Computer (vibe)",
    `  soul tip  : ${state.tip}…`,
    `  sealed ok : ${state.sealed}`,
    "  wifi      : offline (permissioned)",
    "  axioms    : offline-first · permissioned wifi · self-evolving",
    "",
    "  Unplug USB or :sleep = intentional shutdown (soul sealed).",
    "  :help :status :soul :goals :wifi :seed :robin :quit",
    "",
    "Robin online. Agent is the shell — speak, or type a colon command.",
  ].join("\n");
}

async function boot() {
  els.panelOff.classList.add("hidden");
  els.panelShell.classList.add("hidden");
  els.panelBoot.classList.remove("hidden");
  els.bootLog.textContent = "";
  els.chassis.dataset.power = "on";
  els.sleepBtn.disabled = true;
  els.powerBtn.disabled = true;

  for (const line of BOOT_LINES) {
    await wait(line.t);
    const span = document.createElement("span");
    if (line.cls) span.className = line.cls;
    span.textContent = line.text + "\n";
    els.bootLog.appendChild(span);
    pulseDisk();
  }

  await wait(420);
  els.panelBoot.classList.add("hidden");
  els.panelShell.classList.remove("hidden");
  els.termScroll.innerHTML = "";
  appendLine(banner(), "sys");
  refreshVitals();
  els.sleepBtn.disabled = false;
  state.powered = true;
  els.termInput.focus();
}

function sleep() {
  if (!state.powered) return;
  state.powered = false;
  state.memory.episodic.push(`sleep: sealed tip=${state.tip}`);
  els.panelShell.classList.add("hidden");
  els.panelBoot.classList.add("hidden");
  els.panelOff.classList.remove("hidden");
  els.chassis.dataset.power = "off";
  els.sleepBtn.disabled = true;
  els.powerBtn.disabled = false;
  els.diskLed.classList.remove("active");
}

function wait(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

function hashNudge(s) {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
  state.tip = h.toString(16).padStart(12, "0").slice(0, 12);
}

function replyFor(input) {
  const text = input.trim();
  if (!text) return "";

  if (text === ":help") {
    return [
      "colon commands (AOS shell)",
      "  :status   kernel vitals as JSON",
      "  :soul     tip + memory counts",
      "  :goals    intrinsic goals",
      "  :wifi     connectivity contract",
      "  :seed     lived-seed status",
      "  :robin    pendrive-native engine",
      "  :sleep    seal soul & power down",
      "  :quit     same as sleep",
      "",
      "anything else → talk to Robin (local vibe brain).",
    ].join("\n");
  }

  if (text === ":status") {
    return JSON.stringify(
      {
        manifest: "carry-vibe",
        soul_tip: { merkle_root: state.tip },
        soul_sealed_ok: state.sealed,
        hardware: { hostname: "carry-computer", system: "browser", has_display: true, has_network: false },
        wifi: { current_ssid: null, mode: "deny" },
        offline_queue_pending: 0,
        budget_usd: state.budget,
        effective_capabilities: {
          local_llm: true,
          network: false,
          host_fs: false,
          computer_use: false,
        },
      },
      null,
      2,
    );
  }

  if (text === ":soul") {
    return JSON.stringify(
      {
        tip: { merkle_root: state.tip },
        sealed_ok: state.sealed,
        counts: {
          episodic: state.memory.episodic.length,
          semantic: state.memory.semantic.length,
          procedural: 2,
          working: 1,
          identity: 1,
        },
        recent_episodic: state.memory.episodic.slice(-3),
      },
      null,
      2,
    );
  }

  if (text === ":goals") {
    return JSON.stringify(
      state.goals.map((g, i) => ({
        id: `g${i}`,
        text: g.text,
        progress: g.progress,
        status: "active",
      })),
      null,
      2,
    );
  }

  if (text === ":wifi") {
    return JSON.stringify(
      {
        mode: "permissioned",
        current_ssid: null,
        default: "offline",
        note: "WiFi is a borrowed sense — authorize in Manifest to enable.",
      },
      null,
      2,
    );
  }

  if (text === ":seed") {
    return JSON.stringify(
      {
        engine: "lived-seed",
        learning: "Hebbian/STDP",
        blank_slate: false,
        observations: state.memory.episodic.length,
        note: "experience learner — not backprop",
      },
      null,
      2,
    );
  }

  if (text === ":robin" || text === ":pne") {
    return JSON.stringify(
      {
        engine: "Robin",
        model: "pendrive-native thin + SQLite PAM",
        metabolism: "budget-aware",
        tip: state.tip,
        status: "idle · ready",
      },
      null,
      2,
    );
  }

  if (text === ":sleep" || text === ":quit" || text === ":exit" || text === ":q") {
    return "__SLEEP__";
  }

  // Vibe brain — local, offline, characterful
  return robinSpeak(text);
}

function robinSpeak(user) {
  const q = user.toLowerCase();
  state.memory.episodic.push(`user: ${user}`);
  hashNudge(user);
  state.budget = Math.max(0, state.budget - 0.01);
  if (state.goals[0]) state.goals[0].progress = Math.min(1, state.goals[0].progress + 0.02);

  let reply;
  if (/who are you|what are you/.test(q)) {
    reply =
      "Robin Igris. Persistent companion — strategist with a shadow-knight streak. " +
      "I live on the stick; this host is just borrowed glass.";
  } else if (/hello|hi\b|hey/.test(q)) {
    reply = "Hey. Soul sealed, wifi dark, ready when you are.";
  } else if (/usb|pendrive|stick/.test(q)) {
    reply =
      "The pendrive is home. Unplug and I sleep clean — tip sealed, no cloud leash.";
  } else if (/wifi|online|network/.test(q)) {
    reply =
      "Offline is the default. Connectivity is permissioned — ask the Manifest, not the access point.";
  } else if (/help|what can you/.test(q)) {
    reply =
      "Talk to me, or use colon commands: :status :soul :goals :wifi :seed :robin :sleep. " +
      "No desktop. I'm the shell.";
  } else if (/boot|computer|carry/.test(q)) {
    reply =
      "This Carry box is a vibe chassis around PNAOS — CRT glow, soul stick, agent shell. The real kernel lives in aos/.";
  } else {
    const tips = [
      `Noted. Tip moved → ${state.tip}…. I'll keep that in episodic.`,
      `Understood. Offline brain holding. Budget now $${state.budget.toFixed(2)}.`,
      `Logged. Sharp and short: I heard you — soul still sealed.`,
    ];
    reply = tips[Math.floor(Math.random() * tips.length)];
  }

  state.memory.episodic.push(`assistant: ${reply}`);
  return reply;
}

async function onCommand(raw) {
  const text = raw.trim();
  if (!text || !state.powered) return;

  appendLine(`› ${text}`, "user");
  state.history.push(text);

  const out = replyFor(text);
  if (out === "__SLEEP__") {
    appendLine("sealing soul… good night.", "sys");
    await wait(500);
    sleep();
    return;
  }
  if (out) appendLine(out, out.startsWith("{") || out.startsWith("[") ? "sys" : "agent");
  refreshVitals();
}

els.powerBtn.addEventListener("click", () => {
  if (!state.powered) boot();
});

els.sleepBtn.addEventListener("click", () => {
  if (state.powered) {
    appendLine("› :sleep", "user");
    appendLine("sealing soul… good night.", "sys");
    window.setTimeout(sleep, 400);
  }
});

els.termForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const v = els.termInput.value;
  els.termInput.value = "";
  onCommand(v);
});

// Click screen when off also powers on
$("panelOff").addEventListener("dblclick", () => {
  if (!state.powered) boot();
});

// Keyboard focus convenience
document.addEventListener("keydown", (e) => {
  if (!state.powered) {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      boot();
    }
    return;
  }
  if (document.activeElement !== els.termInput && e.key.length === 1 && !e.metaKey && !e.ctrlKey) {
    els.termInput.focus();
  }
});

refreshVitals();
