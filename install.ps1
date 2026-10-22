param([string]$NukeDirectory = (Join-Path $env:USERPROFILE '.nuke'))
$ErrorActionPreference = 'Stop'
$target = Join-Path $NukeDirectory 'RepeatFrameRIFE'
New-Item -ItemType Directory -Force -Path $target | Out-Null
foreach ($file in @('repeatframe_core.py', 'repeatframe_rife.py', 'menu.py')) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $file) -Destination (Join-Path $target $file) -Force
}
$init = Join-Path $NukeDirectory 'init.py'
$line = 'nuke.pluginAddPath("./RepeatFrameRIFE")'
$content = if (Test-Path -LiteralPath $init) { [IO.File]::ReadAllText($init) } else { '' }
if (-not $content.Contains($line)) {
    if (Test-Path -LiteralPath $init) {
        Copy-Item -LiteralPath $init -Destination ($init + '.repeatframe-' + (Get-Date -Format 'yyyyMMddHHmmss') + '.bak')
    }
    [IO.File]::AppendAllText($init, "`r`n# Repeat Frame RIFE`r`nimport nuke`r`n$line`r`n", [Text.UTF8Encoding]::new($false))
}
Write-Output "Installed RepeatFrameRIFE at $target. Restart NukeX, then Tab > RepeatFrameRIFE."
