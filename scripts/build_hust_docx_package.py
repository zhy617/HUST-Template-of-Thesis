from __future__ import annotations

import re
import shutil
import sys
import zipfile
import json
from html import escape, unescape
from pathlib import Path
from xml.etree import ElementTree as ET


REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
W14_NS = "http://schemas.microsoft.com/office/word/2010/wordml"
ET.register_namespace("", REL_NS)
ET.register_namespace("", CT_NS)
ET.register_namespace("w", W_NS)
ET.register_namespace("r", R_NS)
ET.register_namespace("m", M_NS)
ET.register_namespace("w14", W14_NS)


def w(tag: str) -> str:
    return f"{{{W_NS}}}{tag}"


def m(tag: str) -> str:
    return f"{{{M_NS}}}{tag}"


def read_text(zf: zipfile.ZipFile, name: str) -> str:
    return zf.read(name).decode("utf-8")


def parse_main_metadata(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    fields = {
        "title": r"\\title\{([^}]*)\}",
        "author": r"\\author\{([^}]*)\}",
        "school": r"\\school\{([^}]*)\}",
        "classnum": r"\\classnum\{([^}]*)\}",
        "stunum": r"\\stunum\{([^}]*)\}",
        "instructor": r"\\instructor\{([^}]*)\}",
        "date": r"\\date\{([^}]*)\}",
    }
    out: dict[str, str] = {}
    for key, pattern in fields.items():
        match = re.search(pattern, text)
        if match:
            out[key] = match.group(1).strip()
    return out


def add_missing_doc_namespaces(xml: str) -> str:
    start = xml.find("<w:document")
    end = xml.find(">", start)
    tag = xml[start:end]
    inserts = []
    if "xmlns:a=" not in tag:
        inserts.append(' xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"')
    if "xmlns:pic=" not in tag:
        inserts.append(' xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"')
    if inserts:
        xml = xml[:end] + "".join(inserts) + xml[end:]
    return xml


def paragraph_start_before(xml: str, pos: int) -> int:
    matches = list(re.finditer(r"<w:p(?=[\s>])", xml[:pos]))
    if not matches:
        raise RuntimeError("Could not find paragraph start")
    return matches[-1].start()


def final_sectpr_suffix(xml: str) -> str:
    body_end = xml.rfind("</w:body>")
    sect_start = xml.rfind("<w:sectPr", 0, body_end)
    if sect_start < 0:
        raise RuntimeError("Could not find final document sectPr")
    return xml[sect_start:]


def ensure_body_page_numbering(sectpr_xml: str) -> str:
    pg_num = '<w:pgNumType w:fmt="decimal" w:start="1"/>'
    if "<w:pgNumType" in sectpr_xml:
        return re.sub(r"<w:pgNumType\b[^/]*/>", pg_num, sectpr_xml, count=1)
    return sectpr_xml.replace("</w:sectPr>", pg_num + "</w:sectPr>", 1)


def body_fragment_without_final_sectpr(xml: str) -> str:
    body_start = xml.find("<w:body>")
    body_end = xml.rfind("</w:body>")
    if body_start < 0 or body_end < 0:
        raise RuntimeError("Could not find body")
    inner_start = body_start + len("<w:body>")
    sect_start = xml.rfind("<w:sectPr", inner_start, body_end)
    if sect_start < 0:
        return xml[inner_start:body_end]
    return xml[inner_start:sect_start]


def extract_front_section_breaks(template_xml: str, content_start: int) -> list[str]:
    body_end = template_xml.rfind("</w:body>")
    region = template_xml[content_start:body_end]
    pattern = re.compile(r"<w:p\b(?:(?!</w:p>).)*?<w:sectPr\b(?:(?!</w:p>).)*?</w:p>", re.S)
    breaks = pattern.findall(region)
    if len(breaks) < 3:
        raise RuntimeError("Could not extract template front-matter section breaks")
    return breaks[:3]


def make_toc_xml() -> str:
    toc_title_ppr = (
        '<w:pPr><w:keepNext />'
        '<w:adjustRightInd /><w:snapToGrid />'
        '<w:spacing w:beforeLines="100" w:before="240" w:afterLines="100" w:after="240" />'
        '<w:ind w:firstLineChars="0" w:firstLine="0" />'
        '<w:jc w:val="center" />'
        '<w:rPr><w:rFonts w:eastAsia="黑体" w:cs="Times New Roman" />'
        '<w:b /><w:bCs /><w:kern w:val="44" /><w:sz w:val="36" /><w:szCs w:val="36" /></w:rPr>'
        '</w:pPr>'
    )
    toc_title_rpr = (
        '<w:rPr><w:rFonts w:eastAsia="黑体" w:cs="Times New Roman" />'
        '<w:b /><w:bCs /><w:kern w:val="44" /><w:sz w:val="36" /><w:szCs w:val="36" /></w:rPr>'
    )
    return (
        '<w:sdt><w:sdtPr><w:docPartObj>'
        '<w:docPartGallery w:val="Table of Contents"/><w:docPartUnique/>'
        '</w:docPartObj></w:sdtPr><w:sdtContent>'
        '<w:p>' + toc_title_ppr + '<w:r>' + toc_title_rpr + '<w:t>目  录</w:t></w:r></w:p>'
        '<w:p><w:r><w:fldChar w:fldCharType="begin"/></w:r>'
        '<w:r><w:instrText xml:space="preserve"> TOC \\o "1-2" \\h \\z \\u </w:instrText></w:r>'
        '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
        '<w:r><w:t>目录将在打开文档后自动更新</w:t></w:r>'
        '<w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>'
        '</w:sdtContent></w:sdt>'
    )


def make_page_break_paragraph() -> str:
    return (
        '<w:p><w:pPr><w:spacing w:before="0" w:after="0" />'
        '<w:rPr><w:sz w:val="1" /><w:szCs w:val="1" /></w:rPr></w:pPr>'
        '<w:r><w:br w:type="page" /></w:r></w:p>'
    )


def insert_front_matter(body_xml: str, section_breaks: list[str]) -> str:
    abstract_pos = body_xml.find(">Abstract<")
    if abstract_pos < 0:
        raise RuntimeError("Could not find English abstract heading")
    abstract_p = paragraph_start_before(body_xml, abstract_pos)
    body_xml = body_xml[:abstract_p] + section_breaks[0] + body_xml[abstract_p:]

    chapter_p: int | None = None
    for paragraph in re.finditer(r"<w:p\b(?:(?!</w:p>).)*?</w:p>", body_xml, re.S):
        if is_body_heading1(paragraph.group(0)):
            chapter_p = paragraph.start()
            break
    if chapter_p is None:
        raise RuntimeError("Could not find first numbered chapter heading")
    toc_block = section_breaks[1] + make_page_break_paragraph() + make_toc_xml() + section_breaks[2]
    body_xml = body_xml[:chapter_p] + toc_block + body_xml[chapter_p:]
    return body_xml


def paragraph_text(p_xml: str) -> str:
    return "".join(re.findall(r"<w:t\b[^>]*>(.*?)</w:t>", p_xml, re.S))


def demote_abstract_headings(body_xml: str) -> str:
    title_ppr = (
        '<w:pPr><w:keepNext />'
        '<w:adjustRightInd /><w:snapToGrid />'
        '<w:spacing w:beforeLines="100" w:before="240" w:afterLines="100" w:after="240" />'
        '<w:ind w:firstLineChars="0" w:firstLine="0" />'
        '<w:jc w:val="center" />'
        '<w:outlineLvl w:val="0" />'
        '<w:rPr><w:rFonts w:eastAsia="黑体" w:cs="Times New Roman" />'
        '<w:b /><w:bCs /><w:kern w:val="44" /><w:sz w:val="36" /><w:szCs w:val="36" /></w:rPr>'
        '</w:pPr>'
    )
    title_rpr = (
        '<w:rPr><w:rFonts w:eastAsia="黑体" w:cs="Times New Roman" />'
        '<w:b /><w:bCs /><w:kern w:val="44" /><w:sz w:val="36" /><w:szCs w:val="36" /></w:rPr>'
    )

    def repl(match: re.Match[str]) -> str:
        p_xml = match.group(0)
        text = re.sub(r"\s+", "", paragraph_text(p_xml))
        if text not in {"摘要", "Abstract"}:
            return p_xml
        if "<w:pPr>" in p_xml:
            p_xml = re.sub(r"<w:pPr>.*?</w:pPr>", title_ppr, p_xml, count=1, flags=re.S)
        else:
            p_xml = p_xml.replace("<w:p>", "<w:p>" + title_ppr, 1)
        p_xml = re.sub(r"<w:rPr>.*?</w:rPr>", title_rpr, p_xml, flags=re.S)
        p_xml = re.sub(r"(<w:r>)(<w:t\b)", r"\1" + title_rpr + r"\2", p_xml)
        return p_xml

    return re.sub(r"<w:p\b(?:(?!</w:p>).)*?</w:p>", repl, body_xml, flags=re.S)


def paragraph_bookmark_name(p_xml: str) -> str | None:
    match = re.search(r'<w:bookmarkStart\b[^>]*\bw:name="([^"]+)"', p_xml)
    if not match:
        return None
    return unescape(match.group(1))


def paragraph_style_value(p_xml: str) -> str | None:
    match = re.search(r'<w:pStyle\b[^>]*\bw:val="([^"]+)"', p_xml)
    if not match:
        return None
    return match.group(1)


def is_body_heading1(p_xml: str) -> bool:
    return paragraph_style_value(p_xml) in {"1", "Heading1"}


def normalize_table_caption(title: str) -> str:
    title = unescape(title)
    replacements = {
        r"\to": "→",
        r"\Delta": "Δ",
        r"\%": "%",
    }
    for old, new in replacements.items():
        title = title.replace(old, new)
    title = re.sub(r"\\[a-zA-Z]+", "", title)
    title = title.replace("{", "").replace("}", "")
    title = re.sub(r"\s+", " ", title).strip()
    title = re.sub(r"[。．.]\s*$", "", title)
    title = re.sub(r"^表\s*\d+(?:-\d+)?\s*", "", title)
    return title


def table_caption_value(tbl_xml: str) -> str | None:
    match = re.search(r'<w:tblCaption\b[^>]*\bw:val="([^"]*)"', tbl_xml)
    if not match:
        return None
    return normalize_table_caption(match.group(1))


def make_table_caption_paragraph(original_p: str, table_number: str, title: str) -> str:
    return make_caption_paragraph(original_p, "表", table_number, title, keep_next=True)


def make_figure_caption_paragraph(original_p: str, figure_number: str, title: str) -> str:
    return make_caption_paragraph(original_p, "图", figure_number, title, keep_next=False)


def make_caption_paragraph(original_p: str, prefix: str, number: str, title: str, *, keep_next: bool) -> str:
    p_open_match = re.match(r"<w:p\b[^>]*>", original_p)
    p_open = p_open_match.group(0) if p_open_match else "<w:p>"
    bookmarks = "".join(re.findall(r"<w:bookmark(?:Start|End)\b[^>]*/>", original_p))
    text = escape(f"{prefix} {number} {title}")
    keep_xml = "<w:keepNext/>" if keep_next else ""
    ppr = (
        f"<w:pPr>{keep_xml}"
        '<w:spacing w:before="30" w:after="30" w:line="240" w:lineRule="auto"/>'
        '<w:ind w:firstLine="0" w:firstLineChars="0" w:left="0" w:right="0"/>'
        '<w:jc w:val="center"/>'
        '<w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" '
        'w:eastAsia="宋体" w:cs="Times New Roman"/>'
        '<w:b/><w:bCs/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr>'
        '</w:pPr>'
    )
    rpr = (
        '<w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" '
        'w:eastAsia="宋体" w:cs="Times New Roman"/>'
        '<w:b/><w:bCs/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr>'
    )
    return f'{p_open}{ppr}{bookmarks}<w:r>{rpr}<w:t>{text}</w:t></w:r></w:p>'


def ensure_child(parent: ET.Element, tag: str, first: bool = False) -> ET.Element:
    child = parent.find(tag)
    if child is not None:
        return child
    child = ET.Element(tag)
    if first:
        parent.insert(0, child)
    else:
        parent.append(child)
    return child


def remove_children(parent: ET.Element, tag: str) -> None:
    for child in list(parent):
        if child.tag == tag:
            parent.remove(child)


TABLE_RULE_COLOR = "008000"


def make_border(tag: str, val: str, sz: str = "0", color: str = TABLE_RULE_COLOR) -> ET.Element:
    el = ET.Element(w(tag))
    el.set(w("val"), val)
    el.set(w("sz"), sz)
    el.set(w("space"), "0")
    el.set(w("color"), color if val != "none" else "auto")
    return el


def add_table_borders(tbl_pr: ET.Element) -> None:
    remove_children(tbl_pr, w("tblBorders"))
    borders = ET.Element(w("tblBorders"))
    borders.extend(
        [
            make_border("top", "none", "0"),
            make_border("left", "none", "0"),
            make_border("bottom", "none", "0"),
            make_border("right", "none", "0"),
            make_border("insideH", "none", "0"),
            make_border("insideV", "none", "0"),
        ]
    )
    tbl_pr.append(borders)


def add_table_cell_margins(tbl_pr: ET.Element, compact: bool = False) -> None:
    remove_children(tbl_pr, w("tblCellMar"))
    mar = ET.Element(w("tblCellMar"))
    horizontal = "36" if compact else "72"
    vertical = "36" if compact else "48"
    for side, width in (("top", vertical), ("left", horizontal), ("bottom", vertical), ("right", horizontal)):
        el = ET.Element(w(side))
        el.set(w("w"), width)
        el.set(w("type"), "dxa")
        mar.append(el)
    tbl_pr.append(mar)


def set_run_font(run: ET.Element, size_val: str = "21") -> None:
    rpr = run.find(w("rPr"))
    if rpr is None:
        rpr = ET.Element(w("rPr"))
        run.insert(0, rpr)
    for tag in ("rFonts", "sz", "szCs"):
        remove_children(rpr, w(tag))
    fonts = ET.Element(w("rFonts"))
    fonts.set(w("ascii"), "Times New Roman")
    fonts.set(w("hAnsi"), "Times New Roman")
    fonts.set(w("eastAsia"), "宋体")
    fonts.set(w("cs"), "Times New Roman")
    rpr.insert(0, fonts)
    size = ET.Element(w("sz"))
    size.set(w("val"), size_val)
    size_cs = ET.Element(w("szCs"))
    size_cs.set(w("val"), size_val)
    rpr.append(size)
    rpr.append(size_cs)


def replace_hyphen_with_no_break_hyphen(run: ET.Element) -> None:
    for child in list(run):
        if child.tag != w("t") or not child.text or "-" not in child.text:
            continue
        index = list(run).index(child)
        run.remove(child)
        parts = child.text.split("-")
        insert_at = index
        for part_index, part in enumerate(parts):
            if part:
                text_node = ET.Element(w("t"))
                text_node.text = part
                run.insert(insert_at, text_node)
                insert_at += 1
            if part_index < len(parts) - 1:
                run.insert(insert_at, ET.Element(w("noBreakHyphen")))
                insert_at += 1


def simple_table_math_text(math_el: ET.Element) -> str | None:
    text = "".join(node.text or "" for node in math_el.iter(m("t"))).strip()
    if not text:
        return None
    text = text.replace("−", "-")
    if re.fullmatch(r"[+-]?\d+(?:\.\d+)?%?", text):
        return text
    if text in {"Δ", "\\Delta"}:
        return "Δ"
    return None


def make_table_text_run(text: str, size_val: str, bold: bool = False) -> ET.Element:
    run = ET.Element(w("r"))
    if bold:
        rpr = ET.SubElement(run, w("rPr"))
        ET.SubElement(rpr, w("b"))
        ET.SubElement(rpr, w("bCs"))
    set_run_font(run, size_val)
    t = ET.SubElement(run, w("t"))
    t.text = text
    return run


def convert_simple_math_in_table(tbl: ET.Element, size_val: str) -> None:
    for paragraph in tbl.iter(w("p")):
        for child in list(paragraph):
            if child.tag not in {m("oMath"), m("oMathPara")}:
                continue
            text = simple_table_math_text(child)
            if text is None:
                continue
            index = list(paragraph).index(child)
            paragraph.remove(child)
            paragraph.insert(index, make_table_text_run(text, size_val))


def cell_text(cell: ET.Element) -> str:
    parts = []
    for node in cell.iter():
        if node.tag in {w("t"), m("t")} and node.text:
            parts.append(node.text)
    return "".join(parts).strip()


def clear_cell_text(cell: ET.Element) -> None:
    for node in cell.iter():
        if node.tag in {w("t"), m("t")}:
            node.text = ""


def set_cell_border(
    cell: ET.Element,
    *,
    top_rule: bool = False,
    header_rule: bool = False,
    bottom_rule: bool = False,
) -> None:
    tc_pr = ensure_child(cell, w("tcPr"), first=True)
    remove_children(tc_pr, w("tcBorders"))
    borders = ET.Element(w("tcBorders"))
    bottom_val = "single" if header_rule or bottom_rule else "none"
    bottom_size = "12" if bottom_rule else ("4" if header_rule else "0")
    borders.extend(
        [
            make_border("top", "single" if top_rule else "none", "12" if top_rule else "0"),
            make_border("left", "none", "0"),
            make_border("bottom", bottom_val, bottom_size),
            make_border("right", "none", "0"),
            make_border("insideH", "none", "0"),
            make_border("insideV", "none", "0"),
        ]
    )
    tc_pr.append(borders)
    remove_children(tc_pr, w("vAlign"))
    valign = ET.Element(w("vAlign"))
    valign.set(w("val"), "center")
    tc_pr.append(valign)


def set_cell_width(cell: ET.Element, width: int, no_wrap: bool = False) -> None:
    tc_pr = ensure_child(cell, w("tcPr"), first=True)
    remove_children(tc_pr, w("tcW"))
    tc_w = ET.Element(w("tcW"))
    tc_w.set(w("w"), str(width))
    tc_w.set(w("type"), "dxa")
    tc_pr.insert(0, tc_w)
    if no_wrap and tc_pr.find(w("noWrap")) is None:
        tc_pr.append(ET.Element(w("noWrap")))


def should_left_align(text: str, cell_index: int, header: bool) -> bool:
    if header:
        return False
    if len(text) >= 14:
        return True
    if any(ch in text for ch in "，。；：、"):
        return True
    return cell_index == 0 and not re.fullmatch(r"[-+0-9.%（）()A-Za-z/ ]+", text)


def style_table_paragraph(
    p: ET.Element,
    alignment: str,
    size_val: str = "21",
    line_val: str = "240",
    no_break_hyphen: bool = False,
) -> None:
    ppr = ensure_child(p, w("pPr"), first=True)
    remove_children(ppr, w("ind"))
    ind = ET.Element(w("ind"))
    ind.set(w("firstLine"), "0")
    ind.set(w("left"), "0")
    ind.set(w("right"), "0")
    ppr.append(ind)
    remove_children(ppr, w("spacing"))
    spacing = ET.Element(w("spacing"))
    spacing.set(w("before"), "0")
    spacing.set(w("after"), "0")
    spacing.set(w("line"), line_val)
    spacing.set(w("lineRule"), "auto")
    ppr.append(spacing)
    remove_children(ppr, w("jc"))
    jc = ET.Element(w("jc"))
    jc.set(w("val"), alignment)
    ppr.append(jc)
    for run in p.findall(w("r")):
        set_run_font(run, size_val)
        if no_break_hyphen:
            replace_hyphen_with_no_break_hyphen(run)


def text_width_score(text: str) -> float:
    text = re.sub(r"\s+", "", text)
    if not text:
        return 1.0
    score = 0.0
    for ch in text:
        code = ord(ch)
        if 0x4E00 <= code <= 0x9FFF:
            score += 1.85
        elif ch.isdigit():
            score += 0.75
        elif ch.isalpha():
            score += 0.92
        elif ch in "-+/%.()":
            score += 0.45
        else:
            score += 0.65
    return max(1.0, score)


def clamp_weights(weights: list[float], min_weight: float, max_weight: float) -> list[float]:
    weights = [min(max(weight, min_weight), max_weight) for weight in weights]
    total = sum(weights) or 1.0
    return [weight / total for weight in weights]


def apply_weight_floors(weights: list[float], floors: list[float]) -> list[float]:
    if len(weights) != len(floors):
        return weights
    floor_total = sum(floors)
    if floor_total >= 0.98:
        total = floor_total or 1.0
        return [floor / total for floor in floors]
    extras = [max(0.0, weight - floor) for weight, floor in zip(weights, floors)]
    extra_total = sum(extras)
    remaining = 1.0 - floor_total
    if extra_total <= 0:
        return [floor + remaining / len(floors) for floor in floors]
    return [floor + remaining * extra / extra_total for floor, extra in zip(floors, extras)]


def compute_table_widths(existing_widths: list[int], cols: int, column_scores: list[float] | None = None) -> list[int]:
    total = 8312
    if column_scores and len(column_scores) == cols:
        adjusted = [max(1.0, score) ** 1.08 for score in column_scores]
        score_total = sum(adjusted) or 1.0
        weights = [score / score_total for score in adjusted]
        if cols >= 9:
            weights = clamp_weights(weights, 0.065, 0.27)
        elif cols >= 5:
            weights = clamp_weights(weights, 0.10, 0.36)
            if cols == 6:
                weights = apply_weight_floors(weights, [0.22, 0.27, 0.12, 0.12, 0.12, 0.12])
        elif cols == 4:
            weights = clamp_weights(weights, 0.16, 0.46)
            weights = apply_weight_floors(weights, [0.22, 0.22, 0.24, 0.20])
        else:
            weights = clamp_weights(weights, 0.14, 0.72)
    elif cols >= 9:
        if cols == 9:
            weights = [0.24] + [0.095] * 8
        elif cols == 10:
            weights = [0.22] + [0.083] * 8 + [0.116]
        else:
            weights = [1 / cols] * cols
    elif cols == 7:
        weights = [0.18, 0.14, 0.14, 0.14, 0.14, 0.13, 0.13]
    elif cols == 6:
        weights = [0.18, 0.30, 0.11, 0.14, 0.14, 0.13]
    elif cols == 5:
        weights = [0.24, 0.26, 0.14, 0.18, 0.18]
    elif cols == 4:
        weights = [0.28, 0.22, 0.25, 0.25]
    elif cols == 3:
        weights = [0.28, 0.52, 0.20]
    elif cols == 2:
        weights = [0.24, 0.76]
    else:
        weights = [1 / cols] * cols
    widths = [max(360, int(total * weight)) for weight in weights]
    widths[-1] += total - sum(widths)
    return widths


def source_table_width_overrides(root: Path) -> dict[str, list[int]]:
    path = root / "docx-table-widths.json"
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    overrides: dict[str, list[int]] = {}
    if not isinstance(raw, dict):
        return overrides
    for label, widths in raw.items():
        if not isinstance(label, str) or not isinstance(widths, list):
            continue
        values = [int(value) for value in widths if isinstance(value, (int, float)) or str(value).isdigit()]
        if values and sum(values) > 0:
            overrides[label] = values
    return overrides


def set_table_grid_and_cell_widths(tbl: ET.Element, widths: list[int], no_wrap: bool, no_wrap_columns: set[int] | None = None) -> None:
    no_wrap_columns = no_wrap_columns or set()
    remove_children(tbl, w("tblGrid"))
    grid = ET.Element(w("tblGrid"))
    for width in widths:
        col = ET.Element(w("gridCol"))
        col.set(w("w"), str(width))
        grid.append(col)
    insert_at = 1 if tbl.find(w("tblPr")) is not None else 0
    tbl.insert(insert_at, grid)

    for row in tbl.findall(w("tr")):
        col_index = 0
        for cell in row.findall(w("tc")):
            tc_pr = ensure_child(cell, w("tcPr"), first=True)
            span_el = tc_pr.find(w("gridSpan"))
            span = int(span_el.attrib.get(w("val"), "1")) if span_el is not None else 1
            cell_width = sum(widths[col_index : col_index + span])
            cell_no_wrap = no_wrap or any(index in no_wrap_columns for index in range(col_index, col_index + span))
            set_cell_width(cell, cell_width, no_wrap=cell_no_wrap)
            col_index += span


def table_cell_span(cell: ET.Element) -> int:
    tc_pr = cell.find(w("tcPr"))
    span_el = tc_pr.find(w("gridSpan")) if tc_pr is not None else None
    return int(span_el.attrib.get(w("val"), "1")) if span_el is not None else 1


def table_column_scores(rows: list[ET.Element], cols: int) -> list[float]:
    scores = [1.0] * cols
    for row in rows:
        col_index = 0
        for cell in row.findall(w("tc")):
            span = table_cell_span(cell)
            text = cell_text(cell)
            if re.fullmatch(r"\d+-\d+\s*\(lr\)\d+-\d+", text):
                text = ""
            score = text_width_score(text)
            if span <= 1:
                if col_index < cols:
                    scores[col_index] = max(scores[col_index], score)
            else:
                per_col = max(1.0, score / span)
                for offset in range(span):
                    target = col_index + offset
                    if target < cols:
                        scores[target] = max(scores[target], per_col)
            col_index += span
    return scores


def expand_latex_colspec_stars(spec: str) -> str:
    pattern = re.compile(r"\*\{(\d+)\}\{([^{}]*)\}")
    while True:
        match = pattern.search(spec)
        if not match:
            return spec
        spec = spec[: match.start()] + match.group(2) * int(match.group(1)) + spec[match.end() :]


def latex_column_alignments(spec: str) -> list[str]:
    spec = expand_latex_colspec_stars(spec)
    spec = re.sub(r"[@!<>]\{[^{}]*\}", "", spec)
    alignments: list[str] = []
    i = 0
    while i < len(spec):
        ch = spec[i]
        if ch == "l":
            alignments.append("left")
        elif ch == "c":
            alignments.append("center")
        elif ch == "r":
            alignments.append("right")
        elif ch in "pmbX":
            alignments.append("left")
            if i + 1 < len(spec) and spec[i + 1] == "{":
                depth = 0
                j = i + 1
                while j < len(spec):
                    if spec[j] == "{":
                        depth += 1
                    elif spec[j] == "}":
                        depth -= 1
                        if depth == 0:
                            i = j
                            break
                    j += 1
        i += 1
    return alignments


def source_table_alignments(root: Path) -> dict[str, list[str]]:
    alignments: dict[str, list[str]] = {}
    table_pattern = re.compile(r"\\begin\{table\}.*?\\end\{table\}", re.S)
    tabular_pattern = re.compile(r"\\begin\{(?:tabular|tabularx|longtable)\}(?:\{[^{}]*\})?\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}", re.S)
    for path in word_input_files(root):
        text = strip_latex_comment_lines(path.read_text(encoding="utf-8"))
        for table in table_pattern.finditer(text):
            block = table.group(0)
            label = re.search(r"\\label\{([^}]+)\}", block)
            tabular = tabular_pattern.search(block)
            if not label or not tabular:
                continue
            align = latex_column_alignments(tabular.group(1))
            if align:
                alignments[label.group(1)] = align
    return alignments


def table_column_alignment(alignments: list[str] | None, cell_index: int, text: str, header: bool) -> str:
    if header:
        return "center"
    if alignments and cell_index < len(alignments):
        return alignments[cell_index]
    return "left" if should_left_align(text, cell_index, header) else "center"


def style_table_xml(
    tbl_xml: str,
    table_number: str,
    title: str,
    alignments: list[str] | None = None,
    label: str | None = None,
    width_override: list[int] | None = None,
) -> str:
    wrapped = (
        f'<root xmlns:w="{W_NS}" xmlns:r="{R_NS}" xmlns:m="{M_NS}" xmlns:w14="{W14_NS}">'
        f"{tbl_xml}</root>"
    )
    root = ET.fromstring(wrapped)
    tbl = root[0]
    tbl_pr = ensure_child(tbl, w("tblPr"), first=True)
    remove_children(tbl_pr, w("tblStyle"))
    remove_children(tbl_pr, w("tblLayout"))
    existing_widths = [
        int(col.attrib.get(w("w"), "0"))
        for col in (tbl.find(w("tblGrid")).findall(w("gridCol")) if tbl.find(w("tblGrid")) is not None else [])
        if col.attrib.get(w("w"), "0").isdigit()
    ]
    rows = tbl.findall(w("tr"))
    max_cols = max((sum(table_cell_span(tc) for tc in row.findall(w("tc"))) for row in rows), default=0)
    scores = table_column_scores(rows, max_cols) if max_cols else []
    widths = compute_table_widths(existing_widths, max_cols, scores) if max_cols else existing_widths
    if width_override and len(width_override) == max_cols:
        total = sum(width_override) or 1
        widths = [max(360, int(8312 * value / total)) for value in width_override]
        widths[-1] += 8312 - sum(widths)
    layout = ET.Element(w("tblLayout"))
    layout.set(w("type"), "fixed")
    tbl_pr.append(layout)
    remove_children(tbl_pr, w("tblW"))
    tbl_w = ET.Element(w("tblW"))
    tbl_w.set(w("w"), str(sum(widths) if widths else 0))
    tbl_w.set(w("type"), "dxa")
    tbl_pr.insert(0, tbl_w)
    remove_children(tbl_pr, w("jc"))
    jc = ET.Element(w("jc"))
    jc.set(w("val"), "center")
    tbl_pr.append(jc)
    caption = tbl_pr.find(w("tblCaption"))
    if caption is None:
        caption = ET.Element(w("tblCaption"))
        tbl_pr.append(caption)
    caption.set(w("val"), f"表 {table_number} {title}")
    add_table_borders(tbl_pr)
    add_table_cell_margins(tbl_pr, compact=max_cols >= 7)
    if widths:
        no_wrap_columns = {0} if max_cols == 4 else set()
        set_table_grid_and_cell_widths(tbl, widths, no_wrap=max_cols >= 5, no_wrap_columns=no_wrap_columns)

    if not rows:
        return tbl_xml
    font_size = "20" if max_cols >= 7 else "21"
    line_size = "240"
    first_row_cells = rows[0].findall(w("tc"))
    header_rows = 2 if len(rows) > 1 and any(
        (cell.find(w("tcPr")) is not None and cell.find(w("tcPr")).find(w("gridSpan")) is not None)
        for cell in first_row_cells
    ) else 1

    for row_index, row in enumerate(rows):
        tr_pr = ensure_child(row, w("trPr"), first=True)
        remove_children(tr_pr, w("tblHeader"))
        if row_index < header_rows:
            tr_pr.append(ET.Element(w("tblHeader")))
        cells = row.findall(w("tc"))
        for cell_index, cell in enumerate(cells):
            text = cell_text(cell)
            if row_index == 1 and re.fullmatch(r"\d+-\d+\s*\(lr\)\d+-\d+", text):
                clear_cell_text(cell)
                text = ""
            set_cell_border(
                cell,
                top_rule=(row_index == 0),
                header_rule=(row_index == header_rows - 1),
                bottom_rule=(row_index == len(rows) - 1),
            )
            alignment = table_column_alignment(alignments, cell_index, text, row_index < header_rows)
            for p in cell.findall(w("p")):
                no_break_hyphen = max_cols >= 5 or (max_cols == 4 and cell_index == 0)
                style_table_paragraph(p, alignment, font_size, line_size, no_break_hyphen=no_break_hyphen)
    convert_simple_math_in_table(tbl, font_size)
    return ET.tostring(tbl, encoding="unicode")


def update_table_crossrefs(body_xml: str, label_to_number: dict[str, str]) -> str:
    for label, number in label_to_number.items():
        pattern = re.compile(
            rf'(<w:hyperlink\b[^>]*\bw:anchor="{re.escape(label)}"[^>]*>)(.*?)(</w:hyperlink>)',
            re.S,
        )

        def repl(match: re.Match[str]) -> str:
            rpr = normal_crossref_rpr()
            return f"{match.group(1)}<w:r>{rpr}<w:t>{number}</w:t></w:r>{match.group(3)}"

        body_xml = pattern.sub(repl, body_xml)
    body_xml = re.sub(r"(表(?:<[^>]+>)*[\s\u00a0]*)(表(?:<[^>]+>)*[\s\u00a0]*)", r"\1", body_xml)
    return body_xml


def normal_crossref_rpr() -> str:
    return (
        '<w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" '
        'w:eastAsia="宋体" w:cs="Times New Roman"/>'
        '<w:color w:val="000000"/><w:u w:val="none"/></w:rPr>'
    )


def update_figure_crossrefs(body_xml: str, label_to_number: dict[str, str]) -> str:
    for label, number in label_to_number.items():
        pattern = re.compile(
            rf'(<w:hyperlink\b[^>]*\bw:anchor="{re.escape(label)}"[^>]*>)(.*?)(</w:hyperlink>)',
            re.S,
        )

        def repl(match: re.Match[str]) -> str:
            rpr = normal_crossref_rpr()
            return f"{match.group(1)}<w:r>{rpr}<w:t>{number}</w:t></w:r>{match.group(3)}"

        body_xml = pattern.sub(repl, body_xml)
    body_xml = re.sub(r"(图(?:<[^>]+>)*[\s\u00a0]*)(图(?:<[^>]+>)*[\s\u00a0]*)", r"\1", body_xml)
    return body_xml


def source_algorithm_info(root: Path) -> dict[str, tuple[str, str]]:
    algorithms: dict[str, tuple[str, str]] = {}
    chapter = 0
    algorithm_count = 0
    event_pattern = re.compile(r"\\section(\*?)\{[^}]*\}|\\begin\{algorithm\}.*?\\end\{algorithm\}", re.S)
    for path in word_input_files(root):
        text = strip_latex_comment_lines(path.read_text(encoding="utf-8"))
        for match in event_pattern.finditer(text):
            event = match.group(0)
            if event.startswith("\\section"):
                if not match.group(1):
                    chapter += 1
                    algorithm_count = 0
                continue
            label = re.search(r"\\label\{([^}]+)\}", event)
            caption = re.search(r"\\caption\{([^}]*)\}", event)
            if label and caption and chapter > 0:
                algorithm_count += 1
                algorithms[label.group(1)] = (f"{chapter}-{algorithm_count}", normalize_table_caption(caption.group(1)))
    return algorithms


def update_algorithm_crossrefs(body_xml: str, label_to_number: dict[str, str]) -> str:
    for label, number in label_to_number.items():
        pattern = re.compile(
            rf'(<w:hyperlink\b[^>]*\bw:anchor="{re.escape(label)}"[^>]*>)(.*?)(</w:hyperlink>)',
            re.S,
        )

        def repl(match: re.Match[str]) -> str:
            rpr = normal_crossref_rpr()
            return f"{match.group(1)}<w:r>{rpr}<w:t>{number}</w:t></w:r>{match.group(3)}"

        body_xml = pattern.sub(repl, body_xml)
        body_xml = body_xml.replace(f"[{label}]", number)
    return body_xml


def algorithm_border_xml(side: str) -> str:
    return f'<w:{side} w:val="single" w:sz="6" w:space="1" w:color="000000"/>'


def make_border_xml(side: str, val: str) -> str:
    if val == "none":
        return f'<w:{side} w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
    return f'<w:{side} w:val="{val}" w:sz="6" w:space="1" w:color="000000"/>'


def algorithm_cell_border_xml(*, top: bool = False, bottom: bool = False) -> str:
    return (
        '<w:tcBorders>'
        f'{algorithm_border_xml("top") if top else make_border_xml("top", "none")}'
        f'{make_border_xml("left", "none")}'
        f'{algorithm_border_xml("bottom") if bottom else make_border_xml("bottom", "none")}'
        f'{make_border_xml("right", "none")}'
        '</w:tcBorders>'
    )


def algorithm_table_cell(
    content: str,
    *,
    width: int,
    borders: str = "",
    grid_span: int | None = None,
    left_margin: int = 24,
    right_margin: int = 24,
) -> str:
    span = f'<w:gridSpan w:val="{grid_span}"/>' if grid_span else ""
    return (
        '<w:tc><w:tcPr>'
        f'<w:tcW w:w="{width}" w:type="dxa"/>{span}'
        f'<w:tcMar><w:top w:w="0" w:type="dxa"/><w:left w:w="{left_margin}" w:type="dxa"/>'
        f'<w:bottom w:w="0" w:type="dxa"/><w:right w:w="{right_margin}" w:type="dxa"/></w:tcMar>'
        '<w:vAlign w:val="top"/>'
        f"{borders}"
        f"</w:tcPr>{content}</w:tc>"
    )


def item_paragraph_for_algorithm_table(p_xml: str) -> str:
    match = re.match(r"<w:p\b[^>]*>(.*)</w:p>", p_xml, re.S)
    inner = match.group(1) if match else p_xml
    inner = re.sub(r"<w:pPr\b.*?</w:pPr>", "", inner, count=1, flags=re.S)
    ppr = (
        '<w:pPr><w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/>'
        '<w:ind w:firstLine="0" w:firstLineChars="0" w:left="0" w:right="0"/>'
        '<w:jc w:val="left"/>'
        '<w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" '
        'w:eastAsia="宋体" w:cs="Times New Roman"/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr>'
        '</w:pPr>'
    )
    return f"<w:p>{ppr}{inner}</w:p>"


def algorithm_number_paragraph(number: int) -> str:
    rpr = (
        '<w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" '
        'w:eastAsia="宋体" w:cs="Times New Roman"/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr>'
    )
    ppr = (
        '<w:pPr><w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/>'
        '<w:ind w:firstLine="0" w:firstLineChars="0" w:left="0" w:right="0"/>'
        '<w:jc w:val="right"/>'
        '<w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" '
        'w:eastAsia="宋体" w:cs="Times New Roman"/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr>'
        '</w:pPr>'
    )
    return f"<w:p>{ppr}<w:r>{rpr}<w:t>{number}:</w:t></w:r></w:p>"


def make_algorithm_table(original_p: str, algorithm_number: str, title: str, item_blocks: list[str]) -> str:
    bookmarks = "".join(re.findall(r"<w:bookmark(?:Start|End)\b[^>]*/>", original_p))
    label_rpr = (
        '<w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" '
        'w:eastAsia="宋体" w:cs="Times New Roman"/><w:b/><w:bCs/>'
        '<w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr>'
    )
    title_rpr = (
        '<w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" '
        'w:eastAsia="宋体" w:cs="Times New Roman"/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr>'
    )
    header_ppr = (
        '<w:pPr><w:keepNext/><w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/>'
        '<w:ind w:firstLine="0" w:firstLineChars="0" w:left="0" w:right="0"/>'
        '<w:jc w:val="left"/>'
        '<w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" '
        'w:eastAsia="宋体" w:cs="Times New Roman"/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr>'
        '</w:pPr>'
    )
    header_content = (
        f"<w:p>{header_ppr}{bookmarks}"
        f"<w:r>{label_rpr}<w:t>算法 {escape(algorithm_number)}</w:t></w:r>"
        f'<w:r>{title_rpr}<w:t xml:space="preserve"> {escape(title)}</w:t></w:r>'
        "</w:p>"
    )
    rows = [
        '<w:tr><w:trPr><w:tblHeader/></w:trPr>'
        + algorithm_table_cell(header_content, width=8312, borders=algorithm_cell_border_xml(top=True, bottom=True), grid_span=2, left_margin=0, right_margin=0)
        + "</w:tr>"
    ]
    for item_index, item in enumerate(item_blocks, start=1):
        is_last = item_index == len(item_blocks)
        borders = algorithm_cell_border_xml(bottom=is_last)
        rows.append(
            "<w:tr>"
            + algorithm_table_cell(algorithm_number_paragraph(item_index), width=360, borders=borders, left_margin=0, right_margin=18)
            + algorithm_table_cell(item_paragraph_for_algorithm_table(item), width=7952, borders=borders, left_margin=0, right_margin=0)
            + "</w:tr>"
        )
    return (
        '<w:tbl><w:tblPr>'
        '<w:tblW w:w="8312" w:type="dxa"/><w:jc w:val="center"/><w:tblLayout w:type="fixed"/>'
        '<w:tblBorders>'
        '<w:top w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        '<w:left w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        '<w:bottom w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        '<w:right w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        '<w:insideH w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        '<w:insideV w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        '</w:tblBorders></w:tblPr>'
        '<w:tblGrid><w:gridCol w:w="360"/><w:gridCol w:w="7952"/></w:tblGrid>'
        + "".join(rows)
        + "</w:tbl>"
    )


def style_algorithms(body_xml: str, root: Path) -> str:
    algorithm_info = source_algorithm_info(root)
    if not algorithm_info:
        return body_xml
    label_to_number = {label: number for label, (number, _title) in algorithm_info.items()}
    caption_to_number = {title: number for number, title in algorithm_info.values()}

    block_pattern = re.compile(r"<w:p\b.*?</w:p>|<w:tbl\b.*?</w:tbl>", re.S)
    pieces: list[str] = []
    pos = 0
    for match in block_pattern.finditer(body_xml):
        if match.start() > pos:
            pieces.append(body_xml[pos:match.start()])
        pieces.append(match.group(0))
        pos = match.end()
    if pos < len(body_xml):
        pieces.append(body_xml[pos:])

    out: list[str] = []
    index = 0
    while index < len(pieces):
        block = pieces[index]
        if not block.startswith("<w:p"):
            out.append(block)
            index += 1
            continue
        text = plain_paragraph_text(block)
        match_text = re.match(r"算法\s+(\d+-\d+)\s+(.+)$", text)
        if not match_text:
            out.append(block)
            index += 1
            continue

        title = normalize_table_caption(match_text.group(2))
        number = caption_to_number.get(title, match_text.group(1))
        item_blocks: list[str] = []
        scan = index + 1
        skipped: list[str] = []
        while scan < len(pieces):
            if not pieces[scan].startswith("<w:p"):
                if pieces[scan].strip():
                    break
                skipped.append(pieces[scan])
                scan += 1
                continue
            if "<w:numPr" not in pieces[scan]:
                break
            item_blocks.append(pieces[scan])
            scan += 1
        if item_blocks:
            out.append(make_algorithm_table(block, number, title, item_blocks))
            index = scan
        else:
            out.append(make_algorithm_table(block, number, title, []))
            out.extend(skipped)
            index = index + 1

    return update_algorithm_crossrefs("".join(out), label_to_number)


def word_input_files(root: Path) -> list[Path]:
    entry = root / "word.tex"
    if not entry.exists():
        return []
    seen: set[Path] = set()
    ordered: list[Path] = []

    def visit(path: Path) -> None:
        path = path.with_suffix(".tex") if path.suffix == "" else path
        if not path.is_absolute():
            path = root / path
        path = path.resolve()
        if path in seen or not path.exists():
            return
        seen.add(path)
        ordered.append(path)
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"\\(?:input|include)\{([^}]+)\}", text):
            visit(Path(match.group(1)))

    visit(entry)
    return ordered


def custom_list_item_counts(root: Path) -> list[int]:
    counts: list[int] = []
    for path in word_input_files(root):
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"\\begin\{list\}\{（\\arabic\{enumi\}）\}\{.*?\\end\{list\}", text, re.S):
            counts.append(len(re.findall(r"\\item\b", match.group(0))))
    return counts


def plain_paragraph_text(p_xml: str) -> str:
    return "".join(unescape(text) for text in re.findall(r"<w:t\b[^>]*>(.*?)</w:t>", p_xml, re.S)).strip()


def add_static_list_number(p_xml: str, number: int) -> str:
    first_rpr = re.search(r"<w:rPr>.*?</w:rPr>", p_xml, re.S)
    rpr = first_rpr.group(0) if first_rpr else ""
    prefix_run = f"<w:r>{rpr}<w:t>（{number}）</w:t></w:r>"
    if "<w:pPr>" in p_xml:
        return re.sub(r"(</w:pPr>)", r"\1" + prefix_run, p_xml, count=1)
    return p_xml.replace(">", ">" + prefix_run, 1)


def fix_custom_numbered_lists(body_xml: str, counts: list[int]) -> str:
    if not counts:
        return body_xml
    block_pattern = re.compile(r"<w:p\b.*?</w:p>|<w:tbl\b.*?</w:tbl>", re.S)
    out: list[str] = []
    pos = 0
    list_index = 0
    remaining = 0
    current_number = 1

    for match in block_pattern.finditer(body_xml):
        out.append(body_xml[pos:match.start()])
        block = match.group(0)
        if block.startswith("<w:p"):
            text = plain_paragraph_text(block)
            if text == "（）" and list_index < len(counts):
                remaining = counts[list_index]
                current_number = 1
                list_index += 1
                pos = match.end()
                continue
            if remaining > 0 and text:
                block = add_static_list_number(block, current_number)
                remaining -= 1
                current_number += 1
        out.append(block)
        pos = match.end()
    out.append(body_xml[pos:])
    return "".join(out)


def equation_label_numbers(root: Path) -> dict[str, str]:
    labels: dict[str, str] = {}
    chapter = 0
    eq_count = 0
    event_pattern = re.compile(r"\\section(\*?)\{[^}]*\}|\\begin\{equation\}.*?\\end\{equation\}", re.S)
    for path in word_input_files(root):
        text = strip_latex_comment_lines(path.read_text(encoding="utf-8"))
        for match in event_pattern.finditer(text):
            event = match.group(0)
            if event.startswith("\\section"):
                if not match.group(1):
                    chapter += 1
                    eq_count = 0
                continue
            label = re.search(r"\\label\{([^}]+)\}", event)
            if label and chapter > 0:
                eq_count += 1
                labels[label.group(1)] = f"{chapter}-{eq_count}"
    return labels


def update_equation_crossrefs(body_xml: str, label_to_number: dict[str, str]) -> str:
    for label, number in label_to_number.items():
        pattern = re.compile(
            rf'(<w:hyperlink\b[^>]*\bw:anchor="{re.escape(label)}"[^>]*>)(.*?)(</w:hyperlink>)',
            re.S,
        )

        def repl(match: re.Match[str]) -> str:
            rpr = normal_crossref_rpr()
            return f"{match.group(1)}<w:r>{rpr}<w:t>{number}</w:t></w:r>{match.group(3)}"

        body_xml = pattern.sub(repl, body_xml)
    return body_xml


def style_equation_paragraph(p_xml: str, number: str) -> str:
    wrapped = (
        f'<root xmlns:w="{W_NS}" xmlns:r="{R_NS}" xmlns:m="{M_NS}" xmlns:w14="{W14_NS}">'
        f"{p_xml}</root>"
    )
    root = ET.fromstring(wrapped)
    p = root[0]
    ppr = ensure_child(p, w("pPr"), first=True)
    remove_children(ppr, w("ind"))
    ind = ET.Element(w("ind"))
    ind.set(w("firstLine"), "0")
    ind.set(w("left"), "0")
    ind.set(w("right"), "0")
    ppr.append(ind)
    remove_children(ppr, w("tabs"))
    tabs = ET.Element(w("tabs"))
    center_tab = ET.Element(w("tab"))
    center_tab.set(w("val"), "center")
    center_tab.set(w("pos"), "4145")
    tabs.append(center_tab)
    right_tab = ET.Element(w("tab"))
    right_tab.set(w("val"), "right")
    right_tab.set(w("pos"), "8290")
    tabs.append(right_tab)
    ppr.append(tabs)

    lead = ET.Element(w("r"))
    lead.append(ET.Element(w("tab")))
    insert_at = 1 if len(p) and p[0].tag == w("pPr") else 0
    p.insert(insert_at, lead)

    r = ET.Element(w("r"))
    rpr = ET.Element(w("rPr"))
    fonts = ET.Element(w("rFonts"))
    fonts.set(w("ascii"), "Times New Roman")
    fonts.set(w("hAnsi"), "Times New Roman")
    fonts.set(w("eastAsia"), "宋体")
    fonts.set(w("cs"), "Times New Roman")
    rpr.append(fonts)
    size = ET.Element(w("sz"))
    size.set(w("val"), "21")
    size_cs = ET.Element(w("szCs"))
    size_cs.set(w("val"), "21")
    rpr.append(size)
    rpr.append(size_cs)
    r.append(rpr)
    r.append(ET.Element(w("tab")))
    t = ET.Element(w("t"))
    t.text = f"({number})"
    r.append(t)
    p.append(r)
    return ET.tostring(p, encoding="unicode")


def add_equation_numbers(body_xml: str, label_to_number: dict[str, str]) -> str:
    numbers = list(label_to_number.values())
    if not numbers:
        return body_xml
    block_pattern = re.compile(r"<w:p\b.*?</w:p>|<w:tbl\b.*?</w:tbl>", re.S)
    out: list[str] = []
    pos = 0
    eq_index = 0
    for match in block_pattern.finditer(body_xml):
        out.append(body_xml[pos:match.start()])
        block = match.group(0)
        if (
            block.startswith("<w:p")
            and "<m:oMath" in block
            and not re.search(r"<w:t\b[^>]*>\s*\S", block)
            and eq_index < len(numbers)
        ):
            block = style_equation_paragraph(block, numbers[eq_index])
            eq_index += 1
        out.append(block)
        pos = match.end()
    out.append(body_xml[pos:])
    return "".join(out)


def fix_equation_numbering(body_xml: str, root: Path) -> str:
    label_to_number = equation_label_numbers(root)
    body_xml = update_equation_crossrefs(body_xml, label_to_number)
    return add_equation_numbers(body_xml, label_to_number)


def strip_latex_comment_lines(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("%"))


def source_figure_info(root: Path) -> dict[str, tuple[str, str]]:
    figures: dict[str, tuple[str, str]] = {}
    chapter = 0
    figure_count = 0
    event_pattern = re.compile(r"\\section(\*?)\{[^}]*\}|\\begin\{figure\}.*?\\end\{figure\}", re.S)
    for path in word_input_files(root):
        text = strip_latex_comment_lines(path.read_text(encoding="utf-8"))
        for match in event_pattern.finditer(text):
            event = match.group(0)
            if event.startswith("\\section"):
                if not match.group(1):
                    chapter += 1
                    figure_count = 0
                continue
            label = re.search(r"\\label\{([^}]+)\}", event)
            caption = re.search(r"\\caption\{([^}]*)\}", event)
            if label and caption and chapter > 0:
                figure_count += 1
                figures[label.group(1)] = (f"{chapter}-{figure_count}", normalize_table_caption(caption.group(1)))
    return figures


TEXTWIDTH_INCHES = 5.763888888888889
EMU_PER_INCH = 914400


def source_image_widths(root: Path) -> dict[str, float]:
    widths: dict[str, float] = {}
    pattern = re.compile(
        r"\\includegraphics\[[^\]]*\bwidth\s*=\s*([0-9.]+)\s*\\textwidth[^\]]*\]\{([^}]+)\}"
    )
    for path in word_input_files(root):
        text = strip_latex_comment_lines(path.read_text(encoding="utf-8"))
        for match in pattern.finditer(text):
            factor = float(match.group(1))
            src = match.group(2)
            png_src = re.sub(r"\.pdf$", ".png", src)
            widths[png_src] = factor * TEXTWIDTH_INCHES
            widths[f".docx-build/pdf-images/{png_src}"] = factor * TEXTWIDTH_INCHES
    return widths


def style_image_paragraph(p_xml: str) -> str:
    ppr = (
        '<w:pPr><w:keepNext/>'
        '<w:spacing w:before="60" w:after="30" w:line="240" w:lineRule="auto"/>'
        '<w:ind w:firstLine="0" w:firstLineChars="0" w:left="0" w:right="0"/>'
        '<w:jc w:val="center"/></w:pPr>'
    )
    if "<w:pPr" in p_xml:
        return re.sub(r"<w:pPr\b.*?</w:pPr>", ppr, p_xml, count=1, flags=re.S)
    return re.sub(r"(<w:p\b[^>]*>)", r"\1" + ppr, p_xml, count=1)


def resize_inline_image(inline_xml: str, width_inches: float) -> str:
    extent = re.search(r'<wp:extent cx="(\d+)" cy="(\d+)"', inline_xml)
    if not extent:
        return inline_xml
    old_cx = int(extent.group(1))
    old_cy = int(extent.group(2))
    if old_cx <= 0:
        return inline_xml
    new_cx = int(width_inches * EMU_PER_INCH)
    new_cy = int(old_cy * new_cx / old_cx)
    inline_xml = re.sub(r'<wp:extent cx="\d+" cy="\d+"', f'<wp:extent cx="{new_cx}" cy="{new_cy}"', inline_xml, count=1)
    inline_xml = re.sub(r'<a:ext cx="\d+" cy="\d+"', f'<a:ext cx="{new_cx}" cy="{new_cy}"', inline_xml, count=1)
    return inline_xml


def style_document_images(body_xml: str, root: Path) -> str:
    image_widths = source_image_widths(root)

    def inline_repl(match: re.Match[str]) -> str:
        inline = match.group(0)
        descr = re.search(r'<pic:cNvPr\b[^>]*\bdescr="([^"]*)"', inline)
        if descr:
            src = unescape(descr.group(1))
            width = image_widths.get(src)
            if width is not None:
                inline = resize_inline_image(inline, width)
        return inline

    body_xml = re.sub(r"<wp:inline\b.*?</wp:inline>", inline_repl, body_xml, flags=re.S)

    def p_repl(match: re.Match[str]) -> str:
        p_xml = match.group(0)
        if "<w:drawing" not in p_xml:
            return p_xml
        return style_image_paragraph(p_xml)

    return re.sub(r"<w:p\b.*?</w:p>", p_repl, body_xml, flags=re.S)


def arrange_cross_model_heatmap_figure(body_xml: str) -> str:
    table_pattern = re.compile(
        r'(<w:bookmarkStart\b[^>]*\bw:name="fig:cross_model_heatmap_extra"[^>]*/>\s*)'
        r'(<w:tbl\b.*?</w:tbl>)',
        re.S,
    )

    def table_repl(match: re.Match[str]) -> str:
        tbl_xml = match.group(2)
        if tbl_xml.count("<w:drawing") != 3:
            return match.group(0)
        rows = re.findall(r"<w:tr\b.*?</w:tr>", tbl_xml, re.S)
        if len(rows) != 1:
            return match.group(0)
        cells = re.findall(r"<w:tc\b.*?</w:tc>", rows[0], re.S)
        if len(cells) != 3:
            return match.group(0)
        tbl_xml = re.sub(
            r"<w:tblGrid\b.*?</w:tblGrid>",
            '<w:tblGrid><w:gridCol w:w="4156"/><w:gridCol w:w="4156"/></w:tblGrid>',
            tbl_xml,
            count=1,
            flags=re.S,
        )
        tbl_xml = re.sub(r'<w:tblW\b[^>]*/>', '<w:tblW w:type="dxa" w:w="8312"/>', tbl_xml, count=1)
        third = cells[2]
        if "<w:tcPr" in third:
            third = re.sub(
                r"<w:tcPr\b[^>]*>.*?</w:tcPr>|<w:tcPr\s*/>",
                '<w:tcPr><w:gridSpan w:val="2"/></w:tcPr>',
                third,
                count=1,
                flags=re.S,
            )
        else:
            third = third.replace("<w:tc>", '<w:tc><w:tcPr><w:gridSpan w:val="2"/></w:tcPr>', 1)
        new_rows = f"<w:tr>{cells[0]}{cells[1]}</w:tr><w:tr>{third}</w:tr>"
        tbl_xml = re.sub(r"<w:tr\b.*?</w:tr>", new_rows, tbl_xml, count=1, flags=re.S)
        return match.group(1) + tbl_xml

    body_xml = table_pattern.sub(table_repl, body_xml)

    block_pattern = re.compile(r"<w:p\b.*?</w:p>|<w:tbl\b.*?</w:tbl>", re.S)
    blocks: list[str] = []
    pos = 0
    for match in block_pattern.finditer(body_xml):
        if match.start() > pos:
            blocks.append(body_xml[pos:match.start()])
        blocks.append(match.group(0))
        pos = match.end()
    if pos < len(body_xml):
        blocks.append(body_xml[pos:])

    for index, block in enumerate(blocks):
        if block.startswith("<w:p") and "fig:cross_model_heatmap_extra" in block and "<w:drawing" in block:
            following: list[int] = []
            scan = index + 1
            while scan < len(blocks) and len(following) < 2:
                if blocks[scan].startswith("<w:p"):
                    if "<w:drawing" not in blocks[scan]:
                        break
                    following.append(scan)
                elif blocks[scan].strip():
                    break
                scan += 1
            if len(following) < 2:
                return body_xml
            second_index, third_index = following
            first_inner = re.match(r"(<w:p\b[^>]*>)(.*)(</w:p>)", block, re.S)
            second_inner = re.match(r"<w:p\b[^>]*>(.*)</w:p>", blocks[second_index], re.S)
            if not first_inner or not second_inner:
                return body_xml
            spacer = '<w:r><w:t xml:space="preserve">  </w:t></w:r>'
            merged = f"{first_inner.group(1)}{first_inner.group(2)}{spacer}{second_inner.group(1)}{first_inner.group(3)}"
            blocks[index] = style_image_paragraph(merged)
            blocks[second_index] = style_image_paragraph(blocks[third_index])
            del blocks[third_index]
            return "".join(blocks)
    return body_xml


def style_figures(body_xml: str, root: Path) -> str:
    figure_info = source_figure_info(root)
    if not figure_info:
        return body_xml
    label_to_number = {label: number for label, (number, _title) in figure_info.items()}
    caption_to_number = {title: number for number, title in figure_info.values()}
    block_pattern = re.compile(r"<w:p\b.*?</w:p>|<w:tbl\b.*?</w:tbl>", re.S)

    def repl(match: re.Match[str]) -> str:
        block = match.group(0)
        if not block.startswith("<w:p"):
            return block
        title = plain_paragraph_text(block)
        number = caption_to_number.get(title)
        if number is None:
            return block
        return make_figure_caption_paragraph(block, number, title)

    body_xml = block_pattern.sub(repl, body_xml)
    return update_figure_crossrefs(body_xml, label_to_number)


def float_module_architecture_figure(body_xml: str) -> str:
    # LaTeX floats this large figure to the next page while allowing the
    # following explanation to fill the previous page. In Word, an inline
    # image would otherwise leave a large blank area before the figure.
    block_pattern = re.compile(r"<w:p\b.*?</w:p>|<w:tbl\b.*?</w:tbl>", re.S)
    blocks = block_pattern.findall(body_xml)
    if not blocks:
        return body_xml

    figure_start: int | None = None
    for index, block in enumerate(blocks):
        if block.startswith("<w:p") and "<w:drawing" in block and "fig:module_architecture" in block:
            figure_start = index
            break
    if figure_start is None:
        for index, block in enumerate(blocks):
            if (
                block.startswith("<w:p")
                and "桥接式压缩方法总体模块结构" in plain_paragraph_text(block)
                and index > 0
                and "<w:drawing" in blocks[index - 1]
            ):
                figure_start = index - 1
                break
    if figure_start is None or figure_start + 1 >= len(blocks):
        return body_xml

    caption_index = figure_start + 1
    figure_blocks = blocks[figure_start : caption_index + 1]
    remaining = blocks[:figure_start] + blocks[caption_index + 1 :]

    insert_at: int | None = None
    for index in range(figure_start, len(remaining)):
        if (
            remaining[index].startswith("<w:p")
            and "<m:oMath" in remaining[index]
            and "<w:tab" in remaining[index]
        ):
            insert_at = index
            break
    if insert_at is None:
        return body_xml

    return "".join(remaining[:insert_at] + figure_blocks + remaining[insert_at:])


def move_bibliography_before_acknowledgement(body_xml: str) -> str:
    # Pandoc citeproc appends the bibliography at the end of the converted
    # body. The LaTeX thesis orders references before acknowledgements.
    block_pattern = re.compile(r"<w:p\b.*?</w:p>|<w:tbl\b.*?</w:tbl>", re.S)
    pieces: list[str] = []
    pos = 0
    for match in block_pattern.finditer(body_xml):
        if match.start() > pos:
            pieces.append(body_xml[pos:match.start()])
        pieces.append(match.group(0))
        pos = match.end()
    if pos < len(body_xml):
        pieces.append(body_xml[pos:])

    ack_index: int | None = None
    refs_index: int | None = None
    for index, piece in enumerate(pieces):
        if not piece.startswith("<w:p"):
            continue
        compact_text = plain_paragraph_text(piece).replace(" ", "")
        if ack_index is None and compact_text == "致谢":
            ack_index = index
        if refs_index is None and compact_text == "参考文献":
            refs_index = index

    if ack_index is None or refs_index is None or refs_index < ack_index:
        return body_xml

    refs_chunk = pieces[refs_index:]
    before_refs = pieces[:refs_index]
    return "".join(before_refs[:ack_index] + refs_chunk + before_refs[ack_index:])


def suppress_heading_numbering(p_xml: str) -> str:
    wrapped = f'<root xmlns:w="{W_NS}" xmlns:r="{R_NS}" xmlns:m="{M_NS}" xmlns:w14="{W14_NS}">{p_xml}</root>'
    root = ET.fromstring(wrapped)
    p = root[0]
    ppr = ensure_child(p, w("pPr"), first=True)
    remove_children(ppr, w("numPr"))
    num_pr = ET.Element(w("numPr"))
    ilvl = ET.Element(w("ilvl"))
    ilvl.set(w("val"), "0")
    num_id = ET.Element(w("numId"))
    num_id.set(w("val"), "0")
    num_pr.extend([ilvl, num_id])
    ppr.append(num_pr)
    return ET.tostring(p, encoding="unicode")


def style_back_matter_headings(body_xml: str) -> str:
    block_pattern = re.compile(r"<w:p\b.*?</w:p>|<w:tbl\b.*?</w:tbl>", re.S)

    def repl(match: re.Match[str]) -> str:
        block = match.group(0)
        if not block.startswith("<w:p"):
            return block
        compact_text = plain_paragraph_text(block).replace(" ", "")
        if compact_text in {"参考文献", "致谢"}:
            return suppress_heading_numbering(block)
        return block

    return block_pattern.sub(repl, body_xml)


def style_thesis_tables(body_xml: str, root: Path) -> str:
    block_pattern = re.compile(r"<w:p\b.*?</w:p>|<w:tbl\b.*?</w:tbl>", re.S)
    out: list[str] = []
    label_to_number: dict[str, str] = {}
    label_to_alignment = source_table_alignments(root)
    width_overrides = source_table_width_overrides(root)
    chapter = 0
    chapter_table_counts: dict[int, int] = {}
    pos = 0

    for match in block_pattern.finditer(body_xml):
        out.append(body_xml[pos:match.start()])
        block = match.group(0)
        if block.startswith("<w:p"):
            if is_body_heading1(block):
                chapter += 1
            out.append(block)
        elif block.startswith("<w:tbl"):
            caption_index = next((i for i in range(len(out) - 1, -1, -1) if out[i].startswith("<w:p")), None)
            caption_p = out[caption_index] if caption_index is not None else ""
            label = paragraph_bookmark_name(caption_p) if caption_p else None
            if label is None:
                recent = "".join(out[-8:])
                labels = re.findall(r'<w:bookmarkStart\b[^>]*\bw:name="(chart:[^"]+)"', recent)
                label = unescape(labels[-1]) if labels else None
            title = table_caption_value(block)
            row_count = len(re.findall(r"<w:tr\b", block))
            if label and label.startswith("chart:") and title and row_count > 1 and chapter > 0:
                chapter_table_counts[chapter] = chapter_table_counts.get(chapter, 0) + 1
                table_number = f"{chapter}-{chapter_table_counts[chapter]}"
                label_to_number[label] = table_number
                out[caption_index] = make_table_caption_paragraph(caption_p, table_number, title)
                block = style_table_xml(
                    block,
                    table_number,
                    title,
                    label_to_alignment.get(label),
                    label,
                    width_overrides.get(label),
                )
            out.append(block)
        pos = match.end()
    out.append(body_xml[pos:])
    styled = "".join(out)
    return update_table_crossrefs(styled, label_to_number)


def merge_content_types(template_zip: zipfile.ZipFile, body_zip: zipfile.ZipFile) -> bytes:
    tpl = ET.fromstring(template_zip.read("[Content_Types].xml"))
    body = ET.fromstring(body_zip.read("[Content_Types].xml"))
    existing = {el.attrib["Extension"] for el in tpl.findall(f"{{{CT_NS}}}Default")}
    for default in body.findall(f"{{{CT_NS}}}Default"):
        if default.attrib["Extension"] not in existing:
            tpl.append(default)
            existing.add(default.attrib["Extension"])
    return ET.tostring(tpl, encoding="utf-8", xml_declaration=True)


def merge_relationships(
    template_zip: zipfile.ZipFile,
    body_zip: zipfile.ZipFile,
    body_xml: str,
) -> tuple[bytes, str, dict[str, bytes]]:
    tpl = ET.fromstring(template_zip.read("word/_rels/document.xml.rels"))
    body = ET.fromstring(body_zip.read("word/_rels/document.xml.rels"))
    body_rels = {el.attrib["Id"]: el for el in body}
    used = set(re.findall(r'r:(?:id|embed|link)="([^"]+)"', body_xml))
    existing = {el.attrib["Id"] for el in tpl}
    next_num = 1000
    copied: dict[str, bytes] = {}

    for old_id in sorted(used):
        rel = body_rels.get(old_id)
        if rel is None:
            continue
        while f"rId{next_num}" in existing:
            next_num += 1
        new_id = f"rId{next_num}"
        existing.add(new_id)
        next_num += 1

        new_rel = ET.Element(f"{{{REL_NS}}}Relationship", rel.attrib)
        new_rel.set("Id", new_id)
        target = new_rel.attrib.get("Target", "")
        if new_rel.attrib.get("TargetMode") != "External" and target.startswith("media/"):
            src = "word/" + target
            ext = Path(target).suffix
            dst = f"media/pandoc_{new_id}{ext}"
            new_rel.set("Target", dst)
            copied["word/" + dst] = body_zip.read(src)
        tpl.append(new_rel)
        body_xml = re.sub(rf'="{re.escape(old_id)}"', f'="{new_id}"', body_xml)

    return ET.tostring(tpl, encoding="utf-8", xml_declaration=True), body_xml, copied


def enable_update_fields(settings_xml: bytes) -> bytes:
    text = settings_xml.decode("utf-8")
    if "<w:updateFields" in text:
        text = re.sub(r"<w:updateFields\b[^/]*/>", '<w:updateFields w:val="true"/>', text)
    else:
        text = text.replace("</w:settings>", '<w:updateFields w:val="true"/></w:settings>')
    if "<w:autoHyphenation" in text:
        text = re.sub(r"<w:autoHyphenation\b[^/]*/>", '<w:autoHyphenation w:val="false"/>', text)
    else:
        text = text.replace("</w:settings>", '<w:autoHyphenation w:val="false"/></w:settings>')
    return text.encode("utf-8")


def disable_midword_latin_wrap(xml: str) -> str:
    # In Chinese Word layouts, w:wordWrap allows Latin text to wrap in the
    # middle of a word. Removing it keeps English words intact; existing
    # hyphen characters remain valid line-break opportunities.
    return re.sub(r"<w:wordWrap\b[^/]*/>", "", xml)


def build(template_path: Path, body_path: Path, output_path: Path, main_tex: Path) -> None:
    meta = parse_main_metadata(main_tex)
    with zipfile.ZipFile(template_path) as template_zip, zipfile.ZipFile(body_path) as body_zip:
        template_xml = read_text(template_zip, "word/document.xml")
        template_xml = add_missing_doc_namespaces(template_xml)

        replacements = {
            "XXX系统的设计与实现": meta.get("title", ""),
            "计算机科学与技术": meta.get("school", ""),
            "计科2201": meta.get("classnum", ""),
            "小岳岳": meta.get("author", ""),
            "U202215102": meta.get("stunum", ""),
            "郭德纲": meta.get("instructor", ""),
        }
        for old, new in replacements.items():
            if new:
                template_xml = template_xml.replace(old, new)
        if meta.get("date"):
            template_xml = template_xml.replace("[状态]", meta["date"], 1)

        abstract_marker = template_xml.find("<w:t>摘</w:t>")
        if abstract_marker < 0:
            raise RuntimeError("Could not find template abstract heading")
        content_start = paragraph_start_before(template_xml, abstract_marker)
        prefix = template_xml[:content_start]
        suffix = ensure_body_page_numbering(final_sectpr_suffix(template_xml))
        section_breaks = extract_front_section_breaks(template_xml, content_start)

        body_xml = body_fragment_without_final_sectpr(read_text(body_zip, "word/document.xml"))
        body_xml = demote_abstract_headings(body_xml)
        body_xml = insert_front_matter(body_xml, section_breaks)
        body_xml = fix_custom_numbered_lists(body_xml, custom_list_item_counts(main_tex.parent))
        body_xml = fix_equation_numbering(body_xml, main_tex.parent)
        body_xml = style_algorithms(body_xml, main_tex.parent)
        body_xml = style_document_images(body_xml, main_tex.parent)
        body_xml = arrange_cross_model_heatmap_figure(body_xml)
        body_xml = style_figures(body_xml, main_tex.parent)
        body_xml = style_thesis_tables(body_xml, main_tex.parent)
        body_xml = move_bibliography_before_acknowledgement(body_xml)
        body_xml = style_back_matter_headings(body_xml)
        rels_xml, body_xml, copied_files = merge_relationships(template_zip, body_zip, body_xml)
        document_xml = disable_midword_latin_wrap(prefix + body_xml + suffix).encode("utf-8")

        replacements_xml = {
            "[Content_Types].xml": merge_content_types(template_zip, body_zip),
            "word/document.xml": document_xml,
            "word/_rels/document.xml.rels": rels_xml,
            "word/settings.xml": enable_update_fields(template_zip.read("word/settings.xml")),
        }
        for name in ("word/styles.xml", "word/numbering.xml"):
            if name in body_zip.namelist():
                data = body_zip.read(name)
                if name == "word/styles.xml":
                    data = disable_midword_latin_wrap(data.decode("utf-8")).encode("utf-8")
                replacements_xml[name] = data

        tmp = output_path.with_suffix(output_path.suffix + ".tmp")
        if tmp.exists():
            tmp.unlink()
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as out:
            written: set[str] = set()
            for item in template_zip.infolist():
                data = replacements_xml.get(item.filename)
                if data is None:
                    data = template_zip.read(item.filename)
                out.writestr(item, data)
                written.add(item.filename)
            for name, data in copied_files.items():
                if name not in written:
                    out.writestr(name, data)
        shutil.move(str(tmp), str(output_path))


def main() -> int:
    if len(sys.argv) != 5:
        print("Usage: build_hust_docx_package.py TEMPLATE_DOCX BODY_DOCX OUTPUT_DOCX MAIN_TEX", file=sys.stderr)
        return 2
    build(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
