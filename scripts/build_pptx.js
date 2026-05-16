// MA2E Demo Presentation — 2 slides
// Generated for direction MA2E demo (2026-05-15)

const pptxgen = require("pptxgenjs");
const path = require("path");

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5 inches
pres.title = "MA2E — Plateforme Digitale d'Identification";
pres.author = "A. Siriki OUATTARA — GS2E / ERANOVE";

// ---------- Palette ----------
const COLOR = {
  green: "00A045",
  greenDark: "007A33",
  orange: "FFA500",
  ink: "0F172A",
  inkSoft: "475569",
  inkMute: "94A3B8",
  line: "E2E8F0",
  surface: "F8FAFC",
  white: "FFFFFF",
};

const FONT_H = "Calibri";
const FONT_B = "Calibri";

const ROOT = "C:/Users/LENOVO/Desktop/PROJET/GS2E/virtual-ai";
const LOGO = path.join(ROOT, "frontend/public/logo.png");
const ASSISTANT = path.join(ROOT, "frontend/public/assistant.png");

// ============================================================
// SLIDE 1 — HERO
// ============================================================
const s1 = pres.addSlide();
s1.background = { color: COLOR.white };

// Right pane (assistant image area) — ~40% of width
const RIGHT_W = 5.3;
const RIGHT_X = 13.333 - RIGHT_W;

// Soft surface band behind assistant
s1.addShape("rect", {
  x: RIGHT_X, y: 0, w: RIGHT_W, h: 7.5,
  fill: { color: COLOR.surface },
  line: { type: "none" },
});

// Assistant image — full-height on right, contained
s1.addImage({
  path: ASSISTANT,
  x: RIGHT_X + 0.4, y: 0.5,
  w: RIGHT_W - 0.8, h: 6.5,
  sizing: { type: "contain", w: RIGHT_W - 0.8, h: 6.5 },
});

// Logo top-left
s1.addImage({
  path: LOGO,
  x: 0.6, y: 0.55,
  w: 0.95, h: 0.95,
});

// Eyebrow
s1.addText("MUTUELLE DES AGENTS DE L'EAU ET DE L'ÉLECTRICITÉ", {
  x: 0.6, y: 2.0, w: 7.3, h: 0.35,
  fontFace: FONT_H, fontSize: 10, bold: true,
  color: COLOR.inkMute, charSpacing: 4,
  margin: 0,
});

// Big title MA2E
s1.addText("MA2E", {
  x: 0.55, y: 2.4, w: 7.3, h: 1.8,
  fontFace: FONT_H, fontSize: 144, bold: true,
  color: COLOR.green,
  margin: 0,
});

// Subtitle
s1.addText("Plateforme Digitale d'Identification des Sociétaires", {
  x: 0.6, y: 4.25, w: 7.3, h: 0.55,
  fontFace: FONT_H, fontSize: 22, bold: true,
  color: COLOR.ink,
  margin: 0,
});

// Accent divider
s1.addShape("rect", {
  x: 0.6, y: 4.95, w: 0.5, h: 0.04,
  fill: { color: COLOR.green },
  line: { type: "none" },
});

// Tagline italic
s1.addText("Identifiez vos sociétaires en moins de 10 minutes, sur WhatsApp, conforme loi 2013-450.", {
  x: 0.6, y: 5.15, w: 7.3, h: 0.7,
  fontFace: FONT_B, fontSize: 15, italic: true,
  color: COLOR.inkSoft,
  margin: 0, valign: "top",
});

// Footer block (left)
s1.addShape("rect", {
  x: 0.6, y: 6.55, w: 0.04, h: 0.5,
  fill: { color: COLOR.green },
  line: { type: "none" },
});
s1.addText([
  { text: "A. Siriki OUATTARA", options: { bold: true, color: COLOR.ink } },
  { text: "  ·  GS2E / ERANOVE", options: { color: COLOR.inkSoft } },
], {
  x: 0.8, y: 6.5, w: 6.5, h: 0.3,
  fontFace: FONT_B, fontSize: 12,
  margin: 0, valign: "middle",
});
s1.addText("15 mai 2026  ·  Démonstration direction MA2E", {
  x: 0.8, y: 6.78, w: 6.5, h: 0.28,
  fontFace: FONT_B, fontSize: 10,
  color: COLOR.inkMute,
  margin: 0, valign: "middle",
});

// ============================================================
// SLIDE 2 — SOLUTION + KPIs
// ============================================================
const s2 = pres.addSlide();
s2.background = { color: COLOR.white };

// Small logo top-left
s2.addImage({
  path: LOGO,
  x: 0.6, y: 0.45,
  w: 0.55, h: 0.55,
});
s2.addText("MA2E  ·  Identification digitale", {
  x: 1.3, y: 0.5, w: 5.0, h: 0.45,
  fontFace: FONT_H, fontSize: 11, bold: true,
  color: COLOR.inkMute, charSpacing: 2,
  margin: 0, valign: "middle",
});

// Slide number / context (top right)
s2.addText("02 / 02", {
  x: 11.3, y: 0.5, w: 1.5, h: 0.45,
  fontFace: FONT_B, fontSize: 10,
  color: COLOR.inkMute, align: "right",
  margin: 0, valign: "middle",
});

// Title
s2.addText("Une expérience conversationnelle, pensée pour vos sociétaires.", {
  x: 0.6, y: 1.15, w: 12.1, h: 0.7,
  fontFace: FONT_H, fontSize: 28, bold: true,
  color: COLOR.ink,
  margin: 0,
});

// Accent under title
s2.addShape("rect", {
  x: 0.6, y: 1.85, w: 0.5, h: 0.04,
  fill: { color: COLOR.green },
  line: { type: "none" },
});

// ---------- 3 Columns (cards) ----------
const cardY = 2.2;
const cardH = 2.55;
const cardGap = 0.25;
const cardW = (12.1 - cardGap * 2) / 3;
const cardX0 = 0.6;

const cards = [
  {
    num: "01",
    title: "Multi-canal natif",
    items: [
      "WhatsApp Cloud API",
      "Web Chat embarqué",
      "QR Code partageable",
    ],
  },
  {
    num: "02",
    title: "IA & extraction OCR",
    items: [
      "Mindee OCR (CNI ivoirienne)",
      "Groq Llama 3.3 70B",
      "MRZ ICAO 9303",
    ],
  },
  {
    num: "03",
    title: "Conformité ARTCI",
    items: [
      "Loi 2013-450 native",
      "Consentements signés HMAC-SHA256",
      "Audit log immuable",
    ],
  },
];

cards.forEach((c, i) => {
  const x = cardX0 + i * (cardW + cardGap);

  // Card outline
  s2.addShape("rect", {
    x: x, y: cardY, w: cardW, h: cardH,
    fill: { color: COLOR.white },
    line: { color: COLOR.line, width: 1 },
    rectRadius: 0.04,
  });

  // Top accent strip (left edge)
  s2.addShape("rect", {
    x: x, y: cardY, w: 0.04, h: cardH,
    fill: { color: COLOR.green },
    line: { type: "none" },
  });

  // Card number
  s2.addText(c.num, {
    x: x + 0.3, y: cardY + 0.25, w: cardW - 0.6, h: 0.3,
    fontFace: FONT_H, fontSize: 10, bold: true,
    color: COLOR.green, charSpacing: 3,
    margin: 0,
  });

  // Card title
  s2.addText(c.title, {
    x: x + 0.3, y: cardY + 0.55, w: cardW - 0.6, h: 0.5,
    fontFace: FONT_H, fontSize: 17, bold: true,
    color: COLOR.ink,
    margin: 0,
  });

  // Divider
  s2.addShape("line", {
    x: x + 0.3, y: cardY + 1.1, w: cardW - 0.6, h: 0,
    line: { color: COLOR.line, width: 0.75 },
  });

  // Items
  const itemsText = c.items.map((it) => ({
    text: it,
    options: { bullet: { code: "25CF" }, paraSpaceAfter: 6 },
  }));
  s2.addText(itemsText, {
    x: x + 0.3, y: cardY + 1.2, w: cardW - 0.6, h: cardH - 1.4,
    fontFace: FONT_B, fontSize: 12,
    color: COLOR.inkSoft, valign: "top",
    margin: 0,
  });
});

// ---------- KPIs ----------
const kpiY = 5.05;
const kpiH = 1.55;
const kpiGap = 0.25;
const kpiW = (12.1 - kpiGap * 2) / 3;

const kpis = [
  { value: "35 min → 10 min", label: "Délai d'enrôlement" },
  { value: "60% → 95%", label: "Complétude 1ère soumission" },
  { value: "8 500 → 2 800 FCFA", label: "Coût administratif unitaire" },
];

kpis.forEach((k, i) => {
  const x = cardX0 + i * (kpiW + kpiGap);

  // KPI background card
  s2.addShape("rect", {
    x: x, y: kpiY, w: kpiW, h: kpiH,
    fill: { color: COLOR.surface },
    line: { type: "none" },
    rectRadius: 0.04,
  });

  // KPI value
  s2.addText(k.value, {
    x: x + 0.25, y: kpiY + 0.25, w: kpiW - 0.5, h: 0.7,
    fontFace: FONT_H, fontSize: 26, bold: true,
    color: COLOR.green,
    margin: 0, valign: "middle",
  });

  // KPI label
  s2.addText(k.label.toUpperCase(), {
    x: x + 0.25, y: kpiY + 1.0, w: kpiW - 0.5, h: 0.4,
    fontFace: FONT_B, fontSize: 10, bold: true,
    color: COLOR.inkMute, charSpacing: 2,
    margin: 0, valign: "top",
  });
});

// ---------- Footer ----------
s2.addText([
  { text: "Démonstration live", options: { color: COLOR.ink, bold: true } },
  { text: "  ↓", options: { color: COLOR.orange, bold: true } },
], {
  x: 0.6, y: 6.8, w: 12.1, h: 0.5,
  fontFace: FONT_H, fontSize: 16,
  align: "center", margin: 0, valign: "middle",
});

// ============================================================
// SLIDE 3 — DE LA DEMO A LA PRODUCTION
// ============================================================
const s3 = pres.addSlide();
s3.background = { color: COLOR.white };

// Header
s3.addImage({
  path: LOGO,
  x: 0.6, y: 0.45,
  w: 0.55, h: 0.55,
});
s3.addText("MA2E  ·  Identification digitale", {
  x: 1.3, y: 0.5, w: 5.0, h: 0.45,
  fontFace: FONT_H, fontSize: 11, bold: true,
  color: COLOR.inkMute, charSpacing: 2,
  margin: 0, valign: "middle",
});
s3.addText("03 / 03", {
  x: 11.3, y: 0.5, w: 1.5, h: 0.45,
  fontFace: FONT_B, fontSize: 10,
  color: COLOR.inkMute, align: "right",
  margin: 0, valign: "middle",
});

// Title
s3.addText("De la démo à la production", {
  x: 0.6, y: 1.15, w: 12.1, h: 0.6,
  fontFace: FONT_H, fontSize: 28, bold: true,
  color: COLOR.ink,
  margin: 0,
});
s3.addText("Tout ce que MA2E doit mettre en place avant le passage en production réelle.", {
  x: 0.6, y: 1.7, w: 12.1, h: 0.35,
  fontFace: FONT_B, fontSize: 12, italic: true,
  color: COLOR.inkSoft,
  margin: 0,
});

// Accent
s3.addShape("rect", {
  x: 0.6, y: 2.1, w: 0.5, h: 0.04,
  fill: { color: COLOR.green },
  line: { type: "none" },
});

// ---------- 4 production cards ----------
const p3Y = 2.4;
const p3H = 3.6;
const p3Gap = 0.2;
const p3W = (12.1 - p3Gap * 3) / 4;

const prodCards = [
  {
    num: "01",
    title: "Côté MA2E",
    sub: "Administratif",
    items: [
      ["Business Manager Meta", "3-5 j"],
      ["Numéro WhatsApp dédié", "1-2 j"],
      ["Display Name + Templates HSM", "5 j"],
      ["Désignation DPO interne", "Admin"],
      ["Convention RH employeurs", "2 sem"],
    ],
  },
  {
    num: "02",
    title: "Infrastructure",
    sub: "Technique",
    items: [
      ["Serveurs prod (Docker / Linux)", "1 sem"],
      ["Domaine + SSL TLS 1.3", "1 j"],
      ["PostgreSQL HA + backup", "1 sem"],
      ["MinIO chiffré au repos", "3 j"],
      ["CI/CD + monitoring", "2 sem"],
      ["Tests charge 5 000 sessions", "1 sem"],
    ],
  },
  {
    num: "03",
    title: "Conformité",
    sub: "ARTCI · Juridique",
    items: [
      ["Déclaration ARTCI + AIPD", "1 mois revue"],
      ["Validation texte consentement", "1 sem"],
      ["Convention Mindee + Groq", "1 sem"],
      ["Mentions légales + privacy", "3 j"],
      ["Pen test sécurité externe", "2 sem"],
    ],
  },
  {
    num: "04",
    title: "Équipe & lancement",
    sub: "Opérationnel",
    items: [
      ["Formation gestionnaires", "2 j"],
      ["Documentation utilisateur", "1 sem"],
      ["Support N1 / N2", "Process"],
      ["Plan continuité RPO/RTO", "1 sem"],
      ["Pilote 100 sociétaires", "2 sem"],
      ["Go-live production", "Jour J"],
    ],
  },
];

prodCards.forEach((c, i) => {
  const x = 0.6 + i * (p3W + p3Gap);

  // Card outline
  s3.addShape("rect", {
    x: x, y: p3Y, w: p3W, h: p3H,
    fill: { color: COLOR.white },
    line: { color: COLOR.line, width: 1 },
    rectRadius: 0.04,
  });
  // Accent
  s3.addShape("rect", {
    x: x, y: p3Y, w: 0.04, h: p3H,
    fill: { color: COLOR.green },
    line: { type: "none" },
  });
  // Number
  s3.addText(c.num, {
    x: x + 0.25, y: p3Y + 0.2, w: p3W - 0.5, h: 0.25,
    fontFace: FONT_H, fontSize: 9.5, bold: true,
    color: COLOR.green, charSpacing: 3,
    margin: 0,
  });
  // Title
  s3.addText(c.title, {
    x: x + 0.25, y: p3Y + 0.45, w: p3W - 0.5, h: 0.4,
    fontFace: FONT_H, fontSize: 15, bold: true,
    color: COLOR.ink,
    margin: 0,
  });
  // Subtitle
  s3.addText(c.sub.toUpperCase(), {
    x: x + 0.25, y: p3Y + 0.82, w: p3W - 0.5, h: 0.22,
    fontFace: FONT_B, fontSize: 8.5,
    color: COLOR.inkMute, charSpacing: 2,
    margin: 0,
  });
  // Divider
  s3.addShape("line", {
    x: x + 0.25, y: p3Y + 1.12, w: p3W - 0.5, h: 0,
    line: { color: COLOR.line, width: 0.75 },
  });
  // Items — label + delay (italic mute)
  const runs = [];
  c.items.forEach(([label, delay]) => {
    runs.push({
      text: label,
      options: { bullet: { code: "25CF" }, color: COLOR.ink, fontSize: 10.5 },
    });
    runs.push({
      text: `   ${delay}`,
      options: { color: COLOR.inkMute, italic: true, fontSize: 9, paraSpaceAfter: 5 },
    });
  });
  s3.addText(runs, {
    x: x + 0.25, y: p3Y + 1.25, w: p3W - 0.45, h: p3H - 1.4,
    fontFace: FONT_B,
    valign: "top",
    margin: 0,
  });
});

// ---------- Timeline / total band ----------
const tY = 6.15;
const tH = 0.75;
s3.addShape("rect", {
  x: 0.6, y: tY, w: 12.1, h: tH,
  fill: { color: COLOR.surface },
  line: { type: "none" },
  rectRadius: 0.04,
});

s3.addText("TOTAL ESTIMÉ", {
  x: 0.85, y: tY + 0.13, w: 2.5, h: 0.25,
  fontFace: FONT_B, fontSize: 9, bold: true,
  color: COLOR.inkMute, charSpacing: 2,
  margin: 0,
});
s3.addText("6 à 8 semaines", {
  x: 0.85, y: tY + 0.35, w: 2.6, h: 0.35,
  fontFace: FONT_H, fontSize: 18, bold: true,
  color: COLOR.green,
  margin: 0,
});

// Vertical divider
s3.addShape("line", {
  x: 3.6, y: tY + 0.15, w: 0, h: 0.45,
  line: { color: COLOR.line, width: 0.75 },
});

s3.addText("DÉPENDANCE CRITIQUE", {
  x: 3.85, y: tY + 0.13, w: 4.5, h: 0.25,
  fontFace: FONT_B, fontSize: 9, bold: true,
  color: COLOR.inkMute, charSpacing: 2,
  margin: 0,
});
s3.addText("Déclaration ARTCI (revue ~1 mois)", {
  x: 3.85, y: tY + 0.35, w: 4.8, h: 0.3,
  fontFace: FONT_H, fontSize: 13, bold: true,
  color: COLOR.ink,
  margin: 0,
});

// Vertical divider 2
s3.addShape("line", {
  x: 8.8, y: tY + 0.15, w: 0, h: 0.45,
  line: { color: COLOR.line, width: 0.75 },
});

s3.addText("CHANTIERS PARALLÈLES", {
  x: 9.0, y: tY + 0.13, w: 4.0, h: 0.25,
  fontFace: FONT_B, fontSize: 9, bold: true,
  color: COLOR.inkMute, charSpacing: 2,
  margin: 0,
});
s3.addText("Technique + Conformité dès J+1", {
  x: 9.0, y: tY + 0.35, w: 4.0, h: 0.3,
  fontFace: FONT_H, fontSize: 13, bold: true,
  color: COLOR.ink,
  margin: 0,
});

// ---------- Footer ----------
s3.addText([
  { text: "Prochaine étape", options: { color: COLOR.ink, bold: true } },
  { text: "  →  ", options: { color: COLOR.orange, bold: true } },
  { text: "Lancement Business Manager Meta + dossier ARTCI", options: { color: COLOR.inkSoft } },
], {
  x: 0.6, y: 7.05, w: 12.1, h: 0.35,
  fontFace: FONT_H, fontSize: 11,
  align: "center", margin: 0, valign: "middle",
});

// ---------- Save ----------
const OUT = path.join(ROOT, "MA2E_Demo_Presentation_v3.pptx");
pres.writeFile({ fileName: OUT }).then((f) => {
  console.log("Wrote:", f);
});
