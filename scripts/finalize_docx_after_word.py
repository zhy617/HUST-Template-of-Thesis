from __future__ import annotations

import re
import shutil
import sys
import zipfile
from pathlib import Path
from html import unescape


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
PARA_RE = re.compile(r"(<w:p\b[^>]*>)(.*?)(</w:p>)", re.S)
PPR_RE = re.compile(r"(<w:pPr\b[^>]*>)(.*?)(</w:pPr>)", re.S)
RPR_RE = re.compile(r"(<w:rPr\b[^>]*>)(.*?)(</w:rPr>)", re.S)
REF_HYPERLINK_RE = re.compile(r'(<w:hyperlink\b[^>]*\bw:anchor="ref-[^"]*"[^>]*>)(.*?)(</w:hyperlink>)', re.S)
CROSSREF_HYPERLINK_RE = re.compile(
    r'(<w:hyperlink\b[^>]*\bw:anchor="(?:eq|fig|chart|al):[^"]*"[^>]*>)(.*?)(</w:hyperlink>)',
    re.S,
)
SPACING_RE = re.compile(r"<w:spacing\b[^>]*/>", re.S)
IND_RE = re.compile(r"<w:ind\b[^>]*/>", re.S)
SIZE_RE = re.compile(r"<w:sz(?:Cs)?\b[^>]*/>", re.S)
VERT_ALIGN_RE = re.compile(r"<w:vertAlign\b[^>]*/>", re.S)
RSTYLE_RE = re.compile(r"<w:rStyle\b[^>]*/>", re.S)
COLOR_RE = re.compile(r"<w:color\b[^>]*/>", re.S)
UNDERLINE_RE = re.compile(r"<w:u\b[^>]*/>", re.S)
TEXT_RE = re.compile(r"<w:t\b[^>]*>(.*?)</w:t>", re.S)
RUN_RE = re.compile(r"(<w:r\b[^>]*>)(.*?)(</w:r>)", re.S)
EQUATION_SPACING = '<w:spacing w:before="180" w:after="180" w:line="240" w:lineRule="auto"/>'
BODY_SIZE = '<w:sz w:val="24"/><w:szCs w:val="24"/>'
TABLE_SIZE = '<w:sz w:val="21"/><w:szCs w:val="21"/>'
ALGORITHM_SIZE = '<w:sz w:val="22"/><w:szCs w:val="22"/>'
CROSSREF_STYLE = '<w:color w:val="000000"/><w:u w:val="none"/>'
EQUATION_INDENT = '<w:ind w:firstLine="0" w:firstLineChars="0" w:left="0" w:right="0"/>'
EQUATION_TABS = '<w:tabs><w:tab w:val="center" w:pos="4145"/><w:tab w:val="right" w:pos="8290"/></w:tabs>'
INLINE_MATH_SPACE = '<w:r><w:t xml:space="preserve"> </w:t></w:r>'
INLINE_MATH_INNER_SPACE = '<m:r><m:t xml:space="preserve"> </m:t></m:r>'
TABLE_PARAGRAPH_INDENT = '<w:ind w:firstLine="0" w:firstLineChars="0" w:left="0" w:right="0"/>'
TABLE_RUN_FONTS = '<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="宋体" w:cs="Times New Roman"/>'
CUSTOM_LIST_RUN_FONTS = '<w:rFonts w:ascii="宋体" w:hAnsi="宋体" w:eastAsia="宋体" w:cs="宋体" w:hint="eastAsia"/>'
CIRCLED_NUMBER_FONTS = CUSTOM_LIST_RUN_FONTS
CIRCLED_NUMBER_RE = re.compile(r"[\u2460-\u2473]")


def paragraph_text(xml: str) -> str:
    return unescape("".join(TEXT_RE.findall(xml))).strip()


def has_math(xml: str) -> bool:
    return "<m:oMath" in xml or "<m:oMathPara" in xml


def patch_paragraph_spacing(inner: str) -> str:
    ppr_match = PPR_RE.search(inner)
    if ppr_match:
        body = SPACING_RE.sub("", ppr_match.group(2))
        patched_ppr = f"{ppr_match.group(1)}{body}{EQUATION_SPACING}{ppr_match.group(3)}"
        return inner[: ppr_match.start()] + patched_ppr + inner[ppr_match.end() :]
    return f"<w:pPr>{EQUATION_SPACING}</w:pPr>{inner}"


def patch_equation_layout(inner: str) -> str:
    ppr_match = PPR_RE.search(inner)
    if ppr_match:
        body = SPACING_RE.sub("", ppr_match.group(2))
        body = re.sub(r"<w:ind\b[^>]*/>", "", body)
        body = re.sub(r"<w:tabs\b.*?</w:tabs>", "", body, flags=re.S)
        body = re.sub(r"<w:jc\b[^>]*/>", "", body)
        patched_ppr = (
            f"{ppr_match.group(1)}{body}{EQUATION_TABS}{EQUATION_INDENT}"
            f"{EQUATION_SPACING}{ppr_match.group(3)}"
        )
        inner = inner[: ppr_match.start()] + patched_ppr + inner[ppr_match.end() :]
    else:
        inner = f"<w:pPr>{EQUATION_TABS}{EQUATION_INDENT}{EQUATION_SPACING}</w:pPr>{inner}"

    math_pos = inner.find("<m:oMath")
    if math_pos >= 0:
        before_math = inner[:math_pos]
        after_ppr = before_math.rfind("</w:pPr>")
        check_region = before_math[after_ppr + len("</w:pPr>") :] if after_ppr >= 0 else before_math
        if "<w:tab" not in check_region:
            inner = inner[:math_pos] + "<w:r><w:tab/></w:r>" + inner[math_pos:]
    return inner


def patch_inline_math_spacing(inner: str) -> str:
    if "<m:oMath" not in inner:
        return inner
    if re.search(r"\(\d+-\d+\)\s*$", paragraph_text(inner)):
        return inner

    def strip_trailing_external_space(text: str) -> str:
        while text.endswith(INLINE_MATH_SPACE):
            text = text[: -len(INLINE_MATH_SPACE)]
        return text

    def strip_leading_external_space(text: str) -> str:
        while text.startswith(INLINE_MATH_SPACE):
            text = text[len(INLINE_MATH_SPACE) :]
        return text

    def patch_math_box(math_xml: str) -> str:
        open_match = re.match(r"(<m:oMath\b[^>]*>)", math_xml)
        if not open_match or not math_xml.endswith("</m:oMath>"):
            return math_xml
        start = open_match.group(1)
        body = math_xml[len(start) : -len("</m:oMath>")]
        while body.startswith(INLINE_MATH_INNER_SPACE):
            body = body[len(INLINE_MATH_INNER_SPACE) :]
        while body.endswith(INLINE_MATH_INNER_SPACE):
            body = body[: -len(INLINE_MATH_INNER_SPACE)]
        return f"{start}{INLINE_MATH_INNER_SPACE}{body}{INLINE_MATH_INNER_SPACE}</m:oMath>"

    pattern = re.compile(r"<m:oMath\b.*?</m:oMath>", re.S)
    out: list[str] = []
    pos = 0
    for match in pattern.finditer(inner):
        out.append(strip_trailing_external_space(inner[pos : match.start()]))
        out.append(patch_math_box(match.group(0)))
        if inner[match.end() :].startswith(INLINE_MATH_SPACE):
            pos = match.end() + len(INLINE_MATH_SPACE)
        else:
            pos = match.end()
        if pos < len(inner):
            tail = inner[pos:]
            stripped = strip_leading_external_space(tail)
            if len(stripped) != len(tail):
                pos += len(tail) - len(stripped)
    out.append(inner[pos:])
    return "".join(out)


def patch_rpr_size(rpr_xml: str, size_xml: str) -> str:
    match = RPR_RE.fullmatch(rpr_xml)
    if not match:
        return rpr_xml
    body = SIZE_RE.sub("", match.group(2))
    return f"{match.group(1)}{body}{size_xml}{match.group(3)}"


def patch_caption_body_size(inner: str, size_xml: str = BODY_SIZE) -> str:
    ppr_match = PPR_RE.search(inner)
    if ppr_match:
        ppr_body = ppr_match.group(2)
        rpr_match = RPR_RE.search(ppr_body)
        if rpr_match:
            patched_rpr = patch_rpr_size(rpr_match.group(0), size_xml)
            ppr_body = ppr_body[: rpr_match.start()] + patched_rpr + ppr_body[rpr_match.end() :]
        else:
            ppr_body = f"{ppr_body}<w:rPr>{size_xml}</w:rPr>"
        patched_ppr = f"{ppr_match.group(1)}{ppr_body}{ppr_match.group(3)}"
        inner = inner[: ppr_match.start()] + patched_ppr + inner[ppr_match.end() :]
    else:
        inner = f"<w:pPr><w:rPr>{size_xml}</w:rPr></w:pPr>{inner}"
    return RPR_RE.sub(lambda m: patch_rpr_size(m.group(0), size_xml), inner)


def patch_citation_hyperlink_superscript(xml: str) -> str:
    def patch_run(run_match: re.Match[str]) -> str:
        run = run_match.group(0)
        rpr_match = RPR_RE.search(run)
        if rpr_match:
            body = RSTYLE_RE.sub("", rpr_match.group(2))
            body = COLOR_RE.sub("", body)
            body = UNDERLINE_RE.sub("", body)
            body = VERT_ALIGN_RE.sub("", body)
            rpr = (
                f'{rpr_match.group(1)}{body}{CROSSREF_STYLE}'
                '<w:vertAlign w:val="superscript"/>'
                f"{rpr_match.group(3)}"
            )
            return run[: rpr_match.start()] + rpr + run[rpr_match.end() :]
        return run.replace("<w:r>", f'<w:r><w:rPr>{CROSSREF_STYLE}<w:vertAlign w:val="superscript"/></w:rPr>', 1)

    def repl(match: re.Match[str]) -> str:
        start, inner, end = match.groups()
        visible = paragraph_text(inner)
        if not re.fullmatch(r"\[\d+(?:,\d+)*\]", visible):
            return match.group(0)
        inner = re.sub(r"<w:r\b[^>]*>.*?</w:r>", patch_run, inner, flags=re.S)
        return f"{start}{inner}{end}"

    return REF_HYPERLINK_RE.sub(repl, xml)


def patch_plain_crossref_hyperlink_style(xml: str) -> str:
    def patch_run(run_match: re.Match[str]) -> str:
        run = run_match.group(0)
        rpr_match = RPR_RE.search(run)
        if rpr_match:
            body = RSTYLE_RE.sub("", rpr_match.group(2))
            body = COLOR_RE.sub("", body)
            body = UNDERLINE_RE.sub("", body)
            rpr = f"{rpr_match.group(1)}{body}{CROSSREF_STYLE}{rpr_match.group(3)}"
            return run[: rpr_match.start()] + rpr + run[rpr_match.end() :]
        return re.sub(
            r"(<w:r\b[^>]*>)",
            r"\1<w:rPr>" + CROSSREF_STYLE + r"</w:rPr>",
            run,
            count=1,
        )

    def repl(match: re.Match[str]) -> str:
        start, inner, end = match.groups()
        inner = re.sub(r"<w:r\b[^>]*>.*?</w:r>", patch_run, inner, flags=re.S)
        return f"{start}{inner}{end}"

    return CROSSREF_HYPERLINK_RE.sub(repl, xml)


def patch_reference_external_hyperlink_style(xml: str) -> str:
    def patch_run(run_match: re.Match[str]) -> str:
        run = run_match.group(0)
        rpr_match = RPR_RE.search(run)
        if rpr_match:
            body = RSTYLE_RE.sub("", rpr_match.group(2))
            body = COLOR_RE.sub("", body)
            body = UNDERLINE_RE.sub("", body)
            rpr = f"{rpr_match.group(1)}{body}{CROSSREF_STYLE}{rpr_match.group(3)}"
            return run[: rpr_match.start()] + rpr + run[rpr_match.end() :]
        return re.sub(
            r"(<w:r\b[^>]*>)",
            r"\1<w:rPr>" + CROSSREF_STYLE + r"</w:rPr>",
            run,
            count=1,
        )

    def patch_para(match: re.Match[str]) -> str:
        start, inner, end = match.groups()
        if not re.match(r"\[\d+\]", paragraph_text(inner)):
            return match.group(0)

        def patch_link(link_match: re.Match[str]) -> str:
            link = link_match.group(0)
            if "w:anchor=" in link:
                return link
            return re.sub(r"<w:r\b[^>]*>.*?</w:r>", patch_run, link, flags=re.S)

        inner = re.sub(r"<w:hyperlink\b[^>]*>.*?</w:hyperlink>", patch_link, inner, flags=re.S)
        return f"{start}{inner}{end}"

    return PARA_RE.sub(patch_para, xml)


def patch_table_paragraph_indents(xml: str) -> str:
    def patch_ppr(match: re.Match[str]) -> str:
        body = IND_RE.sub("", match.group(2))
        return f"{match.group(1)}{body}{TABLE_PARAGRAPH_INDENT}{match.group(3)}"

    def patch_para(match: re.Match[str]) -> str:
        start, inner, end = match.groups()
        ppr_match = PPR_RE.search(inner)
        if ppr_match:
            inner = inner[: ppr_match.start()] + patch_ppr(ppr_match) + inner[ppr_match.end() :]
        else:
            inner = f"<w:pPr>{TABLE_PARAGRAPH_INDENT}</w:pPr>{inner}"
        return f"{start}{inner}{end}"

    def patch_table(match: re.Match[str]) -> str:
        return PARA_RE.sub(patch_para, match.group(0))

    return re.sub(r"<w:tbl\b.*?</w:tbl>", patch_table, xml, flags=re.S)


def patch_table_run_fonts(xml: str) -> str:
    def patch_run(match: re.Match[str]) -> str:
        return patch_run_with_default(match, "21")

    def patch_run_with_default(match: re.Match[str], default_size: str) -> str:
        start, inner, end = match.groups()
        if "<w:drawing" in inner:
            return match.group(0)
        size_match = re.search(r'<w:sz\b[^>]*\bw:val="(\d+)"[^>]*/>', inner)
        size_val = size_match.group(1) if size_match else default_size
        size_xml = f'<w:sz w:val="{size_val}"/><w:szCs w:val="{size_val}"/>'
        rpr_match = RPR_RE.search(inner)
        if rpr_match:
            body = RSTYLE_RE.sub("", rpr_match.group(2))
            body = re.sub(r"<w:rFonts\b[^>]*/>", "", body)
            body = SIZE_RE.sub("", body)
            patched = f"{rpr_match.group(1)}{TABLE_RUN_FONTS}{body}{size_xml}{rpr_match.group(3)}"
            inner = inner[: rpr_match.start()] + patched + inner[rpr_match.end() :]
        else:
            inner = f"<w:rPr>{TABLE_RUN_FONTS}{size_xml}</w:rPr>{inner}"
        return f"{start}{inner}{end}"

    def patch_table(match: re.Match[str]) -> str:
        table = match.group(0)
        table_text = unescape("".join(TEXT_RE.findall(table)))
        default_size = "22" if re.search(r"算法\s+\d+-\d+\s+\S", table_text) else "21"
        return RUN_RE.sub(lambda run_match: patch_run_with_default(run_match, default_size), table)

    return re.sub(r"<w:tbl\b.*?</w:tbl>", patch_table, xml, flags=re.S)


def patch_body_tables_only(xml: str) -> str:
    markers = ['w:name="摘-要"', "<w:t>Abstract</w:t>", 'w:name="abstract"']
    positions = [xml.find(marker) for marker in markers if xml.find(marker) >= 0]
    if not positions:
        return patch_table_run_fonts(patch_table_paragraph_indents(xml))
    start = min(positions)
    prefix = xml[:start]
    suffix = xml[start:]
    suffix = patch_table_paragraph_indents(suffix)
    suffix = patch_table_run_fonts(suffix)
    return prefix + suffix


def patch_circled_number_fonts(xml: str) -> str:
    def patch_run(match: re.Match[str]) -> str:
        start, inner, end = match.groups()
        visible_text = unescape("".join(TEXT_RE.findall(inner)))
        if not CIRCLED_NUMBER_RE.search(visible_text):
            return match.group(0)

        rpr_match = RPR_RE.search(inner)
        if rpr_match:
            body = re.sub(r"<w:rFonts\b[^>]*/>", "", rpr_match.group(2))
            patched = f"{rpr_match.group(1)}{CIRCLED_NUMBER_FONTS}{body}{rpr_match.group(3)}"
            inner = inner[: rpr_match.start()] + patched + inner[rpr_match.end() :]
        else:
            inner = f"<w:rPr>{CIRCLED_NUMBER_FONTS}</w:rPr>{inner}"
        return f"{start}{inner}{end}"

    return RUN_RE.sub(patch_run, xml)


def patch_custom_list_fonts(xml: str) -> str:
    def patch_run(run_match: re.Match[str]) -> str:
        start, inner, end = run_match.groups()
        rpr_match = RPR_RE.search(inner)
        if rpr_match:
            body = re.sub(r"<w:rFonts\b[^>]*/>", "", rpr_match.group(2))
            body = re.sub(r"<w:b(?:Cs)?\b[^>]*/>", "", body)
            patched = f"{rpr_match.group(1)}{CUSTOM_LIST_RUN_FONTS}{body}{rpr_match.group(3)}"
            inner = inner[: rpr_match.start()] + patched + inner[rpr_match.end() :]
        else:
            inner = f"<w:rPr>{CUSTOM_LIST_RUN_FONTS}</w:rPr>{inner}"
        return f"{start}{inner}{end}"

    def patch_para(match: re.Match[str]) -> str:
        start, inner, end = match.groups()
        text = paragraph_text(inner).replace(" ", "")
        if not re.match(r"^(?:[（(]\d+[）)]|[\u2460-\u2473]|[A-Z]三级列表)", text):
            return match.group(0)
        inner = RUN_RE.sub(patch_run, inner)
        return f"{start}{inner}{end}"

    return PARA_RE.sub(patch_para, xml)


def patch_document_xml(data: bytes) -> bytes:
    text = data.decode("utf-8")

    def repl(match: re.Match[str]) -> str:
        start, inner, end = match.groups()
        if has_math(inner) and re.search(r"\(\d+-\d+\)\s*$", paragraph_text(inner)):
            inner = patch_equation_layout(inner)
        elif re.match(r"表\s+\d+-\d+\s+\S", paragraph_text(inner)):
            inner = patch_caption_body_size(inner, TABLE_SIZE)
        elif re.match(r"算法\s+\d+-\d+\s+\S", paragraph_text(inner)):
            inner = patch_caption_body_size(inner, ALGORITHM_SIZE)
        elif re.match(r"图\s+\d+-\d+\s+\S", paragraph_text(inner)):
            inner = patch_caption_body_size(inner, BODY_SIZE)
        elif has_math(inner):
            inner = patch_inline_math_spacing(inner)
        return f"{start}{inner}{end}"

    text = PARA_RE.sub(repl, text)
    text = patch_plain_crossref_hyperlink_style(text)
    text = patch_citation_hyperlink_superscript(text)
    text = patch_reference_external_hyperlink_style(text)
    text = patch_body_tables_only(text)
    text = patch_circled_number_fonts(text)
    text = patch_custom_list_fonts(text)
    return text.encode("utf-8")


def patch_settings_xml(data: bytes) -> bytes:
    text = data.decode("utf-8")
    if "<w:updateFields" in text:
        text = re.sub(r"<w:updateFields\b[^/]*/>", '<w:updateFields w:val="false"/>', text)
    else:
        text = text.replace("</w:settings>", '<w:updateFields w:val="false"/></w:settings>')
    if "<w:autoHyphenation" in text:
        text = re.sub(r"<w:autoHyphenation\b[^/]*/>", '<w:autoHyphenation w:val="false"/>', text)
    else:
        text = text.replace("</w:settings>", '<w:autoHyphenation w:val="false"/></w:settings>')
    return text.encode("utf-8")


def finalize_docx(path: Path) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    if tmp.exists():
        tmp.unlink()
    with zipfile.ZipFile(path, "r") as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as out:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "word/document.xml":
                data = patch_document_xml(data)
            elif item.filename == "word/settings.xml":
                data = patch_settings_xml(data)
            out.writestr(item, data)
    shutil.move(str(tmp), str(path))


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: finalize_docx_after_word.py DOCX_PATH", file=sys.stderr)
        return 2
    finalize_docx(Path(sys.argv[1]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
