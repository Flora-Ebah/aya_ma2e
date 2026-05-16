const pptxgen = require("/Program Files/nodejs/node_modules/pptxgenjs");

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5 inches (16:9)
pres.title = "MA2E — Plateforme Digitale d'Identification";
pres.author = "A. Siriki OUATTARA";
pres.company = "GS2E / ERANOVE";

const W = 13.333;
const H = 7.5;
const GREEN = "00A045";
const GREEN_DARK = "00913D";
const ORANGE = "FFA500";
const INK_900 = "0F172A";
const INK_700 = "334155";
const INK_500 = "64748B";
const INK_400 = "94A3B8";
const INK_200 = "E2E8F0";
const INK_100 = "F1F5F9";
const INK_50 = "F8FAFC";

const LOGO = "C:/Users/LENOVO/Desktop/PROJET/GS2E/virtual-ai/frontend/public/logo.png";
const ASSISTANT = "C:/Users/LENOVO/Desktop/PROJET/GS2E/virtual-ai/frontend/public/assistant.png";

// ====================================================================
// SLIDE 1 — HERO
// ====================================================================
const s1 = pres.addSlide();
s1.background = { color: "FFFFFF" };

// Logo top-left
s1.addImage({ path: LOGO, x: 0.55, y: 0.45, w: 0.85, h: 0.85 });

// Tenant/brand line top
s1.addText("MA2E", {
  x: 1.55, y: 0.55, w: 4, h: 0.4,
  fontSize: 14, fontFace: "Calibri", bold: true, color: INK_900,
});
s1.addText("Mutuelle des Agents de l'Eau et de l'Électricité", {
  x: 1.55, y: 0.92, w: 6, h: 0.3,
  fontSize: 10, fontFace: "Calibri", color: INK_500,
});

// Eyebrow
s1.addText("PLATEFORME DIGITALE D'IDENTIFICATION · 2026", {
  x: 0.55, y: 2.4, w: 7, h: 0.35,
  fontSize: 11, fontFace: "Calibri", bold: true, color: GREEN,
  charSpacing: 4,
});

// Big title MA2E
s1.addText("Identifier vos sociétaires", {
  x: 0.55, y: 2.8, w: 7.5, h: 1.0,
  fontSize: 48, fontFace: "Calibri", bold: true, color: INK_900,
  charSpacing: -1,
});
s1.addText("en moins de 10 minutes.", {
  x: 0.55, y: 3.65, w: 7.5, h: 1.0,
  fontSize: 48, fontFace: "Calibri", bold: true, color: GREEN,
  charSpacing: -1,
});

// Tagline
s1.addText(
  "Une expérience conversationnelle sur WhatsApp et Web, nativement conforme à la loi ivoirienne 2013-450 sur la protection des données personnelles.",
  {
    x: 0.55, y: 4.85, w: 7.3, h: 1.2,
    fontSize: 16, fontFace: "Calibri", color: INK_500, italic: true,
  }
);

// Bottom info row
s1.addShape(pres.ShapeType.line, {
  x: 0.55, y: 6.65, w: 7, h: 0,
  line: { color: INK_200, width: 0.75 },
});
s1.addText(
  [
    { text: "A. Siriki OUATTARA", options: { bold: true, color: INK_900 } },
    { text: "   ·   ", options: { color: INK_400 } },
    { text: "GS2E / ERANOVE — Sous-Direction Développement Logiciel", options: { color: INK_500 } },
    { text: "   ·   ", options: { color: INK_400 } },
    { text: "15 mai 2026", options: { color: INK_500 } },
  ],
  {
    x: 0.55, y: 6.8, w: 9, h: 0.35,
    fontSize: 11, fontFace: "Calibri",
  }
);

// Right side: green gradient block + assistant image
s1.addShape(pres.ShapeType.rect, {
  x: 8.6, y: 0, w: 4.73, h: H,
  fill: { color: GREEN, transparency: 88 },
  line: { color: "FFFFFF", width: 0 },
});
s1.addShape(pres.ShapeType.rect, {
  x: 8.6, y: H - 2.5, w: 4.73, h: 2.5,
  fill: { color: GREEN, transparency: 70 },
  line: { color: "FFFFFF", width: 0 },
});

// Assistant image
s1.addImage({ path: ASSISTANT, x: 8.5, y: 0.7, w: 4.9, h: 6.7 });

// ====================================================================
// SLIDE 2 — SOLUTION + KPIs
// ====================================================================
const s2 = pres.addSlide();
s2.background = { color: "FFFFFF" };

// Logo small top-left
s2.addImage({ path: LOGO, x: 0.55, y: 0.45, w: 0.5, h: 0.5 });
s2.addText("MA2E", {
  x: 1.15, y: 0.55, w: 2, h: 0.4,
  fontSize: 12, fontFace: "Calibri", bold: true, color: INK_900,
});

// Page indicator top-right
s2.addText("2 / 2", {
  x: 12.4, y: 0.55, w: 0.5, h: 0.4,
  fontSize: 10, fontFace: "Calibri", color: INK_400, align: "right",
});

// Eyebrow + Title
s2.addText("LA SOLUTION", {
  x: 0.55, y: 1.4, w: 5, h: 0.3,
  fontSize: 11, fontFace: "Calibri", bold: true, color: GREEN,
  charSpacing: 4,
});
s2.addText("Une expérience conversationnelle,", {
  x: 0.55, y: 1.75, w: 12.5, h: 0.65,
  fontSize: 28, fontFace: "Calibri", bold: true, color: INK_900,
  charSpacing: -0.5,
});
s2.addText("pensée pour vos sociétaires.", {
  x: 0.55, y: 2.35, w: 12.5, h: 0.65,
  fontSize: 28, fontFace: "Calibri", bold: true, color: INK_500,
  charSpacing: -0.5,
});

// 3 columns of cards
const colY = 3.3;
const colH = 2.3;
const colW = 4.0;
const gap = 0.2;
const startX = 0.55;

function addColumn(idx, title, items, accent) {
  const x = startX + (colW + gap) * idx;

  // Card background
  s2.addShape(pres.ShapeType.rect, {
    x: x, y: colY, w: colW, h: colH,
    fill: { color: INK_50 },
    line: { color: INK_200, width: 0.5 },
    rectRadius: 0.05,
  });

  // Accent square (icon placeholder)
  s2.addShape(pres.ShapeType.rect, {
    x: x + 0.25, y: colY + 0.25, w: 0.32, h: 0.32,
    fill: { color: accent },
    line: { color: accent, width: 0 },
    rectRadius: 0.03,
  });
  s2.addText(String(idx + 1), {
    x: x + 0.25, y: colY + 0.25, w: 0.32, h: 0.32,
    fontSize: 14, fontFace: "Calibri", bold: true, color: "FFFFFF",
    align: "center", valign: "middle",
  });

  // Title
  s2.addText(title, {
    x: x + 0.7, y: colY + 0.2, w: colW - 0.9, h: 0.45,
    fontSize: 14, fontFace: "Calibri", bold: true, color: INK_900,
  });

  // Items
  const itemsText = items.map((t) => ({
    text: t,
    options: { fontSize: 11, color: INK_700, breakLine: true },
  }));
  s2.addText(
    items.map((t, i) => ({
      text: "•  " + t,
      options: {
        fontSize: 11.5, color: INK_700, breakLine: i < items.length - 1,
        paraSpaceAfter: 6,
      },
    })),
    {
      x: x + 0.25, y: colY + 0.85, w: colW - 0.5, h: colH - 1.0,
      fontFace: "Calibri", valign: "top",
    }
  );
}

addColumn(0, "Multi-canal natif", [
  "WhatsApp Cloud API",
  "Web Chat embarqué",
  "QR Code partageable",
], GREEN);

addColumn(1, "IA & extraction OCR", [
  "Mindee OCR (CNI UEMOA)",
  "Groq Llama 3.3 70B",
  "MRZ ICAO 9303 parsée",
], GREEN_DARK);

addColumn(2, "Conformité ARTCI", [
  "Loi 2013-450 native",
  "HMAC-SHA256 signé",
  "Audit log immuable",
], ORANGE);

// KPI row
const kpiY = 6.05;
const kpiH = 0.95;
const kpiW = 4.0;

function addKpi(idx, big, label) {
  const x = startX + (kpiW + gap) * idx;

  s2.addText(big, {
    x: x, y: kpiY, w: kpiW, h: 0.6,
    fontSize: 28, fontFace: "Calibri", bold: true, color: GREEN,
    charSpacing: -1, align: "left",
  });
  s2.addText(label, {
    x: x, y: kpiY + 0.6, w: kpiW, h: 0.3,
    fontSize: 10.5, fontFace: "Calibri", color: INK_500,
    charSpacing: 1, align: "left",
  });
}

addKpi(0, "35 min  →  10 min", "Délai d'enrôlement par sociétaire");
addKpi(1, "60 %  →  95 %", "Complétude documentaire 1ʳᵉ soumission");
addKpi(2, "8 500  →  2 800 FCFA", "Coût administratif par dossier");

// Bottom CTA
s2.addText("Démonstration live  →", {
  x: 0.55, y: 7.1, w: 5, h: 0.35,
  fontSize: 14, fontFace: "Calibri", bold: true, color: ORANGE,
});

// Footer
s2.addText("MA2E · 15 mai 2026", {
  x: 8.5, y: 7.15, w: 4.5, h: 0.3,
  fontSize: 9, fontFace: "Calibri", color: INK_400, align: "right",
});

pres
  .writeFile({
    fileName: "C:/Users/LENOVO/Desktop/PROJET/GS2E/virtual-ai/MA2E_Demo_Presentation.pptx",
  })
  .then((f) => console.log("PPTX written to:", f))
  .catch((e) => {
    console.error("ERROR:", e);
    process.exit(1);
  });
