# AnkerVR — base Android pour Meta Quest 1

## Ce que contient cette archive
Cette archive est un **projet Android Studio de démarrage** nommé AnkerVR, configuré pour Android ARM64 et une cible minimale Android 10 (API 29), adaptée à l'environnement logiciel du Quest 1.

L'application affiche une interface immersive simple dans le casque.

## Limite importante
Cette version **n'est pas encore un client PCVR fonctionnel** : elle ne transmet pas la vidéo du PC, ne décode pas le flux ALVR et ne renvoie pas encore le suivi de tête ni les contrôleurs. Elle ne doit donc pas être présentée comme une solution permettant déjà de jouer à AnkerGame.

Pour obtenir le PCVR réel, il faut intégrer le moteur client ALVR correspondant à une version compatible Quest 1, puis relier son pipeline OpenXR/streaming à cette application. Le protocole ALVR est un composant spécialisé, pas quelque chose qu'une simple Activity Android peut remplacer.

## Compilation
1. Installe Android Studio et un JDK 17.
2. Ouvre le dossier `AnkerVR_Quest1` dans Android Studio.
3. Laisse Gradle synchroniser le projet.
4. Dans SDK Manager, installe Android SDK Platform 35 et les Build Tools proposés.
5. Choisis **Build > Build Bundle(s) / APK(s) > Build APK(s)**.
6. L'APK de debug sera normalement créé dans `app/build/outputs/apk/debug/app-debug.apk`.

## Installation sur Quest 1
1. Active le mode développeur du casque via les procédures officielles Meta (avec l'autorisation du titulaire du compte).
2. Active le débogage USB et accepte l'invite dans le casque.
3. Branche le casque au PC avec un câble USB de données.
4. Installe l'APK avec Android Studio ou `adb install -r app/build/outputs/apk/debug/app-debug.apk`.

## Prochaine étape pour le streaming
Utiliser le client ALVR officiel compatible Quest 1 et son serveur Windows. Documentation et versions :
- https://github.com/alvr-org/ALVR
- https://github.com/alvr-org/ALVR/releases

Vérifier les notes de version ALVR pour choisir une version qui prend explicitement en charge Quest 1. Le mode USB dépend aussi de la version du serveur, d'ADB et des pilotes du PC.
