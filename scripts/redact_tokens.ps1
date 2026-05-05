Param(
  [string]$Root = "."
)

$pattern = [regex]'[MN][A-Za-z0-9_-]{23}\.[A-Za-z0-9_-]{6}\.[A-Za-z0-9_-]{27}'

Get-ChildItem -LiteralPath $Root -Recurse -File -Force | ForEach-Object {
  $path = $_.FullName
  try {
    $content = Get-Content -LiteralPath $path -Raw -ErrorAction Stop
  } catch {
    return
  }

  $newContent = $pattern.Replace($content, 'REDACTED_TOKEN')
  if ($newContent -ne $content) {
    Set-Content -LiteralPath $path -Value $newContent -NoNewline
  }
}

