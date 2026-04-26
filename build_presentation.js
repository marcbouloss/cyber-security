"use strict";
const pptxgen = require("pptxgenjs");
const path = require("path");

// ─── Color palette ──────────────────────────────────────────────────────────
const C = {
  bg:       "0A1628",
  card:     "162236",
  card2:    "1A2D44",
  green:    "00D68F",
  red:      "FF4757",
  blue:     "1A56DB",
  orange:   "FFA500",
  purple:   "9B59B6",
  cyan:     "3498DB",
  white:    "FFFFFF",
  muted:    "C5D0DC",
  dim:      "6B7E94",
  yellow:   "F1C40F",
};

// ─── Paths ───────────────────────────────────────────────────────────────────
const REPORTS = "C:\\Users\\jadal\\Desktop\\cybersecurity\\reports\\";
const img = (name) => REPORTS + name;

// ─── Helpers ─────────────────────────────────────────────────────────────────
function addTitle(slide, text, opts = {}) {
  slide.addText(text, {
    x: 0.4, y: 0.18, w: 9.2, h: 0.65,
    fontSize: 30, bold: true, color: C.white,
    fontFace: "Calibri", align: "left", margin: 0,
    ...opts,
  });
}

function addSubtitle(slide, text, opts = {}) {
  slide.addText(text, {
    x: 0.4, y: 0.82, w: 9.2, h: 0.35,
    fontSize: 13, color: C.muted, fontFace: "Calibri",
    align: "left", margin: 0, ...opts,
  });
}

function card(slide, x, y, w, h, color = C.card) {
  slide.addShape("rect", {
    x, y, w, h,
    fill: { color },
    line: { color: "FFFFFF", transparency: 92, width: 0.5 },
  });
}

function accentBar(slide, x, y, h, color = C.green) {
  slide.addShape("rect", { x, y, w: 0.06, h, fill: { color }, line: { color } });
}

function divider(slide) {
  slide.addShape("line", {
    x: 0.4, y: 0.78, w: 9.2, h: 0,
    line: { color: C.green, width: 1.5, transparency: 40 },
  });
}

function statBox(slide, x, y, value, label, color = C.green) {
  card(slide, x, y, 2.2, 1.1);
  slide.addText(value, {
    x, y: y + 0.05, w: 2.2, h: 0.65,
    fontSize: 36, bold: true, color, align: "center",
    fontFace: "Calibri", margin: 0,
  });
  slide.addText(label, {
    x, y: y + 0.68, w: 2.2, h: 0.35,
    fontSize: 10, color: C.muted, align: "center",
    fontFace: "Calibri", margin: 0,
  });
}

// ═══════════════════════════════════════════════════════════════════════════
//  SLIDE BUILDERS
// ═══════════════════════════════════════════════════════════════════════════

// ─── Slide 1: Title ──────────────────────────────────────────────────────────
function slide01(pres) {
  const s = pres.addSlide();
  s.background = { color: C.bg };

  // Top accent bar full width
  s.addShape("rect", { x: 0, y: 0, w: 10, h: 0.08, fill: { color: C.green }, line: { color: C.green } });

  // Main title
  s.addText("IoT Intrusion Detection", {
    x: 0.5, y: 0.55, w: 9, h: 0.9,
    fontSize: 48, bold: true, color: C.white, fontFace: "Calibri",
    align: "center", margin: 0,
  });
  s.addText("with Real-Time Drift Monitoring", {
    x: 0.5, y: 1.4, w: 9, h: 0.55,
    fontSize: 28, color: C.green, fontFace: "Calibri",
    align: "center", margin: 0,
  });

  // Subtitle
  s.addText("Multi-class ML system · 9 attack families · CICIoT2023 dataset", {
    x: 0.5, y: 1.95, w: 9, h: 0.35,
    fontSize: 14, color: C.muted, fontFace: "Calibri",
    align: "center", margin: 0,
  });

  // 4 stat boxes in a row
  statBox(s, 0.5,  2.55, "9",      "Attack Classes",  C.green);
  statBox(s, 2.85, 2.55, "7.8M+",  "Raw Flows",       C.blue);
  statBox(s, 5.2,  2.55, "5",      "Models Trained",  C.orange);
  statBox(s, 7.55, 2.55, "0.830",  "Best Macro-F1",   C.cyan);

  // Tags
  const tags = ["FastAPI", "Docker", "LightGBM ★", "PyTorch MLP", "KS Drift Test"];
  tags.forEach((t, i) => {
    s.addShape("rect", {
      x: 0.5 + i * 1.82, y: 3.9, w: 1.65, h: 0.32,
      fill: { color: "1A56DB", transparency: 65 },
      line: { color: C.blue, width: 0.5 },
    });
    s.addText(t, {
      x: 0.5 + i * 1.82, y: 3.9, w: 1.65, h: 0.32,
      fontSize: 9.5, color: C.muted, align: "center", margin: 0, fontFace: "Calibri",
    });
  });

  // Bottom bar
  s.addShape("rect", { x: 0, y: 5.33, w: 10, h: 0.3, fill: { color: "0D1E35" }, line: { color: "0D1E35" } });
  s.addText("CICIoT2023 · University of New Brunswick  |  Macro-F1 as primary metric (class imbalance)", {
    x: 0.4, y: 5.34, w: 9.2, h: 0.28,
    fontSize: 9, color: C.dim, align: "center", margin: 0, fontFace: "Calibri",
  });
}

// ─── Slide 2: The Problem ─────────────────────────────────────────────────────
function slide02(pres) {
  const s = pres.addSlide();
  s.background = { color: C.bg };
  addTitle(s, "The Problem — IoT Networks Under Attack");
  divider(s);
  addSubtitle(s, "33 raw attack types → 9 families · 7.8M+ labeled flows · extreme class imbalance");

  // Left panel — problem statement
  card(s, 0.4, 1.05, 4.4, 3.9);
  accentBar(s, 0.4, 1.05, 3.9, C.red);

  s.addText("Why this matters", {
    x: 0.6, y: 1.12, w: 4.1, h: 0.38,
    fontSize: 16, bold: true, color: C.red, fontFace: "Calibri", margin: 0,
  });
  const problems = [
    "Smart TVs, cameras, sensors — billions of devices with zero built-in security",
    "Attackers exploit them for DDoS, botnet C2, and lateral movement",
    "Traditional signature-based IDS fails on novel attack patterns",
    "Class imbalance: 27.9× more Benign than rare attack types",
    "We need ML that generalises across 9 different threat families",
  ];
  s.addText(
    problems.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < problems.length - 1 } })),
    { x: 0.6, y: 1.55, w: 4.0, h: 3.1, fontSize: 12, color: C.muted, fontFace: "Calibri", paraSpaceAfter: 5 }
  );

  // Right panel — 9 attack families
  card(s, 5.05, 1.05, 4.5, 3.9);
  accentBar(s, 5.05, 1.05, 3.9, C.green);

  s.addText("9 Attack Families", {
    x: 5.25, y: 1.12, w: 4.1, h: 0.38,
    fontSize: 16, bold: true, color: C.green, fontFace: "Calibri", margin: 0,
  });
  const classes = [
    ["Benign",              "Normal IoT traffic"],
    ["DDoS",                "Distributed volumetric floods"],
    ["DoS",                 "Single-source service denial"],
    ["Mirai",               "Botnet C2 & propagation"],
    ["Spoofing",            "DNS / ARP poisoning"],
    ["Recon",               "Port scans, OS fingerprinting"],
    ["Recon-HostDiscovery", "Host discovery sweeps"],
    ["Web",                 "SQLi, XSS, command injection"],
    ["DictionaryBruteForce","Password brute force"],
  ];
  const classColors = [C.green, C.red, C.orange, C.blue, C.purple, C.orange, C.cyan, C.cyan, C.red];
  classes.forEach(([name, desc], i) => {
    const yy = 1.58 + i * 0.38;
    s.addShape("rect", {
      x: 5.25, y: yy, w: 0.08, h: 0.24,
      fill: { color: classColors[i] }, line: { color: classColors[i] },
    });
    s.addText(name, {
      x: 5.42, y: yy, w: 1.55, h: 0.24,
      fontSize: 10, bold: true, color: C.white, fontFace: "Calibri", margin: 0,
    });
    s.addText(desc, {
      x: 7.0, y: yy, w: 2.4, h: 0.24,
      fontSize: 9, color: C.muted, fontFace: "Calibri", margin: 0,
    });
  });
}

// ─── Slide 3: Dataset & Pipeline ─────────────────────────────────────────────
function slide03(pres) {
  const s = pres.addSlide();
  s.background = { color: C.bg };
  addTitle(s, "Dataset & ML Pipeline");
  divider(s);
  addSubtitle(s, "CICIoT2023 · 46 features · Stratified sampling → SMOTE → 5 models");

  // Pipeline steps
  const steps = [
    { num: "1", label: "Raw CSV", detail: "7.8M flows\n33 labels", color: C.blue },
    { num: "2", label: "Label Map", detail: "33 → 9\nfamilies", color: C.cyan },
    { num: "3", label: "Sample", detail: "≤20K / class\nstratified", color: C.orange },
    { num: "4", label: "Split", detail: "70 / 15 / 15\ntemporal", color: C.purple },
    { num: "5", label: "SMOTE", detail: "Balance rare\nclasses", color: C.green },
    { num: "6", label: "Scale", detail: "StandardScaler\n+ imputation", color: C.yellow },
    { num: "7", label: "Train", detail: "5 models\nGoogle Colab", color: C.red },
    { num: "8", label: "Deploy", detail: "FastAPI\n+ Docker", color: C.green },
  ];
  steps.forEach((st, i) => {
    const x = 0.4 + i * 1.15;
    // circle
    s.addShape("ellipse", {
      x: x + 0.22, y: 1.12, w: 0.65, h: 0.65,
      fill: { color: st.color, transparency: 20 },
      line: { color: st.color, width: 1.5 },
    });
    s.addText(st.num, {
      x: x + 0.22, y: 1.12, w: 0.65, h: 0.65,
      fontSize: 18, bold: true, color: C.white, align: "center", valign: "middle",
      fontFace: "Calibri", margin: 0,
    });
    // label
    s.addText(st.label, {
      x: x, y: 1.82, w: 1.1, h: 0.32,
      fontSize: 11, bold: true, color: C.white, align: "center",
      fontFace: "Calibri", margin: 0,
    });
    s.addText(st.detail, {
      x: x, y: 2.1, w: 1.1, h: 0.45,
      fontSize: 8.5, color: C.muted, align: "center",
      fontFace: "Calibri", margin: 0,
    });
    // arrow
    if (i < steps.length - 1) {
      s.addShape("line", {
        x: x + 0.97, y: 1.44, w: 0.2, h: 0,
        line: { color: C.muted, width: 1.2 },
      });
    }
  });

  // Key decisions boxes
  const decisions = [
    { title: "Why Macro-F1?", body: "Accuracy is deceptive with imbalanced data — a model predicting only 'Benign' would score 17% accuracy but catch zero attacks. Macro-F1 penalises equally across all classes.", color: C.orange },
    { title: "Why Temporal Split?", body: "Random shuffle leaks future data into training. We split by row order (time) to prevent data leakage — the model never sees 'future' traffic during training.", color: C.blue },
    { title: "Why SMOTE?", body: "DictionaryBruteForce had only 1,541 training samples. SMOTE synthesises new minority examples by interpolating nearest neighbours — not just duplicating.", color: C.green },
  ];
  decisions.forEach((d, i) => {
    const x = 0.4 + i * 3.1;
    card(s, x, 2.75, 2.9, 2.2, C.card);
    accentBar(s, x, 2.75, 2.2, d.color);
    s.addText(d.title, {
      x: x + 0.18, y: 2.82, w: 2.6, h: 0.36,
      fontSize: 13, bold: true, color: d.color, fontFace: "Calibri", margin: 0,
    });
    s.addText(d.body, {
      x: x + 0.18, y: 3.22, w: 2.6, h: 1.6,
      fontSize: 10, color: C.muted, fontFace: "Calibri", margin: 0, wrap: true,
    });
  });
}

// ─── Slide 4: Class Imbalance ────────────────────────────────────────────────
function slide04(pres) {
  const s = pres.addSlide();
  s.background = { color: C.bg };
  addTitle(s, "Class Imbalance — The Core Challenge");
  divider(s);
  addSubtitle(s, "Raw dataset: 27.9× imbalance between largest and smallest class");

  // Plot centre-stage
  s.addImage({ path: img("class_distribution.png"), x: 0.4, y: 1.05, w: 9.2, h: 3.4 });

  // Bottom explanation
  card(s, 0.4, 4.55, 9.2, 0.75);
  s.addText([
    { text: "Problem: ", options: { bold: true, color: C.red } },
    { text: "Standard ML trains on majority class — minority attack types get ignored. A naive model scoring 83% accuracy by always guessing 'Benign' catches ZERO attacks.  ", options: { color: C.muted } },
    { text: "Fix →  SMOTE + class_weight='balanced'", options: { bold: true, color: C.green } },
  ], { x: 0.6, y: 4.6, w: 8.8, h: 0.65, fontSize: 11, fontFace: "Calibri", margin: 0 });
}

// ─── Slide 5: SMOTE ───────────────────────────────────────────────────────────
function slide05(pres) {
  const s = pres.addSlide();
  s.background = { color: C.bg };
  addTitle(s, "Fixing Imbalance — SMOTE Oversampling");
  divider(s);
  addSubtitle(s, "Synthetic Minority Over-sampling: synthesises new examples, not simple copies");

  s.addImage({ path: img("smote_comparison.png"), x: 0.4, y: 1.05, w: 9.2, h: 3.25 });

  // How SMOTE works
  const cards = [
    { t: "Step 1 — Pick minority sample", b: "Select a random sample from the minority class (e.g. DictionaryBruteForce)", c: C.orange },
    { t: "Step 2 — Find K neighbours", b: "Find its K nearest neighbours in feature space using Euclidean distance", c: C.blue },
    { t: "Step 3 — Interpolate", b: "Synthesise new sample by randomly interpolating between the point and a neighbour", c: C.green },
  ];
  cards.forEach((cd, i) => {
    const x = 0.4 + i * 3.1;
    card(s, x, 4.38, 2.9, 1.0);
    accentBar(s, x, 4.38, 1.0, cd.c);
    s.addText(cd.t, { x: x + 0.18, y: 4.42, w: 2.6, h: 0.28, fontSize: 11, bold: true, color: cd.c, fontFace: "Calibri", margin: 0 });
    s.addText(cd.b, { x: x + 0.18, y: 4.73, w: 2.6, h: 0.55, fontSize: 9.5, color: C.muted, fontFace: "Calibri", margin: 0 });
  });
}

// ─── Slide 6: Model 1 — Logistic Regression ──────────────────────────────────
function slide06(pres) {
  const s = pres.addSlide();
  s.background = { color: C.bg };
  addTitle(s, "Model 1 — Logistic Regression (Baseline)");
  divider(s);
  addSubtitle(s, "Softmax classifier · L2 regularisation · Isotonic calibration · SAGA solver");

  // Confusion matrix
  s.addImage({ path: img("confusion_matrix_logistic_regression.png"), x: 0.4, y: 1.05, w: 5.2, h: 3.8 });

  // Stats
  statBox(s, 5.85, 1.05, "0.484", "Macro-F1", C.red);
  statBox(s, 7.7,  1.05, "0.929", "ROC-AUC",  C.orange);
  statBox(s, 5.85, 2.3,  "34.2%", "Benign FP%", C.red);
  statBox(s, 7.7,  2.3,  "Worst", "vs All Models", C.dim);

  // Why it fails
  card(s, 5.85, 3.5, 3.7, 1.4, C.card2);
  accentBar(s, 5.85, 3.5, 1.4, C.red);
  s.addText("Why LR struggled", { x: 6.05, y: 3.55, w: 3.3, h: 0.32, fontSize: 13, bold: true, color: C.red, fontFace: "Calibri", margin: 0 });
  const reasons = [
    "Linear decision boundary — IoT attacks are non-linear",
    "Recon & Web attacks heavily confused with Benign",
    "34% of benign traffic gets falsely flagged as attack",
  ];
  s.addText(
    reasons.map((r, i) => ({ text: r, options: { bullet: true, breakLine: i < 2 } })),
    { x: 6.05, y: 3.88, w: 3.3, h: 0.9, fontSize: 10, color: C.muted, fontFace: "Calibri", paraSpaceAfter: 3 }
  );

  // Label
  s.addShape("rect", { x: 0.4, y: 4.9, w: 1.5, h: 0.28, fill: { color: C.red, transparency: 50 }, line: { color: C.red } });
  s.addText("BASELINE", { x: 0.4, y: 4.9, w: 1.5, h: 0.28, fontSize: 10, bold: true, color: C.white, align: "center", margin: 0 });
}

// ─── Slide 7: Model 2 — Random Forest ────────────────────────────────────────
function slide07(pres) {
  const s = pres.addSlide();
  s.background = { color: C.bg };
  addTitle(s, "Model 2 — Random Forest");
  divider(s);
  addSubtitle(s, "200 trees · Bagging + feature subsampling · balanced_subsample · OOB validation");

  s.addImage({ path: img("confusion_matrix_random_forest.png"), x: 0.4, y: 1.05, w: 5.2, h: 3.8 });

  statBox(s, 5.85, 1.05, "0.808", "Macro-F1",  C.blue);
  statBox(s, 7.7,  1.05, "0.994", "ROC-AUC",   C.green);
  statBox(s, 5.85, 2.3,  "9.5%",  "Benign FP%",C.orange);
  statBox(s, 7.7,  2.3,  "+67%",  "vs LR Macro-F1", C.green);

  card(s, 5.85, 3.5, 3.7, 1.4, C.card2);
  accentBar(s, 5.85, 3.5, 1.4, C.blue);
  s.addText("Why RF leaps ahead", { x: 6.05, y: 3.55, w: 3.3, h: 0.32, fontSize: 13, bold: true, color: C.blue, fontFace: "Calibri", margin: 0 });
  const pts = [
    "200 trees vote — no single tree overfits",
    "balanced_subsample handles imbalance per tree",
    "OOB score used as held-out validation",
  ];
  s.addText(
    pts.map((r, i) => ({ text: r, options: { bullet: true, breakLine: i < 2 } })),
    { x: 6.05, y: 3.88, w: 3.3, h: 0.9, fontSize: 10, color: C.muted, fontFace: "Calibri", paraSpaceAfter: 3 }
  );

  s.addShape("rect", { x: 0.4, y: 4.9, w: 1.5, h: 0.28, fill: { color: C.blue, transparency: 50 }, line: { color: C.blue } });
  s.addText("ENSEMBLE", { x: 0.4, y: 4.9, w: 1.5, h: 0.28, fontSize: 10, bold: true, color: C.white, align: "center", margin: 0 });
}

// ─── Slide 8: Feature Importance ─────────────────────────────────────────────
function slide08(pres) {
  const s = pres.addSlide();
  s.background = { color: C.bg };
  addTitle(s, "What the Model Looks At — Feature Importance");
  divider(s);
  addSubtitle(s, "Permutation importance on Random Forest · Macro-F1 drop when feature is shuffled");

  s.addImage({ path: img("feature_importance_random_forest.png"), x: 0.4, y: 1.05, w: 6.0, h: 4.2 });

  // Callouts
  const callouts = [
    { label: "syn_flag_number", desc: "SYN floods signature of DDoS/DoS — top discriminator", color: C.red },
    { label: "Rate",            desc: "Packet rate reveals volumetric attacks instantly",       color: C.orange },
    { label: "ack_flag_number", desc: "ACK ratio separates normal TCP from attack traffic",     color: C.blue },
    { label: "flow_duration",   desc: "Short flows = scans; Long flows = legitimate sessions",  color: C.green },
    { label: "Header_Length",   desc: "Crafted headers expose spoofing & injection attacks",    color: C.purple },
  ];
  callouts.forEach((c, i) => {
    const y = 1.15 + i * 0.82;
    card(s, 6.6, y, 3.0, 0.72, C.card);
    s.addShape("rect", { x: 6.6, y, w: 0.07, h: 0.72, fill: { color: c.color }, line: { color: c.color } });
    s.addText(c.label, { x: 6.78, y: y + 0.05, w: 2.7, h: 0.28, fontSize: 12, bold: true, color: c.color, fontFace: "Calibri", margin: 0 });
    s.addText(c.desc,  { x: 6.78, y: y + 0.34, w: 2.7, h: 0.3,  fontSize: 9,  color: C.muted, fontFace: "Calibri", margin: 0 });
  });
}

// ─── Slide 9: XGBoost & LightGBM ─────────────────────────────────────────────
function slide09(pres) {
  const s = pres.addSlide();
  s.background = { color: C.bg };
  addTitle(s, "Models 3 & 4 — XGBoost vs LightGBM");
  divider(s);
  addSubtitle(s, "Both are gradient boosting ensembles — but LightGBM wins with leaf-wise growth");

  // Two confusion matrices side by side
  s.addImage({ path: img("confusion_matrix_xgboost.png"),  x: 0.3, y: 1.05, w: 4.6, h: 3.4 });
  s.addImage({ path: img("confusion_matrix_lightgbm.png"), x: 5.1, y: 1.05, w: 4.6, h: 3.4 });

  // Labels
  s.addShape("rect", { x: 0.3, y: 1.05, w: 2.0, h: 0.3, fill: { color: C.orange }, line: { color: C.orange } });
  s.addText("XGBoost  F1=0.815", { x: 0.3, y: 1.05, w: 2.0, h: 0.3, fontSize: 10, bold: true, color: C.bg, align: "center", margin: 0 });

  s.addShape("rect", { x: 5.1, y: 1.05, w: 2.3, h: 0.3, fill: { color: C.green }, line: { color: C.green } });
  s.addText("LightGBM ★  F1=0.830", { x: 5.1, y: 1.05, w: 2.3, h: 0.3, fontSize: 10, bold: true, color: C.bg, align: "center", margin: 0 });

  // Comparison cards
  const cmpItems = [
    ["XGBoost", "Level-wise growth, 2nd-order gradients, exact split search · 300 estimators · lr=0.05", C.orange],
    ["LightGBM ★", "Leaf-wise growth (deeper branches), GOSS sampling, histogram bins · 10× faster · Best F1", C.green],
  ];
  cmpItems.forEach(([title, body, color], i) => {
    const x = 0.3 + i * 4.8;
    card(s, x, 4.52, 4.5, 0.85);
    accentBar(s, x, 4.52, 0.85, color);
    s.addText(title, { x: x + 0.18, y: 4.56, w: 4.1, h: 0.28, fontSize: 13, bold: true, color, fontFace: "Calibri", margin: 0 });
    s.addText(body,  { x: x + 0.18, y: 4.85, w: 4.1, h: 0.45, fontSize: 9.5, color: C.muted, fontFace: "Calibri", margin: 0 });
  });
}

// ─── Slide 10: MLP Neural Network ────────────────────────────────────────────
function slide10(pres) {
  const s = pres.addSlide();
  s.background = { color: C.bg };
  addTitle(s, "Model 5 — MLP Neural Network (PyTorch)");
  divider(s);
  addSubtitle(s, "4-layer network · BatchNorm · Dropout · Adam optimizer · Early stopping");

  // Left: confusion matrix
  s.addImage({ path: img("confusion_matrix_mlp.png"), x: 0.3, y: 1.05, w: 4.7, h: 3.5 });

  // Right: architecture diagram
  const layers = [
    { label: "Input",   size: "46 features", color: C.muted,  w: 1.2 },
    { label: "Dense 256", size: "+ BatchNorm + ReLU + Dropout(0.3)", color: C.blue,   w: 1.6 },
    { label: "Dense 128", size: "+ BatchNorm + ReLU + Dropout(0.3)", color: C.blue,   w: 1.4 },
    { label: "Dense 64",  size: "+ BatchNorm + ReLU + Dropout(0.2)", color: C.blue,   w: 1.2 },
    { label: "Output",    size: "9 classes  (Softmax)",              color: C.green,  w: 1.0 },
  ];
  layers.forEach((l, i) => {
    const y = 1.15 + i * 0.7;
    s.addShape("rect", { x: 5.25, y, w: l.w, h: 0.42, fill: { color: l.color, transparency: 55 }, line: { color: l.color, width: 1 } });
    s.addText(l.label, { x: 5.25, y, w: l.w, h: 0.42, fontSize: 10, bold: true, color: C.white, align: "center", valign: "middle", fontFace: "Calibri", margin: 0 });
    s.addText(l.size, { x: 5.25 + l.w + 0.1, y: y + 0.05, w: 3.5, h: 0.32, fontSize: 9, color: C.muted, fontFace: "Calibri", margin: 0 });
    if (i < layers.length - 1) {
      s.addShape("line", { x: 5.25 + l.w / 2, y: y + 0.42, w: 0, h: 0.28, line: { color: C.dim, width: 1 } });
    }
  });

  // Stats
  statBox(s, 5.25, 4.7 - 1.35, "0.630", "Macro-F1",  C.purple);
  statBox(s, 7.45, 4.7 - 1.35, "0.976", "ROC-AUC",   C.blue);

  // Insight
  card(s, 5.25, 4.62, 4.35, 0.7, C.card2);
  accentBar(s, 5.25, 4.62, 0.7, C.purple);
  s.addText("⚡ Surprise finding", { x: 5.43, y: 4.66, w: 3.95, h: 0.28, fontSize: 12, bold: true, color: C.purple, fontFace: "Calibri", margin: 0 });
  s.addText("MLP underperforms LightGBM by 20% on Macro-F1 — tabular data favours trees over deep learning", {
    x: 5.43, y: 4.94, w: 3.95, h: 0.32, fontSize: 9.5, color: C.muted, fontFace: "Calibri", margin: 0,
  });
}

// ─── Slide 11: Model Comparison ──────────────────────────────────────────────
function slide11(pres) {
  const s = pres.addSlide();
  s.background = { color: C.bg };
  addTitle(s, "Model Comparison — All 5 Models");
  divider(s);
  addSubtitle(s, "Test set: 102,167 samples  ·  LightGBM selected as production model");

  s.addImage({ path: img("model_comparison_chart.png"), x: 0.3, y: 1.05, w: 9.4, h: 3.55 });

  // Key takeaway row
  const takeaways = [
    { text: "LR: linear boundaries can't separate IoT attacks", color: C.red },
    { text: "RF/XGB/LGBM: tree ensembles dominate tabular data", color: C.green },
    { text: "MLP: needs more data / tuning for tabular tasks", color: C.orange },
  ];
  takeaways.forEach((t, i) => {
    const x = 0.3 + i * 3.17;
    s.addShape("rect", { x, y: 4.7, w: 3.05, h: 0.55, fill: { color: C.card }, line: { color: t.color, width: 0.8 } });
    s.addText(t.text, { x: x + 0.1, y: 4.72, w: 2.85, h: 0.51, fontSize: 9.5, color: t.color, fontFace: "Calibri", margin: 0 });
  });

  // Winner badge
  s.addShape("ellipse", { x: 7.55, y: 1.1, w: 1.9, h: 1.9, fill: { color: C.green, transparency: 82 }, line: { color: C.green, width: 2 } });
  s.addText(["LightGBM\n★ WINNER"], { x: 7.55, y: 1.1, w: 1.9, h: 1.9, fontSize: 14, bold: true, color: C.green, align: "center", valign: "middle", fontFace: "Calibri", margin: 0 });
}

// ─── Slide 12: Drift Monitoring ───────────────────────────────────────────────
function slide12(pres) {
  const s = pres.addSlide();
  s.background = { color: C.bg };
  addTitle(s, "Drift Monitoring — Is the Model Still Valid?");
  divider(s);
  addSubtitle(s, "3 complementary checks: KS test · PSI · 3-sigma alert rate monitor");

  const monitors = [
    {
      title: "KS Drift Test",
      icon: "KS",
      body: "Kolmogorov-Smirnov test compares each feature's distribution between training data and incoming traffic.\n\np-value < 0.05 → feature has drifted.\nRuns every 500 predictions.",
      threshold: "p < 0.05 = DRIFTED",
      color: C.blue,
    },
    {
      title: "PSI Score",
      icon: "PSI",
      body: "Population Stability Index measures how much a feature's distribution has shifted.\n\nPSI < 0.1  Stable\nPSI 0.1–0.2  Moderate\nPSI > 0.2  DRIFTED",
      threshold: "PSI > 0.2 = ACTION",
      color: C.orange,
    },
    {
      title: "Alert Rate Monitor",
      icon: "3σ",
      body: "Tracks % of traffic flagged as attack in rolling windows.\n\nSudden spike = real attack OR model behaviour has changed.\n\nZ-score > 3  CRITICAL warning",
      threshold: "Z > 3 = CRITICAL",
      color: C.red,
    },
  ];
  monitors.forEach((m, i) => {
    const x = 0.4 + i * 3.1;
    card(s, x, 1.05, 2.9, 3.5);
    accentBar(s, x, 1.05, 3.5, m.color);
    // icon circle
    s.addShape("ellipse", { x: x + 1.0, y: 1.15, w: 0.85, h: 0.85, fill: { color: m.color, transparency: 60 }, line: { color: m.color, width: 1.5 } });
    s.addText(m.icon, { x: x + 1.0, y: 1.15, w: 0.85, h: 0.85, fontSize: 14, bold: true, color: C.white, align: "center", valign: "middle", fontFace: "Consolas", margin: 0 });
    s.addText(m.title, { x: x + 0.18, y: 2.12, w: 2.58, h: 0.36, fontSize: 14, bold: true, color: m.color, fontFace: "Calibri", margin: 0 });
    s.addText(m.body,  { x: x + 0.18, y: 2.52, w: 2.58, h: 1.45, fontSize: 9.5, color: C.muted, fontFace: "Calibri", margin: 0 });
    s.addShape("rect", { x: x + 0.18, y: 4.08, w: 2.55, h: 0.28, fill: { color: m.color, transparency: 70 }, line: { color: m.color, width: 0.5 } });
    s.addText(m.threshold, { x: x + 0.18, y: 4.08, w: 2.55, h: 0.28, fontSize: 9.5, bold: true, color: m.color, align: "center", margin: 0 });
  });

  // How it wires into API
  card(s, 0.4, 4.55, 9.2, 0.65);
  s.addText([
    { text: "API Integration: ", options: { bold: true, color: C.green } },
    { text: "Every /predict call feeds features + prediction into DriftMonitor.update()  →  drift checked every 500 calls  →  GET /drift/status returns full report", options: { color: C.muted } },
  ], { x: 0.6, y: 4.6, w: 8.8, h: 0.55, fontSize: 10.5, fontFace: "Calibri", margin: 0 });
}

// ─── Slide 13: FastAPI Demo ───────────────────────────────────────────────────
function slide13(pres) {
  const s = pres.addSlide();
  s.background = { color: C.bg };
  addTitle(s, "Live System — FastAPI + Docker Deployment");
  divider(s);
  addSubtitle(s, "3-step startup · Swagger UI · 5 REST endpoints · Docker Hub image");

  // Left column: API endpoints
  card(s, 0.4, 1.05, 4.4, 3.25, C.card);
  accentBar(s, 0.4, 1.05, 3.25, C.green);
  s.addText("REST Endpoints", { x: 0.6, y: 1.1, w: 4.0, h: 0.36, fontSize: 15, bold: true, color: C.green, fontFace: "Calibri", margin: 0 });

  const endpoints = [
    ["POST", "/predict",       "Classify single flow → label + confidence"],
    ["POST", "/predict/batch", "Classify multiple flows at once"],
    ["GET",  "/drift/status",  "PSI + KS drift report"],
    ["GET",  "/health",        "Liveness check"],
    ["GET",  "/docs",          "Interactive Swagger UI"],
  ];
  const mColors = { POST: C.blue, GET: C.green };
  endpoints.forEach(([method, ep, desc], i) => {
    const y = 1.56 + i * 0.56;
    s.addShape("rect", { x: 0.6, y, w: 0.65, h: 0.28, fill: { color: mColors[method] }, line: { color: mColors[method] } });
    s.addText(method, { x: 0.6, y, w: 0.65, h: 0.28, fontSize: 9, bold: true, color: C.bg, align: "center", margin: 0 });
    s.addText(ep,   { x: 1.32, y, w: 1.55, h: 0.28, fontSize: 10, bold: true, color: C.white, fontFace: "Consolas", margin: 0 });
    s.addText(desc, { x: 1.32, y: y + 0.28, w: 3.3, h: 0.22, fontSize: 8.5, color: C.dim, fontFace: "Calibri", margin: 0 });
  });

  // Right column: 3-step start + docker
  card(s, 5.05, 1.05, 4.5, 3.25, C.card);
  accentBar(s, 5.05, 1.05, 3.25, C.blue);
  s.addText("Start in 3 Steps", { x: 5.25, y: 1.1, w: 4.1, h: 0.36, fontSize: 15, bold: true, color: C.blue, fontFace: "Calibri", margin: 0 });

  const steps3 = [
    ["1", "git clone  github.com/…/cybersecurity", C.muted],
    ["2", "pip install -r requirements.txt",        C.muted],
    ["3", "py -3.10 -m uvicorn src.api:app --port 8000", C.green],
  ];
  steps3.forEach(([n, cmd, col], i) => {
    const y = 1.56 + i * 0.52;
    s.addShape("ellipse", { x: 5.25, y, w: 0.36, h: 0.36, fill: { color: C.blue, transparency: 40 }, line: { color: C.blue } });
    s.addText(n, { x: 5.25, y, w: 0.36, h: 0.36, fontSize: 12, bold: true, color: C.white, align: "center", valign: "middle", fontFace: "Calibri", margin: 0 });
    s.addText(cmd, { x: 5.7, y: y + 0.04, w: 3.7, h: 0.28, fontSize: 9, color: col, fontFace: "Consolas", margin: 0 });
  });

  s.addShape("line", { x: 5.25, y: 3.15, w: 4.2, h: 0, line: { color: C.dim, width: 0.5, dashType: "dash" } });
  s.addText("Or with Docker:", { x: 5.25, y: 3.2, w: 4.1, h: 0.26, fontSize: 10, bold: true, color: C.orange, fontFace: "Calibri", margin: 0 });
  s.addText("docker pull <username>/iot-ids:latest\ndocker run -p 8000:8000 <username>/iot-ids:latest", {
    x: 5.25, y: 3.48, w: 4.2, h: 0.45, fontSize: 9, color: C.muted, fontFace: "Consolas", margin: 0,
  });

  // Bottom: sample request/response
  card(s, 0.4, 4.38, 9.2, 0.87);
  s.addText([
    { text: "Example response: ", options: { bold: true, color: C.green } },
    { text: '{ "label": "DDoS", "confidence": 0.9997, "model_used": "LightGBM", "probabilities": {"Benign": 0.0, "DDoS": 0.9997, ...} }', options: { color: C.muted, fontFace: "Consolas" } },
  ], { x: 0.6, y: 4.44, w: 8.8, h: 0.75, fontSize: 10, fontFace: "Calibri", margin: 0 });
}

// ─── Slide 14: Conclusion ─────────────────────────────────────────────────────
function slide14(pres) {
  const s = pres.addSlide();
  s.background = { color: C.bg };

  // Full-width top accent
  s.addShape("rect", { x: 0, y: 0, w: 10, h: 0.08, fill: { color: C.green }, line: { color: C.green } });

  s.addText("Key Takeaways", {
    x: 0.5, y: 0.3, w: 9, h: 0.65,
    fontSize: 36, bold: true, color: C.white, fontFace: "Calibri", align: "center", margin: 0,
  });

  const takeaways = [
    { num: "01", title: "Trees beat deep learning on tabular data",  body: "LightGBM outperforms a 4-layer MLP by 20% on Macro-F1 — tabular IoT features don't benefit from raw neural feature learning.", color: C.green },
    { num: "02", title: "Imbalance must be fixed, not ignored",       body: "SMOTE + class_weight='balanced' prevents the model from collapsing to majority class. Without it, rare attacks are invisible.", color: C.orange },
    { num: "03", title: "Accuracy is a misleading metric here",       body: "A model predicting 'Benign' every time scores 83% accuracy but catches zero attacks. Macro-F1 is the honest metric.", color: C.red },
    { num: "04", title: "Drift monitoring is production-critical",    body: "KS test + PSI + 3-sigma alert rate catches both feature distribution shifts and sudden attack spikes in real-time.", color: C.blue },
    { num: "05", title: "End-to-end from CSV to live API",            body: "Full pipeline: raw data → label mapping → SMOTE → 5 trained models → FastAPI → Docker → /drift/status in production.", color: C.purple },
    { num: "06", title: "Temporal split prevents data leakage",       body: "Splitting by row order (time proxy) ensures the model is evaluated on 'future' traffic, not shuffled-in training data.", color: C.cyan },
  ];

  const cols = [0, 1, 2, 0, 1, 2];
  const rows = [0, 0, 0, 1, 1, 1];
  takeaways.forEach((t, i) => {
    const x = 0.4 + cols[i] * 3.1;
    const y = 1.1 + rows[i] * 2.1;
    card(s, x, y, 2.9, 1.95);
    accentBar(s, x, y, 1.95, t.color);
    s.addText(t.num, { x: x + 0.18, y: y + 0.1, w: 0.5, h: 0.4, fontSize: 20, bold: true, color: t.color, fontFace: "Calibri", margin: 0 });
    s.addText(t.title, { x: x + 0.18, y: y + 0.48, w: 2.58, h: 0.4, fontSize: 11, bold: true, color: C.white, fontFace: "Calibri", margin: 0 });
    s.addText(t.body,  { x: x + 0.18, y: y + 0.9,  w: 2.58, h: 0.95, fontSize: 8.5, color: C.muted, fontFace: "Calibri", margin: 0 });
  });
}

// ═══════════════════════════════════════════════════════════════════════════
//  MAIN
// ═══════════════════════════════════════════════════════════════════════════
async function main() {
  const pres = new pptxgen();
  pres.layout  = "LAYOUT_16x9";
  pres.author  = "IoT IDS Team";
  pres.title   = "IoT Intrusion Detection with Drift Monitoring";
  pres.subject = "Machine Learning — CICIoT2023";

  slide01(pres);
  slide02(pres);
  slide03(pres);
  slide04(pres);
  slide05(pres);
  slide06(pres);
  slide07(pres);
  slide08(pres);
  slide09(pres);
  slide10(pres);
  slide11(pres);
  slide12(pres);
  slide13(pres);
  slide14(pres);

  const outPath = "C:\\Users\\jadal\\Desktop\\cybersecurity\\docs\\presentation.pptx";
  await pres.writeFile({ fileName: outPath });
  console.log("✅  presentation.pptx saved →", outPath);
}

main().catch(err => { console.error(err); process.exit(1); });
