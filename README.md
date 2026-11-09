# AnkerGame VR

Un lanceur Windows pour organiser tes jeux et les jouer en VR sur un **Meta Quest 1, 2 ou 3** grâce au streaming [ALVR](https://github.com/alvr-org/ALVR).

> Le lanceur ne convertit pas un jeu classique en VR : le jeu doit avoir un mode VR natif ou un mod compatible.

## Installation rapide

1. Télécharge ou clone ce dépôt.
2. Double-clique sur **`INSTALLER.bat`**.

Le script installe ce qui manque et ignore ce qui est déjà présent :

| Composant | Rôle |
|---|---|
| Python 3 (avec Tkinter) | exécute le lanceur |
| ADB (platform-tools) | communique avec le casque en USB |
| Steam + SteamVR | requis par ALVR |
| ALVR (serveur PC + APK client) | streaming PC vers casque |
| Raccourci « AnkerGame VR » | sur le bureau |

## Premier lancement

1. Sur le casque : active le **mode développeur**, branche-le en USB et accepte le débogage USB.
2. Ouvre **AnkerGame VR** (raccourci bureau).
3. Clique **Détecter** : le profil Quest 1, 2 ou 3 est choisi automatiquement.
4. Clique **Installer APK sur Quest** et choisis `alvr_client_android.apk`.
5. Clique **Ouvrir ALVR**, lance le client ALVR dans le casque et accepte la connexion.
6. Clique **+ Ajouter un jeu**, choisis son `.exe`, puis double-clique dessus pour le lancer.

## Profils de casque

Choisis ton casque dans la liste : le lanceur affiche les réglages ALVR conseillés.

| Casque | Résolution | Débit | Fréquence | Codec |
|---|---|---|---|---|
| Quest 1 | basse à moyenne | 100 Mb/s | 72 Hz | H.264 |
| Quest 2 | moyenne | 150 Mb/s | 90 Hz | HEVC |
| Quest 3 | haute | 200 Mb/s | 90 à 120 Hz | HEVC ou AV1 |

Ces valeurs sont des points de départ : saisis-les dans ALVR puis ajuste selon ton Wi-Fi (5 GHz ou 6 GHz, routeur proche).

## Contenu du dépôt

- `AnkerGameVR/` : le lanceur Python (`AnkerGameVR.py`), sa bibliothèque `games.json`.
- `install.ps1` et `INSTALLER.bat` : l'installateur automatique.
- `AnkerVR_Quest1/` : projet Android Studio expérimental (voir ci-dessous).

## Projet Android expérimental

`AnkerVR_Quest1/` est une simple coquille d'application : il n'y a ni streaming, ni suivi, ni manettes. Pour jouer, utilise le client ALVR installé par `INSTALLER.bat`. Détails dans [`AnkerVR_Quest1/README_FR.md`](AnkerVR_Quest1/README_FR.md).

## Dépannage

- **« Aucun casque détecté »** : vérifie le câble USB de données, le mode développeur et l'autorisation affichée dans le casque.
- **ALVR ne se connecte pas** : PC et casque doivent être sur le même réseau Wi-Fi 5 GHz ou plus, avec SteamVR installé.
- **SteamVR manquant** : ouvre Steam, connecte-toi et installe SteamVR (le script le demande).

## Prérequis

Windows 10/11 avec `winget`, une carte graphique compatible VR et une connexion Internet.
