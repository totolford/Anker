import json
import os
import shutil
import subprocess
import webbrowser
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

APP_DIR = os.path.dirname(os.path.abspath(__file__))
LIBRARY_FILE = os.path.join(APP_DIR, "games.json")

DEFAULT_GAMES = [
    {
        "name": "Five Nights at Freddy's: Help Wanted",
        "exe": "",
        "vr": True,
        "notes": "Jeu VR natif. Ajoute ici le fichier .exe du jeu installé sur ton PC."
    }
]

def default_games():
    return [dict(g) for g in DEFAULT_GAMES]

def load_games():
    if os.path.exists(LIBRARY_FILE):
        try:
            with open(LIBRARY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                games = [g for g in data if isinstance(g, dict) and g.get("name")]
                for g in games:
                    g.setdefault("exe", "")
                    g.setdefault("vr", False)
                    g.setdefault("notes", "")
                return games
        except (OSError, json.JSONDecodeError):
            pass
    return default_games()

def save_games(games):
    tmp = LIBRARY_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(games, f, ensure_ascii=False, indent=2)
    os.replace(tmp, LIBRARY_FILE)

ALVR_CANDIDATES = [
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "ALVR", "ALVR Dashboard.exe"),
    r"C:\Program Files\ALVR\ALVR Dashboard.exe",
    r"C:\Program Files\ALVR\alvr_dashboard.exe",
    os.path.join(APP_DIR, "alvr_streamer_windows", "ALVR Dashboard.exe"),
]

def find_alvr():
    for p in ALVR_CANDIDATES:
        if p and os.path.isfile(p):
            return p
    return shutil.which("ALVR Dashboard") or shutil.which("alvr_dashboard")

SETTINGS_FILE = os.path.join(APP_DIR, "settings.json")

# Profils par casque : réglages ALVR conseillés (à saisir dans ALVR > Video / Headset).
PROFILES = {
    "Meta Quest 1": {
        "models": ["quest"],
        "resolution": "Basse à moyenne (~1440 px de large par oeil)",
        "bitrate": "100 Mb/s", "refresh": "72 Hz", "codec": "H.264",
        "notes": "Matériel ancien : garde une résolution modeste. Wi-Fi 5 GHz requis.",
    },
    "Meta Quest 2": {
        "models": ["quest 2"],
        "resolution": "Moyenne (~1832 px de large par oeil)",
        "bitrate": "150 Mb/s", "refresh": "90 Hz", "codec": "HEVC (H.265)",
        "notes": "Wi-Fi 5/6 sur 5 GHz, routeur proche du casque.",
    },
    "Meta Quest 3": {
        "models": ["quest 3", "quest 3s"],
        "resolution": "Haute (~2064 px de large par oeil)",
        "bitrate": "200 Mb/s", "refresh": "90 Hz (120 Hz si le PC suit)", "codec": "HEVC (H.265) ou AV1 si la carte graphique le gère",
        "notes": "Idéal en Wi-Fi 6/6E dédié. Le Quest 3 gère le passthrough couleur.",
    },
}
DEFAULT_PROFILE = "Meta Quest 3"

def load_settings():
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and data.get("headset") in PROFILES:
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return {"headset": DEFAULT_PROFILE}

def save_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

def find_adb():
    adb = shutil.which("adb")
    if adb:
        return adb
    p = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Android", "Sdk", "platform-tools", "adb.exe")
    return p if os.path.isfile(p) else None

def detect_headset():
    """Retourne (nom_profil, message). nom_profil vaut None si rien n'est détecté."""
    adb = find_adb()
    if not adb:
        return None, "ADB introuvable. Lance INSTALLER.bat."
    try:
        r = subprocess.run([adb, "shell", "getprop", "ro.product.model"],
                           capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, f"Erreur ADB : {e}"
    model = r.stdout.strip().lower()
    if r.returncode != 0 or not model:
        return None, "Aucun casque détecté (câble USB, mode développeur, autorisation dans le casque)."
    for name, prof in PROFILES.items():
        if model in prof["models"]:
            return name, f"Casque détecté : {r.stdout.strip()}"
    return None, f"Appareil détecté ({r.stdout.strip()}) mais modèle inconnu."

class Launcher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AnkerGame VR")
        self.geometry("900x680")
        self.minsize(760, 560)
        self.configure(bg="#101522")
        self.games = load_games()
        self.settings = load_settings()
        self._style()
        self._build()
        self.refresh()

    def _style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Treeview", background="#1b2538", foreground="#f1f5ff",
                        fieldbackground="#1b2538", rowheight=34, borderwidth=0)
        style.configure("Treeview.Heading", background="#263653",
                        foreground="#ffffff", font=("Segoe UI", 10, "bold"))
        style.map("Treeview", background=[("selected", "#315b91")])
        style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=9)

    def _build(self):
        header = tk.Frame(self, bg="#101522")
        header.pack(fill="x", padx=26, pady=(22, 8))
        tk.Label(header, text="ANKERGAME VR", bg="#101522", fg="#69d5ff",
                 font=("Segoe UI", 25, "bold")).pack(anchor="w")
        tk.Label(header, text="Ta bibliothèque de jeux, réunie au même endroit.",
                 bg="#101522", fg="#c4cee0", font=("Segoe UI", 11)).pack(anchor="w", pady=(3, 0))

        hs = tk.Frame(header, bg="#101522")
        hs.pack(fill="x", pady=(10, 0))
        tk.Label(hs, text="Casque :", bg="#101522", fg="#c4cee0",
                 font=("Segoe UI", 10, "bold")).pack(side="left")
        self.headset_var = tk.StringVar(value=self.settings["headset"])
        combo = ttk.Combobox(hs, textvariable=self.headset_var, values=list(PROFILES),
                             state="readonly", width=16)
        combo.pack(side="left", padx=8)
        combo.bind("<<ComboboxSelected>>", lambda _e: self.set_headset(self.headset_var.get()))
        ttk.Button(hs, text="Détecter", command=self.auto_detect).pack(side="left")
        self.profile_info = tk.Label(header, text="", bg="#101522", fg="#9eabc2",
                                     font=("Segoe UI", 9), anchor="w", justify="left", wraplength=840)
        self.profile_info.pack(fill="x", pady=(6, 0))
        self.update_profile_info()

        panel = tk.Frame(self, bg="#172238", highlightbackground="#2d4162",
                         highlightthickness=1)
        panel.pack(fill="both", expand=True, padx=26, pady=15)

        top = tk.Frame(panel, bg="#172238")
        top.pack(fill="x", padx=16, pady=14)
        tk.Label(top, text="MES JEUX", bg="#172238", fg="white",
                 font=("Segoe UI", 14, "bold")).pack(side="left")
        ttk.Button(top, text="+ Ajouter un jeu", command=self.add_game).pack(side="right")

        columns = ("name", "vr", "path")
        self.table = ttk.Treeview(panel, columns=columns, show="headings", selectmode="browse")
        self.table.heading("name", text="Jeu")
        self.table.heading("vr", text="Compatibilité VR")
        self.table.heading("path", text="Fichier du jeu")
        self.table.column("name", width=270)
        self.table.column("vr", width=140, anchor="center")
        self.table.column("path", width=380)
        self.table.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        self.table.bind("<<TreeviewSelect>>", self.show_details)
        self.table.bind("<Double-1>", lambda _e: self.launch())

        actions = tk.Frame(panel, bg="#172238")
        actions.pack(fill="x", padx=16, pady=(0, 16))
        ttk.Button(actions, text="Lancer le jeu sélectionné", command=self.launch).pack(side="left")
        ttk.Button(actions, text="Modifier", command=self.edit_game).pack(side="left", padx=8)
        ttk.Button(actions, text="Supprimer", command=self.delete_game).pack(side="left")
        ttk.Button(actions, text="Ouvrir ALVR", command=self.open_alvr).pack(side="right")
        ttk.Button(actions, text="Installer APK sur Quest", command=self.install_apk).pack(side="right", padx=8)

        self.details = tk.Label(panel, text="Sélectionne un jeu pour afficher ses informations.",
                                bg="#172238", fg="#bdc9dc", anchor="w",
                                justify="left", wraplength=800)
        self.details.pack(fill="x", padx=17, pady=(0, 14))

        footer = tk.Frame(self, bg="#101522")
        footer.pack(fill="x", padx=26, pady=(0, 18))
        self.status = tk.Label(footer, text="Prêt. Le lanceur ne convertit pas les jeux classiques en VR.",
                               bg="#101522", fg="#9eabc2", font=("Segoe UI", 9))
        self.status.pack(anchor="w")

    def refresh(self):
        for item in self.table.get_children():
            self.table.delete(item)
        for i, game in enumerate(self.games):
            vr = "VR native" if game.get("vr") else "Non déclarée"
            path = game.get("exe") or "Aucun exécutable sélectionné"
            self.table.insert("", "end", iid=str(i), values=(game["name"], vr, path))

    def selected_index(self):
        selection = self.table.selection()
        return int(selection[0]) if selection else None

    def show_details(self, _event=None):
        i = self.selected_index()
        if i is None:
            return
        g = self.games[i]
        self.details.config(text=f"{g['name']}  |  {'VR native déclarée' if g.get('vr') else 'VR non déclarée'}\n{g.get('notes','')}")

    def add_game(self):
        path = filedialog.askopenfilename(
            title="Choisir le fichier exécutable du jeu",
            filetypes=[("Applications Windows", "*.exe"), ("Tous les fichiers", "*.*")]
        )
        if not path:
            return
        name = os.path.splitext(os.path.basename(path))[0]
        vr = messagebox.askyesno("Compatibilité VR", "Ce jeu possède-t-il un mode VR natif connu ?\n\nRéponds Oui uniquement si le jeu prend réellement en charge la VR.")
        self.games.append({"name": name, "exe": path, "vr": vr,
                           "notes": "Ajouté manuellement depuis le PC."})
        save_games(self.games)
        self.refresh()
        self.status.config(text=f"{name} ajouté à la bibliothèque.")

    def edit_game(self):
        i = self.selected_index()
        if i is None:
            messagebox.showinfo("AnkerGame VR", "Sélectionne d'abord un jeu.")
            return
        g = self.games[i]
        name = simpledialog.askstring("Nom du jeu", "Nom :", initialvalue=g["name"], parent=self)
        if name and name.strip():
            g["name"] = name.strip()
        path = filedialog.askopenfilename(
            title="Choisir le fichier .exe du jeu (Annuler = garder l'actuel)",
            filetypes=[("Applications Windows", "*.exe"), ("Tous les fichiers", "*.*")]
        )
        if path:
            g["exe"] = path
        g["vr"] = messagebox.askyesno("Compatibilité VR", "Ce jeu a-t-il un mode VR natif ?", initialvalue="yes" if g.get("vr") else "no")
        save_games(self.games)
        self.refresh()
        self.table.selection_set(str(i))

    def delete_game(self):
        i = self.selected_index()
        if i is None:
            return
        if messagebox.askyesno("Supprimer", f"Retirer {self.games[i]['name']} de la bibliothèque ?"):
            del self.games[i]
            save_games(self.games)
            self.refresh()
            self.details.config(text="Jeu retiré de la bibliothèque.")

    def update_profile_info(self):
        p = PROFILES[self.settings["headset"]]
        self.profile_info.config(text=(
            f"Réglages ALVR conseillés : résolution {p['resolution']} · débit {p['bitrate']} · "
            f"{p['refresh']} · codec {p['codec']}.  {p['notes']}"))

    def set_headset(self, name):
        if name in PROFILES:
            self.settings["headset"] = name
            self.headset_var.set(name)
            save_settings(self.settings)
            self.update_profile_info()

    def auto_detect(self):
        name, msg = detect_headset()
        if name:
            self.set_headset(name)
        self.status.config(text=msg)

    def open_alvr(self):
        exe = find_alvr()
        if not exe:
            if messagebox.askyesno("ALVR introuvable",
                                   "ALVR n'est pas installé.\n\nOuvrir la page de téléchargement (GitHub) ?"):
                webbrowser.open("https://github.com/alvr-org/ALVR/releases")
            return
        try:
            subprocess.Popen([exe], cwd=os.path.dirname(exe))
            self.status.config(text="ALVR lancé. Ouvre le client ALVR sur le Quest pour te connecter.")
        except OSError as e:
            messagebox.showerror("Erreur de lancement", str(e))

    def install_apk(self):
        adb = find_adb()
        if not adb:
            messagebox.showwarning("ADB introuvable", "Lance INSTALLER.bat, puis branche le casque en mode développeur.")
            return
        alvr_dir = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "ALVR")
        apk = filedialog.askopenfilename(title="Choisir l'APK à installer (ex. client ALVR)",
                                         initialdir=alvr_dir if os.path.isdir(alvr_dir) else None,
                                         filetypes=[("APK Android", "*.apk")])
        if not apk:
            return
        try:
            r = subprocess.run([adb, "install", "-r", apk], capture_output=True, text=True, timeout=180)
        except (OSError, subprocess.TimeoutExpired) as e:
            messagebox.showerror("Erreur ADB", str(e))
            return
        out = (r.stdout + r.stderr).strip()
        (messagebox.showinfo if r.returncode == 0 else messagebox.showerror)("Installation APK", out or "Terminé.")

    def launch(self):
        i = self.selected_index()
        if i is None:
            messagebox.showinfo("AnkerGame VR", "Sélectionne un jeu à lancer.")
            return
        game = self.games[i]
        exe = game.get("exe", "")
        if not exe or not os.path.isfile(exe):
            messagebox.showwarning(
                "Fichier du jeu manquant",
                "Ce jeu est dans la bibliothèque, mais son fichier .exe n'a pas encore été indiqué.\n\n"
                "Clique sur Modifier pour sélectionner le fichier .exe du jeu installé."
            )
            return
        if game.get("vr"):
            messagebox.showinfo(
                "Avant le lancement VR",
                "Ce jeu est marqué comme compatible VR. Vérifie que ton runtime VR et ton casque sont "
                "connectés et configurés. La compatibilité réelle dépend du jeu, du casque et des pilotes."
            )
        try:
            subprocess.Popen([exe], cwd=os.path.dirname(exe))
            self.status.config(text=f"Lancement demandé : {game['name']}")
        except OSError as e:
            messagebox.showerror("Erreur de lancement", str(e))

if __name__ == "__main__":
    Launcher().mainloop()
