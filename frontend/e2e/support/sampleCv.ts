import { createHash } from "node:crypto";

/**
 * Le CV fictif de `backend/scripts/sample_cv.py` (Camille Exemple, `make_cv_pdf()` avec ses valeurs
 * par défaut), écrit octet pour octet comme lui : un bandeau de couleur, deux colonnes (contact,
 * compétences et langues à gauche ; profil, expériences et formation à droite), une page A4,
 * Helvetica. Aucun vrai CV (aucune donnée personnelle) : identité fictive, domaine `example.org`.
 *
 * `SAMPLE_CV_SHA256` est l'empreinte du PDF : le test Python `test_cv_script.py` vérifie la même
 * valeur sur `make_cv_pdf()`, et le parcours n° 2 la vérifie sur `sampleCvPdf()`. Les deux
 * écritures ne peuvent pas diverger sans qu'un des deux échoue.
 */
export const SAMPLE_CV_SHA256 = "3924eb0157a1efb94b280d1d6ddbd48244fbc4fb28dcbc2860090f10024ea9b0";

type Rgb = readonly [number, number, number];
/** Une ligne de texte : x, y de la ligne de base, gras, taille, couleur, texte. */
type Text = readonly [number, number, boolean, number, Rgb, string];
/** Un rectangle rempli : x, y, largeur, hauteur, couleur. */
type Rect = readonly [number, number, number, number, Rgb];

const FACTS = {
  name: "Camille Exemple",
  title: "Développeuse Python et IA",
  email: "camille.exemple@example.org",
  phone: "+33 6 00 00 00 00",
  city: "Lyon",
  role1: "Développeuse IA",
  company1: "Atelier Fictif",
  period1: "2023 – 2026",
  role2: "Développeuse Python",
  company2: "Données Exemple",
  period2: "2020 – 2023",
  metric1: "30 %",
  metric2: "12 000",
  tools: "Python, FastAPI, LangGraph, Docker, SQL",
  degree: "Master Informatique",
  school: "Université Exemple",
  language: "Anglais C1",
};
const SKILLS = ["Python", "FastAPI", "LangGraph", "Docker", "SQL"];
const WIDTH = 595;
const HEIGHT = 842;
const BAND_HEIGHT = 110;
const PANEL_WIDTH = 190;
const WHITE: Rgb = [1, 1, 1];
const INK: Rgb = [0.13, 0.13, 0.13];
const MUTED: Rgb = [0.4, 0.4, 0.4];
const PANEL: Rgb = [0.93, 0.93, 0.93];
const ACCENT: Rgb = [0.13, 0.33, 0.6];
// Caractères hors Latin-1 écrits en cp1252 dans le PDF.
const CP1252: Record<number, number> = { 0x2013: 0x96, 0x2014: 0x97, 0x2022: 0x95 };

function num(value: number): string {
  return value.toFixed(3).replace(/0+$/, "").replace(/\.$/, "") || "0";
}

function escape(text: string): Buffer {
  const escaped = text.replaceAll("\\", "\\\\").replaceAll("(", "\\(").replaceAll(")", "\\)");
  const bytes = [...escaped].map((char) => {
    const code = char.codePointAt(0) ?? 0x3f;
    if (code < 0x80 || (code >= 0xa0 && code <= 0xff)) return code;
    return CP1252[code] ?? 0x3f;
  });
  return Buffer.from(bytes);
}

function color(rgb: Rgb): string {
  return `${rgb.map(num).join(" ")} rg`;
}

function rectOp([x, y, width, height, rgb]: Rect): Buffer {
  return Buffer.from(`${color(rgb)} ${num(x)} ${num(y)} ${num(width)} ${num(height)} re f`);
}

function textOp([x, y, bold, size, rgb, value]: Text): Buffer {
  const head = `BT ${bold ? "/F2" : "/F1"} ${num(size)} Tf ${color(rgb)} ${num(x)} ${num(y)} Td (`;
  return Buffer.concat([Buffer.from(head), escape(value), Buffer.from(") Tj ET")]);
}

/** Titre de section (11 pt gras, couleur d'accent) puis ses lignes (9 pt), de haut en bas. */
function section(x: number, y: number, title: string, lines: string[]): Text[] {
  const out: Text[] = [[x, y, true, 11, ACCENT, title]];
  lines.forEach((line, index) => {
    out.push([x, y - 4 - 13 * (index + 1), false, 9, INK, line]);
  });
  return out;
}

function experiences(x: number, top: number): Text[] {
  const f = FACTS;
  const rows: [boolean, number, Rgb, string][] = [
    [true, 12, ACCENT, "Expériences"],
    [true, 10.5, INK, `${f.role1} — ${f.company1}`],
    [false, 9, MUTED, `${f.period1}, ${f.city}`],
    [false, 10, INK, "• Conçu un assistant interne avec LangGraph pour le support"],
    [false, 10, INK, `• Réduit de ${f.metric1} le temps de traitement des demandes`],
    [false, 10, INK, `• Outils : ${f.tools}`],
    [true, 10.5, INK, `${f.role2} — ${f.company2}`],
    [false, 9, MUTED, `${f.period2}, ${f.city}`],
    [false, 10, INK, `• Automatisé le contrôle de ${f.metric2} factures par mois`],
    [false, 10, INK, "• Écrit les tests et la documentation des services de données"],
    [true, 12, ACCENT, "Formation"],
    [true, 10.5, INK, `${f.degree} — ${f.school}`],
    [false, 9, MUTED, "2020"],
  ];
  return rows.map(([bold, size, rgb, text], index) => [x, top - 17 * index, bold, size, rgb, text]);
}

function profile(x: number, top: number): Text[] {
  return [
    [x, top, true, 12, ACCENT, "Profil"],
    [x, top - 18, false, 10, INK, `${FACTS.title}, cinq ans d'expérience en données`],
    [x, top - 31, false, 10, INK, "et en agents conversationnels. Aime livrer des outils utiles."],
  ];
}

function pageContent(): Buffer {
  const f = FACTS;
  const bandY = HEIGHT - BAND_HEIGHT;
  const rects: Rect[] = [
    [0, bandY, WIDTH, BAND_HEIGHT, ACCENT],
    [0, 0, PANEL_WIDTH, bandY, PANEL],
  ];
  const contact = [f.email, f.phone, `${f.city}, France`];
  const languages = ["Français (langue maternelle)", f.language];
  const right = PANEL_WIDTH + 22;
  const texts: Text[] = [
    [36, HEIGHT - 58, true, 22, WHITE, f.name],
    [36, HEIGHT - 82, false, 13, WHITE, f.title],
    ...section(24, bandY - 30, "Contact", contact),
    ...section(24, bandY - 110, "Compétences", SKILLS),
    ...section(24, bandY - 220, "Langues", languages),
    ...profile(right, bandY - 30),
    ...experiences(right, bandY - 90),
  ];
  const ops = [...rects.map(rectOp), ...texts.map(textOp)];
  return Buffer.concat(ops.flatMap((op, index) => (index === 0 ? [op] : [Buffer.from("\n"), op])));
}

function font(baseFont: string): string {
  return `<< /Type /Font /Subtype /Type1 /BaseFont /${baseFont} /Encoding /WinAnsiEncoding >>`;
}

function descriptor(baseFont: string): string {
  return (
    `<< /Type /FontDescriptor /FontName /${baseFont} /Flags 32 /FontBBox [-200 -250 1200 950]` +
    " /ItalicAngle 0 /Ascent 950 /Descent -250 /CapHeight 700 /StemV 80 >>"
  );
}

/** Table `xref` calculée, comme `scripts/pdf_writer.assemble_pdf`. */
function assemble(objects: Buffer[]): Buffer {
  const parts: Buffer[] = [Buffer.from("%PDF-1.4\n")];
  const offsets: number[] = [];
  let size = parts[0]?.length ?? 0;
  objects.forEach((body, index) => {
    offsets.push(size);
    const chunk = Buffer.concat([
      Buffer.from(`${index + 1} 0 obj\n`),
      body,
      Buffer.from("\nendobj\n"),
    ]);
    parts.push(chunk);
    size += chunk.length;
  });
  const entries = offsets.map((offset) => `${String(offset).padStart(10, "0")} 00000 n \n`);
  const tail =
    `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n${entries.join("")}` +
    `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${size}\n%%EOF\n`;
  parts.push(Buffer.from(tail));
  return Buffer.concat(parts);
}

/** Le PDF du CV fictif : même contenu, mêmes octets que `make_cv_pdf()` côté Python. */
export function sampleCvPdf(): Buffer {
  const stream = pageContent();
  const objects = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [7 0 R] /Count 1 >>",
    font("Helvetica"),
    font("Helvetica-Bold"),
    descriptor("Helvetica"),
    descriptor("Helvetica-Bold"),
    `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${WIDTH} ${HEIGHT}] ` +
      "/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents 8 0 R >>",
  ].map((body) => Buffer.from(body));
  objects.push(
    Buffer.concat([
      Buffer.from(`<< /Length ${stream.length} >>\nstream\n`),
      stream,
      Buffer.from("\nendstream"),
    ]),
  );
  return assemble(objects);
}

export function sampleCvSha256(): string {
  return createHash("sha256").update(sampleCvPdf()).digest("hex");
}
