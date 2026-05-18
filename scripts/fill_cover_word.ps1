param(
  [string]$Docx = "main.docx",
  [string]$MainTex = "main.tex"
)

$ErrorActionPreference = "Stop"
$wdReplaceAll = 2

$root = (Resolve-Path ".").Path
$docxPath = (Resolve-Path $Docx).Path
$mainTexPath = if ([IO.Path]::IsPathRooted($MainTex)) { $MainTex } else { Join-Path $root $MainTex }
$mainTex = Get-Content -Raw -Encoding UTF8 $mainTexPath

function Get-LatexField([string]$Name) {
  $pattern = "\\" + $Name + "\{([^}]*)\}"
  $m = [regex]::Match($mainTex, $pattern)
  if ($m.Success) { return $m.Groups[1].Value.Trim() }
  return ""
}

function ConvertFrom-UnicodeEscape([string]$Text) {
  return [regex]::Replace($Text, "\\u([0-9a-fA-F]{4})", {
    param($match)
    return [char][Convert]::ToInt32($match.Groups[1].Value, 16)
  })
}

$replacements = [ordered]@{
  (ConvertFrom-UnicodeEscape "XXX\u7cfb\u7edf\u7684\u8bbe\u8ba1\u4e0e\u5b9e\u73b0") = Get-LatexField "title"
  (ConvertFrom-UnicodeEscape "\u8ba1\u7b97\u673a\u79d1\u5b66\u4e0e\u6280\u672f") = Get-LatexField "school"
  (ConvertFrom-UnicodeEscape "\u8ba1\u79d12201") = Get-LatexField "classnum"
  (ConvertFrom-UnicodeEscape "\u5c0f\u5cb3\u5cb3") = Get-LatexField "author"
  "U202215102" = Get-LatexField "stunum"
  (ConvertFrom-UnicodeEscape "\u90ed\u5fb7\u7eb2") = Get-LatexField "instructor"
}

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0

try {
  $doc = $word.Documents.Open($docxPath)
  foreach ($key in $replacements.Keys) {
    $value = $replacements[$key]
    if ([string]::IsNullOrWhiteSpace($value)) { continue }
    $range = $doc.Content
    $find = $range.Find
    $find.ClearFormatting()
    $find.Replacement.ClearFormatting()
    [void]$find.Execute($key, $false, $true, $false, $false, $false, $true, 1, $false, $value, $wdReplaceAll)
  }
  $doc.Save()
  $doc.Close($false)
}
finally {
  try { $word.Quit() } catch {}
}
