"""Helpers communs pour les documents Word MA2E.
Regle stricte : tout noir, Times New Roman, tableaux Table Grid sans couleur.
"""
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Cm, Pt, RGBColor

FONT = "Times New Roman"
BLACK = RGBColor(0x00, 0x00, 0x00)


def _force_run(run, size=12, bold=False, italic=False):
    run.font.name = FONT
    run.font.size = Pt(size)
    run.font.color.rgb = BLACK
    run.bold = bold
    run.italic = italic
    # forcer le East-Asian fallback aussi
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:ascii"), FONT)
    rFonts.set(qn("w:hAnsi"), FONT)
    rFonts.set(qn("w:eastAsia"), FONT)
    rFonts.set(qn("w:cs"), FONT)


def set_doc_defaults(doc):
    # Style Normal
    style = doc.styles["Normal"]
    style.font.name = FONT
    style.font.size = Pt(12)
    style.font.color.rgb = BLACK
    # rFonts XML pour styles
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.insert(0, rfonts)
    rfonts.set(qn("w:ascii"), FONT)
    rfonts.set(qn("w:hAnsi"), FONT)
    rfonts.set(qn("w:eastAsia"), FONT)
    rfonts.set(qn("w:cs"), FONT)

    # Styles Heading 1/2/3 -> Times New Roman noir
    for sname, size in [("Heading 1", 16), ("Heading 2", 14), ("Heading 3", 12)]:
        try:
            s = doc.styles[sname]
            s.font.name = FONT
            s.font.size = Pt(size)
            s.font.color.rgb = BLACK
            s.font.bold = True
            rpr = s.element.get_or_add_rPr()
            rfonts = rpr.find(qn("w:rFonts"))
            if rfonts is None:
                rfonts = OxmlElement("w:rFonts")
                rpr.insert(0, rfonts)
            rfonts.set(qn("w:ascii"), FONT)
            rfonts.set(qn("w:hAnsi"), FONT)
            rfonts.set(qn("w:eastAsia"), FONT)
            rfonts.set(qn("w:cs"), FONT)
        except KeyError:
            pass

    # Marges
    for section in doc.sections:
        section.top_margin = Cm(2.2)
        section.bottom_margin = Cm(2.2)
        section.left_margin = Cm(2.2)
        section.right_margin = Cm(2.2)


def H(doc, text, level=1):
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        _force_run(run, size={1: 16, 2: 14, 3: 12}.get(level, 12), bold=True)
    return h


def P(doc, text, bold=False, italic=False, size=12, align=None,
      space_after=None):
    p = doc.add_paragraph()
    if align:
        p.alignment = align
    if space_after is not None:
        p.paragraph_format.space_after = Pt(space_after)
    run = p.add_run(text)
    _force_run(run, size=size, bold=bold, italic=italic)
    return p


def BUL(doc, text, size=12):
    p = doc.add_paragraph(style="List Bullet")
    run = p.add_run(text)
    _force_run(run, size=size)
    return p


def NUM(doc, text, size=12):
    p = doc.add_paragraph(style="List Number")
    run = p.add_run(text)
    _force_run(run, size=size)
    return p


def TABLE(doc, headers, rows, header_bold=True, font_size=11):
    """Tableau simple style 'Table Grid' (juste les bordures noires).
    Pas de couleur de fond, en-tete en gras, texte noir, Times New Roman.
    """
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    # Header
    for j, h in enumerate(headers):
        cell = table.cell(0, j)
        cell.text = ""
        p = cell.paragraphs[0]
        run = p.add_run(str(h))
        _force_run(run, size=font_size, bold=header_bold)
    # Body
    for i, row in enumerate(rows, start=1):
        for j, v in enumerate(row):
            cell = table.cell(i, j)
            cell.text = ""
            p = cell.paragraphs[0]
            run = p.add_run(str(v))
            _force_run(run, size=font_size)
    return table


def KVTABLE(doc, rows, font_size=11):
    """Tableau cle/valeur 2 colonnes, sans couleur. Cle en gras."""
    table = doc.add_table(rows=len(rows), cols=2)
    table.style = "Table Grid"
    for i, (k, v) in enumerate(rows):
        c1 = table.cell(i, 0)
        c2 = table.cell(i, 1)
        c1.text = ""
        c2.text = ""
        r1 = c1.paragraphs[0].add_run(str(k))
        _force_run(r1, size=font_size, bold=True)
        r2 = c2.paragraphs[0].add_run(str(v))
        _force_run(r2, size=font_size)
    for row in table.rows:
        row.cells[0].width = Cm(5)
        row.cells[1].width = Cm(11)
    return table


def PAGE_BREAK(doc):
    doc.add_page_break()


def CENTER(doc, text, size=12, bold=False, italic=False):
    return P(doc, text, bold=bold, italic=italic, size=size,
             align=WD_ALIGN_PARAGRAPH.CENTER)


def IMG(doc, path, width_cm=16, caption=None):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    run.add_picture(str(path), width=Cm(width_cm))
    if caption:
        cap = doc.add_paragraph()
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = cap.add_run(caption)
        _force_run(r, size=10, italic=True)
