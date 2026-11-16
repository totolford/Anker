"""Gestion du casque Quest via ADB : détection, connexion Wi-Fi, mise à jour du client ALVR.

Ne touche qu'à l'application ALVR du casque (adb install / adb uninstall d'un paquet ALVR).
Aucune commande système : pas de flash, pas de bootloader, pas de réinitialisation.
"""
import json
import os
import re
import shutil
import subprocess
import urllib.request

ALVR_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "Programs", "ALVR")
APK_PATH = os.path.join(ALVR_DIR, "alvr_client_android.apk")
VERSION_FILE = os.path.join(ALVR_DIR, "client_version.txt")
UA = {"User-Agent": "AnkerGameVR"}
MIN_SDK = 26  # minSdkVersion du client ALVR 20.x (Android 8.0), vérifié sur l'APK v20.14.1

# état -> (message pour l'utilisateur)
GUIDE = {
    "no_adb": "ADB est introuvable. Lance INSTALLER.bat pour l'installer.",
    "none": ("Aucun casque détecté.\n\n"
             "• Allume le casque et branche-le avec un câble USB DE DONNÉES (pas un câble de charge seule).\n"
             "• Active le mode développeur : app Meta Horizon sur le téléphone > Appareils > ton casque > "
             "Paramètres du casque > Mode développeur.\n"
             "• Mets le casque sur la tête : accepte « Autoriser le débogage USB » (coche « Toujours autoriser »).\n\n"
             "Sans câble : utilise « Connexion Wi-Fi » (nécessite un premier branchement USB)."),
    "unauthorized": ("Le casque est branché mais n'a pas autorisé ce PC.\n\n"
                     "Mets le casque sur la tête et accepte « Autoriser le débogage USB » "
                     "(coche « Toujours autoriser »), puis reclique."),
    "offline": "Le casque est en veille ou la connexion est instable. Réveille-le, rebranche le câble, puis reclique.",
}


def find_adb():
    adb = shutil.which("adb")
    if adb:
        return adb
    p = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Android", "Sdk", "platform-tools", "adb.exe")
    return p if os.path.isfile(p) else None


def adb(args, timeout=30):
    exe = find_adb()
    if not exe:
        raise FileNotFoundError("adb")
    return subprocess.run([exe] + args, capture_output=True, text=True, timeout=timeout)


def devices():
    """Liste [(serial, état)] avec état = device | unauthorized | offline."""
    out = adb(["devices"]).stdout.splitlines()[1:]
    res = []
    for line in out:
        parts = line.split()
        if len(parts) >= 2:
            res.append((parts[0], parts[1]))
    return res


def status():
    """Retourne (code, message, modèle) ; code = ready | none | unauthorized | offline | no_adb."""
    if not find_adb():
        return "no_adb", GUIDE["no_adb"], ""
    try:
        devs = devices()
    except (OSError, subprocess.TimeoutExpired) as e:
        return "none", f"Erreur ADB : {e}", ""
    if not devs:
        return "none", GUIDE["none"], ""
    ready = [d for d in devs if d[1] == "device"]
    if not ready:
        state = devs[0][1] if devs[0][1] in GUIDE else "offline"
        return state, GUIDE[state], ""
    model = adb(["-s", ready[0][0], "shell", "getprop", "ro.product.model"]).stdout.strip()
    return "ready", f"Casque détecté : {model}", model


def wifi_ip():
    """IP Wi-Fi du casque (casque connecté en USB)."""
    out = adb(["shell", "ip", "-f", "inet", "addr", "show", "wlan0"]).stdout
    m = re.search(r"inet (\d+\.\d+\.\d+\.\d+)", out)
    return m.group(1) if m else None


def enable_wifi_adb():
    """Passe l'ADB du casque en TCP (port 5555) ; retourne (ok, ip, message)."""
    ip = wifi_ip()
    if not ip:
        return False, None, "Le casque n'a pas d'adresse Wi-Fi (Wi-Fi désactivé ?)."
    r = adb(["tcpip", "5555"])
    if r.returncode != 0:
        return False, ip, (r.stdout + r.stderr).strip()
    return True, ip, f"ADB sans fil activé sur {ip}:5555 (valable jusqu'au redémarrage du casque)."


def connect_wifi(ip):
    r = adb(["connect", f"{ip}:5555"], timeout=20)
    out = (r.stdout + r.stderr).strip()
    ok = "connected to" in out.lower() and "cannot" not in out.lower() and "failed" not in out.lower()
    return ok, out


def alvr_packages():
    out = adb(["shell", "pm", "list", "packages"]).stdout
    return [l.split(":", 1)[1].strip() for l in out.splitlines() if l.startswith("package:") and "alvr" in l.lower()]


def ensure_apk(log):
    """APK du client ALVR identique au serveur installé sur le PC (même version = connexion garantie)."""
    if os.path.isfile(APK_PATH):
        return APK_PATH
    log("Téléchargement du client ALVR…")
    req = urllib.request.Request("https://api.github.com/repos/alvr-org/ALVR/releases/latest", headers=UA)
    rel = json.load(urllib.request.urlopen(req, timeout=30))
    asset = next((a for a in rel["assets"] if a["name"] == "alvr_client_android.apk"), None)
    if not asset:
        raise RuntimeError("APK du client ALVR introuvable dans la dernière version.")
    os.makedirs(ALVR_DIR, exist_ok=True)
    urllib.request.urlretrieve(asset["browser_download_url"], APK_PATH)
    open(VERSION_FILE, "w").write(rel["tag_name"])
    return APK_PATH


def apk_version():
    try:
        return open(VERSION_FILE).read().strip()
    except OSError:
        return "inconnue"


def update_client(log, ask):
    """Installe/met à jour le client ALVR sur le casque. Retourne un message final."""
    code, msg, model = status()
    if code != "ready":
        return msg
    sdk_txt = adb(["shell", "getprop", "ro.build.version.sdk"]).stdout.strip()
    abi = adb(["shell", "getprop", "ro.product.cpu.abi"]).stdout.strip()
    if sdk_txt.isdigit() and int(sdk_txt) < MIN_SDK:
        return (f"Le logiciel du casque est trop ancien (Android API {sdk_txt}, minimum {MIN_SDK}).\n\n"
                "Mets le casque à jour (Paramètres > Système > Mise à jour logicielle), connecté au Wi-Fi, "
                "puis recommence.")
    if abi and "arm64" not in abi:
        return f"Processeur non pris en charge par ALVR ({abi})."
    log(f"{model} : préparation du client ALVR…")
    apk = ensure_apk(log)
    before = alvr_packages()
    log("Installation sur le casque (garde les réglages ALVR)…")
    r = adb(["install", "-r", apk], timeout=300)
    out = (r.stdout + r.stderr).strip()
    if r.returncode != 0 or "Success" not in out:
        incompatible = any(k in out for k in ("UPDATE_INCOMPATIBLE", "VERSION_DOWNGRADE", "SIGNATURE"))
        if incompatible and before and ask(
                "Réinstallation nécessaire",
                "L'ancienne version d'ALVR ne peut pas être mise à jour directement.\n\n"
                "La désinstaller puis installer la bonne version ? (les réglages ALVR du casque seront effacés ; "
                "ni le système ni tes jeux ne sont touchés.)"):
            for pkg in before:
                adb(["uninstall", pkg])
            r = adb(["install", apk], timeout=300)
            out = (r.stdout + r.stderr).strip()
        if "OLDER_SDK" in out:
            return ("Ce casque est trop ancien pour cette version d'ALVR. Mets le casque à jour "
                    "(Paramètres > Système > Mise à jour logicielle), puis recommence.")
        if "Success" not in out:
            return f"Installation échouée : {out or 'raison inconnue'}"
    after = alvr_packages()
    if not after:
        return "Installation signalée réussie, mais ALVR n'apparaît pas dans le casque. Réessaie."
    return (f"Client ALVR {apk_version()} installé sur {model} ({after[0]}).\n\n"
            "Dans le casque : Bibliothèque > Sources inconnues > ALVR. Lance ensuite « Ouvrir ALVR » sur le PC "
            "et accepte la connexion.")
