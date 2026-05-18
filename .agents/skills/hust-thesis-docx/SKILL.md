---
name: hust-thesis-docx
description: Convert or repair this HUST undergraduate thesis LaTeX project into a Word DOCX using hust-template.docx. Use for Pandoc DOCX regeneration, template front matter, TOC/page-number fixes, equations, tables, custom lists, references, and repeated thesis formatting iterations.
---

# HUST Thesis DOCX

Use this skill for `C:\Users\13183\Documents\Repositories\HUST-Thesis-of-Undergraduate`, the reusable template repo `C:\Users\13183\Documents\Repositories\HUST-Template-of-Thesis`, or a shared copy of the same HUST undergraduate LaTeX thesis template.

Always keep a single user-facing deliverable, preferably `main.docx`. Do not create many stage-named DOCX files unless debugging requires it. If a DOCX is open in Word, write to `main-next.docx` temporarily, then ask the user to close Word before replacing it.

## Standard Workflow

For the reusable template repo, prefer the wrapped one-command pipeline:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\convert_to_docx.ps1
```

Use manual steps below when debugging a specific stage or working in an older thesis copy without the wrapper.

1. Prepare Pandoc inputs and generate the Pandoc body:

```powershell
python scripts\prepare_docx_image_fallbacks.py
python scripts\expand_algorithms_for_pandoc.py word.tex .docx-build\word-expanded.tex
pandoc .docx-build\word-expanded.tex -o .docx-build\body.docx --reference-doc=hust-template.docx --lua-filter=pandoc-image-fallback.lua --resource-path='.;images;.docx-build/pdf-images' --bibliography=ref.bib --citeproc --csl=numeric-superscript-brackets.csl -M link-citations=true -M reference-section-title=参考文献
```

2. Package the final DOCX:

```powershell
python scripts\build_hust_docx_package.py hust-template.docx .docx-build\body.docx main.docx main.tex
```

3. Fill cover placeholders with Word COM:

```powershell
powershell -ExecutionPolicy Bypass -Command "& { `$script = Get-Content -Raw -Encoding UTF8 'scripts\fill_cover_word.ps1'; `$block = [scriptblock]::Create(`$script); & `$block -Docx 'main.docx' }"
```

4. Update the TOC and fields with Word COM:

```powershell
$path=(Resolve-Path 'main.docx').Path; $word=New-Object -ComObject Word.Application; $word.Visible=$false; $word.DisplayAlerts=0; try { $doc=$word.Documents.Open($path); foreach($toc in $doc.TablesOfContents){ $toc.Update() | Out-Null }; $doc.Fields.Update() | Out-Null; $doc.Save(); $doc.Close($false) } finally { $word.Quit() }
```

5. Run the final DOCX patch after Word saves. This is intentionally last because Word may remove `w:autoHyphenation` and displayed-equation paragraph spacing when it updates fields:

```powershell
python scripts\finalize_docx_after_word.py main.docx
```

## Required Fixes

Keep these fixes in `scripts/build_hust_docx_package.py` and update this skill whenever a new recurring fix is added.

- Preserve the template cover and originality/authorization pages from `hust-template.docx`.
- Insert front matter in template order: cover, authorization, Chinese abstract, English abstract, TOC, body.
- Do not hard-code the first chapter title as `绪论`; find the first numbered Heading 1 paragraph after abstracts. Shared templates may rename chapter 1.
- Force a real page break between the English abstract and the TOC; the TOC must not begin on the same page as `Keywords`.
- Include `摘 要` and `Abstract` in the TOC via `w:outlineLvl=0`, but do not assign them chapter numbering.
- Use TOC field `TOC \o "1-2" \h \z \u`; do not include third-level headings.
- Set the TOC title `目  录` and abstract titles to the same visual style as body Heading 1: 黑体, bold, 18 pt, centered.
- Reset body page numbering to decimal page 1 after front matter; abstract/TOC pages remain Roman.
- Remove `w:wordWrap` globally and set `w:autoHyphenation w:val="false"` so Latin text does not break mid-word. Existing hyphens remain valid break points.
- Convert Pandoc math to Word equations and avoid raw `\begin{equation}` text in the DOCX.
- Use `numeric-superscript-brackets.csl` with `--citeproc -M link-citations=true` so bibliography citations render as superscript square-bracket numbers, e.g. `LLaVA[1]`, and link to the numbered reference list.
- Reapply citation hyperlink superscript in `scripts\finalize_docx_after_word.py` so the whole bracketed citation `[n]`, including `[` and `]`, is superscript after Word saves. Citation hyperlinks to `ref-*` must also look like normal black text with `w:u w:val="none"` and no Word hyperlink run style;正文文献引用 must not show blue or underlined text.
- Strip visible hyperlink styling from bibliography external links in `scripts\finalize_docx_after_word.py`: reference-list titles/DOIs/URLs may keep their `r:id` target, but their runs must be black with `w:u w:val="none"` and no `w:rStyle` hyperlink style. The reference list should not contain blue underlined text.
- Number displayed equations by chapter from LaTeX source order, replace `式 [eq:...]` with visible references like `式 4-1`, and append right-side equation numbers like `(4-1)` to displayed equation paragraphs.
- Add displayed-equation paragraph spacing to mimic LaTeX vertical separation from body text; use Word paragraph spacing around equation paragraphs rather than inserting literal spaces into the math object. Reapply this in `scripts\finalize_docx_after_word.py` after Word field/TOC updates, because Word may strip the spacing on save.
- Reapply table caption run sizes in `scripts\finalize_docx_after_word.py` after Word saves; Word may keep only `w:szCs`, so final captions must have both `w:sz=24` and `w:szCs=24` while table body cells keep their smaller table size.
- Reapply zero paragraph indentation inside正文 table cells in `scripts\finalize_docx_after_word.py` after Word saves. Word may reintroduce body-style first-line indentation such as `w:firstLine="400"` inside table cells; this consumes numeric-column width and makes values such as `35.2` wrap into `35.` plus `2`. This finalizer patch must start at/after the `摘-要` bookmark and must not touch the template cover/originality front-matter tables.
- Reapply正文 table run font declarations in `scripts\finalize_docx_after_word.py` after Word saves. Table runs must declare `w:ascii`, `w:hAnsi`, and `w:cs` as Times New Roman, `w:eastAsia` as 宋体, and must include both `w:sz` and `w:szCs`; Word may otherwise leave only `w:cs` or strip one size declaration, making Latin/digit text look inconsistent. Do not apply this to cover/originality template tables.
- Turn table captions into `表 章号-序号 表名`, placed above the table, centered, bold, and the same size as正文; keep table body font sizes unchanged.
- Update `\tabref` so the visible正文 cross-reference is the full chapter-local text, such as `表 3-2`. In this project Pandoc's macro emits the `表` prefix outside the hyperlink, so the hyperlink body should usually be the bare number and the final visible paragraph must be checked for duplicate `表 表`.
- Turn figure captions into `图 章号-序号 图名`, placed below the image, centered, bold, and the same size as table captions/正文. Reapply both `w:sz=24` and `w:szCs=24` in the finalizer because Word may strip one of them.
- Update `\figref` so the visible正文 cross-reference is the full chapter-local text, such as `图 2-1`. As with `\tabref`, Pandoc emits the `图` prefix outside the hyperlink, so replace the hyperlink body with the bare chapter-local number and check for duplicate `图 图`.
- Style image paragraphs as centered, non-indented paragraphs with compact spacing and `keepNext` to keep the image with its caption. Do not reuse body first-line indentation on image-only paragraphs.
- Reapply LaTeX `\includegraphics[width=...\textwidth]` widths to DOCX image extents, especially subfigures, because Pandoc may otherwise use image DPI and make subfigures too small.
- For `fig:cross_model_heatmap_extra`, preserve the LaTeX subfigure layout in Word: merge the first two `0.48\textwidth` image paragraphs into one centered top row, then keep the third image as a separate centered bottom row before the caption. This avoids Word laying the three heatmaps in an uneven single-row arrangement.
- Keep table cells readable: use green three-line-table styling with enough vertical padding and 12 pt line spacing; do not over-compress row height just to match page count.
- Style thesis data tables as green three-line tables: no vertical borders; first header row top border and last table row bottom border must be thick rules (`w:sz=12`), while the last header row bottom border must be a thinner middle rule (`w:sz=4`), all using color `008000`. Do not make the three rules the same thickness. These rules must be explicit cell borders; keep table-level top/bottom `tblBorders` as `none` so Word does not draw an extra thick bottom rule at page breaks for split tables.
- Read each source table's LaTeX column spec from `\begin{tabular}{...}` by `\label`: map `l` to left, `c` to center, `r` to right, and apply those alignments to Word body cells. Keep header cells centered. Do not infer table alignment only from text length.
- Set explicit `tblGrid` and cell widths that approximate the LaTeX distribution, but never exceed the HUST text width (`8312` dxa). Wide result tables reserve enough width for method/model columns and use `w:noWrap` for 5+ column data tables so short labels such as `Qwen3-VL` and `HC-SMoE+桥接 75%` do not break across lines. Word may remove `tblLayout=fixed` on save, so validate the persisted grid/cell widths and no-wrap flags rather than relying only on that tag.
- For 5/6-column result tables, do not leave the table narrow and do not exceed the page text area. Force a full-text-width grid (`8312` dxa in this template) and allocate extra width to the method column and final numeric columns so values like `0.430` and method names do not wrap.
- Prefer adaptive column widths over fixed column-count presets. Estimate each column's display width from its actual content (Chinese wider than Latin, numbers narrower, punctuation/連字符 narrower), then allocate `tblGrid` widths so long model/method labels get more space and short numeric columns get less.
- Adaptive widths still need minimum readable widths. For 4-column task/metric tables, keep the total grid near full text width and enforce a wider minimum for short metric columns so tokens like `ANLS` do not split.
- Four-column comparison tables must not exceed the HUST text width. Keep their grid at about `8312` dxa, reserve at least about 22% for the first column, set `w:noWrap` on the first column, and convert first-column hyphens to `w:noBreakHyphen` so method names like `HC-SMoE`, `MC-SMoE`, and `MergeMoE` do not split.
- For `chart:merge_comparison` specifically, use a text-width grid `[1600, 2400, 2900, 1412]` dxa and set `w:noWrap` on the first three columns. The last yes/no column may be narrow; method, clustering-basis, and merge-strategy entries should stay on one line.
- For 6-column result tables, enforce true minimum widths for the model-family column and method column before distributing remaining width to numeric columns; model-family needs enough width for labels like `Qwen3-VL` even when method names are longer.
- In 5+ column data tables, convert normal hyphens inside table cell labels to Word `w:noBreakHyphen` so labels such as `Qwen3-VL`, `HC-SMoE`, and `DeepSeek-VL2-Small` do not split at the hyphen. Limit this to tables; keep normal body-text hyphen behavior unchanged.
- Do not apply three-line table styling to cover tables or image-layout tables.
- Table text: 宋体 for East Asian text, Times New Roman for Latin text, 五号; center short values and headers, left-align long explanatory cells.
- Convert simple inline math values in tables, such as `$+2.4$`, `$-3.4$`, and `$\Delta$`, into ordinary table text runs during packaging. These values should not remain as Word equation objects, because equation runs use Cambria Math and appear inconsistent with normal Times New Roman table numbers. Preserve source `\textbf{...}` emphasis where it already exists.
- Remove Pandoc artifacts from `\cmidrule`, especially literal strings like `2-5 (lr)6-9`.
- Repair custom LaTeX `list` environments using `（\arabic{enumi}）`: delete the empty `（）` paragraph and prefix each item paragraph with `（1）`, `（2）`, etc.
- Before Pandoc, run `scripts\expand_algorithms_for_pandoc.py` to flatten `word.tex` and convert LaTeX `algorithm`/`algorithmic` blocks into centered captions plus numbered `enumerate` steps. This keeps algorithm content in `main.docx` and lets Pandoc convert inline math inside each step.
- Style algorithm blocks to resemble the LaTeX `algorithmic` output using an invisible two-column Word table, not loose paragraphs. The first row is the algorithm title `算法 章号-序号 标题`, has black top/bottom rules, and must be marked `w:tblHeader` so Word repeats the title automatically when the algorithm crosses a page break. Step rows use static labels `1:`, `2:`, etc. in a narrow number column and the converted Pandoc content in the second column; keep the grid near `[360, 7952]` dxa, remove left padding in the number cell, and keep only a tiny right margin so line numbers sit close to the LaTeX version while still fitting two-digit labels like `10:` and `11:`. Add a full-width bottom rule on the last row. Do not add `w:tblCaption`, otherwise the normal table formatter may treat algorithms as data tables. Update `\algref` cross-references so body text displays normal black no-underline references such as `算法 3-1`.
- Reapply algorithm caption run sizes in `scripts\finalize_docx_after_word.py` together with figure/table captions, because Word may strip `w:sz` and leave only `w:szCs` after field updates.

## Validation Checklist

Run structural checks after each build:

- `main.docx` opens in Word read-only.
- The English abstract `Keywords` paragraph and the TOC title `目  录` are on different pages.
- TOC starts with `摘 要I`, `AbstractII`, and `1绪论1`.
- TOC has no third-level examples such as `研究背景与趋势`, `面临的问题和挑战`, or `MoE架构与视觉语言模型`.
- No raw `\begin{equation}` remains; `m:oMath` count is nonzero.
- Bibliography citations are numeric square brackets with the whole bracketed citation superscripted and no author-year remnants like `(Liu et al. 2023)` in正文.
- Equation references no longer contain `[eq:...]`; displayed equations have visible right-side `(chapter-number)` labels.
- Displayed equation paragraphs have nonzero before/after spacing so formulas do not crowd surrounding正文.
- `w:wordWrap` count is zero and `w:autoHyphenation w:val="false"` exists.
- All正文 data tables have the green three-line borders and no `2-5 (lr)6-9` text.
- Representative table cell alignments match LaTeX column specs, e.g. `chart:symbols` uses first column centered and second column left-aligned from `{cl}`.
- Table captions use正文-sized bold text with both `w:sz=24` and `w:szCs=24`, while table body text remains at the established table size.
- Table cross-references in正文 display as `表 x-y`, for example `如表 3-2 所示`.
- Figure captions use the same size/style as table captions and display as `图 x-y 图名`.
- Figure cross-references in正文 display as `图 x-y`, for example `如图 2-1 所示`, with no bare global numbers like `图 1` and no duplicate `图 图`.
- Image-only paragraphs are centered with no first-line indent; subfigures respect the LaTeX width factor such as `0.48\textwidth`.
- No empty `（）` paragraphs remain in custom lists.

If the Documents renderer is available, render PNG pages and inspect them. If it fails because `pdf2image` is missing, state that visual PNG QA could not be completed and rely on structural checks plus Word read-only open validation.

## 2026-05-18 Pipeline Notes

- The template repo now carries the reusable workflow: `hust-template.docx`, `word.tex`, `pandoc-word-macros.tex`, `pandoc-image-fallback.lua`, `numeric-superscript-brackets.csl`, `scripts\convert_to_docx.ps1`, and the Python/PowerShell post-processing scripts. Keep `word.tex` generic and point it to `body/*`; do not copy thesis-specific `my-body/*` content or personal metadata into the template repo.
- In the reusable template repo, avoid hard-coded project/table labels for column widths. Default to adaptive widths and support optional root-level `docx-table-widths.json` overrides whose keys are LaTeX table labels and whose values are width weights. The script scales the weights to the HUST text width.
- `scripts\prepare_docx_image_fallbacks.py` should be non-fatal when `pdftoppm` is missing. Warn the user and continue, because some templates use PNG/SVG only or Pandoc may handle the images directly.
- Before running Pandoc, run `python scripts\prepare_docx_image_fallbacks.py`. This renders every `images/*.pdf` figure into `.docx-build\pdf-images\images\*.png` with `pdftoppm`; `pandoc-image-fallback.lua` must prefer these generated PNGs over stale checked-in `images/*.png` files. This keeps DOCX figures visually aligned with the LaTeX/PDF source.
- Figure/table/equation cross-reference hyperlinks must look like normal body text: black, no underline, and no Word hyperlink run style. Keep the internal jump target, but strip hyperlink visual styling during packaging and again in `scripts\finalize_docx_after_word.py` after Word saves.
- Standalone displayed equations must be visually centered while equation numbers stay right-aligned. Use a leading center-tab before the `m:oMath`, a center tab at `4145`, a right tab at `8290`, and clear inherited first-line indentation. Reapply this in `scripts\finalize_docx_after_word.py` because Word can convert `m:oMathPara` to `m:oMath` and reintroduce body indentation on save.
- Inline paragraph math should not touch surrounding Chinese text. In `scripts\finalize_docx_after_word.py`, add one preserved-space `m:r/m:t` run inside each inline `m:oMath` at the beginning and end of the math box, but do not add external `w:r` spaces in the paragraph. Also remove any older external preserved-space runs adjacent to inline math. Skip standalone displayed equations with right-side `(chapter-number)` labels. The patch must be idempotent so repeated finalization does not add multiple spaces.
- When resizing DOCX figures, `scripts\build_hust_docx_package.py` must recognize both `images/foo.png` and `.docx-build/pdf-images/images/foo.png` as the same LaTeX source image so `\includegraphics[width=...\textwidth]` is preserved.
- For wide result tables (`>= 7` columns), force the Word table grid to the HUST text width (`8312` dxa), keep readable table spacing, and use column widths/no-wrap to reduce Word-only wrapping. Do not shrink table rows to chase page count, and do not use a grid wider than the page text area.
- For LaTeX `\fitwidetable` result tables with layout `lcccccccc`, do not let the adaptive scorer over-allocate width to the first metric header. Use a LaTeX-like natural distribution: one moderately wide method column and metric-aware numeric columns, e.g. `chart:50pct`, `chart:75pct`, and `chart:tiny_50pct` use `[1700, 980, 790, 740, 780, 800, 850, 780, 892]` dxa. This gives `InfoVQA` and `WinoG` enough width while preventing Word from splitting values such as `51.9` into two lines and keeping method names on one line.
- For the 10-column component ablation `\fitwidetable`, use a similar distribution with a compact method column and metric-aware numeric columns, e.g. `chart:hcsmoe_component_ablation` uses `[1450, 920, 760, 640, 640, 730, 800, 680, 640, 1052]` dxa so method labels, `InfoVQA`, `MMMU`, `WinoG`, and `综合平均` do not wrap unnecessarily.
- If the generated DOCX gains pages in Chapter 4, first inspect the wide result tables, but do not solve it by making rows cramped. Prefer column rebalancing, fixed layout, no-wrap for short labels, or accepting a small page-count drift over ugly table spacing.
- The LaTeX source uses `\fitwidetable` for 9/10-column result tables, but the DOCX version should still keep visually acceptable row height. Compact font size is acceptable for 7+ column tables, but line spacing should remain close to normal table text.
- LaTeX may float large figures while Word keeps images inline. A tested attempt to move `fig:module_architecture` after following text made Word pagination worse, so do not enable that move by default; prefer keeping figure order stable unless a later visual QA pass proves a specific float emulation improves total pagination.
- `word.tex` must include `my-body/references` before `my-body/acknowledgement`. Pandoc citeproc may still append bibliography at the end, so `build_hust_docx_package.py` moves the bibliography block before acknowledgement and suppresses numbering on both `参考文献` and `致谢` headings with direct `w:numId=0`.
- LibreOffice rendering on this machine may be blocked by a damaged Scoop `bootstrap.ini`. Use Word COM page export for visual QA when the Documents renderer cannot run, then still perform structural OOXML checks before delivering `main.docx`.
