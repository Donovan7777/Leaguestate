# db.py
# -----------------------------------------------------------------------------
# Rôle : tout ce qui touche la base de données
#        - chemins (BASE_DIR, DB_PATH, IMAGES_DIR, LAST_DB_FILE)
#        - schéma SQL (SCHEMA)
#        - helpers de connexion (connect, reconnect)
# -----------------------------------------------------------------------------

import sqlite3
import os
import sys

# ───────────────────────── PATHS / DB ──────────────────────────
# Truc simple : si on est dans un .exe, on prend le dossier de l’exe,
# sinon on prend le dossier du script. Pas plus compliqué que ça.
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Emplacements par défaut : fichier de BD, dossier d’images,
# et petit fichier texte qui retient la dernière BD ouverte.
DB_PATH = os.path.join(BASE_DIR, 'statteam.db')
IMAGES_DIR = os.path.join(BASE_DIR, 'images')
LAST_DB_FILE = os.path.join(BASE_DIR, 'last_db.txt')

# ────────────────────────── SCHEMA ─────────────────────────────
# NOTE IMPORTANTE:
# - On garde le schéma dans un gros string SQL et on l’applique avec executescript().
# - Toutes les FOREIGN KEY ont ON DELETE CASCADE → si tu supprimes une équipe,
#   ça nettoie les joueurs/matchs/stats liés automatiquement. Propre.
# - Index unique uq_teamowners_captain pour imposer « un capitaine = une seule équipe ».
SCHEMA = '''
CREATE TABLE IF NOT EXISTS Teams(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    logo TEXT,
    side TEXT NOT NULL DEFAULT 'my');

CREATE TABLE IF NOT EXISTS Players(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    logo TEXT,
    FOREIGN KEY(team_id) REFERENCES Teams(id) ON DELETE CASCADE);

CREATE TABLE IF NOT EXISTS Maps(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    image TEXT DEFAULT '');

CREATE TABLE IF NOT EXISTS Matches(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL,
    map_id INTEGER NOT NULL,
    rounds_won INTEGER DEFAULT 0,
    rounds_lost INTEGER DEFAULT 0,
    FOREIGN KEY(team_id) REFERENCES Teams(id) ON DELETE CASCADE,
    FOREIGN KEY(map_id) REFERENCES Maps(id) ON DELETE CASCADE);

CREATE TABLE IF NOT EXISTS PlayerStats(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    kills INTEGER DEFAULT 0,
    deaths INTEGER DEFAULT 0,
    bombs INTEGER DEFAULT 0,
    FOREIGN KEY(match_id) REFERENCES Matches(id) ON DELETE CASCADE,
    FOREIGN KEY(player_id) REFERENCES Players(id) ON DELETE CASCADE);

CREATE TABLE IF NOT EXISTS Captains(
    username TEXT PRIMARY KEY,
    password TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS TeamOwners(
    team_id INTEGER UNIQUE,
    captain TEXT NOT NULL,
    FOREIGN KEY(team_id) REFERENCES Teams(id) ON DELETE CASCADE,
    FOREIGN KEY(captain) REFERENCES Captains(username) ON DELETE CASCADE);

-- Règle d’affaires claire :
-- - 1 capitaine max par équipe (déjà UNIQUE(team_id))
-- - un capitaine ne peut pas gérer deux équipes.
-- On met un UNIQUE sur la colonne captain et c’est réglé.
CREATE UNIQUE INDEX IF NOT EXISTS uq_teamowners_captain ON TeamOwners(captain);
-- Fin des règles d’affaires
'''

# ----------------------------------------------------------------
# get_last_db
# ----------------------------------------------------------------
# Idée : on garde un « last_db.txt » pour rouvrir la dernière base utilisée.
# - Si le fichier existe ET que le chemin dedans est valide → on le renvoie.
# - Sinon, on retombe sur la DB par défaut (à côté de l’app).
# Bref : qualité de vie. Ça évite à l’usager de re-brows-er à chaque fois.
def get_last_db():
    """
    Recharge la dernière BD utilisée si on la retrouve (question de qualité de vie).
    S’il n’y a rien, on retombe sur la BD par défaut à côté de l’app.
    """
    if os.path.exists(LAST_DB_FILE):
        with open(LAST_DB_FILE, 'r', encoding='utf-8') as f:
            path = f.read().strip()
            if os.path.exists(path):
                return path
    return DB_PATH


# Chemin courant vers la BD (peut changer si l’usager en ouvre une autre)
CURRENT_DB_PATH = get_last_db()

# S’assurer que le dossier d’images existe pour éviter des erreurs bêtes.
os.makedirs(IMAGES_DIR, exist_ok=True)


# ----------------------------------------------------------------
# connect()
# ----------------------------------------------------------------
# Connexion initiale : on ouvre la BD courante, on active les FK
# et on applique le schéma.
def connect():
    """
    Ouvre la BD courante (CURRENT_DB_PATH), active les foreign keys
    et applique le schéma. Retourne (conn, cursor).
    """
    conn = sqlite3.connect(CURRENT_DB_PATH)
    cursor = conn.cursor()
    cursor.execute('PRAGMA foreign_keys = ON')
    cursor.executescript(SCHEMA)
    conn.commit()
    return conn, cursor


# ----------------------------------------------------------------
# reconnect(path, conn)
# ----------------------------------------------------------------
# But : « basculer » l’application sur une autre BD SQLite.
# - Ferme l’ancienne connexion (si présente)
# - Met à jour CURRENT_DB_PATH + sauvegarde dans last_db.txt
# - Ouvre la nouvelle connect, active les foreign keys, applique SCHEMA
# - La partie UI (show_login, overlays, messages) est gérée dans main.py.
def reconnect(path, conn=None):
    """
    Ouvre/rouvre une BD SQLite sur `path`, réapplique le schéma, met à jour
    CURRENT_DB_PATH et mémorise le choix dans LAST_DB_FILE.
    Retourne (conn, cursor) pour que main.py mette à jour ses globals.
    """
    global CURRENT_DB_PATH

    try:
        if conn is not None:
            conn.close()
    except Exception:
        # Si ça existait pas ou c’était déjà fermé : pas grave.
        pass

    CURRENT_DB_PATH = path

    # Garder la trace du dernier fichier ouvert
    with open(LAST_DB_FILE, 'w', encoding='utf-8') as f:
        f.write(CURRENT_DB_PATH)

    # Connexion + activer les clés étrangères (sinon SQLite laisse passer trop de trucs)
    conn = sqlite3.connect(CURRENT_DB_PATH)
    cursor = conn.cursor()
    cursor.execute('PRAGMA foreign_keys = ON')
    # On s’assure que tout le schéma est bien en place
    cursor.executescript(SCHEMA)
    conn.commit()
    return conn, cursor
