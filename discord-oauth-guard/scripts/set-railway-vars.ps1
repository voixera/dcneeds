param(
  [string]$Service = "",
  [string]$Environment = "",
  [string]$Project = "",
  [switch]$NoSkipDeploys
)

$ErrorActionPreference = "Stop"

$variables = [ordered]@{
  DISCORD_TOKEN = "EDIT_ME_DISCORD_BOT_TOKEN"
  CLIENT_ID = "EDIT_ME_DISCORD_APPLICATION_CLIENT_ID"
  GUILD_ID = "EDIT_ME_DISCORD_GUILD_ID"
  NIXPACKS_NODE_VERSION = "24"
  DATABASE_PATH = "/data/oauth-guard.sqlite"
  TEMP_DIR = "/tmp/oauth-guard"
  LOG_LEVEL = "info"
  LOG_CHANNEL_NAME = "oauth-guard-logs"
  MOD_LOG_CHANNEL_ID = ""
  CREATE_LOG_CHANNEL = "true"
  SUSPICIOUS_THRESHOLD = "40"
  MALICIOUS_THRESHOLD = "70"
  DELETE_MALICIOUS_MESSAGES = "true"
  ENABLE_AUTO_TIMEOUT = "true"
  TIMEOUT_DURATION_MS = "3600000"
  WARNING_DELETE_AFTER_MS = "15000"
  OCR_LANGUAGE = "eng"
  OCR_TIMEOUT_MS = "30000"
  IMAGE_MAX_BYTES = "8388608"
  IMAGE_SIMILARITY_DISTANCE = "8"
  NEW_ACCOUNT_DAYS = "7"
  SPAM_WINDOW_SECONDS = "120"
  SPAM_ATTACHMENT_THRESHOLD = "4"
  SPAM_CHANNEL_THRESHOLD = "3"
  MASS_MENTION_THRESHOLD = "5"
  VOICE_NOTIFY_CHANNEL_ID = ""
  VOICE_RECONNECT_DELAY_MS = "5000"
}

$baseArgs = @("variable", "set")
if ($Service) {
  $baseArgs += @("--service", $Service)
}
if ($Environment) {
  $baseArgs += @("--environment", $Environment)
}
if ($Project) {
  $baseArgs += @("--project", $Project)
}
if (-not $NoSkipDeploys) {
  $baseArgs += "--skip-deploys"
}

Write-Host "Setting $($variables.Count) Railway variable(s). Secret placeholders must be edited in Railway after this finishes."

foreach ($entry in $variables.GetEnumerator()) {
  $pair = "$($entry.Key)=$($entry.Value)"
  Write-Host "Setting $($entry.Key)"
  & npx -y @railway/cli @baseArgs $pair
  if ($LASTEXITCODE -ne 0) {
    throw "Failed to set $($entry.Key). Make sure Railway CLI is logged in or RAILWAY_TOKEN is set, and the directory is linked to the target service."
  }
}

Write-Host "Done. Edit DISCORD_TOKEN, CLIENT_ID, GUILD_ID, MOD_LOG_CHANNEL_ID, and VOICE_NOTIFY_CHANNEL_ID in Railway if needed."
