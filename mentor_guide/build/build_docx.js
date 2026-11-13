// Builds mentor_guide/PrivAgent_Complete_Learning_and_Presentation_Guide.docx from the
// Markdown version. Needs the "docx" npm package (v9):
//   NODE_PATH=<dir containing node_modules> node mentor_guide/build/build_docx.js
// Supported Markdown subset: # / ## / ### headings, paragraphs, "- " bullets
// (two levels), "1. " numbered lists, pipe tables, ![caption](path) images,
// ``` code blocks, "> " quotes, --- rules, **bold**, *italic*, `code`.
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell, WidthType,
  ShadingType, ImageRun, AlignmentType, LevelFormat, PageBreak, TableOfContents, Footer, Header,
  PageNumber, BorderStyle,
} = require("docx");

const ROOT = path.resolve(__dirname, "..", "..");
const GUIDE = path.join(ROOT, "mentor_guide");
const MD = path.join(GUIDE, "PrivAgent_Complete_Learning_and_Presentation_Guide.md");
const OUT = path.join(GUIDE, "PrivAgent_Complete_Learning_and_Presentation_Guide.docx");

const FONT = "Calibri";
const MONO = "Consolas";
const CONTENT_W = 10080; // DXA, US Letter with 0.75" margins
const BLUE = "1F4E79", ACCENT = "2A78D6", HEAD_FILL = "DCE6F2", ZEBRA = "F5F7FA";

// ---------- inline formatting ----------
function runs(text, base = {}) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|`[^`]+`|\*[^*\s][^*]*\*)/g;
  let last = 0, m;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), ...base }));
    const tok = m[0];
    if (tok.startsWith("**")) out.push(...runs(tok.slice(2, -2), { ...base, bold: true }));
    else if (tok.startsWith("`")) out.push(new TextRun({ text: tok.slice(1, -1), ...base, font: MONO,
      size: base.size ? base.size - 2 : 19, color: "2B2B2B" }));
    else out.push(...runs(tok.slice(1, -1), { ...base, italics: true }));
    last = m.index + tok.length;
  }
  if (last < text.length) out.push(new TextRun({ text: text.slice(last), ...base }));
  return out;
}

// ---------- images ----------
function pngSize(buf) { return { w: buf.readUInt32BE(16), h: buf.readUInt32BE(20) }; }
function image(src, caption, figNo) {
  const file = path.join(GUIDE, src);
  const data = fs.readFileSync(file);
  const { w, h } = pngSize(data);
  const maxW = 560, maxH = 330;
  let width = Math.min(maxW, w);
  let height = Math.round(h * width / w);
  if (height > maxH) { width = Math.round(width * maxH / height); height = maxH; }
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 60 }, keepNext: true,
      children: [new ImageRun({ type: "png", data, transformation: { width, height } })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 },
      children: runs(caption, { italics: true, size: 18, color: "444444" }) }),
  ];
}

// ---------- tables ----------
function splitRow(line) {
  return line.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map(c => c.trim());
}
function table(lines) {
  const header = splitRow(lines[0]);
  const body = lines.slice(2).map(splitRow);
  const n = header.length;
  const lens = header.map((h, i) => Math.max(h.length, ...body.map(r => (r[i] || "").length)));
  const weights = lens.map(l => Math.max(8, Math.min(l, 60)));
  const total = weights.reduce((a, b) => a + b, 0);
  let widths = weights.map(x => Math.floor(CONTENT_W * x / total));
  widths[n - 1] += CONTENT_W - widths.reduce((a, b) => a + b, 0);
  const border = { style: BorderStyle.SINGLE, size: 4, color: "BFBFBF" };
  const borders = { top: border, bottom: border, left: border, right: border };
  const cell = (text, i, isHead, zebra) => new TableCell({
    width: { size: widths[i], type: WidthType.DXA }, borders,
    margins: { top: 50, bottom: 50, left: 90, right: 90 },
    shading: isHead ? { type: ShadingType.CLEAR, color: "auto", fill: HEAD_FILL }
      : zebra ? { type: ShadingType.CLEAR, color: "auto", fill: ZEBRA } : undefined,
    children: [new Paragraph({ spacing: { before: 0, after: 0 },
      children: runs(text, { size: 18, bold: isHead ? true : undefined }) })],
  });
  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA }, columnWidths: widths,
    rows: [new TableRow({ tableHeader: true, children: header.map((h, i) => cell(h, i, true)) }),
      ...body.map((r, k) => new TableRow({ cantSplit: true,
        children: header.map((_, i) => cell(r[i] || "", i, false, k % 2 === 1)) }))],
  });
}

// ---------- block parser ----------
function build() {
  const md = fs.readFileSync(MD, "utf8").replace(/\r/g, "");
  const lines = md.split("\n");
  const kids = [];
  let i = 0, fig = 0, listInstance = 0, h1Count = 0;
  let inNumbered = false;

  // Title page from the first lines
  const title = lines[0].replace(/^#\s+/, "");
  kids.push(new Paragraph({ spacing: { before: 2400, after: 200 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: title, bold: true, size: 48, color: BLUE, font: FONT })] }));
  i = 1;
  while (i < lines.length && !lines[i].startsWith("## ")) {
    const l = lines[i].trim();
    if (l) kids.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 160 },
      children: runs(l, { size: 24 }) }));
    i++;
  }
  kids.push(new Paragraph({ children: [new PageBreak()] }));
  kids.push(new Paragraph({ spacing: { after: 160 }, children: [new TextRun({ text: "Contents", bold: true, size: 32, color: BLUE })] }));
  kids.push(new TableOfContents("Contents", { hyperlink: true, headingStyleRange: "1-2" }));
  kids.push(new Paragraph({ children: [new PageBreak()] }));

  while (i < lines.length) {
    const line = lines[i];
    const t = line.trim();
    if (!t.match(/^\d+\.\s/)) inNumbered = false;
    if (t === "" || t === "---") { i++; continue; }
    if (t.startsWith("```")) {
      const code = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith("```")) code.push(lines[i++]);
      i++;
      code.forEach((c, k) => kids.push(new Paragraph({
        shading: { type: ShadingType.CLEAR, color: "auto", fill: "F2F2F2" },
        spacing: { before: k === 0 ? 80 : 0, after: k === code.length - 1 ? 120 : 0 },
        indent: { left: 200 },
        children: [new TextRun({ text: c || " ", font: MONO, size: 17 })] })));
      continue;
    }
    if (t.startsWith("# ")) {
      h1Count++;
      if (/^Part 14|^Appendix/.test(t.slice(2))) kids.push(new Paragraph({ children: [new PageBreak()] }));
      kids.push(new Paragraph({ heading: HeadingLevel.HEADING_1, children: runs(t.slice(2)) }));
      i++; continue;
    }
    if (t.startsWith("## ")) { kids.push(new Paragraph({ heading: HeadingLevel.HEADING_2, children: runs(t.slice(3)) })); i++; continue; }
    if (t.startsWith("### ")) { kids.push(new Paragraph({ heading: HeadingLevel.HEADING_3, children: runs(t.slice(4)) })); i++; continue; }
    const img = t.match(/^!\[(.*)\]\((.+)\)$/);
    if (img) { fig++; kids.push(...image(img[2], img[1], fig)); i++; continue; }
    if (t.startsWith("|")) {
      const block = [];
      while (i < lines.length && lines[i].trim().startsWith("|")) block.push(lines[i++]);
      kids.push(table(block));
      kids.push(new Paragraph({ spacing: { after: 120 }, children: [] }));
      continue;
    }
    if (t.startsWith("> ")) {
      kids.push(new Paragraph({ indent: { left: 400, right: 400 }, spacing: { before: 80, after: 120 },
        border: { left: { style: BorderStyle.SINGLE, size: 18, color: ACCENT, space: 8 } },
        children: runs(t.slice(2), { italics: true }) }));
      i++; continue;
    }
    const bullet = line.match(/^(\s*)- (.*)$/);
    if (bullet) {
      const level = bullet[1].length >= 2 ? 1 : 0;
      kids.push(new Paragraph({ numbering: { reference: "bullets", level }, spacing: { after: 60 },
        children: runs(bullet[2]) }));
      i++; continue;
    }
    const num = t.match(/^(\d+)\.\s(.*)$/);
    if (num) {
      if (!inNumbered) { listInstance++; inNumbered = true; }
      kids.push(new Paragraph({ numbering: { reference: "numbers", level: 0, instance: listInstance },
        spacing: { after: 60 }, children: runs(num[2]) }));
      i++; continue;
    }
    // paragraph: join following plain lines
    const para = [t];
    i++;
    while (i < lines.length && lines[i].trim() && !/^(#|\||!\[|```|> |- |\d+\.\s|---)/.test(lines[i].trim())) {
      para.push(lines[i].trim()); i++;
    }
    kids.push(new Paragraph({ spacing: { after: 100 }, children: runs(para.join(" ")) }));
  }

  const doc = new Document({
    creator: "PrivAgent project", title: "PrivAgent Complete Learning and Presentation Guide",
    styles: {
      default: { document: { run: { font: FONT, size: 20 }, paragraph: { spacing: { line: 252 } } } },
      paragraphStyles: [
        { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { font: FONT, size: 34, bold: true, color: BLUE },
          paragraph: { spacing: { before: 360, after: 140 }, keepNext: true, outlineLevel: 0 } },
        { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { font: FONT, size: 27, bold: true, color: ACCENT },
          paragraph: { spacing: { before: 260, after: 100 }, keepNext: true, outlineLevel: 1 } },
        { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { font: FONT, size: 23, bold: true, color: "333333" },
          paragraph: { spacing: { before: 200, after: 80 }, keepNext: true, outlineLevel: 2 } },
      ],
    },
    numbering: { config: [
      { reference: "bullets", levels: [
        { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 540, hanging: 270 } } } },
        { level: 1, format: LevelFormat.BULLET, text: "–", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 1000, hanging: 270 } } } }] },
      { reference: "numbers", levels: [
        { level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 540, hanging: 300 } } } }] },
    ] },
    sections: [{
      properties: { page: { size: { width: 12240, height: 15840 },
        margin: { top: 1080, bottom: 1080, left: 1080, right: 1080 } } },
      headers: { default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT,
        children: [new TextRun({ text: "PrivAgent: Learning and Presentation Guide", size: 16, color: "888888" })] })] }) },
      footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
        children: [new TextRun({ children: ["Page ", PageNumber.CURRENT, " of ", PageNumber.TOTAL_PAGES],
          size: 16, color: "888888" })] })] }) },
      children: kids,
    }],
  });
  return Packer.toBuffer(doc).then(buf => { fs.writeFileSync(OUT, buf); console.log("wrote", OUT, buf.length); });
}

build();
