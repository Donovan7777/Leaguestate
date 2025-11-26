
Simplement faire :
pip install pyperclip pillow matplotlib



# StatTeam — Application de Suivi de Performance pour Équipes FPS Compétitives
Conçue pour les joueurs d’eSport et les entraîneurs qui veulent une vision claire et locale des performances d’équipe et adverses.

---

## Description complète du projet

**StatTeam** est une application **de bureau locale** développée en **Python/Tkinter**. Elle permet d’enregistrer et d’analyser les performances d’une équipe FPS (Onward, CS:GO, Valorant, etc.) **sans dépendre d’un service web**.

**Fonctions principales :**
- Créer et gérer des **équipes** et leurs **joueurs** ;
- Gérer des **cartes (maps)** avec **images** ;
- **Enregistrer des matchs** (rounds gagnés/perdus) et **statistiques individuelles** (kills, deaths, bombs) ;
- **Visualiser** le **win-rate par carte** et les **ratios K/D** des joueurs via des **graphiques Matplotlib** intégrés ;
- **Exporter** des rapports (CSV) : meilleurs joueurs, meilleures équipes, cartes les plus jouées ;
- Gérer la **base de données SQLite** : nouvelle base, chargement, rappel du dernier fichier utilisé.

L’app convient aux **ligues locales**, **tournois LAN**, **écoles** et **petites organisations eSport** cherchant un outil **100% local**.

---

## Fonctionnalités détaillées

### Gestion des équipes
- Ajout, modification et suppression d’équipes (limite éducative : **12 équipes**).
- Logo personnalisé par équipe.
- Distinction **« My Team »** vs **« Opposition »**.
- Affichage du **win-rate global** (toutes maps confondues).

### Gestion des joueurs
- Ajout jusqu’à **40 joueurs** par équipe.
- Nom + avatar.
- **KD global** et **KD par carte**.
- Case **✔ A joué** pour cibler uniquement les joueurs ayant participé au match.

### Gestion des cartes (maps)
- Ajout/modification/suppression de cartes avec image.
- Affichage du **nombre total de parties/rounds** joués par carte.
- **Win-rate par rounds** automatiquement calculé.

### Enregistrement des matchs
- Sélection de la **map**.
- Saisie des **rounds gagnés/perdus** pour deux équipes (vue double).
- Saisie des stats par joueur : **Kills, Deaths, Bombs** (+ ✔ A joué).
- Insertion automatique des lignes côté **équipe A** et **équipe B**.

### Analyse avancée
- Graphiques Matplotlib :
  - **Win-rate de l’équipe par carte** ;
  - **Ratios K/D des joueurs**.
- Fiches joueurs : récap **par carte** (games, KD, win-rate, bombs) et **KD global**.

### Exportation de données
- CSV **Meilleurs joueurs** (KD global).
- CSV **Meilleures équipes** (win-rate global).
- CSV **Cartes les plus jouées** (rounds cumulés).
- Importables dans **Excel / Google Sheets / Discord**.

### Gestion de base de données
- **Créer** une base SQLite **vierge**.
- **Charger** une base existante.
- Mémorisation automatique du **dernier fichier `.db`** ouvert.

### Rôles & permissions (intégrés à l’UI)
- **Visiteur** : lecture seule.
- **Capitaine** : gère **sa** team (création unique), ajout de matchs et joueurs sur **son** équipe.
- **Admin** : accès complet (équipes, joueurs, maps, matchs, base).

---

## Arborescence du projet

```text
statteam/
├── main.py               # Application Tkinter (point d'entrée)
├── statteam.db           # Base SQLite (créée au 1er lancement si absente)
├── last_db.txt           # Mémorise le dernier chemin de DB utilisé
├── images/               # Ressources graphiques (logos & icônes)
│   ├── anonymous.png     # Placeholder par défaut
│   ├── back.png          # Icône bouton "retour"
│   ├── logoapp.png       # Logo de l’application (accueil)
│   ├── ajouterequipe.png # Icône "Ajouter équipe"
│   ├── ajoutermatch.png  # Icône "Ajouter match"
│   ├── ajoutermap.png    # Icône "Ajouter map"
│   ├── deletemap.png     # Icône "Supprimer map"
│   ├── database.png      # Icône "Database"
│   └── logout.png        # Icône "Se déconnecter"
└── README.md             # Ce document
# Prérequis techniques

- **Python 3.10+**
- **Bibliothèques standard :** `tkinter`, `sqlite3`, `os`, `shutil`, `csv`, `sys`
- **Dépendances externes (via pip) :**
  ```bash
  pip install pillow matplotlib pyperclip
Sous Linux, si tkinter manque : installez le paquet de votre distribution (ex. Debian/Ubuntu) :

bash
Copier le code
sudo apt install python3-tk
Démarrage rapide
Placez main.py dans un dossier dédié (ex. statteam/).

Créez un dossier images/ (même vide) à côté de main.py.

(Optionnel) Ajoutez vos images (logos, portraits, maps) dans images/.

Lancez l’application :

bash
Copier le code
python main.py
Au premier démarrage :

Le fichier statteam.db est créé automatiquement.

L’interface d’accueil s’ouvre (choix Visiteur / Capitaine / Admin).

Mode d’utilisation recommandé
(Admin) Ajouter les cartes de votre ligue (nom + image).

(Capitaine) Créer votre équipe (My Team).

(Optionnel) Ajouter des équipes Opposition pour vos adversaires.

Après chaque match :

Ouvrir l’équipe concernée ;

Cliquer sur Ajouter match ;

Saisir la map, les rounds, puis les stats par joueur (✔ A joué, K/D/B).

Dans la fiche d’équipe, utiliser Analyse pour :

Visualiser le Win-rate par map ;

Consulter les Ratios K/D par joueur.

Cliquer sur Exporter pour générer les rapports CSV.

Structure de la base de données
Table	Description
Teams	Équipe (nom, logo, side = my / opp)
Players	Joueur (nom, logo) rattaché à une équipe
Maps	Carte (nom unique, image optionnelle)
Matches	Match côté équipe (références : équipe + map ; rounds_won, rounds_lost)
PlayerStats	Statistiques par joueur et par match (kills, deaths, bombs)
Captains	Comptes capitaine (username, password — usage pédagogique, sécurité simplifiée)
TeamOwners	Association capitaine ↔ équipe (1 équipe par capitaine)

Toutes les relations pertinentes activent les clés étrangères avec ON DELETE CASCADE pour un nettoyage cohérent.

Cas d’usage réels
Équipes eSport scolaires / collégiales en ligue régionale.

Cours / projets académiques autour des bases de données et interfaces GUI.

Entraîneurs : suivi des forces/faiblesses par carte.

Capitaines : organisation des rôles selon K/D et l’impact par map.

LAN locaux : outil offline simple pour consigner les résultats.

Limitations connues
Version éducative limitée à :

12 équipes

40 joueurs par équipe

Application locale uniquement (pas de synchronisation cloud).

Authentification simplifiée (mots de passe non chiffrés, usage pédagogique).

Pas d’import CSV de matchs historiques (export CSV oui).

Améliorations prévues
Système de classement ELO/MMR.

Intégration Discord (export / partage automatisé).

Profils publics (export HTML / PDF des fiches joueurs / équipes).

Heatmaps et statistiques par manche / round.

Import CSV des historiques.

UI : peaufinage responsive / compatible tablette.

Auteur
Donovan Morin
Étudiant — Cégep de la Gaspésie et des Îles
Contact : (à personnaliser)

Licence
© 2025 Donovan Morin — Tous droits réservés.
Projet réalisé dans le cadre d’un cours collégial. Usage éducatif uniquement.