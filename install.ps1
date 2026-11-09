# AnkerGame VR - installation automatique de tout le necessaire (Windows 10/11)
# Installe : Python 3, ADB (platform-tools), Steam + SteamVR, ALVR (serveur PC + APK client Quest).
# Relancable sans risque : ce qui est deja installe est ignore.

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$AlvrDir = Join-Path $env:LOCALAPPDATA 'Programs\ALVR'
$Results = [ordered]@{}

function Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Ok($msg)   { Write-Host "    [OK] $msg" -ForegroundColor Green }
function Warn($msg) { Write-Host "    [!]  $msg" -ForegroundColor Yellow }

function Refresh-Path {
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' +
                [Environment]::GetEnvironmentVariable('Path', 'User')
}

function Has-Command($name) { [bool](Get-Command $name -ErrorAction SilentlyContinue) }

function Winget-Install($id, $label) {
    if (-not (Has-Command winget)) { throw "winget est introuvable. Mets a jour 'Programme d installation d application' dans le Microsoft Store." }
    winget install --id $id -e --silent --accept-package-agreements --accept-source-agreements | Out-Host
    # 0 = installe ; -1978335189 = deja installe / pas de mise a jour
    if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne -1978335189) { throw "Echec de l'installation de $label (code $LASTEXITCODE)." }
    Refresh-Path
}

function Run-Step($name, [scriptblock]$body) {
    Step $name
    try { & $body; $Results[$name] = 'OK' }
    catch { Warn $_.Exception.Message; $Results[$name] = 'ECHEC' }
}

Run-Step 'Python 3' {
    # Le "python" du Microsoft Store est un faux raccourci : on teste une vraie execution.
    $real = $false
    if (Has-Command python) { try { & python -c "import tkinter" 2>$null; $real = ($LASTEXITCODE -eq 0) } catch {} }
    if ($real) { Ok 'Python (avec Tkinter) deja installe.' }
    else { Winget-Install 'Python.Python.3.12' 'Python'; Ok 'Python installe.' }
}

Run-Step 'ADB (Android platform-tools)' {
    if (Has-Command adb) { Ok "ADB deja present : $((Get-Command adb).Source)" }
    else { Winget-Install 'Google.PlatformTools' 'ADB'; Ok 'ADB installe (redemarre le terminal pour le PATH).' }
}

Run-Step 'Steam' {
    $steam = @("${env:ProgramFiles(x86)}\Steam\steam.exe", "$env:ProgramFiles\Steam\steam.exe") | Where-Object { Test-Path $_ }
    if ($steam) { Ok 'Steam deja installe.' }
    else { Winget-Install 'Valve.Steam' 'Steam'; Ok 'Steam installe.' }
}

Run-Step 'SteamVR (requis par ALVR)' {
    $svr = @("${env:ProgramFiles(x86)}\Steam\steamapps\common\SteamVR") | Where-Object { Test-Path $_ }
    if ($svr) { Ok 'SteamVR deja installe.' }
    else {
        Start-Process 'steam://install/250820'
        Warn 'Installation de SteamVR demandee dans Steam. Connecte-toi a Steam si besoin et valide le telechargement.'
    }
}

Run-Step 'ALVR (serveur PC + client Quest)' {
    $rel = Invoke-RestMethod 'https://api.github.com/repos/alvr-org/ALVR/releases/latest' -Headers @{ 'User-Agent' = 'AnkerGameVR-installer' }
    Write-Host "    Derniere version ALVR : $($rel.tag_name)"
    New-Item -ItemType Directory -Force -Path $AlvrDir | Out-Null

    $zipAsset = $rel.assets | Where-Object name -eq 'alvr_streamer_windows.zip'
    $apkAsset = $rel.assets | Where-Object name -eq 'alvr_client_android.apk'
    if (-not $zipAsset -or -not $apkAsset) { throw 'Fichiers ALVR introuvables dans la release.' }

    $zip = Join-Path $env:TEMP 'alvr_streamer_windows.zip'
    Invoke-WebRequest $zipAsset.browser_download_url -OutFile $zip
    $tmp = Join-Path $env:TEMP 'alvr_extract'
    if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
    Expand-Archive $zip -DestinationPath $tmp -Force
    # Le zip contient un dossier racine (alvr_streamer_windows) ; on aplatit dans $AlvrDir.
    $root = Get-ChildItem $tmp | Select-Object -First 1
    $src = if ($root.PSIsContainer -and (Test-Path (Join-Path $root.FullName 'ALVR Dashboard.exe'))) { $root.FullName } else { $tmp }
    Copy-Item (Join-Path $src '*') $AlvrDir -Recurse -Force
    Remove-Item $zip, $tmp -Recurse -Force

    Invoke-WebRequest $apkAsset.browser_download_url -OutFile (Join-Path $AlvrDir 'alvr_client_android.apk')

    if (-not (Test-Path (Join-Path $AlvrDir 'ALVR Dashboard.exe'))) { throw "ALVR Dashboard.exe introuvable dans $AlvrDir" }
    Ok "ALVR $($rel.tag_name) installe dans $AlvrDir"
}

Run-Step 'Raccourci bureau AnkerGame VR' {
    $py = Join-Path $PSScriptRoot 'AnkerGameVR\AnkerGameVR.py'
    $lnk = Join-Path ([Environment]::GetFolderPath('Desktop')) 'AnkerGame VR.lnk'
    $ws = New-Object -ComObject WScript.Shell
    $s = $ws.CreateShortcut($lnk)
    $pyw = (Get-Command pythonw -ErrorAction SilentlyContinue)
    $s.TargetPath = if ($pyw) { $pyw.Source } else { 'pythonw.exe' }
    $s.Arguments = "`"$py`""
    $s.WorkingDirectory = Split-Path $py
    $s.Save()
    Ok "Raccourci cree : $lnk"
}

Write-Host "`n================ RESUME ================" -ForegroundColor Cyan
$Results.GetEnumerator() | ForEach-Object {
    $c = if ($_.Value -eq 'OK') { 'Green' } else { 'Red' }
    Write-Host ("  {0,-8} {1}" -f $_.Value, $_.Key) -ForegroundColor $c
}
Write-Host @"

PROCHAINES ETAPES
  1. Branche ton Quest en USB, active le mode developpeur et accepte le debogage USB.
  2. Ouvre AnkerGame VR (raccourci bureau), clique "Detecter" puis
     "Installer APK sur Quest" et choisis alvr_client_android.apk (dossier ALVR deja ouvert).
  3. Clique "Ouvrir ALVR", lance le client ALVR dans le casque et accepte la connexion.
"@
if ($Results.Values -contains 'ECHEC') { exit 1 }
