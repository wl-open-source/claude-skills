# PowerShell — registriert einen Windows-Task-Scheduler-Job, der triage.py
# regelmaessig laufen laesst. Windows hat kein direktes Ordner-Watch-Aequivalent
# im Task Scheduler, daher ein Intervall-Trigger (alle 15 Minuten) plus Start bei
# Anmeldung. Platzhalter unten ersetzen, dann ausfuehren:
#   powershell -ExecutionPolicy Bypass -File .\register-task.ps1
# Entfernen:
#   Unregister-ScheduledTask -TaskName "PARA-Dateiorganisation-Waechter" -Confirm:$false

$Python   = "__PYTHON__"                                  # z.B. C:\Python312\python.exe
$SkillDir = "__SKILL_DIR__"                               # Pfad zu diesem Skill
$WatchDir = "__WATCH_DIR__"                               # z.B. C:\Users\du\Downloads
$ParaHome = "__PARA_HOME__"                               # z.B. C:\Users\du\Dokumente\PARA
$TaskName = "PARA-Dateiorganisation-Waechter"

$Args = @(
    "$SkillDir\scripts\triage.py",
    "$WatchDir",
    "--apply", "--notify",
    "--manifest", "$ParaHome\.para-manifest.jsonl",
    "--against-home", "$ParaHome"
)

$Action  = New-ScheduledTaskAction -Execute $Python -Argument ($Args -join ' ')

# Intervall-Trigger: alle 15 Minuten, unbegrenzt.
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Minutes 15)

$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable `
    -DontStopOnIdleEnd -AllowStartIfOnBatteries

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger `
    -Settings $Settings -Description "Lokaler PARA-Ordner-Waechter (triage.py)" -Force

Write-Host "Task '$TaskName' registriert. Zum Testen zuerst ohne --apply laufen lassen:"
Write-Host "  $Python $SkillDir\scripts\triage.py $WatchDir"
