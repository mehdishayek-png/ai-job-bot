param (
  [string]$JobFile,
  [string]$OutFile
)

$base = "C:\Users\D\.openclaw\workspace\jobbot"
$template = Get-Content "$base\data\match_prompt.txt" -Raw
$profile  = Get-Content "$base\data\profile.json" -Raw
$job      = Get-Content $JobFile -Raw

$prompt = $template.Replace("{{PROFILE}}",$profile).Replace("{{JOB}}",$job)

Set-Content "$base\data\run_match.txt" $prompt

$p = Get-Content "$base\data\run_match.txt" -Raw
& openclaw --profile jobbot agent --local --agent main --session-id job_match --message $p | Out-File $OutFile -Encoding utf8
