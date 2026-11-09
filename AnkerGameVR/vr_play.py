"""Recherche d'une version VR d'un jeu et lancement sur le casque (ALVR + SteamVR).

Ordre de résolution :
  1. Le jeu a déjà un mode VR officiel (Steam)        -> lancement via Steam
  2. Une édition VR officielle existe sur Steam        -> installation/lancement via Steam
  3. Le jeu tourne sur Unreal Engine                   -> mod UEVR (téléchargé depuis GitHub)
  4. Sinon : liste de mods VR trouvés sur GitHub       -> ouverture de la page choisie
Les jeux doivent être légalement possédés et installés. Pas de jeux multijoueurs avec anti-cheat.
"""
import ctypes
import glob
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import time
import urllib.parse
import urllib.request
import webbrowser
import zipfile

DATA_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "AnkerGameVR")
UEVR_DIR = os.path.join(DATA_DIR, "UEVR")
STEAMVR_APPID = "250820"
UA = {"User-Agent": "AnkerGameVR"}
ANTICHEAT = ("EasyAntiCheat", "BattlEye", "BEService", "vgk.sys", "Vanguard")


def _get_json(url, timeout=20):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def _norm_words(name):
    generic = {"the", "of", "vr", "edition", "special", "remastered", "definitive", "complete",
               "goty", "game", "year", "enhanced", "deluxe", "anniversary", "legendary"}
    return set(re.findall(r"[a-z0-9]+", name.lower())) - generic


# ---------------------------------------------------------------- Steam locale
def steam_path():
    for p in (os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Steam"),
              os.path.join(os.environ.get("ProgramFiles", ""), "Steam")):
        if os.path.isdir(p):
            return p
    return None


def steam_libraries():
    root = steam_path()
    if not root:
        return []
    libs = [root]
    vdf = os.path.join(root, "steamapps", "libraryfolders.vdf")
    try:
        with open(vdf, encoding="utf-8", errors="replace") as f:
            for m in re.finditer(r'"path"\s+"([^"]+)"', f.read()):
                p = m.group(1).replace("\\\\", "\\")
                if os.path.isdir(p) and p not in libs:
                    libs.append(p)
    except OSError:
        pass
    return libs


def scan_steam_games():
    """Jeux Steam installés : liste de dicts {name, appid, folder}."""
    games = []
    for lib in steam_libraries():
        for acf in glob.glob(os.path.join(lib, "steamapps", "appmanifest_*.acf")):
            try:
                txt = open(acf, encoding="utf-8", errors="replace").read()
                appid = re.search(r'"appid"\s+"(\d+)"', txt).group(1)
                name = re.search(r'"name"\s+"([^"]+)"', txt).group(1)
                folder = re.search(r'"installdir"\s+"([^"]+)"', txt).group(1)
            except (OSError, AttributeError):
                continue
            if appid == STEAMVR_APPID or "Steamworks" in name or "Redistributable" in name:
                continue
            games.append({"name": name, "appid": appid,
                          "folder": os.path.join(lib, "steamapps", "common", folder)})
    return sorted(games, key=lambda g: g["name"].lower())


# ------------------------------------------------------------ Édition VR Steam
def steam_details(appid):
    try:
        d = _get_json(f"https://store.steampowered.com/api/appdetails?appids={appid}&l=english")
        return d[str(appid)].get("data")
    except Exception:
        return None


def has_vr(details):
    return bool(details) and any("VR" in c.get("description", "") for c in details.get("categories", []))


def find_official_vr(game):
    """Retourne (appid, nom, deja_le_jeu) pour une version VR officielle, sinon None."""
    appid = game.get("appid")
    if appid and has_vr(steam_details(appid)):
        return appid, game["name"], True
    base = _norm_words(game["name"])
    if not base:
        return None
    term = urllib.parse.quote(" ".join(sorted(base, key=game["name"].lower().find)) + " VR")
    try:
        items = _get_json(f"https://store.steampowered.com/api/storesearch/?term={term}&cc=us&l=english")["items"]
    except Exception:
        return None
    for it in items[:8]:
        if str(it["id"]) == str(appid):
            continue
        if base <= _norm_words(it["name"]) and has_vr(steam_details(it["id"])):
            return str(it["id"]), it["name"], False
    return None


# ------------------------------------------------------------------ Unreal / UEVR
def find_unreal_exe(folder):
    """Chemin du *-Win64-Shipping.exe (processus à injecter) ou None si pas Unreal."""
    if not folder or not os.path.isdir(folder):
        return None
    for depth in range(1, 6):
        hits = glob.glob(os.path.join(folder, *["*"] * depth, "*-Win64-Shipping.exe"))
        if hits:
            return hits[0]
    return None


def has_anticheat(folder):
    for _root, dirs, files in os.walk(folder):
        if any(a.lower() in n.lower() for a in ANTICHEAT for n in dirs + files):
            return True
        if _root.count(os.sep) - folder.count(os.sep) > 4:
            dirs[:] = []
    return False


def ensure_uevr(log):
    dll = os.path.join(UEVR_DIR, "UEVRBackend.dll")
    if os.path.isfile(dll):
        return UEVR_DIR
    log("Téléchargement de UEVR (mod VR pour jeux Unreal Engine)…")
    rel = _get_json("https://api.github.com/repos/praydog/UEVR/releases/latest")
    assets = {a["name"]: a["browser_download_url"] for a in rel["assets"]}
    os.makedirs(DATA_DIR, exist_ok=True)
    zpath = os.path.join(DATA_DIR, "UEVR.zip")
    urllib.request.urlretrieve(assets["UEVR.zip"], zpath)
    if "UEVR.zip.sha256" in assets:
        want = urllib.request.urlopen(urllib.request.Request(assets["UEVR.zip.sha256"], headers=UA)).read().decode().split()[0].lower()
        got = hashlib.sha256(open(zpath, "rb").read()).hexdigest()
        if want != got:
            os.remove(zpath)
            raise RuntimeError("Somme de contrôle UEVR invalide : téléchargement rejeté.")
    shutil.rmtree(UEVR_DIR, ignore_errors=True)
    with zipfile.ZipFile(zpath) as z:
        z.extractall(UEVR_DIR)
    os.remove(zpath)
    if not os.path.isfile(dll):  # certains zips ont un dossier racine
        found = glob.glob(os.path.join(UEVR_DIR, "**", "UEVRBackend.dll"), recursive=True)
        if not found:
            raise RuntimeError("UEVRBackend.dll introuvable dans l'archive UEVR.")
        return os.path.dirname(found[0])
    log(f"UEVR {rel['tag_name']} installé.")
    return UEVR_DIR


def find_pid(exe_name):
    out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {exe_name}", "/FO", "CSV", "/NH"],
                         capture_output=True, text=True).stdout
    m = re.search(r'"[^"]+","(\d+)"', out)
    return int(m.group(1)) if m else None


def inject_dll(pid, dll_path):
    """Injection LoadLibraryW classique (équivalent de l'injecteur UEVR)."""
    if struct.calcsize("P") != 8:
        raise RuntimeError("Python 64 bits requis pour l'injection.")
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.OpenProcess.restype = ctypes.c_void_p
    k.VirtualAllocEx.restype = ctypes.c_void_p
    k.VirtualAllocEx.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_ulong, ctypes.c_ulong]
    k.WriteProcessMemory.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p]
    k.GetModuleHandleW.restype = ctypes.c_void_p
    k.GetProcAddress.restype = ctypes.c_void_p
    k.GetProcAddress.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    k.CreateRemoteThread.restype = ctypes.c_void_p
    k.CreateRemoteThread.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p,
                                     ctypes.c_void_p, ctypes.c_ulong, ctypes.c_void_p]
    k.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    k.CloseHandle.argtypes = [ctypes.c_void_p]
    h = k.OpenProcess(0x1F0FFF, False, pid)
    if not h:
        raise RuntimeError("Accès au jeu refusé (relance AnkerGame VR en administrateur).")
    try:
        data = (dll_path + "\0").encode("utf-16-le")
        mem = k.VirtualAllocEx(h, None, len(data), 0x3000, 0x04)
        if not mem or not k.WriteProcessMemory(h, mem, data, len(data), None):
            raise RuntimeError("Écriture dans le processus du jeu impossible.")
        load = k.GetProcAddress(k.GetModuleHandleW("kernel32.dll"), b"LoadLibraryW")
        t = k.CreateRemoteThread(h, None, 0, load, mem, 0, None)
        if not t:
            raise RuntimeError("Création du thread distant impossible.")
        k.WaitForSingleObject(t, 20000)
        k.CloseHandle(t)
    finally:
        k.CloseHandle(h)


# -------------------------------------------------------------- Mods via GitHub
def github_vr_mods(name):
    q = urllib.parse.quote(f"{name} VR in:name,description")
    try:
        d = _get_json(f"https://api.github.com/search/repositories?q={q}&sort=stars&per_page=5")
    except Exception:
        return []
    base = _norm_words(name)
    out = []
    for r in d.get("items", []):
        text = (r["full_name"] + " " + (r.get("description") or "")).lower()
        words = set(re.findall(r"[a-z0-9]+", text))
        ident = set(re.findall(r"[a-z0-9]+", r["full_name"].lower()))
        if "vr" in words and base and base <= words and (base & ident or r["stargazers_count"] >= 50) and len(r.get("description") or "") < 300 and r["stargazers_count"] >= 5:
            out.append((r["full_name"], r["stargazers_count"], r["html_url"], r.get("description") or ""))
    return out


# ------------------------------------------------------------------ VR stack
def ensure_vr_stack(log):
    alvr = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "ALVR", "ALVR Dashboard.exe")
    if find_pid("ALVR Dashboard.exe") is None:
        if os.path.isfile(alvr):
            log("Démarrage d'ALVR…")
            subprocess.Popen([alvr], cwd=os.path.dirname(alvr))
        else:
            log("ALVR introuvable : lance INSTALLER.bat.")
    if find_pid("vrserver.exe") is None:
        log("Démarrage de SteamVR…")
        os.startfile(f"steam://rungameid/{STEAMVR_APPID}")
        for _ in range(45):
            time.sleep(1)
            if find_pid("vrserver.exe"):
                break
    log("Mets le casque, ouvre le client ALVR et accepte la connexion si ce n'est pas déjà fait.")


# --------------------------------------------------------------- Orchestration
def play_vr(game, log, ask):
    """Lance `game` en VR. `ask(titre, message)` -> bool pour confirmer. Retourne un message final."""
    folder = game.get("folder") or (os.path.dirname(game["exe"]) if game.get("exe") else "")
    appid = game.get("appid")

    log("Recherche d'une version VR officielle (Steam)…")
    off = find_official_vr(game)
    if off:
        vr_id, vr_name, same = off
        ensure_vr_stack(log)
        installed = any(g["appid"] == vr_id for g in scan_steam_games())
        if installed or same:
            os.startfile(f"steam://rungameid/{vr_id}")
            return f"Lancement VR officiel : {vr_name}."
        if ask("Version VR officielle", f"« {vr_name} » existe sur Steam.\nL'installer maintenant (si tu la possèdes ou veux l'acheter) ?"):
            os.startfile(f"steam://install/{vr_id}")
            return f"Installation de « {vr_name} » demandée dans Steam. Relance ensuite « Jouer en VR »."
        return "Annulé."

    shipping = find_unreal_exe(folder)
    if shipping:
        if has_anticheat(folder):
            return "Ce jeu utilise un anti-cheat : l'injection de mod VR risque un bannissement. Annulé."
        if not ask("Mod VR (UEVR)",
                   f"Aucune version VR officielle, mais « {game['name']} » tourne sur Unreal Engine.\n\n"
                   "Le mod UEVR (open source) va être téléchargé et injecté dans le jeu. "
                   "À utiliser en solo uniquement. Continuer ?"):
            return "Annulé."
        uevr = ensure_uevr(log)
        ensure_vr_stack(log)
        log("Lancement du jeu…")
        if appid:
            os.startfile(f"steam://rungameid/{appid}")
        else:
            subprocess.Popen([game["exe"]], cwd=os.path.dirname(game["exe"]))
        exe_name = os.path.basename(shipping)
        pid = None
        for _ in range(120):
            pid = find_pid(exe_name)
            if pid:
                break
            time.sleep(1)
        if not pid:
            return "Le jeu ne s'est pas lancé à temps."
        log("Jeu détecté, attente de l'initialisation graphique (20 s)…")
        time.sleep(20)
        try:
            inject_dll(pid, os.path.join(uevr, "UEVRBackend.dll"))
        except Exception as e:
            inj = os.path.join(uevr, "UEVRInjector.exe")
            if os.path.isfile(inj):
                subprocess.Popen([inj], cwd=uevr)
            return f"Injection automatique échouée ({e}). L'injecteur UEVR a été ouvert : choisis le jeu puis « Inject »."
        return "Mod UEVR injecté : mets le casque, le jeu s'affiche en VR (menu UEVR avec la touche Inser)."

    log("Recherche de mods VR sur GitHub…")
    mods = github_vr_mods(game["name"])
    if not mods:
        return "Aucune version VR (officielle ou mod) trouvée automatiquement pour ce jeu."
    lines = "\n".join(f"• {n} ({s}★) {d[:60]}" for n, s, _u, d in mods)
    if ask("Mods VR trouvés", f"Pas d'installation automatique possible. Candidats sur GitHub :\n\n{lines}\n\nOuvrir le premier ?"):
        webbrowser.open(mods[0][2])
    return "Mods trouvés : suis les instructions de la page du mod."
