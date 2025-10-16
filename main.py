# ===============================================================
# StatTeam — Phase 3 (UI fidèle à ta maquette; Phase 4 en stubs)
# ===============================================================
# Dépendances pip :  pillow  pyperclip
# Bibliothèques stdlib : tkinter sqlite3 os shutil csv sys
#
# NOTE IMPORTANTE (lire avant d’éditer) :
#  - Cette version est « Phase 3 » : UI prête, navigation complète,
#    opérations de base (équipes, joueurs, maps, suppression de map),
#    gestion DB (créer/charger), export « Meilleurs joueurs (KD) » OK.
#  - Tout ce qui est Phase 4 est VISIBLE (boutons/icônes) mais désactivé.
#    Quand l’usager clique : message « Disponible en Phase 4 ».
#  - Les TODO ci-dessous te guident pour transformer graduellement cette
#    Phase 3 en ton app finale (rôles Capitaine/Admin, Analyse, Matchs,
#    autres exports, etc.), sans briser ce que tu présentes en ce moment.
#
# Recommandation pratique :
#  - Garde ce fichier comme « main_phase3.py » dans Git.
#  - Crée une branche « phase4 » où tu remplaces graduellement les stubs
#    (fonctions not_yet) par du vrai code. Merge quand chaque bloc est prêt.
#
# ===============================================================
# TABLE DES GROS TODO (Phase 4 — à faire plus tard)
# ---------------------------------------------------------------
# TODO[P4-LOGIN]  : Activer vraie connexion Capitaine/Admin (voir show_login)
# TODO[P4-OWNER]  : Lier capitaine ↔ équipe via TeamOwners (limiter actions)
# TODO[P4-MATCH]  : Écran « Ajouter match (2 équipes) » + PlayerStats
# TODO[P4-ANALYSE]: Graphiques WinRate par map + KD par joueur (matplotlib)
# TODO[P4-EXPORT] : Exports « Meilleures équipes » + « Maps les plus jouées »
# TODO[P4-UI]     : Remplacer placeholders côté droit (leaderboard, maps)
# TODO[P4-SECUR]  : Hasher les mots de passe (bcrypt ou passlib)
# TODO[P4-QOL]    : Menu « Éditer équipe » + « Éditer joueur » + suppression
# TODO[P4-VALID]  : Plus de validations (ex. doublon de nom d’équipe, etc.)
#
# (Tu trouveras des TODO détaillés à chaque endroit du code lié)
# ===============================================================

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sqlite3, os, sys, shutil, csv
from PIL import Image, ImageTk
import pyperclip

# ───────────────────── PATHS & APP FILES ─────────────────────
# Ici on règle les chemins et quelques noms d’images que TU utilises déjà.
# On check aussi si l’app est « gelée » (PyInstaller) pour déterminer le dossier de base.
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)    # quand c’est un .exe
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # quand on lance main.py

DB_PATH       = os.path.join(BASE_DIR, "statteam.db")
IMAGES_DIR    = os.path.join(BASE_DIR, "images")
LAST_DB_FILE  = os.path.join(BASE_DIR, "last_db.txt")

# Noms des images (doivent être dans /images) — on respecte ta convention
IMG_APP_LOGO  = os.path.join(IMAGES_DIR, "logoapp.png")
IMG_BACK      = os.path.join(IMAGES_DIR, "back.png")
IMG_ADD_TEAM  = os.path.join(IMAGES_DIR, "ajouterequipe.png")
IMG_ADD_MAP   = os.path.join(IMAGES_DIR, "ajoutermap.png")
IMG_ADD_MATCH = os.path.join(IMAGES_DIR, "ajoutermatch.png")
IMG_DB        = os.path.join(IMAGES_DIR, "database.png")
IMG_DEL_MAP   = os.path.join(IMAGES_DIR, "deletemap.png")
IMG_LOGOUT    = os.path.join(IMAGES_DIR, "logout.png")
IMG_PLACEHOLD = os.path.join(IMAGES_DIR, "anonymous.png")

os.makedirs(IMAGES_DIR, exist_ok=True)

# Petit filet de sécurité : si t’as pas de placeholder, on en crée un vite fait.
if not os.path.exists(IMG_PLACEHOLD):
    # (Pas besoin d’être fancy : une tuile foncée qui respecte ton thème.)
    im = Image.new("RGBA", (256,256), (18,22,30,255))
    im.save(IMG_PLACEHOLD)

# ───────────────────── DATABASE / SCHEMA ─────────────────────
# Schéma SQLite — on inclut déjà toutes les tables (même celles pour Phase 4),
# parce que ça te permet d’avoir une DB stable et d’éviter des migrations plus tard.
SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS Teams(
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT NOT NULL,
    logo    TEXT,
    side    TEXT NOT NULL DEFAULT 'my'
);

CREATE TABLE IF NOT EXISTS Players(
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL,
    name    TEXT NOT NULL,
    logo    TEXT,
    FOREIGN KEY(team_id) REFERENCES Teams(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Maps(
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name  TEXT UNIQUE NOT NULL,
    image TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS Matches(
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id     INTEGER NOT NULL,
    map_id      INTEGER NOT NULL,
    rounds_won  INTEGER DEFAULT 0,
    rounds_lost INTEGER DEFAULT 0,
    FOREIGN KEY(team_id) REFERENCES Teams(id) ON DELETE CASCADE,
    FOREIGN KEY(map_id)  REFERENCES Maps(id)  ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS PlayerStats(
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id  INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    kills     INTEGER DEFAULT 0,
    deaths    INTEGER DEFAULT 0,
    bombs     INTEGER DEFAULT 0,
    FOREIGN KEY(match_id)  REFERENCES Matches(id)  ON DELETE CASCADE,
    FOREIGN KEY(player_id) REFERENCES Players(id) ON DELETE CASCADE
);

/* Phase 4 — comptes + ownership (désactivé côté UI pour l’instant) */
CREATE TABLE IF NOT EXISTS Captains(
    username TEXT PRIMARY KEY,
    password TEXT NOT NULL   /* TODO[P4-SECUR]: Remplacer par un hash (bcrypt) */
);

CREATE TABLE IF NOT EXISTS TeamOwners(
    team_id INTEGER UNIQUE,
    captain TEXT NOT NULL,
    FOREIGN KEY(team_id) REFERENCES Teams(id) ON DELETE CASCADE,
    FOREIGN KEY(captain) REFERENCES Captains(username) ON DELETE CASCADE
);
"""

def _connect(db_path: str):
    """
    Ouvre/initialise la base (avec le schéma complet).
    - Retourne une connexion SQLite utilisable partout.
    - On active les FK ici pour que tout soit cohérent (DELETE CASCADE).
    """
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    conn.commit()
    return conn

def _last_db():
    """
    Recharge le dernier chemin DB utilisé (qualité de vie).
    - Si LAST_DB_FILE pointe vers un fichier valide : on l’utilise.
    - Sinon on retombe sur la DB par défaut (statteam.db).
    """
    if os.path.exists(LAST_DB_FILE):
        with open(LAST_DB_FILE, "r", encoding="utf-8") as f:
            p = f.read().strip()
            if os.path.exists(p):
                return p
    return DB_PATH

# Connexion initiale (prête pour Phase 3)
CURRENT_DB_PATH = _last_db()
conn = _connect(CURRENT_DB_PATH)
cur  = conn.cursor()

# ───────────────────── THEME / STYLES ───────────────────────
# Ici on garde la palette et les styles comme dans ta démo (dark + vert néon).
BG        = "#0f1115"
HEADER_BG = "#1a1d24"
PANEL_BG  = "#141823"
SUB_HDR   = "#222733"
FG        = "white"
MUTED     = "#b8c1cc"
ACCENT    = "#00ff88"

root = tk.Tk()
root.title("StatTeam")
root.geometry("1400x800")
root.configure(bg=BG)

# Style ttk — on colle au thème ‘clam’, puis on ajuste nos styles custom.
style = ttk.Style()
try:
    style.theme_use("clam")
except:
    pass
style.configure(".", background=BG, foreground=FG)
style.configure("TFrame", background=BG)
style.configure("Card.TFrame", background=PANEL_BG, relief="flat")
style.configure("Muted.TLabel", background=BG, foreground=MUTED)
style.configure("Neon.TButton", background=ACCENT, foreground="#04120d", padding=8, borderwidth=0)
style.map("Neon.TButton", background=[("active","#4dffb6")])
style.configure("Login.TEntry", fieldbackground="#0f141c", foreground=FG)

# Cache d’images pour que Tkinter ne « GC » pas nos PhotoImage trop tôt
_img_cache = {}

def load_img(path, size=(120,120)):
    """
    Charge une image, l’ajuste à size (thumbnail LANCZOS), et retourne un PhotoImage.
    - S’il y a un pépin (fichier manquant/corrompu), on tombe sur IMG_PLACEHOLD.
    - On met le résultat dans un cache pour éviter que Tkinter la perde.
    """
    try:
        im = Image.open(path)
    except Exception:
        im = Image.open(IMG_PLACEHOLD)
    im.thumbnail(size, Image.Resampling.LANCZOS if hasattr(Image,"Resampling") else Image.LANCZOS)
    ph = ImageTk.PhotoImage(im)
    _img_cache[(path, size, len(_img_cache))] = ph
    return ph

def copy_to_images(src):
    """
    Copie un fichier image de n’importe où vers /images et retourne juste le nom.
    - Si rien n’a été choisi : retourne "" (pas bloquant).
    - En cas d’erreur de copie : on ignore (on retourne quand même le basename).
    """
    if not src:
        return ""
    dest = os.path.join(IMAGES_DIR, os.path.basename(src))
    try:
        shutil.copy2(src, dest)
    except Exception:
        pass
    return os.path.basename(dest)

# ───────────────────── PHASE 4 STUBS ────────────────────────
def not_yet():
    """
    Petit helper pour les fonctions pas encore disponibles en Phase 3.
    - Affiche un message gentil qui dit « en Phase 4 ».
    - Pratique pour garder l’UI « complète » sans livrer le fond tout de suite.
    """
    messagebox.showinfo("🚧 Bientôt", "Disponible en Phase 4.")

# ───────────────────── DB OVERLAY (Phase 3) ─────────────────
def database_overlay():
    """
    Dialogue « Base de données » (Phase 3) :
    - Créer une base vide (utile si tu veux compartimenter par ligue).
    - Charger une base existante (ex.: travail en équipe, ou démo).
    - On mémorise le dernier choix dans last_db.txt.
    """
    ov = tk.Toplevel(root); ov.configure(bg=BG); ov.resizable(False, False); ov.grab_set()
    ov.title("Base de données")
    frm = ttk.Frame(ov, style="Card.TFrame"); frm.pack(fill="both", expand=True, padx=18, pady=18)
    ttk.Label(frm, text="NAVIGATION BASE DE DONNÉES", font=("Consolas", 18, "bold")).pack(pady=(6, 16), anchor="w")

    def create_new_db():
        """
        Crée une DB neuve (vide). On ferme la connexion actuelle proprement,
        on connecte la nouvelle, et on rafraîchit l’accueil.
        """
        newf = filedialog.asksaveasfilename(
            title="Créer une base vide",
            defaultextension=".db",
            filetypes=[("SQLite DB","*.db;*.sqlite"),("Tous fichiers","*.*")]
        )
        if not newf: return
        try:
            global conn, cur, CURRENT_DB_PATH
            conn.close()
        except:
            pass
        CURRENT_DB_PATH = newf
        with open(LAST_DB_FILE, "w", encoding="utf-8") as f:
            f.write(CURRENT_DB_PATH)
        conn = _connect(CURRENT_DB_PATH)
        cur  = conn.cursor()
        messagebox.showinfo("Succès", f"Nouvelle base créée:\n{os.path.basename(newf)}")
        ov.destroy(); load_home()

    def load_existing():
        """
        Charge une DB existante. Même logique que create_new_db, mais on
        choisit un fichier .db au lieu d’en créer un nouveau.
        """
        path = filedialog.askopenfilename(
            title="Charger une base existante",
            defaultextension=".db",
            filetypes=[("SQLite DB","*.db;*.sqlite"),("Tous fichiers","*.*")]
        )
        if not path: return
        try:
            global conn, cur, CURRENT_DB_PATH
            conn.close()
        except:
            pass
        CURRENT_DB_PATH = path
        with open(LAST_DB_FILE, "w", encoding="utf-8") as f:
            f.write(CURRENT_DB_PATH)
        conn = _connect(CURRENT_DB_PATH)
        cur  = conn.cursor()
        messagebox.showinfo("Succès", f"Base chargée:\n{os.path.basename(path)}")
        ov.destroy(); load_home()

    # Boutons d’action — simples, directs
    btnf = tk.Frame(frm, bg=PANEL_BG); btnf.pack(fill="x")
    tk.Button(btnf, text="Créer nouvelle base vide", bg=ACCENT, fg="#04120d", bd=0, command=create_new_db
             ).pack(pady=6, fill="x")
    tk.Button(btnf, text="Charger base existante", bg=ACCENT, fg="#04120d", bd=0, command=load_existing
             ).pack(pady=6, fill="x")
    tk.Button(frm, text="Fermer", bg=ACCENT, fg="#04120d", bd=0, command=ov.destroy).pack(pady=12)

# ───────────────────── MAP DELETE OVERLAY ───────────────────
def delete_map_overlay():
    """
    Dialogue « Supprimer une map » (Phase 3).
    - On liste les maps par nom; l’usager en choisit une et on supprime.
    - DELETE CASCADE va prendre soin de Matches liés à cette map si nécessaire.
    """
    ov = tk.Toplevel(root); ov.configure(bg=BG); ov.resizable(False, False); ov.grab_set()
    ov.title("Supprimer une map")
    frm = ttk.Frame(ov, style="Card.TFrame"); frm.pack(fill="both", expand=True, padx=18, pady=18)
    ttk.Label(frm, text="SUPPRIMER UNE MAP", font=("Consolas", 18, "bold")).pack(pady=(6, 16), anchor="w")

    cur.execute("SELECT id,name FROM Maps ORDER BY name COLLATE NOCASE")
    rows = cur.fetchall()
    if not rows:
        # Rien à supprimer : on informe poliment
        ttk.Label(frm, text="Aucune map.", style="Muted.TLabel").pack(pady=6)
        ttk.Button(frm, text="Fermer", command=ov.destroy).pack(pady=10)
        return

    names = [r[1] for r in rows]
    val = tk.StringVar(value=names[0])

    ttk.Label(frm, text="Choisir la map:").pack(anchor="w")
    ttk.OptionMenu(frm, val, val.get(), *names).pack(fill="x", pady=6)

    def confirm():
        """
        Confirmation + suppression SQL + refresh UI.
        """
        mid = next(i for i,n in rows if n == val.get())
        if messagebox.askyesno("Confirmer", f"Supprimer la map « {val.get()} » ?"):
            cur.execute("DELETE FROM Maps WHERE id=?", (mid,))
            conn.commit()
            messagebox.showinfo("OK", "Map supprimée.")
            ov.destroy(); load_home()

    bar = ttk.Frame(frm); bar.pack(fill="x", pady=(8,0))
    ttk.Button(bar, text="Annuler", command=ov.destroy).pack(side="left")
    ttk.Button(bar, text="Supprimer", style="Neon.TButton", command=confirm).pack(side="right")

# ───────────────────── ADD TEAM / PLAYER / MAP ──────────────
def add_team_overlay():
    """
    Ajoute une équipe (Phase 3).
    - Nom requis (max 35 chars pour éviter l’UI brisée).
    - Logo facultatif copié dans /images (on stocke seulement le basename).
    - Limite éducative à 12 équipes (ça garde le projet raisonnable).
    """
    ov = tk.Toplevel(root); ov.configure(bg=BG); ov.resizable(False, False); ov.grab_set()
    ov.title("Ajouter une équipe")
    frm = ttk.Frame(ov, style="Card.TFrame"); frm.pack(fill="both", expand=True, padx=18, pady=18)
    ttk.Label(frm, text="AJOUTER UNE ÉQUIPE", font=("Consolas", 18, "bold")).pack(pady=(6, 12), anchor="w")

    name_v, logo_v = tk.StringVar(), tk.StringVar()
    logo_sel = {"p": ""}   # petit conteneur mutable pour stocker le path choisi

    blk = ttk.Frame(frm, style="Card.TFrame"); blk.pack(fill="x", pady=6)
    ttk.Label(blk, text="Nom").pack(anchor="w", padx=8, pady=(8,2))
    ttk.Entry(blk, textvariable=name_v, style="Login.TEntry").pack(fill="x", padx=8, pady=(0,8))

    lg = ttk.Frame(frm, style="Card.TFrame"); lg.pack(fill="x", pady=6)
    ttk.Label(lg, text="Logo (optionnel)").pack(anchor="w", padx=8, pady=(8,2))
    ttk.Label(lg, textvariable=logo_v, style="Muted.TLabel").pack(anchor="w", padx=8)

    def choose_logo():
        """
        Ouvre un file picker; si l’usager choisit, on garde le path.
        """
        p = filedialog.askopenfilename(filetypes=[("Images","*.png;*.jpg;*.jpeg;*.webp;*.gif"),("Tous fichiers","*.*")])
        if p:
            logo_sel["p"] = p
            logo_v.set(os.path.basename(p))

    ttk.Button(lg, text="Choisir…", style="Neon.TButton", command=choose_logo).pack(anchor="w", padx=8, pady=8)

    bar = ttk.Frame(frm); bar.pack(fill="x", pady=(8,0))

    def save():
        """
        Valide le nom, respecte la limite, copie le logo et insère l’équipe.
        - Side = 'my' par défaut en Phase 3 (pas de notion d’Opposition encore).
        - TODO[P4-OWNER]: si capitaine connecté, créer TeamOwners(team_id,captain)
        """
        name = (name_v.get() or "").strip()
        if not name:
            messagebox.showerror("Erreur", "Nom requis.")
            return
        if len(name) > 35:
            messagebox.showerror("Erreur", "Le nom ne peut dépasser 35 caractères.")
            return
        cur.execute("SELECT COUNT(*) FROM Teams")
        if cur.fetchone()[0] >= 12:
            messagebox.showerror("Limite", "Limite éducative: 12 équipes.")
            return

        logo = copy_to_images(logo_sel["p"])
        cur.execute("INSERT INTO Teams(name,logo,side) VALUES (?,?,?)", (name, logo, "my"))
        conn.commit()
        ov.destroy(); load_home()

    ttk.Button(bar, text="Annuler", command=ov.destroy).pack(side="left")
    ttk.Button(bar, text="Enregistrer", style="Neon.TButton", command=save).pack(side="right")

def add_player_overlay(team_id: int):
    """
    Ajoute un joueur à une équipe donnée (Phase 3).
    - 40 joueurs max par équipe (limite scolaire pour éviter le pizza code).
    - Avatar facultatif copiée dans /images.
    - TODO[P4-QOL]: offrir édition/suppression de joueur plus tard.
    """
    ov = tk.Toplevel(root); ov.configure(bg=BG); ov.resizable(False, False); ov.grab_set()
    ov.title("Ajouter un joueur")
    frm = ttk.Frame(ov, style="Card.TFrame"); frm.pack(fill="both", expand=True, padx=18, pady=18)
    ttk.Label(frm, text="AJOUTER UN JOUEUR", font=("Consolas", 18, "bold")).pack(pady=(6, 12), anchor="w")

    name_v, logo_v = tk.StringVar(), tk.StringVar()
    logo_sel = {"p": ""}

    blk = ttk.Frame(frm, style="Card.TFrame"); blk.pack(fill="x", pady=6)
    ttk.Label(blk, text="Nom").pack(anchor="w", padx=8, pady=(8,2))
    ttk.Entry(blk, textvariable=name_v, style="Login.TEntry").pack(fill="x", padx=8, pady=(0,8))

    lg = ttk.Frame(frm, style="Card.TFrame"); lg.pack(fill="x", pady=6)
    ttk.Label(lg, text="Avatar (optionnel)").pack(anchor="w", padx=8, pady=(8,2))
    ttk.Label(lg, textvariable=logo_v, style="Muted.TLabel").pack(anchor="w", padx=8)

    def choose_logo():
        """
        File picker pour le portrait du joueur.
        """
        p = filedialog.askopenfilename(filetypes=[("Images","*.png;*.jpg;*.jpeg;*.webp;*.gif"),("Tous fichiers","*.*")])
        if p:
            logo_sel["p"] = p
            logo_v.set(os.path.basename(p))

    ttk.Button(lg, text="Choisir…", style="Neon.TButton", command=choose_logo).pack(anchor="w", padx=8, pady=8)

    bar = ttk.Frame(frm); bar.pack(fill="x", pady=(8,0))

    def save():
        """
        Valide le nom (max 35), applique la limite et insère le joueur.
        """
        name = (name_v.get() or "").strip()
        if not name:
            messagebox.showerror("Erreur", "Nom requis."); return
        if len(name) > 35:
            messagebox.showerror("Erreur", "Max 35 caractères."); return
        cur.execute("SELECT COUNT(*) FROM Players WHERE team_id=?", (team_id,))
        if cur.fetchone()[0] >= 40:
            messagebox.showerror("Limite", "Limite éducative: 40 joueurs par équipe."); return

        logo = copy_to_images(logo_sel["p"])
        cur.execute("INSERT INTO Players(team_id,name,logo) VALUES (?,?,?)", (team_id, name, logo))
        conn.commit()
        ov.destroy(); open_team(team_id)

    ttk.Button(bar, text="Annuler", command=ov.destroy).pack(side="left")
    ttk.Button(bar, text="Enregistrer", style="Neon.TButton", command=save).pack(side="right")

def add_map_overlay():
    """
    Ajoute une map (Phase 3).
    - Nom unique (contrainte UNIQUE).
    - Image facultative copiée dans /images.
    """
    ov = tk.Toplevel(root); ov.configure(bg=BG); ov.resizable(False, False); ov.grab_set()
    ov.title("Ajouter une map")
    frm = ttk.Frame(ov, style="Card.TFrame"); frm.pack(fill="both", expand=True, padx=18, pady=18)
    ttk.Label(frm, text="AJOUTER UNE MAP", font=("Consolas", 18, "bold")).pack(pady=(6, 12), anchor="w")

    name_v, img_v = tk.StringVar(), tk.StringVar()
    img_sel = {"p": ""}

    blk = ttk.Frame(frm, style="Card.TFrame"); blk.pack(fill="x", pady=6)
    ttk.Label(blk, text="Nom de la map").pack(anchor="w", padx=8, pady=(8,2))
    ttk.Entry(blk, textvariable=name_v, style="Login.TEntry").pack(fill="x", padx=8, pady=(0,8))

    lg = ttk.Frame(frm, style="Card.TFrame"); lg.pack(fill="x", pady=6)
    ttk.Label(lg, text="Image (optionnel)").pack(anchor="w", padx=8, pady=(8,2))
    ttk.Label(lg, textvariable=img_v, style="Muted.TLabel").pack(anchor="w", padx=8)

    def choose_img():
        """
        File picker pour une image de map (facultatif).
        """
        p = filedialog.askopenfilename(filetypes=[("Images","*.png;*.jpg;*.jpeg;*.webp;*.gif"),("Tous fichiers","*.*")])
        if p:
            img_sel["p"] = p
            img_v.set(os.path.basename(p))

    ttk.Button(lg, text="Choisir…", style="Neon.TButton", command=choose_img).pack(anchor="w", padx=8, pady=8)

    bar = ttk.Frame(frm); bar.pack(fill="x", pady=(8,0))

    def save():
        """
        Insère la map (respect du nom unique). Si doublon : message d’erreur.
        """
        name = (name_v.get() or "").strip()
        if not name:
            messagebox.showerror("Erreur", "Nom requis."); return
        if len(name) > 35:
            messagebox.showerror("Erreur", "Max 35 caractères."); return
        try:
            cur.execute("INSERT INTO Maps(name,image) VALUES (?,?)", (name, copy_to_images(img_sel["p"])))
            conn.commit(); ov.destroy(); load_home()
        except sqlite3.IntegrityError:
            messagebox.showerror("Erreur", "Cette map existe déjà.")

    ttk.Button(bar, text="Annuler", command=ov.destroy).pack(side="left")
    ttk.Button(bar, text="Enregistrer", style="Neon.TButton", command=save).pack(side="right")

# ───────────────────── EXPORT OVERLAY ───────────────────────
def export_best_players_csv():
    """
    Exporte un CSV « Meilleurs joueurs (KD) » (Phase 3).
    - Agrège kills/deaths pour chaque joueur.
    - KD = kills/deaths (si deaths == 0 → KD = kills pour éviter la division 0).
    - Tri décroissant par KD.
    """
    path = filedialog.asksaveasfilename(
        title="Enregistrer — Meilleurs joueurs (KD)",
        defaultextension=".csv",
        filetypes=[("CSV","*.csv")]
    )
    if not path: return

    # On prend toutes les stats du joueur sur tous les matchs confondus.
    cur.execute("""
        SELECT p.name, COALESCE(SUM(ps.kills),0) AS k, COALESCE(SUM(ps.deaths),0) AS d
        FROM Players p
        LEFT JOIN PlayerStats ps ON ps.player_id = p.id
        GROUP BY p.id
    """)
    rows = cur.fetchall()

    # Calcul du KD et tri
    data = []
    for name, k, d in rows:
        kd = (k/d) if d else (float(k) if k else 0.0)
        data.append((name, k, d, kd))
    data.sort(key=lambda x: x[3], reverse=True)

    # Écriture du CSV
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Player","Total_Kills","Total_Deaths","KD"])
        for name, k, d, kd in data:
            w.writerow([name, k, d, f"{kd:.2f}"])

    messagebox.showinfo("Succès", "CSV « Meilleurs joueurs » enregistré.")

def export_overlay():
    """
    Petit menu d’exports (Phase 3). On affiche 3 options :
    - « Meilleurs joueurs (KD) » → disponible maintenant
    - « Meilleures équipes »      → Phase 4
    - « Maps les plus jouées »    → Phase 4
    """
    ov = tk.Toplevel(root); ov.configure(bg=BG); ov.resizable(False, False); ov.grab_set()
    ov.title("Exports")
    frm = ttk.Frame(ov, style="Card.TFrame"); frm.pack(fill="both", expand=True, padx=18, pady=18)
    ttk.Label(frm, text="EXPORTER RAPPORTS", font=("Consolas", 18, "bold")).pack(pady=(6, 16), anchor="w")

    btns = tk.Frame(frm, bg=PANEL_BG); btns.pack(fill="x")
    tk.Button(btns, text="Meilleurs joueurs (KD)", bg=ACCENT, fg="#04120d", bd=0,
              command=lambda: (export_best_players_csv(), ov.destroy())).pack(pady=6, fill="x")
    tk.Button(btns, text="Meilleures équipes (Phase 4)", bg=ACCENT, fg="#04120d", bd=0,
              command=not_yet).pack(pady=6, fill="x")
    tk.Button(btns, text="Maps les plus jouées (Phase 4)", bg=ACCENT, fg="#04120d", bd=0,
              command=not_yet).pack(pady=6, fill="x")
    tk.Button(frm, text="Fermer", bg=ACCENT, fg="#04120d", bd=0, command=ov.destroy).pack(pady=10)

# ───────────────────── DATA HELPERS ─────────────────────────
def list_teams():
    """
    Retourne toutes les équipes triées par nom (insensible à la casse).
    - On expose juste ce qu’il faut (id, name, logo) pour alimenter la grille.
    """
    cur.execute("SELECT id, name, logo FROM Teams ORDER BY name COLLATE NOCASE")
    return cur.fetchall()

def list_players(team_id: int):
    """
    Retourne les joueurs d’une équipe, triés par nom.
    - Minimal mais suffisant en Phase 3 pour afficher et scroller.
    """
    cur.execute("SELECT id, name, logo FROM Players WHERE team_id=? ORDER BY name COLLATE NOCASE", (team_id,))
    return cur.fetchall()

# ───────────────────── TEAM VIEW (layout fidèle) ────────────
def open_team(team_id: int):
    """
    Ouvre la fiche d’une équipe :
    - En-tête : logo à gauche (gros), nom à droite + boutons d’action.
    - Colonne gauche : liste des joueurs (scrollable).
    - Colonne droite : placeholder pour les stats de maps (Phase 4).
    - Barre « Exporter » en bas (ouvre export_overlay).
    """
    # On nettoie la fenêtre pour mettre la fiche pleine largeur.
    for w in root.winfo_children():
        w.destroy()

    # Barre du haut : bouton retour (image « back.png » si présent)
    topbar = tk.Frame(root, bg=BG); topbar.pack(fill="x", pady=4, padx=4)
    back_img = load_img(IMG_BACK, (40,40)) if os.path.exists(IMG_BACK) else None
    tk.Button(
        topbar,
        image=back_img if back_img else None,
        text="← Retour" if not back_img else "",
        compound="left",
        bd=0, bg=BG, fg=FG, activebackground=BG,
        command=load_home
    ).pack(side="left")
    if back_img:
        # petite astuce pour conserver la référence image
        topbar.children[list(topbar.children)[0]].image = back_img

    # On récupère nom + logo de l’équipe
    cur.execute("SELECT name, logo FROM Teams WHERE id=?", (team_id,))
    r = cur.fetchone()
    if not r:
        # Si l’équipe n’existe plus (ex. supprimée entre-temps), on retourne à l’accueil.
        load_home(); return
    name, logo = r

    # Header (logo + nom + actions)
    header = tk.Frame(root, bg=BG); header.pack(fill="x", pady=8, padx=10)
    logo_box = tk.Frame(header, bg=BG, bd=2, highlightbackground=ACCENT, highlightthickness=2, width=250, height=250)
    logo_box.pack(side="left"); logo_box.pack_propagate(False)
    lpath = os.path.join(IMAGES_DIR, logo) if logo else IMG_PLACEHOLD
    big_logo = load_img(lpath, (240,240))
    tk.Label(logo_box, image=big_logo, bg=BG).pack(expand=True)

    info = tk.Frame(header, bg=BG); info.pack(side="left", fill="both", expand=True, padx=12)
    tk.Label(info, text=name, fg=FG, bg=BG, font=("Arial", 22, "bold")).pack(anchor="w", pady=8)

    # Actions à droite du nom : Ajouter joueur / Analyse(Phase 4)
    acts = tk.Frame(info, bg=BG); acts.pack(anchor="w", pady=6)
    tk.Button(acts, text="Ajouter joueur", bg=ACCENT, fg="#04120d", bd=0,
              command=lambda: add_player_overlay(team_id)).pack(side="left", padx=6)
    tk.Button(acts, text="Analyse (Phase 4)", bg=ACCENT, fg="#04120d", bd=0,
              command=not_yet).pack(side="left", padx=6)  # TODO[P4-ANALYSE]

    # Corps de page (deux colonnes)
    body = tk.Frame(root, bg=BG); body.pack(fill="both", expand=True, padx=12, pady=10)

    # Colonne gauche : joueurs (scroll)
    left_outer = tk.Frame(body, bg=ACCENT, bd=1)
    left_outer.pack(side="left", fill="both", expand=True, padx=10)
    left_inner = tk.Frame(left_outer, bg=BG); left_inner.pack(fill="both", expand=True, padx=4, pady=4)

    tk.Label(left_inner, text="Joueurs", fg=FG, bg=BG, font=("Consolas", 14, "bold")
            ).pack(anchor="w", padx=8, pady=(6, 4))

    pl_canvas = tk.Canvas(left_inner, bg=BG, highlightthickness=0)
    pl_scroll = tk.Scrollbar(left_inner, orient="vertical", command=pl_canvas.yview)
    pl_canvas.configure(yscrollcommand=pl_scroll.set)
    pl_scroll.pack(side="right", fill="y"); pl_canvas.pack(side="left", fill="both", expand=True)

    players_frame = tk.Frame(pl_canvas, bg=BG)
    wid_pl = pl_canvas.create_window((0,0), window=players_frame, anchor="nw")
    pl_canvas.bind("<Configure>", lambda e: pl_canvas.itemconfig(wid_pl, width=pl_canvas.winfo_width()))
    players_frame.bind("<Configure>", lambda e: pl_canvas.configure(scrollregion=pl_canvas.bbox("all")))

    # On dresse une petite ligne par joueur (photo + nom). Simple et propre pour Phase 3.
    for pid, pname, plogo in list_players(team_id):
        row = tk.Frame(players_frame, bg=BG); row.pack(fill="x", pady=6, padx=4)
        p_path = os.path.join(IMAGES_DIR, plogo) if plogo else IMG_PLACEHOLD
        p_img = load_img(p_path, (80,80))
        tk.Label(row, image=p_img, bg=BG).pack(side="left")
        row.img = p_img  # garder la référence pour Tkinter
        box = tk.Frame(row, bg=BG, bd=1, highlightbackground=ACCENT, highlightthickness=1)
        box.pack(side="left", fill="x", expand=True)
        top = tk.Frame(box, bg=BG); top.pack(fill="x")
        tk.Label(top, text=pname, fg=FG, bg=BG, font=("Arial", 12, "bold")).pack(side="left", padx=6)
        # TODO[P4-QOL] : boutons « éditer » / « supprimer » le joueur ici

    # Colonne droite : placeholder « maps/stats » (pour garder le même layout)
    right_outer = tk.Frame(body, bg=ACCENT, bd=1)
    right_outer.pack(side="left", fill="both", expand=True, padx=10)
    right_inner = tk.Frame(right_outer, bg=BG); right_inner.pack(fill="both", expand=True, padx=4, pady=4)
    tk.Label(right_inner, text="Maps (Phase 4 — stats détaillées ici)", fg=MUTED, bg=BG
            ).pack(anchor="w", padx=8, pady=8)
    # TODO[P4-MAPS] : tableau des maps jouées par l’équipe avec Games/WR par rounds

    # Bouton « Exporter » en bas (ouvre le mini menu d’exports)
    tk.Button(root, text="Exporter", bg=ACCENT, fg="#04120d", bd=0, font=("Arial", 12, "bold"),
              command=export_overlay).pack(pady=10)

# ───────────────────── HOME (fidèle à ton header) ───────────
def action_icon(container, img_path, fallback_text, command, size=(120,120)):
    """
    Place une icône cliquable dans le header (ou un bouton texte si l’image manque).
    - Ça reproduit la barre d’actions à droite que tu as déjà (logout, DB, etc.).
    """
    wrap = tk.Frame(container, bg=HEADER_BG); wrap.pack(side="right", padx=8, pady=8)
    if os.path.exists(img_path):
        ph = load_img(img_path, size)
        b = tk.Button(wrap, image=ph, bd=0, bg=HEADER_BG, activebackground=HEADER_BG, command=command)
        b.image = ph
        b.pack()
    else:
        # Si l’icône n’est pas fournie, on met un bouton texte pour garder l’action accessible.
        tk.Button(wrap, text=fallback_text, bg=ACCENT, fg="#04120d", bd=0, command=command).pack()

def add_team_tile(panel, tid, name, logo, col_count=5):
    """
    Ajoute une « tuile » d’équipe dans la grille (image 100x100 + nom sous l’image).
    - col_count=5 pour faire des rangées pas trop tassées en 1400x800.
    """
    idx = len(panel.grid_slaves())
    r, c = divmod(idx, col_count)
    cell = tk.Frame(panel, bg=BG); cell.grid(row=r, column=c, padx=10, pady=10, sticky="nsew")
    img_path = os.path.join(IMAGES_DIR, logo) if logo else IMG_PLACEHOLD
    ph = load_img(img_path, (100,100))
    btn = tk.Button(cell, image=ph, text=name, compound="top", bg=BG, fg=FG, bd=0, activebackground=BG,
                    command=lambda i=tid: open_team(i))
    btn.image = ph
    btn.pack()

def load_home():
    """
    Page d’accueil :
    - Header foncé avec le logo à gauche et les icônes d’actions à droite.
    - Colonne gauche : « League Teams » (toutes les équipes en grille).
    - Colonne droite : Leaderboard (placeholder Phase 4).
    - Barre « Exporter » en bas.
    """
    for w in root.winfo_children():
        w.destroy()

    # Header (gros logo + titre à gauche)
    header = tk.Frame(root, bg=HEADER_BG); header.pack(fill="x")
    lh = tk.Frame(header, bg=HEADER_BG); lh.pack(side="left", padx=10, pady=10)
    if os.path.exists(IMG_APP_LOGO):
        app_lg = load_img(IMG_APP_LOGO, (150,150))
        tk.Label(lh, image=app_lg, bg=HEADER_BG).pack(side="left", padx=(0,10))
        lh.logo = app_lg
    tk.Label(lh, text="𝕾𝖙𝖆𝖙𝖎𝖘𝖙𝖎𝖖𝖚𝖊 𝕬𝖕𝖕𝖑𝖎𝖈𝖆𝖙𝖎𝖔𝖓", font=("Consolas", 28, "bold"),
             bg=HEADER_BG, fg=FG).pack(side="left")

    # Actions à droite (même ordre visuel que ta maquette)
    # NB : Le plus à droite s’affiche en dernier (pack side=right)
    action_icon(header, IMG_LOGOUT,    "Se déconnecter", lambda: show_login(), size=(120,120))
    action_icon(header, IMG_ADD_MATCH, "Ajouter match (Phase 4)", not_yet, size=(120,120))  # TODO[P4-MATCH]
    action_icon(header, IMG_ADD_TEAM,  "Ajouter équipe", add_team_overlay, size=(120,120))
    action_icon(header, IMG_ADD_MAP,   "Ajouter map", add_map_overlay, size=(120,120))
    action_icon(header, IMG_DB,        "Database", database_overlay, size=(160,160))
    action_icon(header, IMG_DEL_MAP,   "Supprimer map", delete_map_overlay, size=(160,160))

    # Corps (2 colonnes)
    body = tk.Frame(root, bg=BG); body.pack(fill="both", expand=True, padx=20, pady=12)

    # Colonne gauche — League Teams
    left_column = tk.Frame(body, bg=BG); left_column.pack(side="left", fill="both", expand=True, padx=(0,10))
    league_outer = tk.Frame(left_column, bg=ACCENT, bd=1); league_outer.pack(fill="both", expand=True, pady=8)
    league_inner = tk.Frame(league_outer, bg=BG); league_inner.pack(fill="both", expand=True, padx=4, pady=4)
    bar = tk.Frame(league_inner, bg=SUB_HDR); bar.pack(fill="x")
    tk.Label(bar, text="LEAGUE TEAMS", font=("Consolas", 16, "bold"), bg=SUB_HDR, fg=FG).pack(pady=6)

    grid = tk.Frame(league_inner, bg=BG); grid.pack(fill="both", expand=True, pady=(6,2))
    teams = list_teams()
    if not teams:
        # Message d’amorce sympa pour les démos en classe
        tk.Label(grid, text="Aucune équipe. Cliquez « Ajouter équipe ».", bg=BG, fg=MUTED).pack(pady=16)
    else:
        cols = 5
        for tid, name, logo in teams:
            add_team_tile(grid, tid, name, logo, col_count=cols)
        for c in range(cols):
            grid.grid_columnconfigure(c, weight=1)

    # Colonne droite — Leaderboard (placeholder Phase 4)
    right_column = tk.Frame(body, bg=BG); right_column.pack(side="left", fill="both", expand=True, padx=(10,0))
    lb_outer = tk.Frame(right_column, bg=ACCENT, bd=1); lb_outer.pack(fill="both", expand=True)
    lb_inner = tk.Frame(lb_outer, bg=BG); lb_inner.pack(fill="both", expand=True, padx=4, pady=4)
    title_bar = tk.Frame(lb_inner, bg=SUB_HDR); title_bar.pack(fill="x")
    tk.Label(title_bar, text="LEADERBOARD (Phase 4)", font=("Consolas", 16, "bold"), bg=SUB_HDR, fg=FG).pack(pady=6)
    tk.Label(lb_inner, text="Classement détaillé à venir.", bg=BG, fg=MUTED).pack(pady=12)
    # TODO[P4-UI] : alimenter ce panneau avec get_leaderboard() + tri Wins

    # Bas de page — bouton Exporter (ouvre export_overlay)
    bottom = tk.Frame(root, bg=BG); bottom.pack(fill="x", padx=12, pady=(0,12))
    tk.Button(bottom, text="Exporter", bg=ACCENT, fg="#04120d", bd=0, command=export_overlay).pack(side="left")

# ───────────────────── LOGIN (même look; stubs) ─────────────
def show_login():
    """
    Écran d’accueil / login (Phase 3) :
    - Deux grosses tuiles : Visiteur (OK) et Capitaine (stub Phase 4).
    - Lien admin discret en bas à droite (stub Phase 4).
    - Le but ici : conserver ta « vibe UI » tout en contrôlant la portée Phase 3.
    """
    for w in root.winfo_children():
        w.destroy()

    canvas = tk.Canvas(root, bd=0, highlightthickness=0, bg=BG)
    canvas.pack(fill="both", expand=True)

    def draw_grad(_e=None):
        """
        Petit dégradé maison pour donner un peu de relief comme dans ta maquette.
        Rien de sorcier, mais ça rend le rendu plus propre.
        """
        canvas.delete("grad")
        w = canvas.winfo_width(); h = canvas.winfo_height()
        steps = 80
        for i in range(steps):
            c = i/steps
            r = int(15 + (10-15)*c); g = int(17 + (38-17)*c); b = int(21 + (29-21)*c)
            color = f"#{r:02x}{g:02x}{b:02x}"
            y0 = int(h*i/steps); y1 = int(h*(i+1)/steps)
            canvas.create_rectangle(0,y0,w,y1, outline="", fill=color, tags="grad")
        canvas.create_oval(-150,-150,350,350, fill="#0b3d2c", outline="", stipple="gray50", tags="grad")
    canvas.bind("<Configure>", draw_grad)

    # Carte centrale (bord vert + contenu)
    outer = tk.Frame(canvas, bg=ACCENT); outer.place(relx=0.5, rely=0.5, anchor="center", width=784, height=504)
    card  = tk.Frame(canvas, bg="#121726"); card.place(in_=outer, x=2, y=2, width=780, height=500)
    shadow = tk.Frame(canvas, bg="#000000"); shadow.place(in_=card, relx=0, rely=0, x=8, y=12, width=780, height=500)
    shadow.lower()

    # Bandeau haut (logo + title)
    header = tk.Frame(card, bg="#121726"); header.place(relx=0, rely=0, relwidth=1, y=18, height=72)
    if os.path.exists(IMG_APP_LOGO):
        icon = load_img(IMG_APP_LOGO, (64,64))
        lbl_icon = tk.Label(header, image=icon, bg="#121726"); lbl_icon.image = icon; lbl_icon.pack(side="left", padx=22)
    tk.Label(header, text="Bienvenue", font=("Consolas", 28, "bold"), bg="#121726", fg="white").pack(side="left")
    tk.Label(card, text="Choisissez votre mode d’accès", font=("Consolas", 12), bg="#121726", fg=MUTED
            ).place(x=22, y=100)

    tiles_wrap = tk.Frame(card, bg="#121726"); tiles_wrap.place(x=22, y=130, width=736, height=330)

    def tile(title_text, desc_text, emoji, command):
        """
        Construit une tuile (emoji + titre + description + bouton).
        - Hover simple (bord vert) pour donner un feedback visuel.
        """
        holder = tk.Frame(tiles_wrap, bg="#0f141f", bd=0, highlightthickness=1, highlightbackground="#1b2230")
        holder.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        top = tk.Frame(holder, bg="#0f141f"); top.pack(fill="x", padx=16, pady=(16,6))
        tk.Label(top, text=emoji, bg="#0f141f", fg="white", font=("Segoe UI Emoji", 24)).pack(side="left")
        tk.Label(top, text=title_text, font=("Consolas", 16, "bold"), bg="#0f141f", fg="white").pack(side="left", padx=8)
        tk.Label(holder, text=desc_text, font=("Consolas", 10), fg=MUTED, bg="#0f141f",
                 wraplength=220, justify="left").pack(anchor="w", padx=16, pady=(0,12))
        b = ttk.Button(holder, text="Continuer", style="Neon.TButton", command=command); b.pack(anchor="e", padx=16, pady=(0,16))
        def on_enter(_): holder.configure(highlightbackground=ACCENT, bg="#111a26")
        def on_leave(_): holder.configure(highlightbackground="#1b2230", bg="#0f141f")
        holder.bind("<Enter>", on_enter); holder.bind("<Leave>", on_leave)
        for ch in holder.winfo_children():
            ch.bind("<Enter>", on_enter); ch.bind("<Leave>", on_leave)
        return holder

    def go_visitor():
        """
        Mode visiteur (Phase 3) : on va directement à l’accueil.
        - TODO[P4-LOGIN]: quand les rôles seront actifs, tu garderas ici
          la logique « visiteur = read-only », capitaine/admin = actions.
        """
        load_home()

    def captain_stub():
        """
        Stub pour Capitaine (Phase 3) — affiche un message et reroute vers accueil.
        - TODO[P4-LOGIN]: pop modal de connexion (user/pass), valider dans Captains,
          setter une variable de session (current_captain), limiter les actions selon propriétaire.
        """
        messagebox.showinfo("Phase 4", "Connexion capitaine disponible en Phase 4.\n(Accès visiteur pour l’instant.)")
        load_home()

    def admin_stub():
        """
        Stub pour Admin (Phase 3) — même idée que capitaine.
        - TODO[P4-LOGIN]: prévoir un petit modal admin (ou utiliser un onglet dans show_login),
          valider les creds, activer les actions admin seulement (ex.: supprimer map, DB, etc.)
        """
        messagebox.showinfo("Phase 4", "Connexion administrateur disponible en Phase 4.\n(Accès visiteur pour l’instant.)")
        load_home()

    # Deux tuiles (visiteur OK; capitaine pas encore)
    tile("Continuer en visiteur",
         "Lecture seule des équipes et du leaderboard (placeholder).",
         "👀", go_visitor)
    tile("Connexion capitaine",
         "Gérez votre équipe et ajoutez des matchs (Phase 4).",
         "🧭", captain_stub)

    # Lien admin discret (bas droit)
    link = tk.Label(card, text="Connexion administrateur", font=("Consolas", 10, "underline"),
                    bg="#121726", fg=MUTED, cursor="hand2")
    link.place(relx=1.0, rely=1.0, anchor="se", x=-18, y=-14)
    link.bind("<Button-1>", lambda _e: admin_stub())
    link.bind("<Enter>", lambda _e: link.configure(fg=ACCENT))
    link.bind("<Leave>", lambda _e: link.configure(fg=MUTED))

# ───────────────────── START APP ────────────────────────────
# On démarre sur l’écran d’accueil/login.
show_login()
root.mainloop()

# ===============================================================
# ANNEXE — Mini feuille de route Phase 4 (résumé opérationnel)
# ---------------------------------------------------------------
# 1) [P4-LOGIN] show_login():
#    - Ajouter un modal « Capitaine » (user/pass). SELECT 1 FROM Captains WHERE username=? AND password=?
#      → POUR LA SÉCURITÉ en prod : hash du mot de passe (bcrypt) + salage. Pour le cours, simple OK.
#    - Variable globale current_role ('visitor'/'captain'/'admin') + current_captain (username) si captain.
#
# 2) [P4-OWNER] add_team_overlay():
#    - Si current_role == 'captain': insert dans TeamOwners (team_id, current_captain), et limiter
#      add/edit/delete aux équipes où team_id ∈ TeamOwners du capitaine.
#
# 3) [P4-MATCH] Ajouter un overlay « Ajouter match (2 équipes) » :
#    - Sélection Map + Équipe A + Équipe B + score (rounds A — B).
#    - Deux INSERT dans Matches (vue A et vue B), puis INSERT PlayerStats selon les cases cochées.
#    - Validation : équipes différentes, au moins 4 rounds joués, etc.
#
# 4) [P4-ANALYSE] Analyse par équipe :
#    - Graphe WinRate par map (rounds_won / (won+lost)), et KD par joueur (kills/deaths).
#    - matplotlib + FigureCanvasTkAgg (déjà connu). Thème foncé: ajuster tick/labels en blanc.
#
# 5) [P4-EXPORT] Finir les deux exports restants :
#    - « Meilleures équipes » (WinRate%).
#    - « Maps les plus jouées » (total rounds par map).
#
# 6) [P4-QOL] Éditer/Supprimer :
#    - Btn ✎ / 🗑 sur chaque joueur + sur l’équipe (dans open_team).
#    - Confirms avec messagebox.askyesno.
#
# 7) [P4-SECUR] MDP hashés :
#    - Ajouter colonne password_hash, migrer ou régénérer comptes de test.
#
# 8) [P4-UI] Leaderboard :
#    - Requêtes agrégées sur Matches pour compter les « wins » (rounds_won > rounds_lost).
#    - Ordonner DESC + fallback alpha par nom d’équipe.
#
# 9) [P4-VALID] Petits plus :
#    - Vérifier doublon de nom d’équipe (optionnel), contraintes de longueur, etc.
#
# Ce plan te permet d’avancer feature par feature sans casser la démo Phase 3.
# Bon courage — tu es pas mal dessus; reste juste à débloquer la Phase 4 proprement. 💪
# ===============================================================
