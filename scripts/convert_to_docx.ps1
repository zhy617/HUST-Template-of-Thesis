param(
  [string]$Output = "main.docx",
  [string]$MainTex = "main.tex",
  [string]$WordTex = "word.tex",
  [string]$ReferenceDoc = "hust-template.docx",
  [switch]$SkipWordUpdate
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Push-Location $root

function Require-Command([string]$Name) {
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "Required command '$Name' was not found in PATH."
  }
}

function Resolve-RepoPath([string]$PathValue) {
  if ([IO.Path]::IsPathRooted($PathValue)) {
    return $PathValue
  }
  return Join-Path $root $PathValue
}

function ConvertFrom-UnicodeEscape([string]$Text) {
  return [regex]::Replace($Text, "\\u([0-9a-fA-F]{4})", {
    param($match)
    return [char][Convert]::ToInt32($match.Groups[1].Value, 16)
  })
}

try {
  Require-Command "python"
  Require-Command "pandoc"

  $buildDir = Join-Path $root ".docx-build"
  New-Item -ItemType Directory -Force -Path $buildDir | Out-Null

  $expandedTex = Join-Path $buildDir "word-expanded.tex"
  $bodyDocx = Join-Path $buildDir "body.docx"
  $outputPath = Resolve-RepoPath $Output
  $mainTexPath = Resolve-RepoPath $MainTex
  $wordTexPath = Resolve-RepoPath $WordTex
  $referenceDocPath = Resolve-RepoPath $ReferenceDoc
  $luaFilter = Join-Path $root "pandoc-image-fallback.lua"
  $bibFile = Join-Path $root "ref.bib"
  $cslFile = Join-Path $root "numeric-superscript-brackets.csl"
  $referenceSectionTitle = ConvertFrom-UnicodeEscape "\u53c2\u8003\u6587\u732e"

  python (Join-Path $root "scripts\prepare_docx_image_fallbacks.py")
  python (Join-Path $root "scripts\expand_algorithms_for_pandoc.py") $wordTexPath $expandedTex

  pandoc $expandedTex `
    -o $bodyDocx `
    --reference-doc=$referenceDocPath `
    --lua-filter=$luaFilter `
    --resource-path=".;images;.docx-build/pdf-images" `
    --bibliography=$bibFile `
    --citeproc `
    --csl=$cslFile `
    -M link-citations=true `
    -M reference-section-title=$referenceSectionTitle

  python (Join-Path $root "scripts\build_hust_docx_package.py") $referenceDocPath $bodyDocx $outputPath $mainTexPath

  if (-not $SkipWordUpdate) {
    $fillCoverScript = Get-Content -Raw -Encoding UTF8 (Join-Path $root "scripts\fill_cover_word.ps1")
    $fillCoverBlock = [scriptblock]::Create($fillCoverScript)
    & $fillCoverBlock -Docx $outputPath -MainTex $mainTexPath

    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    try {
      $doc = $word.Documents.Open($outputPath)
      foreach ($toc in $doc.TablesOfContents) { $toc.Update() }
      foreach ($field in $doc.Fields) { [void]$field.Update() }
      $doc.Save()
      $doc.Close($false)
    }
    finally {
      $word.Quit()
    }
  }

  python (Join-Path $root "scripts\finalize_docx_after_word.py") $outputPath
  Write-Host "DOCX exported to $outputPath"
}
finally {
  Pop-Location
}
