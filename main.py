# ================================================================
# IMPORTATIONS DE BIBLIOTHÈQUES
# ------------------------------------------------
# Tkinter et ttk : interface graphique native (widgets, styles, dialogues)
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# sqlite3 : base de données embarquée
# os/shutil/sys : gestion de fichiers, chemins et environnement
# pyperclip : gestion du presse-papier (copie de texte)
import sqlite3, os, shutil, pyperclip

# PIL (Pillow) : chargement/redimensionnement d’images
from PIL import Image, ImageTk

# Matplotlib : graphiques intégrés dans Tkinter
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

# CSV : export des rapports
import csv

# sys : pour détecter l’exécutable packagé (PyInstaller, etc.)
import sys

# ───────────────────────── PATHS / DB ──────────────────────────
# Petite astuce : si l’appli est « gelée » (exécutable), on récupère
# le dossier de l’exe; sinon on prend le dossier du script courant.
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Emplacements par défaut : fichier DB, dossier d’images, fichier
# qui mémorise le dernier chemin DB ouvert par l’utilisateur.
DB_PATH = os.path.join(BASE_DIR, 'statteam.db')
IMAGES_DIR = os.path.join(BASE_DIR, 'images')
LAST_DB_FILE = os.path.join(BASE_DIR, 'last_db.txt')

def get_last_db():
    """
    Essaie de recharger le dernier fichier .db utilisé (qualité de vie 👌).
    - Si LAST_DB_FILE existe et pointe vers un chemin valide : on l’utilise.
    - Sinon on retombe sur la DB par défaut dans le dossier de l’app.
    """
    if os.path.exists(LAST_DB_FILE):
        with open(LAST_DB_FILE, 'r', encoding='utf-8') as f:
            path = f.read().strip()
            if os.path.exists(path):
                return path
    return DB_PATH

# Chemin courant de la DB (peut changer si on en charge une autre)
CURRENT_DB_PATH = get_last_db()

# On s’assure que le dossier des images existe — pas d’erreur plus tard.
os.makedirs(IMAGES_DIR, exist_ok=True)

# ────────────────────────── SCHEMA ─────────────────────────────
# Schéma SQL complet. On crée au besoin (IF NOT EXISTS) toutes les tables
# nécessaires : équipes, joueurs, cartes, matchs, stats des joueurs,
# comptes de capitaines et relation « capitaine propriétaire » d’une équipe.
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
'''

def reconnect_db(path):
    """
    (Ré)ouvre une base SQLite donnée par `path`, réapplique le schéma
    et réinitialise le curseur. On mémorise aussi ce choix dans LAST_DB_FILE.
    Finalement, on revient à l’écran de connexion (UX propre).
    """
    global conn, cursor, CURRENT_DB_PATH
    try:
        conn.close()
    except:
        # Si conn n’existait pas encore ou était déjà fermée, on ignore.
        pass
    CURRENT_DB_PATH = path
    # On sauvegarde le dernier chemin DB pour la prochaine exécution.
    with open(LAST_DB_FILE, 'w', encoding='utf-8') as f:
        f.write(CURRENT_DB_PATH)
    # Connexion + activation des clés étrangères (très important avec SQLite).
    conn = sqlite3.connect(CURRENT_DB_PATH)
    cursor = conn.cursor()
    cursor.execute('PRAGMA foreign_keys = ON')
    # On s’assure que le schéma est en place (idempotent).
    cursor.executescript(SCHEMA)
    conn.commit()
    # On repart à l’accueil (utile si on change de DB en cours de route).
    show_login()

def load_db():
    """
    Demande à l’utilisateur de choisir une base existante (.db) via un
    dialogue. Si valide : on se reconnecte et on affiche un toast.
    Petit overlay pour « geler » l’UI pendant l’action.
    """
    ov = _overlay or show_overlay()
    try:
        file = filedialog.askopenfilename(
            title='Charger une base existante',
            defaultextension='.db',
            filetypes=[('SQLite DB','*.db;*.sqlite'),('Tous Fichiers','*.*')]
        )
        if not file:
            # L’utilisateur a annulé — on ferme l’overlay proprement.
            ov.destroy()
            return
        reconnect_db(file)
        messagebox.showinfo('Succès', f'Base chargée : {os.path.basename(file)}')
        ov.destroy()
    except Exception as e:
        messagebox.showerror('Erreur', f'Échec chargement : {e}')

# Connexion initiale
# On ouvre la DB « courante », active les FK et applique le schéma.
conn = sqlite3.connect(CURRENT_DB_PATH)
cursor = conn.cursor()
cursor.execute('PRAGMA foreign_keys = ON')
cursor.executescript(SCHEMA)
conn.commit()

# ───────────────────────── CONSTANTES UI ───────────────────────
# Palette et styles de base de l’interface (fond sombre, accent vert).
BG = '#0f1115'
HEADER_BG = '#1a1d24'
SUB_HDR = '#222733'
FG = 'white'
MUTED = '#b8c1cc'
ACCENT = '#00ff88'
ACCENT_DARK = '#0b3d2c'

# Fenêtre principale Tkinter
root = tk.Tk()
root.title('Statistic Team')
root.geometry('1400x800')  # Largeur/hauteur par défaut (écran desktop)
root.configure(bg=BG)

# États globaux (sélections ou écrans ouverts)
current_team = None
current_player = None
_overlay = None  # Frame plein-écran pour modales simples

# Session / rôles
current_role = None              # 'visitor' | 'captain' | 'admin'
current_captain = None           # username si captain

# Caches pour images (évite GC de Tkinter et rechargements)
team_images = {}
player_images = {}
map_images = {}

# ───────────────────────── UTILITAIRES STYLE ───────────────────
def configure_styles():
    """
    Configure les styles ttk utilisés partout (boutons neon, champs login,
    onglets notebook, etc.). On tente le thème 'clam' qui va bien avec ttk.
    """
    style = ttk.Style()
    try:
        style.theme_use('clam')
    except:
        pass  # Si le thème n’est pas dispo, on garde celui par défaut.

    # Style par défaut : fond sombre, texte clair
    style.configure('.', background=BG, foreground=FG)
    style.configure('TLabel', background=BG, foreground=FG)
    style.configure('TFrame', background=BG)

    # « Card » : panneaux légèrement distincts
    style.configure('Card.TFrame', background='#141823', relief='flat')

    # Label « Muet » : texte en gris
    style.configure('Muted.TLabel', foreground=MUTED, background=BG)

    # Bouton « néon » : look primaire vert punché
    style.configure('Neon.TButton',
                    background=ACCENT,
                    foreground='#04120d',
                    padding=8,
                    borderwidth=0)
    style.map('Neon.TButton', background=[('active', '#4dffb6')])

    # Champs d’entrée pour les écrans de login/create
    style.configure('Login.TEntry',
                    fieldbackground='#0f141c',
                    foreground=FG)
    style.map('Login.TEntry',
              fieldbackground=[('focus', '#0d1720')])

    # Notebook (onglets) pour le dialogue Capitaine
    style.configure('Login.TNotebook', background=BG, borderwidth=0)
    style.configure('Login.TNotebook.Tab', background=SUB_HDR, foreground=FG, padding=(10, 6))
    style.map('Login.TNotebook.Tab', background=[('selected', '#2a3142')])

# On applique nos styles une seule fois au démarrage.
configure_styles()

# ────────────────────────── HELPERS ────────────────────────────
def load_img(path, size=(100, 100)):
    """
    Charge une image depuis `path`, la réduit proportionnellement à `size`
    et la convertit en PhotoImage pour Tkinter.
    - Retourne None si ça foire (fichier manquant/corrompu).
    - Utilise LANCZOS (qualité supérieure) si dispo.
    """
    try:
        img = Image.open(path)
        try:
            resample = Image.Resampling.LANCZOS
        except AttributeError:
            resample = Image.LANCZOS
        img.thumbnail(size, resample)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None

def copy_to_images(src):
    """
    Copie un fichier image arbitraire dans le dossier IMAGES_DIR et
    retourne seulement le nom de fichier (à stocker en DB).
    - Si `src` est vide (pas d’image choisie), retourne ''.
    - En cas d’erreur de copie, on ignore (pas bloquant) et on retourne
      quand même le nom final pour rester cohérent.
    """
    if not src:
        return ''
    dest = os.path.join(IMAGES_DIR, os.path.basename(src))
    try:
        shutil.copy2(src, dest)
    except Exception:
        pass
    return os.path.basename(dest)

def show_overlay():
    """
    Crée un « overlay » plein écran (frame noire) qui désactive le fond,
    parfait pour construire des mini-modales maison. Si un overlay existe
    déjà, on le détruit pour éviter les doublons.
    """
    global _overlay
    if _overlay:
        _overlay.destroy()
    _overlay = tk.Frame(root, bg='#000000')
    _overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
    return _overlay

def is_admin():
    """Petit helper lisible : retourne True si la session est admin."""
    return current_role == 'admin'

def is_captain():
    """
    True si la session est « capitaine » ET qu’on a un username chargé.
    (Évite les états louches genre rôle défini sans identifiant.)
    """
    return current_role == 'captain' and current_captain is not None

def team_owned_by_current_captain(team_id: int) -> bool:
    """
    Vérifie que l’équipe `team_id` appartient bien au capitaine connecté
    (selon la table TeamOwners). Protège toutes les actions sensibles.
    """
    if not is_captain():
        return False
    cursor.execute('SELECT 1 FROM TeamOwners WHERE team_id=? AND captain=?', (team_id, current_captain))
    return cursor.fetchone() is not None

def captain_has_team(username: str) -> bool:
    """
    True si ce capitaine possède déjà une équipe (limite : 1 équipe par
    capitaine — logique d’affaires de l’app).
    """
    cursor.execute('SELECT 1 FROM TeamOwners WHERE captain=?', (username,))
    return cursor.fetchone() is not None

def get_captain_team_id(username: str):
    """
    Donne l’ID d’équipe associé au capitaine `username` si présent;
    sinon retourne None. Pratique pour alimenter la section « My Team ».
    """
    cursor.execute('SELECT team_id FROM TeamOwners WHERE captain=?', (username,))
    r = cursor.fetchone()
    return r[0] if r else None

# ───────────────────────── CONNEXION / INSCRIPTION ─────────────
def show_login():
    """
    Affiche l’écran de bienvenue / choix de rôle (visiteur, capitaine,
    admin). On nettoie l’UI au complet pour repartir propre.
    - Beau canvas en dégradé + carte centrée responsives.
    - Deux tuiles : visiteur/capitaine, et un petit lien pour admin.
    """
    # reset UI
    global _overlay, current_role, current_captain
    if _overlay:
        _overlay.destroy()
        _overlay = None
    for w in root.winfo_children():
        w.destroy()
    current_role = None
    current_captain = None

    # background gradient canvas
    canvas = tk.Canvas(root, bd=0, highlightthickness=0, bg=BG)
    canvas.pack(fill='both', expand=True)

    def draw_gradient(event=None):
        """
        Dessine un dégradé vertical manuel (petites bandes colorées)
        + un halo ovale pour donner un peu de profondeur. Appelé
        lorsqu’on redimensionne la fenêtre pour garder un rendu propre.
        """
        canvas.delete('grad')
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        steps = 80
        for i in range(steps):
            c = i / steps
            r = int(15 + (10-15)*c)
            g = int(17 + (38-17)*c)
            b = int(21 + (29-21)*c)
            color = f'#{r:02x}{g:02x}{b:02x}'
            y0 = int(h * i / steps)
            y1 = int(h * (i+1) / steps)
            canvas.create_rectangle(0, y0, w, y1, outline='', fill=color, tags='grad')
        # soft halo
        canvas.create_oval(-150, -150, 350, 350, fill=ACCENT_DARK, outline='', stipple='gray50', tags='grad')

    canvas.bind('<Configure>', draw_gradient)

    # Carte centrée : un cadre « outer » (bord vert) + « card » (contenu).
    outer = tk.Frame(canvas, bg=ACCENT, bd=0)
    outer.place(relx=0.5, rely=0.5, anchor='center')

    card = tk.Frame(canvas, bg='#121726', bd=0)
    card.place(in_=outer, x=2, y=2)
    card.configure(width=780, height=500)
    outer.configure(width=784, height=504)

    canvas.tag_lower('grad')
    card.lift()

    # Ombre portée toute simple pour le style.
    shadow = tk.Frame(canvas, bg='#000000', bd=0)
    shadow.place(in_=card, relx=0, rely=0, x=8, y=12, width=780, height=500)
    shadow.lower()

    # Bandeau haut de la carte (logo + titre « Bienvenue »)
    header = tk.Frame(card, bg='#121726')
    header.place(relx=0, rely=0, relwidth=1, y=18, height=72)

    icon = load_img(os.path.join(IMAGES_DIR, 'logoapp.png'), (64, 64))
    if icon:
        lbl_icon = tk.Label(header, image=icon, bg='#121726')
        lbl_icon.image = icon
        lbl_icon.pack(side='left', padx=22)

    title = tk.Label(header, text='Bienvenue', font=('Consolas', 28, 'bold'),
                     bg='#121726', fg='white')
    title.pack(side='left')

    subtitle = tk.Label(card, text="Choisissez votre mode d’accès",
                        font=('Consolas', 12), bg='#121726', fg=MUTED)
    subtitle.place(x=22, y=100)

    tiles_wrap = tk.Frame(card, bg='#121726')
    tiles_wrap.place(x=22, y=130, width=736, height=330)

    # helper to create role tiles
    def tile(parent, title_text, desc_text, emoji, command):
        """
        Construit une « tuile » cliquable avec un emoji, un titre,
        une description et un bouton « Continuer ». On ajoute un petit
        hover (survol) pour un feedback visuel.
        """
        holder = tk.Frame(parent, bg='#0f141f', bd=0, highlightthickness=1, highlightbackground='#1b2230')
        holder.pack(side='left', fill='both', expand=True, padx=8, pady=8)

        top = tk.Frame(holder, bg='#0f141f')
        top.pack(fill='x', padx=16, pady=(16, 6))
        lbl_emoji = tk.Label(top, text=emoji, bg='#0f141f', fg='white', font=('Segoe UI Emoji', 24))
        lbl_emoji.pack(side='left')

        lbl_title = tk.Label(top, text=title_text, font=('Consolas', 16, 'bold'), bg='#0f141f', fg='white')
        lbl_title.pack(side='left', padx=8)

        lbl_desc = tk.Label(holder, text=desc_text, font=('Consolas', 10), fg=MUTED, bg='#0f141f',
                            wraplength=220, justify='left')
        lbl_desc.pack(anchor='w', padx=16, pady=(0, 12))

        btn = ttk.Button(holder, text='Continuer', style='Neon.TButton', command=command)
        btn.pack(anchor='e', padx=16, pady=(0, 16))

        # Petits effets de survol : bord + fond plus clair.
        def on_enter(_):
            holder.configure(highlightbackground=ACCENT, bg='#111a26')
        def on_leave(_):
            holder.configure(highlightbackground='#1b2230', bg='#0f141f')
        holder.bind('<Enter>', on_enter); holder.bind('<Leave>', on_leave)
        for ch in holder.winfo_children():
            ch.bind('<Enter>', on_enter); ch.bind('<Leave>', on_leave)
        return holder

    # actions
    def go_visitor():
        """
        Passe en mode « visiteur » (lecture seule), réinitialise le
        capitaine courant et affiche la page d’accueil.
        """
        global current_role, current_captain
        current_role = 'visitor'
        current_captain = None
        load_home()

    def admin_dialog():
        """
        Mini-dialogue modal pour connexion admin (admin/admin).
        On n’encombre pas : juste deux champs + validation de base.
        """
        # simple modal for admin: admin/admin
        win = tk.Toplevel(root)
        win.title('Connexion administrateur')
        win.configure(bg=BG)
        win.resizable(False, False)
        win.grab_set()

        box = ttk.Frame(win, style='Card.TFrame')
        box.pack(padx=18, pady=18, fill='both', expand=True)

        ttk.Label(box, text='Accès administrateur', font=('Consolas', 18, 'bold')).pack(pady=(14, 8), anchor='w')

        frm = ttk.Frame(box); frm.pack(padx=10, pady=6, fill='x')
        ttk.Label(frm, text='Nom d’utilisateur').grid(row=0, column=0, sticky='w', pady=6)
        ttk.Label(frm, text='Mot de passe').grid(row=1, column=0, sticky='w', pady=6)
        u = tk.StringVar(); p = tk.StringVar()
        euser = ttk.Entry(frm, textvariable=u, style='Login.TEntry'); euser.grid(row=0, column=1, sticky='ew', padx=10, pady=6)
        epass = ttk.Entry(frm, textvariable=p, style='Login.TEntry', show='*'); epass.grid(row=1, column=1, sticky='ew', padx=10, pady=6)
        frm.columnconfigure(1, weight=1)

        def submit(_evt=None):
            """
            Valide les identifiants en dur. Si OK, on passe en admin
            et on charge l’accueil; sinon, on affiche une alerte.
            """
            if u.get().strip().lower() == 'admin' and p.get() == 'admin':
                global current_role, current_captain
                current_role = 'admin'
                current_captain = None
                win.destroy()
                load_home()
            else:
                messagebox.showerror('Erreur', 'Identifiants administrateur invalides.')

        btns = ttk.Frame(box); btns.pack(fill='x', padx=10, pady=(6, 12))
        ttk.Button(btns, text='Annuler', command=win.destroy).pack(side='left')
        ttk.Button(btns, text='Se connecter', style='Neon.TButton', command=submit).pack(side='right')

        # Enter submits
        euser.bind('<Return>', submit)
        epass.bind('<Return>', submit)
        win.bind('<Return>', submit)

    def captain_dialog():
        """
        Dialogue modal pour Capitaine :
        - Onglet « Se connecter »
        - Onglet « Créer un compte »
        Le tout avec validation simple et messages clairs.
        """
        win = tk.Toplevel(root)
        win.title('Capitaine — Connexion / Création')
        win.configure(bg=BG)
        win.resizable(False, False)
        win.grab_set()

        box = ttk.Frame(win, style='Card.TFrame')
        box.pack(padx=18, pady=18, fill='both', expand=True)

        t = ttk.Label(box, text='Accès capitaine', font=('Consolas', 18, 'bold'))
        t.pack(pady=(14, 8), anchor='w')

        nb = ttk.Notebook(box, style='Login.TNotebook')
        f_login = ttk.Frame(nb); f_create = ttk.Frame(nb)
        nb.add(f_login, text='Se connecter')
        nb.add(f_create, text='Créer un compte')
        nb.pack(fill='both', expand=True)

        # Login
        frmL = ttk.Frame(f_login); frmL.pack(fill='x', padx=14, pady=14)
        ttk.Label(frmL, text='Nom d’utilisateur').grid(row=0, column=0, sticky='w', pady=6)
        ttk.Label(frmL, text='Mot de passe').grid(row=1, column=0, sticky='w', pady=6)
        u1 = tk.StringVar(); p1 = tk.StringVar()
        ttk.Entry(frmL, textvariable=u1, style='Login.TEntry').grid(row=0, column=1, sticky='ew', padx=10, pady=6)
        ttk.Entry(frmL, textvariable=p1, style='Login.TEntry', show='*').grid(row=1, column=1, sticky='ew', padx=10, pady=6)
        frmL.columnconfigure(1, weight=1)

        def do_login():
            """
            Vérifie les identifiants dans la table Captains.
            Si succès : on retient le username et on bascule en rôle « captain ».
            """
            user = u1.get().strip()
            pwd = p1.get()
            if not user or not pwd:
                messagebox.showerror('Erreur', 'Veuillez saisir nom et mot de passe.')
                return
            cursor.execute('SELECT 1 FROM Captains WHERE username=? AND password=?', (user, pwd))
            if cursor.fetchone():
                global current_role, current_captain
                current_role = 'captain'
                current_captain = user
                win.destroy()
                load_home()
            else:
                messagebox.showerror('Erreur', 'Compte introuvable ou mot de passe invalide.')

        btnsL = ttk.Frame(f_login); btnsL.pack(fill='x', padx=14, pady=(4, 12))
        ttk.Button(btnsL, text='Se connecter', style='Neon.TButton', command=do_login).pack(side='right')

        # Create
        frmC = ttk.Frame(f_create); frmC.pack(fill='x', padx=14, pady=14)
        ttk.Label(frmC, text='Nom d’utilisateur').grid(row=0, column=0, sticky='w', pady=6)
        ttk.Label(frmC, text='Mot de passe').grid(row=1, column=0, sticky='w', pady=6)
        ttk.Label(frmC, text='Confirmer mot de passe').grid(row=2, column=0, sticky='w', pady=6)
        u2 = tk.StringVar(); p2 = tk.StringVar(); p3 = tk.StringVar()
        ttk.Entry(frmC, textvariable=u2, style='Login.TEntry').grid(row=0, column=1, sticky='ew', padx=10, pady=6)
        ttk.Entry(frmC, textvariable=p2, style='Login.TEntry', show='*').grid(row=1, column=1, sticky='ew', padx=10, pady=6)
        ttk.Entry(frmC, textvariable=p3, style='Login.TEntry', show='*').grid(row=2, column=1, sticky='ew', padx=10, pady=6)
        frmC.columnconfigure(1, weight=1)

        def do_create():
            """
            Crée un compte capitaine simple (username unique, mdp basique).
            On reste volontairement léger côté sécurité pour la démo.
            """
            user = u2.get().strip()
            pwd = p2.get()
            pwd2 = p3.get()
            if not user or not pwd:
                messagebox.showerror('Erreur', 'Veuillez saisir nom et mot de passe.')
                return
            if pwd != pwd2:
                messagebox.showerror('Erreur', 'Les mots de passe ne correspondent pas.')
                return
            try:
                cursor.execute('INSERT INTO Captains(username, password) VALUES (?,?)', (user, pwd))
                conn.commit()
                messagebox.showinfo('Succès', 'Compte capitaine créé. Vous pouvez vous connecter.')
                nb.select(f_login)
            except sqlite3.IntegrityError:
                messagebox.showerror('Erreur', 'Ce nom d’utilisateur existe déjà.')

        btnsC = ttk.Frame(f_create); btnsC.pack(fill='x', padx=14, pady=(4, 12))
        ttk.Button(btnsC, text='Créer le compte', style='Neon.TButton', command=do_create).pack(side='right')

    # tiles
    def tile_row():
        """
        Construit la rangée de deux tuiles : Visiteur et Capitaine.
        (On pourrait en ajouter d’autres ici au besoin.)
        """
        tile(tiles_wrap,
             'Continuer en visiteur',
             "Accès en lecture seule aux équipes de ligue et au leaderboard. Pas d’édition.",
             '👀',
             go_visitor)

        tile(tiles_wrap,
             'Connexion capitaine',
             "Gérez votre propre équipe (My Team) et ajoutez des matchs. Les autres équipes restent en lecture seule.",
             '🧭',
             captain_dialog)

    tile_row()

    # --- Small admin link at the bottom-right of the card ---
    # Petit lien discret pour ouvrir le dialogue admin.
    link = tk.Label(
        card,
        text='Connexion administrateur',
        font=('Consolas', 10, 'underline'),
        bg='#121726',
        fg=MUTED,
        cursor='hand2'
    )
    link.place(relx=1.0, rely=1.0, anchor='se', x=-18, y=-14)
    link.bind('<Button-1>', lambda _e: admin_dialog())
    link.bind('<Enter>', lambda _e: link.configure(fg=ACCENT))
    link.bind('<Leave>', lambda _e: link.configure(fg=MUTED))

# ─────────────────────── OVERLAYS : SUPPRIMER MAP ───────────────────────
def delete_map_overlay():
    """
    Overlay pour supprimer une carte (map). Réservé à l’admin.
    - Liste déroulante des maps existantes
    - Confirmation avant suppression
    - Refresh de l’accueil après coup
    """
    if not is_admin():
        return
    ov = show_overlay()
    cursor.execute('SELECT id,name FROM Maps ORDER BY name')
    maps = cursor.fetchall()
    if not maps:
        messagebox.showinfo('Info', 'Aucune map enregistrée.')
        ov.destroy()
        return
    sel = tk.StringVar(value=maps[0][1])
    def confirm():
        """
        Récupère l’ID de la map choisie et la supprime après confirmation
        (messagebox oui/non). Puis on recharge la page d’accueil.
        """
        mid = next(m[0] for m in maps if m[1] == sel.get())
        if messagebox.askyesno('Confirmer', f'Supprimer la map « {sel.get()} » ?'):
            cursor.execute('DELETE FROM Maps WHERE id=?', (mid,))
            conn.commit()
            ov.destroy()
            load_home()
    # Petite modale maison centrée
    frm = tk.Frame(ov, bg=SUB_HDR, bd=2, highlightbackground=ACCENT, highlightthickness=2)
    frm.place(relx=0.5, rely=0.5, anchor='center', width=520, height=320)
    tk.Label(frm, text='SUPPRIMER UNE MAP', fg=FG, bg=SUB_HDR,
             font=('Arial', 18, 'bold')).pack(pady=(14, 10))
    box = tk.Frame(frm, bg=BG, bd=2, highlightbackground=ACCENT, highlightthickness=2)
    box.pack(fill='x', padx=20, pady=12)
    ttk.Label(box, text='Choisir la map :').pack(anchor='w', padx=6, pady=(6,0))
    ttk.OptionMenu(box, sel, sel.get(), *[m[1] for m in maps]).pack(fill='x', padx=6, pady=6)
    bar = tk.Frame(frm, bg=SUB_HDR)
    bar.pack(side='bottom', fill='x', pady=14)
    opt = dict(bg=ACCENT, fg=BG, font=('Arial', 12, 'bold'), bd=0, padx=28, pady=10)
    tk.Button(bar, text='Annuler', command=ov.destroy, **opt).pack(side='left', expand=True, padx=45)
    tk.Button(bar, text='Supprimer', command=confirm, **opt).pack(side='right', expand=True, padx=45)

# ─────────────────────── OVERLAY : BASE DE DONNÉES ───────────────────────
def database_overlay():
    """
    Menu rapide de gestion de base de données (admin uniquement) :
    - Créer une nouvelle DB (option de sauvegarder l’actuelle)
    - Charger une DB existante
    """
    if not is_admin():
        return
    ov = show_overlay()
    def create_new_db():
        """
        Demande un nom de fichier pour une nouvelle DB vide. Offre aussi
        de faire une copie/sauvegarde de la base actuelle pour être safe.
        Ensuite on reconnecte l’app sur la nouvelle DB.
        """
        try:
            new_file = filedialog.asksaveasfilename(
                title='Créer une nouvelle base vide',
                defaultextension='.db',
                filetypes=[('SQLite DB','*.db;*.sqlite'),('Tous Fichiers','*.*')]
            )
            if not new_file:
                return
            if messagebox.askyesno(
                'Sauvegarde',
                'Sauvegarder la base actuelle dans un deuxième fichier avec un nom différent ? '
                'Dites non si vous êtes satisfait du nom de la base de données'
            ):
                backup = filedialog.asksaveasfilename(
                    title='Sauvegarde base actuelle',
                    defaultextension='.db',
                    filetypes=[('SQLite DB','*.db;*.sqlite'),('Tous Fichiers','*.*')]
                )
                if backup:
                    shutil.copy2(CURRENT_DB_PATH, backup)
            reconnect_db(new_file)
            messagebox.showinfo('Succès', f'Nouvelle base créée : {os.path.basename(new_file)}')
            ov.destroy()
        except Exception as e:
            messagebox.showerror('Erreur', f'Échec création : {e}')
    # Cadre de l’overlay
    frm = tk.Frame(ov, bg=SUB_HDR, bd=2, highlightbackground=ACCENT, highlightthickness=2)
    frm.place(relx=0.5, rely=0.5, anchor='center', width=520, height=280)
    tk.Label(frm, text='NAVIGATION BASE DE DONNÉES', fg=FG, bg=SUB_HDR,
             font=('Arial', 18, 'bold')).pack(pady=(14,10))
    btn_frame = tk.Frame(frm, bg=BG)
    btn_frame.pack(fill='both', expand=True, pady=10)
    opt_btn = dict(bg=ACCENT, fg=BG, font=('Arial', 12, 'bold'), bd=0, width=20, pady=10)
    tk.Button(btn_frame, text='Créer nouvelle base vide', command=create_new_db, **opt_btn).pack(pady=5)
    tk.Button(btn_frame, text='Charger base existante', command=load_db, **opt_btn).pack(pady=5)
    bar = tk.Frame(frm, bg=SUB_HDR)
    bar.pack(side='bottom', fill='x', pady=8)
    tk.Button(bar, text='Annuler', command=ov.destroy, bg=ACCENT, fg=BG,
              font=('Arial', 12, 'bold'), bd=0, padx=20, pady=8).pack()

# ======================================================================
# ADD/EDIT TEAM / MAP / PLAYER (permissions respectées)
# ======================================================================
def add_team_overlay():
    """
    Overlay d’ajout d’équipe.
    - Admin : peut choisir le « side » (my/opp)
    - Capitaine : side forcé à 'my' + une seule équipe permise
    - Limites « freemium » : max 12 équipes si pas admin
    """
    if current_role not in ('admin', 'captain'):
        return
    ov = show_overlay()
    name_v, logo_v = tk.StringVar(), tk.StringVar()
    side_v = tk.StringVar(value='my')
    logo_path = ''

    def browse():
        """Ouvre un sélecteur de fichier image pour le logo d’équipe."""
        nonlocal logo_path
        p = filedialog.askopenfilename()
        if p:
            logo_path = p
            logo_v.set(os.path.basename(p))

    def save():
        """
        Valide et enregistre l’équipe :
        - Nom requis et <= 35 caractères
        - Si capitaine a déjà une équipe : on bloque
        - Copie du logo dans /images
        - En tant que capitaine : on enregistre le propriétaire (TeamOwners)
        """
        name = name_v.get().strip()
        if not name:
            messagebox.showerror('Erreur', 'Nom requis')
            return
        if len(name) > 35:
            messagebox.showerror('Erreur', 'Le nom ne peut pas dépasser 35 caractères')
            return
        if is_captain():
            if captain_has_team(current_captain):
                messagebox.showerror('Limite', "Vous avez déjà une équipe associée à votre compte.")
                return
            side = 'my'
        else:
            side = side_v.get()
        cursor.execute('SELECT COUNT(*) FROM Teams')
        if cursor.fetchone()[0] >= 12 and not is_admin():
            messagebox.showerror('Limite atteinte', 'Version payante nécessaire pour plus de 12 équipes')
            return
        logo = copy_to_images(logo_path)
        cursor.execute('INSERT INTO Teams(name,logo,side) VALUES (?,?,?)',
                       (name, logo, side))
        new_team_id = cursor.lastrowid
        if is_captain():
            cursor.execute('INSERT INTO TeamOwners(team_id, captain) VALUES (?,?)',
                           (new_team_id, current_captain))
        conn.commit()
        ov.destroy()
        load_home()

    # Modale centrée avec champs
    root.update_idletasks()
    max_h = root.winfo_height() - 60
    frm = tk.Frame(ov, bg=SUB_HDR, bd=2, highlightbackground=ACCENT, highlightthickness=2)
    frm.place(relx=0.5, rely=0.5, anchor='center', width=620, height=min(540, max_h))
    tk.Label(frm, text='AJOUTER UNE ÉQUIPE', fg=FG, bg=SUB_HDR,
             font=('Arial', 18, 'bold')).pack(pady=(14, 10))
    fld = tk.Frame(frm, bg=BG, bd=2, highlightbackground=ACCENT, highlightthickness=2)
    fld.pack(fill='x', padx=20, pady=8)
    ttk.Label(fld, text='Nom :').pack(anchor='w', padx=6, pady=(6,0))
    ttk.Entry(fld, textvariable=name_v, style='Login.TEntry').pack(fill='x', padx=6, pady=4)
    if is_admin():
        sd = tk.Frame(frm, bg=BG, bd=2, highlightbackground=ACCENT, highlightthickness=2)
        sd.pack(fill='x', padx=20, pady=8)
        ttk.Label(sd, text='Side :').pack(anchor='w', padx=6, pady=(6,0))
        ttk.Radiobutton(sd, text='My Team', variable=side_v, value='my').pack(anchor='w', padx=12, pady=2)
        ttk.Radiobutton(sd, text='Opposition', variable=side_v, value='opp').pack(anchor='w', padx=12, pady=(0,6))
    else:
        # Rappel UX pour le rôle capitaine
        info = tk.Label(frm, text="(En tant que capitaine, l’équipe sera votre « My Team »)",
                        bg=SUB_HDR, fg=FG)
        info.pack(pady=4)
    lg = tk.Frame(frm, bg=BG, bd=2, highlightbackground=ACCENT, highlightthickness=2)
    lg.pack(fill='x', padx=20, pady=8)
    ttk.Label(lg, text='Logo :').pack(anchor='w', padx=6, pady=(6,0))
    tk.Button(lg, text='Choisir logo', command=browse, bg=ACCENT, fg='#04120d', bd=0).pack(anchor='w', padx=6, pady=4)
    tk.Label(lg, textvariable=logo_v, bg=BG, fg=FG).pack(anchor='w', padx=6, pady=(0,6))
    bar = tk.Frame(frm, bg=SUB_HDR)
    bar.pack(side='bottom', fill='x', pady=12)
    ttk.Button(bar, text='Annuler', command=ov.destroy).pack(side='left', padx=45)
    ttk.Button(bar, text='Enregistrer', style='Neon.TButton', command=save).pack(side='right', padx=45)

def edit_team_overlay(tid):
    """
    Édition d’une équipe existante (admin ou capitaine propriétaire).
    - On préremplit les champs avec les données actuelles.
    - Admin peut changer le « side »; capitaine non (forcé à 'my').
    """
    if not (is_admin() or team_owned_by_current_captain(tid)):
        return
    cursor.execute('SELECT name,logo,side FROM Teams WHERE id=?', (tid,))
    nm, lg, sd = cursor.fetchone()
    ov = show_overlay()
    name_v, logo_v, side_v = tk.StringVar(value=nm), tk.StringVar(value=lg or ''), tk.StringVar(value=sd)
    logo_path = os.path.join(IMAGES_DIR, lg) if lg else ''
    def browse():
        """Choisit un nouveau logo si désiré."""
        nonlocal logo_path
        p = filedialog.askopenfilename()
        if p:
            logo_path = p
            logo_v.set(os.path.basename(p))
    def save():
        """
        Applique les changements (avec validations de base) et met à jour la DB.
        """
        name = name_v.get().strip()
        if not name:
            messagebox.showerror('Erreur', 'Nom requis')
            return
        if len(name) > 35:
            messagebox.showerror('Erreur', 'Le nom ne peut pas dépasser 35 caractères')
            return
        logo = copy_to_images(logo_path)
        new_side = side_v.get() if is_admin() else 'my'
        cursor.execute('UPDATE Teams SET name=?,logo=?,side=? WHERE id=?',
                       (name, logo, new_side, tid))
        conn.commit()
        ov.destroy()
        open_team(tid)
    # Modale
    root.update_idletasks()
    max_h = root.winfo_height() - 60
    frm = tk.Frame(ov, bg=SUB_HDR, bd=2, highlightbackground=ACCENT, highlightthickness=2)
    frm.place(relx=0.5, rely=0.5, anchor='center', width=620, height=min(540, max_h))
    tk.Label(frm, text='MODIFIER ÉQUIPE', fg=FG, bg=SUB_HDR,
             font=('Arial', 18, 'bold')).pack(pady=(14, 10))
    fld = tk.Frame(frm, bg=BG, bd=2, highlightbackground=ACCENT, highlightthickness=2)
    fld.pack(fill='x', padx=20, pady=8)
    ttk.Label(fld, text='Nom :').pack(anchor='w', padx=6, pady=(6,0))
    ttk.Entry(fld, textvariable=name_v, style='Login.TEntry').pack(fill='x', padx=6, pady=4)
    if is_admin():
        sd_frame = tk.Frame(frm, bg=BG, bd=2, highlightbackground=ACCENT, highlightthickness=2)
        sd_frame.pack(fill='x', padx=20, pady=8)
        ttk.Label(sd_frame, text='Side :').pack(anchor='w', padx=6, pady=(6,0))
        ttk.Radiobutton(sd_frame, text='My Team', variable=side_v, value='my').pack(anchor='w', padx=12, pady=2)
        ttk.Radiobutton(sd_frame, text='Opposition', variable=side_v, value='opp').pack(anchor='w', padx=12, pady=(0,6))
    lgf = tk.Frame(frm, bg=BG, bd=2, highlightbackground=ACCENT, highlightthickness=2)
    lgf.pack(fill='x', padx=20, pady=8)
    ttk.Label(lgf, text='Logo :').pack(anchor='w', padx=6, pady=(6,0))
    tk.Button(lgf, text='Choisir logo', command=browse, bg=ACCENT, fg='#04120d', bd=0).pack(anchor='w', padx=6, pady=4)
    tk.Label(lgf, textvariable=logo_v, bg=BG, fg=FG).pack(anchor='w', padx=6, pady=(0,6))
    bar = tk.Frame(frm, bg=SUB_HDR)
    bar.pack(side='bottom', fill='x', pady=12)
    ttk.Button(bar, text='Annuler', command=ov.destroy).pack(side='left', padx=45)
    ttk.Button(bar, text='Enregistrer', style='Neon.TButton', command=save).pack(side='right', padx=45)

def add_map_overlay():
    """
    Ajout d’une map (admin seulement).
    - Nom unique (contrainte SQL UNIQUE)
    - Image optionnelle copiée dans /images
    """
    if not is_admin(): return
    ov = show_overlay()
    name_v, img_v = tk.StringVar(), tk.StringVar()
    img_path = ''
    def browse():
        """Choix de l’image de la map (facultatif)."""
        nonlocal img_path
        p = filedialog.askopenfilename()
        if p:
            img_path = p
            img_v.set(os.path.basename(p))
    def save():
        """Valide le nom et pousse la map dans la DB, image comprise."""
        name = name_v.get().strip()
        if not name:
            messagebox.showerror('Erreur', 'Nom requis'); return
        if len(name) > 35:
            messagebox.showerror('Erreur', 'Le nom ne peut pas dépasser 35 caractères'); return
        cursor.execute('INSERT OR IGNORE INTO Maps(name) VALUES (?)', (name,))
        img = copy_to_images(img_path)
        cursor.execute('UPDATE Maps SET image=? WHERE name=?', (img, name))
        conn.commit()
        ov.destroy(); load_home()
    # UI de la modale
    frm = tk.Frame(ov, bg=SUB_HDR, bd=2, highlightbackground=ACCENT, highlightthickness=2)
    frm.place(relx=0.5, rely=0.5, anchor='center', width=620, height=400)
    tk.Label(frm, text='AJOUTER UNE MAP', fg=FG, bg=SUB_HDR, font=('Arial', 18, 'bold')).pack(pady=(14, 10))
    fld = tk.Frame(frm, bg=BG, bd=2, highlightbackground=ACCENT, highlightthickness=2)
    fld.pack(fill='x', padx=20, pady=8)
    ttk.Label(fld, text='Nom de la map :').pack(anchor='w', padx=6, pady=(6,0))
    ttk.Entry(fld, textvariable=name_v, style='Login.TEntry').pack(fill='x', padx=6, pady=4)
    imgf = tk.Frame(frm, bg=BG, bd=2, highlightbackground=ACCENT, highlightthickness=2)
    imgf.pack(fill='x', padx=20, pady=8)
    ttk.Label(imgf, text='Image :').pack(anchor='w', padx=6, pady=(6,0))
    tk.Button(imgf, text='Choisir image', command=browse, bg=ACCENT, fg='#04120d', bd=0).pack(anchor='w', padx=6, pady=4)
    tk.Label(imgf, textvariable=img_v, bg=BG, fg=FG).pack(anchor='w', padx=6, pady=(0,6))
    bar = tk.Frame(frm, bg=SUB_HDR); bar.pack(side='bottom', fill='x', pady=12)
    ttk.Button(bar, text='Annuler', command=ov.destroy).pack(side='left', padx=45)
    ttk.Button(bar, text='Enregistrer', style='Neon.TButton', command=save).pack(side='right', padx=45)

def edit_map_overlay(mid):
    """
    Modification d’une map (admin).
    - Permet de renommer et de remplacer l’image.
    """
    if not is_admin(): return
    cursor.execute('SELECT name,image FROM Maps WHERE id=?', (mid,))
    r = cursor.fetchone()
    if not r: return
    nm, img = r
    ov = show_overlay()
    name_v, img_v = tk.StringVar(value=nm), tk.StringVar(value=img or '')
    img_path = os.path.join(IMAGES_DIR, img) if img else ''
    def browse():
        """Sélection d’une nouvelle image si dispo."""
        nonlocal img_path
        p = filedialog.askopenfilename()
        if p:
            img_path = p; img_v.set(os.path.basename(p))
    def save():
        """Valide et met à jour le nom + l’image de la map."""
        name = name_v.get().strip()
        if not name:
            messagebox.showerror('Erreur', 'Nom requis'); return
        if len(name) > 35:
            messagebox.showerror('Erreur', 'Le nom ne peut pas dépasser 35 caractères'); return
        new_img = copy_to_images(img_path)
        cursor.execute('UPDATE Maps SET name=?,image=? WHERE id=?', (name, new_img, mid))
        conn.commit(); ov.destroy(); load_home()
    # UI
    frm = tk.Frame(ov, bg=SUB_HDR, bd=2, highlightbackground=ACCENT, highlightthickness=2)
    frm.place(relx=0.5, rely=0.5, anchor='center', width=620, height=400)
    tk.Label(frm, text='MODIFIER MAP', fg=FG, bg=SUB_HDR, font=('Arial', 18, 'bold')).pack(pady=(14, 10))
    fld = tk.Frame(frm, bg=BG, bd=2, highlightbackground=ACCENT, highlightthickness=2)
    fld.pack(fill='x', padx=20, pady=8)
    ttk.Label(fld, text='Nom de la map :').pack(anchor='w', padx=6, pady=(6,0))
    ttk.Entry(fld, textvariable=name_v, style='Login.TEntry').pack(fill='x', padx=6, pady=4)
    imgf = tk.Frame(frm, bg=BG, bd=2, highlightbackground=ACCENT, highlightthickness=2)
    imgf.pack(fill='x', padx=20, pady=8)
    ttk.Label(imgf, text='Image :').pack(anchor='w', padx=6, pady=(6,0))
    tk.Button(imgf, text='Choisir image', command=browse, bg=ACCENT, fg='#04120d', bd=0).pack(anchor='w', padx=6, pady=4)
    tk.Label(imgf, textvariable=img_v, bg=BG, fg=FG).pack(anchor='w', padx=6, pady=(0,6))
    bar = tk.Frame(frm, bg=SUB_HDR); bar.pack(side='bottom', fill='x', pady=12)
    ttk.Button(bar, text='Annuler', command=ov.destroy).pack(side='left', padx=45)
    ttk.Button(bar, text='Enregistrer', style='Neon.TButton', command=save).pack(side='right', padx=45)

def add_player_overlay(team_id):
    """
    Ajout d’un joueur dans une équipe donnée (admin ou capitaine propriétaire).
    - Limite « freemium » : 40 joueurs max si pas admin.
    """
    if not (is_admin() or team_owned_by_current_captain(team_id)):
        return
    ov = show_overlay()
    name_v, logo_v = tk.StringVar(), tk.StringVar()
    logo_path = ''
    def browse():
        """Choisit un portrait/logo pour le joueur (facultatif)."""
        nonlocal logo_path
        p = filedialog.askopenfilename()
        if p:
            logo_path = p; logo_v.set(os.path.basename(p))
    def save():
        """Valide nom (<=35) et insère le joueur; copie l’image s’il y en a une."""
        name = name_v.get().strip()
        if not name:
            messagebox.showerror('Erreur', 'Nom requis'); return
        if len(name) > 35:
            messagebox.showerror('Erreur', 'Le nom ne peut pas dépasser 35 caractères'); return
        cursor.execute('SELECT COUNT(*) FROM Players WHERE team_id=?', (team_id,))
        if cursor.fetchone()[0] >= 40 and not is_admin():
            messagebox.showerror('Limite atteinte', 'Version payante nécessaire pour plus de 40 joueurs'); return
        logo = copy_to_images(logo_path)
        cursor.execute('INSERT INTO Players(team_id,name,logo) VALUES (?,?,?)', (team_id, name, logo))
        conn.commit(); ov.destroy(); open_team(team_id)
    # UI
    frm = tk.Frame(ov, bg=SUB_HDR, bd=2, highlightbackground=ACCENT, highlightthickness=2)
    frm.place(relx=0.5, rely=0.5, anchor='center', width=620, height=400)
    tk.Label(frm, text='AJOUTER UN JOUEUR', fg=FG, bg=SUB_HDR, font=('Arial', 18, 'bold')).pack(pady=(14, 10))
    fld = tk.Frame(frm, bg=BG, bd=2, highlightbackground=ACCENT, highlightthickness=2)
    fld.pack(fill='x', padx=20, pady=8)
    ttk.Label(fld, text='Nom :').pack(anchor='w', padx=6, pady=(6,0))
    ttk.Entry(fld, textvariable=name_v, style='Login.TEntry').pack(fill='x', padx=6, pady=4)
    lg = tk.Frame(frm, bg=BG, bd=2, highlightbackground=ACCENT, highlightthickness=2)
    lg.pack(fill='x', padx=20, pady=8)
    ttk.Label(lg, text='Logo :').pack(anchor='w', padx=6, pady=(6,0))
    tk.Button(lg, text='Choisir logo', command=browse, bg=ACCENT, fg='#04120d', bd=0).pack(anchor='w', padx=6, pady=4)
    tk.Label(lg, textvariable=logo_v, bg=BG, fg=FG).pack(anchor='w', padx=6, pady=(0,6))
    bar = tk.Frame(frm, bg=SUB_HDR); bar.pack(side='bottom', fill='x', pady=12)
    ttk.Button(bar, text='Annuler', command=ov.destroy).pack(side='left', padx=45)
    ttk.Button(bar, text='Enregistrer', style='Neon.TButton', command=save).pack(side='right', padx=45)

def edit_player_overlay(pid):
    """
    Modification d’un joueur existant (admin ou capitaine propriétaire).
    - On recharge l’équipe parente pour vérifier les permissions.
    """
    cursor.execute('SELECT team_id,name,logo FROM Players WHERE id=?', (pid,))
    r = cursor.fetchone()
    if not r: return
    team_id, nm, lg = r
    if not (is_admin() or team_owned_by_current_captain(team_id)): return
    ov = show_overlay()
    name_v, logo_v = tk.StringVar(value=nm), tk.StringVar(value=lg or '')
    logo_path = os.path.join(IMAGES_DIR, lg) if lg else ''
    def browse():
        """Remplacer l’image du joueur (optionnel)."""
        nonlocal logo_path
        p = filedialog.askopenfilename()
        if p:
            logo_path = p; logo_v.set(os.path.basename(p))
    def save():
        """Met à jour nom + logo selon validation basique."""
        name = name_v.get().strip()
        if not name:
            messagebox.showerror('Erreur', 'Nom requis'); return
        if len(name) > 35:
            messagebox.showerror('Erreur', 'Le nom ne peut pas dépasser 35 caractères'); return
        logo = copy_to_images(logo_path)
        cursor.execute('UPDATE Players SET name=?,logo=? WHERE id=?', (name, logo, pid))
        conn.commit(); ov.destroy(); open_team(team_id)
    # UI
    frm = tk.Frame(ov, bg=SUB_HDR, bd=2, highlightbackground=ACCENT, highlightthickness=2)
    frm.place(relx=0.5, rely=0.5, anchor='center', width=620, height=400)
    tk.Label(frm, text='MODIFIER JOUEUR', fg=FG, bg=SUB_HDR, font=('Arial', 18, 'bold')).pack(pady=(14, 10))
    fld = tk.Frame(frm, bg=BG, bd=2, highlightbackground=ACCENT, highlightthickness=2)
    fld.pack(fill='x', padx=20, pady=8)
    ttk.Label(fld, text='Nom :').pack(anchor='w', padx=6, pady=(6,0))
    ttk.Entry(fld, textvariable=name_v, style='Login.TEntry').pack(fill='x', padx=6, pady=4)
    lgf = tk.Frame(frm, bg=BG, bd=2, highlightbackground=ACCENT, highlightthickness=2)
    lgf.pack(fill='x', padx=20, pady=8)
    ttk.Label(lgf, text='Logo :').pack(anchor='w', padx=6, pady=(6,0))
    tk.Button(lgf, text='Choisir logo', command=browse, bg=ACCENT, fg='#04120d', bd=0).pack(anchor='w', padx=6, pady=4)
    tk.Label(lgf, textvariable=logo_v, bg=BG, fg=FG).pack(anchor='w', padx=6, pady=(0,6))
    bar = tk.Frame(frm, bg=SUB_HDR); bar.pack(side='bottom', fill='x', pady=12)
    ttk.Button(bar, text='Annuler', command=ov.destroy).pack(side='left', padx=45)
    ttk.Button(bar, text='Enregistrer', style='Neon.TButton', command=save).pack(side='right', padx=45)

def delete_team(tid):
    """
    Supprime une équipe (admin ou capitaine propriétaire) après
    confirmation. Les FK (ON DELETE CASCADE) nettoient le reste.
    """
    if not (is_admin() or team_owned_by_current_captain(tid)): return
    if messagebox.askyesno('Confirmer', 'Supprimer cette équipe ?'):
        cursor.execute('DELETE FROM Teams WHERE id=?', (tid,))
        conn.commit(); load_home()

def delete_player(pid):
    """
    Supprime un joueur (admin/capitaine propriétaire). On récupère
    d’abord l’équipe pour recharger la vue au bon endroit après.
    """
    cursor.execute('SELECT team_id FROM Players WHERE id=?', (pid,))
    r = cursor.fetchone()
    if not r: return
    team_id = r[0]
    if not (is_admin() or team_owned_by_current_captain(team_id)): return
    if messagebox.askyesno('Confirmer', 'Supprimer ce joueur ?'):
        cursor.execute('DELETE FROM Players WHERE id=?', (pid,))
        conn.commit(); open_team(team_id)

# ======================================================================
# Exports CSV
# ======================================================================
def export_best_players():
    """
    Exporte en CSV le classement des joueurs par ratio K/D global.
    - Agrège kills/deaths par joueur (toutes maps/parties confondues).
    - Colonne KD formatée à 2 décimales.
    """
    path = filedialog.asksaveasfilename(
        title='Enregistrer rapport Meilleurs Joueurs',
        defaultextension='.csv',
        filetypes=[('CSV','*.csv')]
    )
    if not path: return
    cursor.execute('''
        SELECT p.name, COALESCE(SUM(ps.kills),0), COALESCE(SUM(ps.deaths),0)
        FROM Players p
        LEFT JOIN PlayerStats ps ON ps.player_id=p.id
        GROUP BY p.id
    ''')
    data = cursor.fetchall()
    players = [(name, k, d, (k/d if d else k)) for name, k, d in data]
    players.sort(key=lambda x: x[3], reverse=True)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Joueur','Total_Kills','Total_Deaths','KD'])
        for name, k, d, kd in players:
            writer.writerow([name, k, d, f"{kd:.2f}"])
    messagebox.showinfo('Succès', 'Rapport Meilleurs Joueurs enregistré.')

def export_best_teams():
    """
    Exporte en CSV le classement des équipes par « WinRate » (en %).
    - WinRate = victoires / (victoires + défaites) * 100
    - Classement décroissant
    """
    path = filedialog.asksaveasfilename(
        title='Enregistrer rapport Meilleures Équipes',
        defaultextension='.csv',
        filetypes=[('CSV','*.csv')]
    )
    if not path: return
    cursor.execute('''
        SELECT t.name, COALESCE(SUM(m.rounds_won),0), COALESCE(SUM(m.rounds_lost),0)
        FROM Teams t
        LEFT JOIN Matches m ON m.team_id=t.id
        GROUP BY t.id
    ''')
    data = cursor.fetchall()
    teams = [(name, w, l, (w/(w+l)*100 if (w+l) else 0)) for name, w, l in data]
    teams.sort(key=lambda x: x[3], reverse=True)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Équipe','Victoires','Défaites','WinRate_%'])
        for name, w, l, wr in teams:
            writer.writerow([name, w, l, f"{wr:.1f}"])
    messagebox.showinfo('Succès', 'Rapport Meilleures Équipes enregistré.')

def export_most_played_maps():
    """
    Exporte en CSV les maps « les plus jouées » selon le nombre total
    de rounds (won+lost) accumulés sur chaque map.
    """
    path = filedialog.asksaveasfilename(
        title='Enregistrer rapport Maps les plus jouées',
        defaultextension='.csv',
        filetypes=[('CSV','*.csv')]
    )
    if not path: return
    cursor.execute('''
        SELECT mp.name,
               COALESCE(SUM(mt.rounds_won),0)+COALESCE(SUM(mt.rounds_lost),0)
        FROM Maps mp
        LEFT JOIN Matches mt ON mt.map_id=mp.id
        GROUP BY mp.id
    ''')
    data = cursor.fetchall()
    maps = sorted(data, key=lambda x: x[1], reverse=True)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Map','Total_Rounds'])
        for name, total in maps:
            writer.writerow([name, total])
    messagebox.showinfo('Succès', 'Rapport Maps les plus jouées enregistré.')

def export_overlay():
    """
    Petit menu d’export (overlay) pour choisir quel rapport produire.
    On délègue ensuite aux fonctions ci-dessus.
    """
    ov = show_overlay()
    frm = tk.Frame(ov, bg=SUB_HDR, bd=2, highlightbackground=ACCENT, highlightthickness=2)
    frm.place(relx=0.5, rely=0.5, anchor='center', width=400, height=280)
    tk.Label(frm, text='EXPORTER RAPPORTS', fg=FG, bg=SUB_HDR,
             font=('Arial', 18, 'bold')).pack(pady=(14,10))
    btn_frame = tk.Frame(frm, bg=BG); btn_frame.pack(fill='both', expand=True, pady=10)
    opt_btn = dict(bg=ACCENT, fg='#04120d', font=('Arial', 12, 'bold'), bd=0, width=25, pady=8)
    tk.Button(btn_frame, text='1 - Meilleurs joueurs', command=export_best_players, **opt_btn).pack(pady=4)
    tk.Button(btn_frame, text='2 - Meilleures équipes', command=export_best_teams, **opt_btn).pack(pady=4)
    tk.Button(btn_frame, text='3 - Maps les plus jouées', command=export_most_played_maps, **opt_btn).pack(pady=4)
    bar = tk.Frame(frm, bg=SUB_HDR); bar.pack(side='bottom', fill='x', pady=8)
    tk.Button(bar, text='Annuler', command=ov.destroy, bg=ACCENT, fg='#04120d', font=('Arial', 12, 'bold'),
              bd=0, padx=20, pady=8).pack()

# ======================================================================
# Analyses / Vues
# ======================================================================
def build_team_winrate_data(tid: int):
    """
    Prépare les données de winrate par map pour une équipe `tid`.
    - Retourne deux listes : labels (noms de maps) et values (winrate %).
    - Calcul : rounds_won / (won+lost) * 100, 0 si aucune partie.
    """
    cursor.execute('''
        SELECT m.name, COALESCE(SUM(mat.rounds_won),0), COALESCE(SUM(mat.rounds_lost),0)
        FROM Maps m
        LEFT JOIN Matches mat ON mat.map_id=m.id AND mat.team_id=?
        GROUP BY m.id
    ''', (tid,))
    data = cursor.fetchall()
    labels, values = [], []
    for name, won, lost in data:
        total = won + lost
        labels.append(name)
        values.append((won/total*100) if total else 0)
    return labels, values

def build_players_kd_data(tid: int):
    """
    Prépare les données K/D par joueur pour l’équipe `tid`.
    - Si deaths == 0 : on prend kills (ou 0) pour éviter la division par 0.
    - Retour : (labels des joueurs, valeurs K/D)
    """
    cursor.execute('''
        SELECT p.name, COALESCE(SUM(ps.kills),0), COALESCE(SUM(ps.deaths),0)
        FROM Players p
        LEFT JOIN Matches m ON m.team_id=?
        LEFT JOIN PlayerStats ps ON ps.player_id=p.id AND ps.match_id=m.id
        WHERE p.team_id=?
        GROUP BY p.id
    ''', (tid, tid))
    data = cursor.fetchall()
    labels, values = [], []
    for name, k, d in data:
        labels.append(name)
        values.append((k/d) if d else (k if k else 0))
    return labels, values

def analyse_team_interface(tid: int):
    """
    Vue « Analyse » d’une équipe :
    - Graphique barres winrate par map
    - Graphique barres K/D par joueur
    - En-tête avec logo et nom de l’équipe
    """
    # On nettoie l’UI sauf l’overlay (s’il existe).
    for w in root.winfo_children():
        if w is not _overlay:
            w.destroy()
    cursor.execute('SELECT name, logo FROM Teams WHERE id = ?', (tid,))
    r = cursor.fetchone()
    if not r:
        load_home(); return
    team_name, team_logo = r

    # Barre de retour (flèche) pour revenir à la fiche d’équipe
    topbar = tk.Frame(root, bg=BG); topbar.pack(fill='x', pady=4, padx=4)
    back_ic = load_img(os.path.join(IMAGES_DIR, 'back.png'), (40, 40))
    btn = tk.Button(topbar, image=back_ic if back_ic else None, text='← Retour' if not back_ic else '',
                    compound='left', bd=0, bg=BG, fg=FG, activebackground=BG,
                    command=lambda i=tid: open_team(i))
    btn.pack(side='left')
    if back_ic: btn.image = back_ic

    # En-tête (logo + nom)
    header = tk.Frame(root, bg=BG); header.pack(fill='x', pady=8, padx=10)
    logo_box = tk.Frame(header, bg=BG, bd=2, highlightbackground=ACCENT, highlightthickness=2,
                        width=200, height=200)
    logo_box.pack(side='left'); logo_box.pack_propagate(False)
    lpath = (os.path.join(IMAGES_DIR, team_logo)
             if team_logo else os.path.join(IMAGES_DIR, 'anonymous.png'))
    big_logo = load_img(lpath, (190, 190))
    if big_logo:
        lbl = tk.Label(logo_box, image=big_logo, bg=BG); lbl.pack(expand=True)
        team_images[tid] = big_logo
    tk.Label(header, text=team_name, fg=FG, bg=BG, font=('Arial', 26, 'bold')).pack(side='left', padx=20)

    # Corps avec deux panneaux côte à côte : winrate + KD
    body = tk.Frame(root, bg=BG); body.pack(fill='both', expand=True, padx=20, pady=10)
    bg_color = '#0f1115'; text_color = 'lightgrey'
    # Palette vive pour les barres (on recycle les couleurs)
    vibrant_colors = ['#e6194B','#3cb44b','#ffe119','#4363d8','#f58231','#911eb4','#46f0f0','#f032e6',
                      '#bcf60c','#fabebe','#008080','#e6beff','#9A6324','#fffac8','#800000','#aaffc3',
                      '#808000','#ffd8b1','#000075','#808080']

    # Graphique Win-rate par map
    left = tk.Frame(body, bg=BG); left.pack(side='left', fill='both', expand=True, padx=10)
    tk.Label(left, text='Win-rate de l’équipe par map', fg=text_color, bg=BG,
             font=('Consolas', 14, 'bold')).pack(pady=6)
    labels, values = build_team_winrate_data(tid)
    fig1 = Figure(figsize=(5, 4), dpi=100); fig1.patch.set_facecolor(bg_color)
    ax1 = fig1.add_subplot(111); ax1.set_facecolor(bg_color)
    colors1 = [vibrant_colors[i % len(vibrant_colors)] for i in range(len(labels))]
    ax1.bar(labels, values, color=colors1)
    ax1.set_ylabel('Win Rate (%)', color=text_color)
    ax1.tick_params(axis='x', colors=text_color, rotation=45)
    ax1.tick_params(axis='y', colors=text_color)
    for spine in ax1.spines.values(): spine.set_color(text_color)
    fig1.tight_layout()
    canvas1 = FigureCanvasTkAgg(fig1, master=left); canvas1.draw()
    canvas1.get_tk_widget().pack(fill='both', expand=True)

    # Graphique K/D par joueur
    right = tk.Frame(body, bg=BG); right.pack(side='left', fill='both', expand=True, padx=10)
    tk.Label(right, text='Ratios K/D des joueurs', fg=text_color, bg=BG,
             font=('Consolas', 14, 'bold')).pack(pady=6)
    pl_labels, pl_values = build_players_kd_data(tid)
    xticks = list(range(len(pl_labels)))
    fig2 = Figure(figsize=(5, 4), dpi=100); fig2.patch.set_facecolor(bg_color)
    ax2 = fig2.add_subplot(111); ax2.set_facecolor(bg_color)
    colors2 = [vibrant_colors[i % len(vibrant_colors)] for i in range(len(pl_labels))]
    ax2.bar(xticks, pl_values, color=colors2)
    ax2.set_ylabel('K/D', color=text_color)
    ax2.set_xticks(xticks); ax2.set_xticklabels(pl_labels, rotation=45)
    ax2.tick_params(axis='x', colors=text_color); ax2.tick_params(axis='y', colors=text_color)
    for spine in ax2.spines.values(): spine.set_color(text_color)
    fig2.tight_layout()
    canvas2 = FigureCanvasTkAgg(fig2, master=right); canvas2.draw()
    canvas2.get_tk_widget().pack(fill='both', expand=True)

def copy_player_stats(pid, pname):
    """
    Construit un résumé texte des stats du joueur `pid` par map et
    le met dans le presse-papier (nom en première ligne, puis détails).
    - Pour chaque map : nb de games, KD, Win-rate, Bombs.
    """
    stats_lines = []
    cursor.execute('SELECT id, name FROM Maps')
    for mid, mname in cursor.fetchall():
        cursor.execute('''
            SELECT
              COUNT(ps.id),
              COALESCE(SUM(ps.kills), 0),
              COALESCE(SUM(ps.deaths), 0),
              COALESCE(SUM(ps.bombs), 0),
              COALESCE(SUM(m.rounds_won), 0),
              COALESCE(SUM(m.rounds_lost), 0)
            FROM Matches m
            LEFT JOIN PlayerStats ps ON ps.match_id = m.id
            WHERE ps.player_id = ? AND m.map_id = ?
        ''', (pid, mid))
        games, k, d, b, rw, rl = cursor.fetchone()
        kd = (k / d) if d else (k if k else 0)
        wr = (rw / (rw + rl) * 100) if (rw + rl) else 0
        stats_lines.append(f"{mname}: Games={games}, KD={kd:.2f}, Win-rate={wr:.1f}%, Bombs={b}")
    text = pname + "\n" + "\n".join(stats_lines)
    root.clipboard_clear()
    root.clipboard_append(text)
    messagebox.showinfo('Copié', 'Nom et stats du joueur copiés !')

def open_player(pid: int):
    """
    Affiche la fiche détaillée d’un joueur (portrait, KD global, stats par map).
    - Bouton « Copier » pour mettre le résumé dans le presse-papier.
    - Retour à l’équipe parent via la flèche.
    """
    global current_player
    current_player = pid
    for w in root.winfo_children():
        if w is not _overlay:
            w.destroy()
    cursor.execute('SELECT team_id,name,logo FROM Players WHERE id=?', (pid,))
    r = cursor.fetchone()
    if not r:
        load_home(); return
    team_id, pname, plogo = r
    cursor.execute('SELECT COALESCE(SUM(kills),0), COALESCE(SUM(deaths),0) FROM PlayerStats WHERE player_id=?', (pid,))
    k_tot, d_tot = cursor.fetchone()
    overall_kd = (k_tot / d_tot) if d_tot else (k_tot if k_tot else 0)

    # Barre de retour
    tb = tk.Frame(root, bg=BG); tb.pack(fill='x', pady=4, padx=4)
    back_ic = load_img(os.path.join(IMAGES_DIR, 'back.png'), (40, 40))
    btn = tk.Button(tb, image=back_ic if back_ic else None, text='← Retour' if not back_ic else '',
                    compound='left', bd=0, bg=BG, fg=FG, activebackground=BG,
                    command=lambda: open_team(team_id))
    btn.pack(side='left')
    if back_ic: btn.image = back_ic

    # En-tête du joueur (image + nom + bouton copier + KD global)
    header = tk.Frame(root, bg=BG); header.pack(fill='x', pady=10, padx=20)
    p_path = (os.path.join(IMAGES_DIR, plogo) if plogo else os.path.join(IMAGES_DIR, 'anonymous.png'))
    p_img = load_img(p_path, (220, 220))
    if p_img:
        lbl = tk.Label(header, image=p_img, bg=BG, bd=2, highlightbackground=ACCENT, highlightthickness=2)
        lbl.pack(side='left', padx=(0, 40))
        player_images[pid] = p_img

    rt = tk.Frame(header, bg=BG); rt.pack(side='left', fill='both', expand=True)
    name_row = tk.Frame(rt, bg=BG); name_row.pack(fill='x')
    tk.Label(name_row, text=pname, fg=FG, bg=BG, font=('Arial', 22, 'bold')).pack(side='left', padx=10, pady=8)
    tk.Button(name_row, text='Copier', bg=ACCENT, fg='#04120d', bd=0,
              command=lambda: copy_player_stats(pid, pname)).pack(side='left', padx=8)

    kd_box = tk.Frame(rt, bg=SUB_HDR); kd_box.pack(fill='x', pady=8)
    tk.Label(kd_box, text=f"KD global : {overall_kd:.2f}", fg=FG, bg=SUB_HDR,
             font=('Consolas', 16, 'bold')).pack(padx=10, pady=12)

    # Liste déroulante des stats par map (scroll)
    body = tk.Frame(root, bg=BG); body.pack(fill='both', expand=True, padx=20, pady=10)
    canvas = tk.Canvas(body, bg=BG, highlightthickness=0)
    yscr = tk.Scrollbar(body, orient='vertical', command=canvas.yview)
    canvas.configure(yscrollcommand=yscr.set)
    yscr.pack(side='right', fill='y'); canvas.pack(side='left', fill='both', expand=True)
    inner = tk.Frame(canvas, bg=BG); wid = canvas.create_window((0, 0), window=inner, anchor='nw')
    canvas.bind('<Configure>', lambda e: canvas.itemconfig(wid, width=canvas.winfo_width()))
    inner.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all'))

    )

    # Pour chaque map, on calcule les stats agrégées du joueur et on affiche une carte.
    cursor.execute('SELECT id, name, image FROM Maps')
    for mid, mname, mimg in cursor.fetchall():
        cursor.execute('''SELECT COUNT(DISTINCT m.id),
                                 COALESCE(SUM(ps.kills),0),
                                 COALESCE(SUM(ps.deaths),0),
                                 COALESCE(SUM(ps.bombs),0),
                                 COALESCE(SUM(m.rounds_won),0),
                                 COALESCE(SUM(m.rounds_lost),0)
                          FROM Matches m
                          JOIN PlayerStats ps ON ps.match_id=m.id
                          WHERE ps.player_id=? AND m.map_id=?''', (pid, mid))
        games, k, d, b, rw, rl = cursor.fetchone()
        kd = (k / d) if d else (k if k else 0)
        wr = (rw / (rw + rl) * 100) if (rw + rl) else 0

        row = tk.Frame(inner, bg=BG); row.pack(fill='x', padx=30, pady=12)
        m_path = os.path.join(IMAGES_DIR, mimg) if mimg else os.path.join(IMAGES_DIR, 'anonymous.png')
        mp = load_img(m_path, (120, 120))
        lbl = tk.Label(row, image=mp, bg=BG, bd=1, highlightbackground=ACCENT, highlightthickness=1)
        lbl.pack(side='left'); map_images[(pid, mname)] = mp
        big = tk.Frame(row, bg=BG, bd=1, highlightbackground=ACCENT, highlightthickness=1)
        big.pack(side='left', fill='x', expand=True, padx=10)
        tk.Label(big, text=mname, fg=FG, bg=BG, font=('Arial', 14, 'bold')).pack(anchor='w', padx=8, pady=(6, 2))
        tk.Label(big, text=f"KD : {kd:.2f}", fg=FG, bg=BG).pack(anchor='w', padx=8)
        tk.Label(big, text=f"Win-rate : {wr:.1f} %", fg=FG, bg=BG).pack(anchor='w', padx=8)
        tk.Label(big, text=f"Games joués : {games} | Bombs : {b}", fg=FG, bg=BG).pack(anchor='w', padx=8, pady=(0, 6))

def open_team(tid: int):
    """
    Fiche d’une équipe :
    - En-tête (logo, nom, winrate global)
    - Liste des joueurs (KD + winrate joueur) avec actions selon permissions
    - Liste des maps jouées par l’équipe (avec stats de rounds)
    - Boutons « Analyse » et « Exporter »
    """
    global current_team
    current_team = tid
    for w in root.winfo_children():
        if w is not _overlay:
            w.destroy()
    cursor.execute('SELECT name, logo FROM Teams WHERE id=?', (tid,))
    r = cursor.fetchone()
    if not r:
        load_home(); return
    team_name, team_logo = r
    cursor.execute('''SELECT COALESCE(SUM(rounds_won),0), COALESCE(SUM(rounds_lost),0)
                      FROM Matches WHERE team_id=?''', (tid,))
    tw, tl = cursor.fetchone()
    overall_wr = tw / (tw + tl) * 100 if tw + tl else 0

    # Barre du haut : bouton retour + actions contextuelles (edit/suppr si permis)
    tb = tk.Frame(root, bg=BG); tb.pack(fill='x', pady=4, padx=4)
    back_ic = load_img(os.path.join(IMAGES_DIR, 'back.png'), (40, 40))
    tk.Button(tb, image=back_ic if back_ic else None, text='← Retour' if not back_ic else '', compound='left',
              bd=0, bg=BG, fg=FG, activebackground=BG, command=load_home).pack(side='left')
    if back_ic:
        tb.children[list(tb.children)[0]].image = back_ic

    is_owner = team_owned_by_current_captain(tid)
    if is_admin() or is_owner:
        ttk.Button(tb, text='Modifier équipe', style='Neon.TButton',
                   command=lambda: edit_team_overlay(tid)).pack(side='right', padx=3)
        ttk.Button(tb, text='Supprimer équipe', style='Neon.TButton',
                   command=lambda: delete_team(tid)).pack(side='right', padx=3)

    # En-tête avec logo + nom + winrate global
    header = tk.Frame(root, bg=BG); header.pack(fill='x', pady=8, padx=10)
    logo_box = tk.Frame(header, bg=BG, bd=2, highlightbackground=ACCENT, highlightthickness=2,
                        width=250, height=250)
    logo_box.pack(side='left'); logo_box.pack_propagate(False)
    lpath = (os.path.join(IMAGES_DIR, team_logo)
             if team_logo else os.path.join(IMAGES_DIR, 'anonymous.png'))
    big_logo = load_img(lpath, (240, 240))
    if big_logo:
        lbl = tk.Label(logo_box, image=big_logo, bg=BG); lbl.pack(expand=True)
        team_images[tid] = big_logo

    info = tk.Frame(header, bg=BG); info.pack(side='left', fill='both', expand=True, padx=12)
    nm_box = tk.Frame(info, bg=BG, bd=1, highlightbackground=ACCENT, highlightthickness=1)
    nm_box.pack(fill='x')
    tk.Label(nm_box, text=team_name, fg=FG, bg=BG, font=('Arial', 22, 'bold')).pack(pady=12)
    wr_box = tk.Frame(info, bg=SUB_HDR); wr_box.pack(fill='x', pady=6)
    tk.Label(wr_box, text=f'Win-rate (toutes maps) : {overall_wr:.1f} %',
             fg=FG, bg=SUB_HDR, font=('Consolas', 14, 'bold')).pack(pady=10)

    # Bouton vers la vue « Analyse » (graphiques)
    tk.Button(root, text='Analyse', bg=ACCENT, fg='#04120d', bd=0, font=('Arial', 12, 'bold'),
              command=lambda i=tid: analyse_team_interface(i)).pack(pady=5)

    # Corps de page : deux colonnes (joueurs à gauche, maps à droite)
    body = tk.Frame(root, bg=BG); body.pack(fill='both', expand=True, padx=10, pady=10)

    # Colonne gauche : joueurs
    left_outer = tk.Frame(body, bg=ACCENT, bd=1)
    left_outer.pack(side='left', fill='both', expand=True, padx=10)
    left_inner = tk.Frame(left_outer, bg=BG); left_inner.pack(fill='both', expand=True, padx=4, pady=4)

    # Action « Ajouter joueur » si on a les permissions
    if is_admin() or is_owner:
        tk.Button(left_inner, text='Ajouter joueur', bg=ACCENT, fg='#04120d', bd=0,
                  command=lambda: add_player_overlay(tid)).pack(pady=6)

    # Liste scrollable des joueurs
    pl_canvas = tk.Canvas(left_inner, bg=BG, highlightthickness=0)
    pl_scroll = tk.Scrollbar(left_inner, orient='vertical', command=pl_canvas.yview)
    pl_canvas.configure(yscrollcommand=pl_scroll.set)
    pl_scroll.pack(side='right', fill='y'); pl_canvas.pack(side='left', fill='both', expand=True)
    players_frame = tk.Frame(pl_canvas, bg=BG)
    wid_pl = pl_canvas.create_window((0, 0), window=players_frame, anchor='nw')
    pl_canvas.bind('<Configure>', lambda e: pl_canvas.itemconfig(wid_pl, width=pl_canvas.winfo_width()))
    players_frame.bind('<Configure>', lambda e: pl_canvas.configure(scrollregion=pl_canvas.bbox('all')))

    # Pour chaque joueur : ligne avec portrait, nom, actions (voir/modifier/supprimer), stats synthèse
    cursor.execute('SELECT id, name, logo FROM Players WHERE team_id=?', (tid,))
    for pid, pname, plogo in cursor.fetchall():
        cursor.execute('''SELECT COALESCE(SUM(ps.kills),0), COALESCE(SUM(ps.deaths),0),
                                 COALESCE(SUM(m.rounds_won),0), COALESCE(SUM(m.rounds_lost),0)
                          FROM PlayerStats ps
                          JOIN Matches m ON ps.match_id = m.id
                          WHERE ps.player_id=?''', (pid,))
        k, d, rw, rl = cursor.fetchone()
        kd = (k / d) if d else (k if k else 0)
        wr = rw / (rw + rl) * 100 if rw + rl else 0

        row = tk.Frame(players_frame, bg=BG); row.pack(fill='x', pady=6, padx=4)
        p_path = os.path.join(IMAGES_DIR, plogo) if plogo else os.path.join(IMAGES_DIR, 'anonymous.png')
        p_img = load_img(p_path, (80, 80))
        lbl = tk.Label(row, image=p_img, bg=BG); lbl.pack(side='left')
        player_images[pid] = p_img
        box = tk.Frame(row, bg=BG, bd=1, highlightbackground=ACCENT, highlightthickness=1)
        box.pack(side='left', fill='x', expand=True)
        top = tk.Frame(box, bg=BG); top.pack(fill='x')
        tk.Label(top, text=pname, fg=FG, bg=BG, font=('Arial', 12, 'bold')).pack(side='left', padx=6)
        btns = tk.Frame(top, bg=BG); btns.pack(side='right', padx=4)
        ttk.Button(btns, text='👁', width=2, command=lambda p=pid: open_player(p)).pack(side='left')
        if is_admin() or is_owner:
            ttk.Button(btns, text='✎', width=2, command=lambda p=pid: edit_player_overlay(p)).pack(side='left', padx=2)
            ttk.Button(btns, text='🗑', width=2, command=lambda p=pid: delete_player(p)).pack(side='left')
        tk.Label(box, text=f"Win-rate : {wr:.1f} % | K/D : {kd:.2f}", fg=FG, bg=BG
                ).pack(anchor='w', padx=6, pady=(0, 6))

    # Colonne droite : maps jouées par l’équipe (avec stats de rounds)
    right_outer = tk.Frame(body, bg=ACCENT, bd=1)
    right_outer.pack(side='left', fill='both', expand=True, padx=10)
    right_inner = tk.Frame(right_outer, bg=BG); right_inner.pack(fill='both', expand=True, padx=4, pady=4)
    map_canvas = tk.Canvas(right_inner, bg=BG, highlightthickness=0)
    ms = tk.Scrollbar(right_inner, orient='vertical', command=map_canvas.yview)
    map_canvas.configure(yscrollcommand=ms.set)
    ms.pack(side='right', fill='y'); map_canvas.pack(side='left', fill='both', expand=True)

    maps_frame = tk.Frame(map_canvas, bg=BG)
    wid_mp = map_canvas.create_window((0, 0), window=maps_frame, anchor='nw')
    map_canvas.bind('<Configure>', lambda e: map_canvas.itemconfig(wid_mp, width=map_canvas.winfo_width()))
    maps_frame.bind('<Configure>', lambda e: map_canvas.configure(scrollregion=map_canvas.bbox('all')))

    # Chaque ligne = une map avec son image et stats (games, win-rate rounds)
    cursor.execute('''SELECT m.id, m.name, m.image,
                             COUNT(matches.id),
                             COALESCE(SUM(matches.rounds_won),0),
                             COALESCE(SUM(matches.rounds_lost),0)
                      FROM Maps m
                      LEFT JOIN Matches matches ON matches.map_id = m.id
                          AND matches.team_id = ?
                      GROUP BY m.id''', (tid,))
    for mid, mname, mimg, games, rw, rl in cursor.fetchall():
        row = tk.Frame(maps_frame, bg=BG); row.pack(fill='x', pady=6, padx=4)
        m_path = os.path.join(IMAGES_DIR, mimg) if mimg else os.path.join(IMAGES_DIR, 'anonymous.png')
        m_img = load_img(m_path, (80, 80))
        lbl = tk.Label(row, image=m_img, bg=BG); lbl.pack(side='left')
        map_images[mid] = m_img
        bbox = tk.Frame(row, bg=BG, bd=1, highlightbackground=ACCENT, highlightthickness=1)
        bbox.pack(side='left', fill='x', expand=True)
        tk.Label(bbox, text=mname, fg=FG, bg=BG, font=('Arial', 12, 'bold')).pack(anchor='w', padx=6)
        wr_val = rw / (rw + rl) * 100 if rw + rl else 0
        tk.Label(bbox, text=f"Games : {games} | Win-rate rounds : {wr_val:.1f} %",
                 fg=FG, bg=BG).pack(anchor='w', padx=6, pady=(0, 6))

    # Bouton export (ouvre l’overlay d’export des rapports)
    tk.Button(root, text='Exporter', bg=ACCENT, fg='#04120d', bd=0, font=('Arial', 12, 'bold'),
              command=export_overlay).pack(pady=10)

# ======================================================================
# Leaderboard + Match overlay
# ======================================================================
def get_leaderboard():
    """
    Construit le leaderboard des équipes trié par nombre de « wins »
    (au sens « match où rounds_won > rounds_lost »).
    - Retourne une liste de tuples (team_id, name, logo, wins)
    - Tri secondaire par nom d’équipe (ordre alpha, insensible à la casse)
    """
    cursor.execute('''
        SELECT
            t.id,
            t.name,
            t.logo,
            COALESCE(SUM(CASE WHEN m.rounds_won > m.rounds_lost THEN 1 ELSE 0 END), 0) AS wins
        FROM Teams t
        LEFT JOIN Matches m ON m.team_id = t.id
        GROUP BY t.id
        ORDER BY wins DESC, t.name COLLATE NOCASE ASC
    ''')
    return cursor.fetchall()

def add_match_dual_overlay():
    """
    Overlay d’ajout d’un match entre deux équipes (A vs B) sur une map.
    - On saisit le score en rounds (A — B).
    - On coche les joueurs ayant joué et on saisit leurs kills/deaths/bombs.
    - On enregistre automatiquement DEUX lignes dans Matches :
      * une vue côté équipe A (rounds_won = score A)
      * une vue côté équipe B (rounds_won = score B)
    - Puis on insère les PlayerStats associés à chacune des deux entrées.
    Permissions : admin ou capitaine (peu importe l’équipe sélectionnée).
    """
    if current_role not in ('admin', 'captain'):
        return
    ov = show_overlay()

    # On charge les maps et les équipes (noms pour les menus déroulants)
    cursor.execute('SELECT id,name FROM Maps ORDER BY name COLLATE NOCASE')
    maps = cursor.fetchall()
    map_names = [m[1] for m in maps] or ['Aucune map']
    map_v = tk.StringVar(value=(map_names[0] if map_names else ''))

    cursor.execute('SELECT id,name FROM Teams ORDER BY name COLLATE NOCASE')
    teams = cursor.fetchall()
    team_names = [t[1] for t in teams]
    team1_v = tk.StringVar(value=(team_names[0] if team_names else ''))
    team2_v = tk.StringVar(value=(team_names[1] if len(team_names) > 1 else (team_names[0] if team_names else '')))

    # Scores en rounds
    team1_rounds_v = tk.IntVar(value=0)
    team2_rounds_v = tk.IntVar(value=0)

    # Dictionnaires : player_id -> (played_var, kills_var, deaths_var, bombs_var)
    team1_entries = {}
    team2_entries = {}

    # Validation pour n’accepter que des chiffres dans les entry
    def only_digits(P): return P.isdigit() or P == ''
    vcmd = (root.register(only_digits), '%P')

    def find_id_by_name(seq, name):
        """Récupère l’ID correspondant à un nom donné dans une liste (id,name)."""
        for _id, nm in seq:
            if nm == name: return _id
        return None

    def build_entries_for_team(parent, tid, target_dict):
        """
        Construit la grille des joueurs pour l’équipe `tid` :
        - Une case à cocher « a joué »
        - 3 champs K/D/B activés uniquement si coché
        - On remplit `target_dict` pour lecture lors de la sauvegarde
        """
        for w in parent.winfo_children(): w.destroy()
        target_dict.clear()
        if tid is None:
            tk.Label(parent, text="Aucune équipe sélectionnée", fg=FG, bg=BG).pack(pady=6)
            return
        cursor.execute('SELECT id,name FROM Players WHERE team_id=? ORDER BY name COLLATE NOCASE', (tid,))
        rows = cursor.fetchall()
        if not rows:
            tk.Label(parent, text="Aucun joueur", fg=FG, bg=BG).pack(pady=6)
            return
        hdr = ttk.Frame(parent); hdr.pack(fill='x', pady=(0, 4))
        ttk.Label(hdr, text='✓').pack(side='left', padx=6)
        ttk.Label(hdr, text='Joueur', width=20).pack(side='left')
        ttk.Label(hdr, text='Kills', width=6).pack(side='left')
        ttk.Label(hdr, text='Deaths', width=6).pack(side='left')
        ttk.Label(hdr, text='Bombs', width=6).pack(side='left')
        for pid, pname in rows:
            row = ttk.Frame(parent); row.pack(fill='x', pady=2)
            played = tk.BooleanVar()
            ttk.Checkbutton(row, variable=played).pack(side='left', padx=6)
            ttk.Label(row, text=pname, width=20).pack(side='left')
            k = tk.IntVar(); d = tk.IntVar(); b = tk.IntVar()
            ent_k = ttk.Entry(row, textvariable=k, width=6, validate='key', validatecommand=vcmd, style='Login.TEntry', state='disabled')
            ent_d = ttk.Entry(row, textvariable=d, width=6, validate='key', validatecommand=vcmd, style='Login.TEntry', state='disabled')
            ent_b = ttk.Entry(row, textvariable=b, width=6, validate='key', validatecommand=vcmd, style='Login.TEntry', state='disabled')
            ent_k.pack(side='left', padx=2); ent_d.pack(side='left', padx=2); ent_b.pack(side='left', padx=2)
            def toggle_fields(*_args, v=played, fields=(ent_k, ent_d, ent_b)):
                """
                Active/désactive les champs au gré de la case « a joué ».
                Ça garde l’UI propre : pas besoin de mettre 0 partout.
                """
                st = 'normal' if v.get() else 'disabled'
                for f in fields: f.configure(state=st)
            played.trace_add('write', toggle_fields)
            target_dict[pid] = (played, k, d, b)

    # UI de la grande modale (sélecteurs + deux colonnes de joueurs)
    root.update_idletasks()
    max_h = root.winfo_height() - 60
    frm = tk.Frame(ov, bg=SUB_HDR, bd=2, highlightbackground=ACCENT, highlightthickness=2)
    frm.place(relx=0.5, rely=0.5, anchor='center', width=1100, height=min(700, max_h))
    tk.Label(frm, text='AJOUTER UN MATCH (2 ÉQUIPES)', fg=FG, bg=SUB_HDR,
             font=('Arial', 18, 'bold')).pack(pady=(14, 10))

    sel = tk.Frame(frm, bg=BG, bd=2, highlightbackground=ACCENT, highlightthickness=2)
    sel.pack(fill='x', padx=16, pady=8)
    mpbox = tk.Frame(sel, bg=BG); mpbox.pack(side='left', padx=12, pady=8)
    ttk.Label(mpbox, text='Map :').pack(anchor='w')
    ttk.OptionMenu(mpbox, map_v, map_v.get(), *map_names).pack()
    t1box = tk.Frame(sel, bg=BG); t1box.pack(side='left', padx=24, pady=8)
    ttk.Label(t1box, text='Équipe A :').pack(anchor='w')
    ttk.OptionMenu(t1box, team1_v, team1_v.get(), *team_names).pack()
    t2box = tk.Frame(sel, bg=BG); t2box.pack(side='left', padx=24, pady=8)
    ttk.Label(t2box, text='Équipe B :').pack(anchor='w')
    ttk.OptionMenu(t2box, team2_v, team2_v.get(), *team_names).pack()
    sc = tk.Frame(sel, bg=BG); sc.pack(side='left', padx=24, pady=8)
    ttk.Label(sc, text='Score (Rounds) :').pack(anchor='w')
    scrow = tk.Frame(sc, bg=BG); scrow.pack()
    ttk.Entry(scrow, textvariable=team1_rounds_v, width=6, validate='key', validatecommand=vcmd, style='Login.TEntry').pack(side='left')
    ttk.Label(scrow, text='  —  ').pack(side='left')
    ttk.Entry(scrow, textvariable=team2_rounds_v, width=6, validate='key', validatecommand=vcmd, style='Login.TEntry').pack(side='left')

    body = tk.Frame(frm, bg=BG); body.pack(fill='both', expand=True, padx=16, pady=8)

    left_outer = tk.Frame(body, bg=ACCENT, bd=1)
    left_outer.pack(side='left', fill='both', expand=True, padx=(0, 8))
    left_inner = tk.Frame(left_outer, bg=BG); left_inner.pack(fill='both', expand=True, padx=4, pady=4)
    tk.Label(left_inner, text='Joueurs Équipe A', fg=FG, bg=SUB_HDR, font=('Consolas', 14, 'bold')).pack(fill='x', pady=(0, 6))
    t1_wrap = tk.Frame(left_inner, bg=BG); t1_wrap.pack(fill='both', expand=True)
    t1_canvas = tk.Canvas(t1_wrap, bg=BG, highlightthickness=0); t1_canvas.pack(side='left', fill='both', expand=True)
    t1_scroll = tk.Scrollbar(t1_wrap, orient='vertical', command=t1_canvas.yview); t1_scroll.pack(side='right', fill='y')
    t1_canvas.configure(yscrollcommand=t1_scroll.set)
    t1_frame = tk.Frame(t1_canvas, bg=BG); t1_id = t1_canvas.create_window((0,0), window=t1_frame, anchor='nw')
    t1_canvas.bind('<Configure>', lambda e: t1_canvas.itemconfig(t1_id, width=t1_canvas.winfo_width()))
    t1_frame.bind('<Configure>', lambda e: t1_canvas.configure(scrollregion=t1_canvas.bbox('all')))

    right_outer = tk.Frame(body, bg=ACCENT, bd=1)
    right_outer.pack(side='left', fill='both', expand=True, padx=(8, 0))
    right_inner = tk.Frame(right_outer, bg=BG); right_inner.pack(fill='both', expand=True, padx=4, pady=4)
    tk.Label(right_inner, text='Joueurs Équipe B', fg=FG, bg=SUB_HDR, font=('Consolas', 14, 'bold')).pack(fill='x', pady=(0, 6))
    t2_wrap = tk.Frame(right_inner, bg=BG); t2_wrap.pack(fill='both', expand=True)
    t2_canvas = tk.Canvas(t2_wrap, bg=BG, highlightthickness=0); t2_canvas.pack(side='left', fill='both', expand=True)
    t2_scroll = tk.Scrollbar(t2_wrap, orient='vertical', command=t2_canvas.yview); t2_scroll.pack(side='right', fill='y')
    t2_canvas.configure(yscrollcommand=t2_scroll.set)
    t2_frame = tk.Frame(t2_canvas, bg=BG); t2_id = t2_canvas.create_window((0,0), window=t2_frame, anchor='nw')
    t2_canvas.bind('<Configure>', lambda e: t2_canvas.itemconfig(t2_id, width=t2_canvas.winfo_width()))
    t2_frame.bind('<Configure>', lambda e: t2_canvas.configure(scrollregion=t2_canvas.bbox('all')))

    def refresh_rosters(*_args):
        """
        Recharge les rosters (listes de joueurs) en fonction des équipes
        choisies dans les menus déroulants.
        """
        tid1 = find_id_by_name(teams, team1_v.get())
        tid2 = find_id_by_name(teams, team2_v.get())
        build_entries_for_team(t1_frame, tid1, team1_entries)
        build_entries_for_team(t2_frame, tid2, team2_entries)

    # Quand on change l’une des équipes, on relit le roster
    team1_v.trace_add('write', refresh_rosters)
    team2_v.trace_add('write', refresh_rosters)
    refresh_rosters()

    def save():
        """
        Valide les entrées et enregistre :
        - Deux lignes dans Matches (une par équipe)
        - Les PlayerStats pour chaque équipe selon les cases cochées
        - Quelques validations UX : 2 équipes différentes, map choisie,
          scores valides, minimum de 4 rounds combinés.
        """
        if not teams or len(teams) < 2:
            messagebox.showerror('Erreur', "Il faut au moins 2 équipes dans la ligue."); return
        tid1 = find_id_by_name(teams, team1_v.get())
        tid2 = find_id_by_name(teams, team2_v.get())
        if tid1 is None or tid2 is None or tid1 == tid2:
            messagebox.showerror('Erreur', "Sélectionnez deux équipes différentes."); return
        mid = find_id_by_name(maps, map_v.get())
        if mid is None:
            messagebox.showerror('Erreur', "Sélectionnez une map."); return
        try:
            s1 = int(team1_rounds_v.get()); s2 = int(team2_rounds_v.get())
        except Exception:
            messagebox.showerror('Erreur', "Scores invalides (entiers requis)."); return
        if (s1 + s2) < 4:
            messagebox.showerror('Erreur', "Au moins 4 rounds au total pour enregistrer un match."); return
        cursor.execute('INSERT INTO Matches(team_id,map_id,rounds_won,rounds_lost) VALUES (?,?,?,?)', (tid1, mid, s1, s2))
        match1_id = cursor.lastrowid
        cursor.execute('INSERT INTO Matches(team_id,map_id,rounds_won,rounds_lost) VALUES (?,?,?,?)', (tid2, mid, s2, s1))
        match2_id = cursor.lastrowid
        for pid, (played, k, d, b) in team1_entries.items():
            if played.get() and (k.get() or d.get() or b.get()):
                cursor.execute('INSERT INTO PlayerStats(match_id,player_id,kills,deaths,bombs) VALUES (?,?,?,?,?)',
                               (match1_id, pid, k.get(), d.get(), b.get()))
        for pid, (played, k, d, b) in team2_entries.items():
            if played.get() and (k.get() or d.get() or b.get()):
                cursor.execute('INSERT INTO PlayerStats(match_id,player_id,kills,deaths,bombs) VALUES (?,?,?,?,?)',
                               (match2_id, pid, k.get(), d.get(), b.get()))
        conn.commit()
        messagebox.showinfo('Succès', 'Match enregistré pour les deux équipes.')
        ov.destroy(); load_home()

    # Barre de boutons de l’overlay
    bar = tk.Frame(frm, bg=SUB_HDR); bar.pack(side='bottom', fill='x', pady=12)
    ttk.Button(bar, text='Annuler', command=ov.destroy).pack(side='left', padx=45)
    ttk.Button(bar, text='Enregistrer', style='Neon.TButton', command=save).pack(side='right', padx=45)

# ======================================================================
# ACCUEIL (avec Se déconnecter)
# ======================================================================
def load_home():
    """
    Page d’accueil dynamique selon le rôle :
    - Admin : gros panneaux d’actions (maps, DB, équipes, matchs)
    - Capitaine : ajouter équipe / match
    - Visiteur : lecture seule
    Sections :
    - Colonne gauche : « MY TEAM » (si capitaine) + « LEAGUE TEAMS »
    - Colonne droite : leaderboard trié par victoires
    """
    global _overlay
    if _overlay:
        _overlay.destroy(); _overlay = None
    for w in root.winfo_children():
        w.destroy()

    header = tk.Frame(root, bg=HEADER_BG); header.pack(fill='x')

    # Logo en grand (si présent dans /images)
    logo_big = load_img(os.path.join(IMAGES_DIR, 'logoapp.png'), (150, 150))
    if logo_big:
        lbl = tk.Label(header, image=logo_big, bg=HEADER_BG); lbl.image = logo_big
        lbl.pack(side='left', padx=10, pady=10)

    # Titre (taille réduite volontairement pour ne pas empiéter sur les icônes)
    tk.Label(header, text='𝕾𝖙𝖆𝖙𝖎𝖘𝖙𝖎𝖖𝖚𝖊 𝕬𝖕𝖕𝖑𝖎𝖈𝖆𝖙𝖎𝖔𝖓',
             font=('Consolas', 28, 'bold'), bg=HEADER_BG, fg=FG).pack(side='left', padx=10)

    def icon(img, cmd, fallback, img_size=(160, 160)):
        """
        Petit helper pour placer une icône d’action dans l’en-tête.
        - Si l’image est absente, on met un bouton texte « fallback ».
        """
        frame = tk.Frame(header, bg=HEADER_BG); frame.pack(side='right', padx=10, pady=10)
        ic = load_img(os.path.join(IMAGES_DIR, img), img_size)
        if ic:
            b = tk.Button(frame, image=ic, bd=0, bg=HEADER_BG, activebackground=HEADER_BG, command=cmd)
            b.image = ic; b.pack()
        else:
            tk.Button(frame, text=fallback, bg=ACCENT, fg='#04120d', bd=0, width=18, height=3, command=cmd).pack()

    # Se déconnecter (retour à l’écran de login)
    icon('logout.png', show_login, 'Se déconnecter', img_size=(120,120))

    # Actions de rôle (à droite, en ordre de priorité)
    if is_admin():
        icon('deletemap.png', delete_map_overlay, 'Supprimer map')
        icon('database.png', database_overlay, 'Database')
        icon('ajoutermap.png', add_map_overlay, 'Ajouter map', img_size=(120, 120))
        icon('ajouterequipe.png', add_team_overlay, 'Ajouter équipe', img_size=(120, 120))
        icon('ajoutermatch.png', add_match_dual_overlay, 'Ajouter match', img_size=(120, 120))
    elif is_captain():
        icon('ajouterequipe.png', add_team_overlay, 'Ajouter équipe', img_size=(120, 120))
        icon('ajoutermatch.png', add_match_dual_overlay, 'Ajouter match', img_size=(120, 120))

    # Corps principal (2 colonnes)
    body = tk.Frame(root, bg=BG); body.pack(fill='both', expand=True, padx=20, pady=12)

    left_column = tk.Frame(body, bg=BG); left_column.pack(side='left', fill='both', expand=True, padx=(0, 10))

    def make_stack_panel(parent, title):
        """
        Construit un panneau empilable avec un en-tête et un contenu scrollable.
        On l’utilise pour « MY TEAM » et « LEAGUE TEAMS ».
        """
        outer = tk.Frame(parent, bg=ACCENT, bd=1); outer.pack(fill='both', expand=True, pady=8)
        inner = tk.Frame(outer, bg=BG); inner.pack(fill='both', expand=True, padx=4, pady=4)
        bar = tk.Frame(inner, bg=SUB_HDR); bar.pack(fill='x')
        tk.Label(bar, text=title, font=('Consolas', 16, 'bold'), bg=SUB_HDR, fg=FG).pack(pady=6)
        wrap = tk.Frame(inner, bg=BG); wrap.pack(fill='both', expand=True, pady=(4, 2))
        canvas = tk.Canvas(wrap, bg=BG, highlightthickness=0)
        ybar = tk.Scrollbar(wrap, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=ybar.set)
        ybar.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        grid = tk.Frame(canvas, bg=BG)
        wid = canvas.create_window((0, 0), window=grid, anchor='nw')
        canvas.bind('<Configure>', lambda e: canvas.itemconfig(wid, width=canvas.winfo_width()))
        grid.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        return grid

    grid_my = None
    # SHOW "MY TEAM" ONLY FOR CAPTAINS
    # Si on est capitaine, on affiche un panneau dédié à son équipe.
    if is_captain():
        grid_my = make_stack_panel(left_column, '𝕄𝕐 𝕋𝔼𝔸𝕄')
    # Panneau des équipes de ligue (toujours visible)
    grid_league = make_stack_panel(left_column, 'LEAGUE TEAMS')

    def add_team_thumbnail(panel, tid, name, logo):
        """
        Ajoute une tuile (vignette) d’équipe dans un grid 4 colonnes.
        - Image 100x100 (ou placeholder « anonymous.png »)
        - Bouton ouvre la fiche d’équipe
        """
        n = len(panel.grid_slaves())
        r, c = divmod(n, 4)
        cell = tk.Frame(panel, bg=BG); cell.grid(row=r, column=c, padx=10, pady=10)
        img_path = os.path.join(IMAGES_DIR, logo) if logo else os.path.join(IMAGES_DIR, 'anonymous.png')
        img = load_img(img_path, (100, 100))
        team_images[tid] = img
        btn = tk.Button(cell, image=img, text=name, compound='top',
                        bg=BG, fg=FG, bd=0, activebackground=BG,
                        command=lambda i=tid: open_team(i))
        btn.image = img; btn.pack()

    # On récupère toutes les équipes pour alimenter les panneaux
    cursor.execute('SELECT id, name, logo, side FROM Teams ORDER BY name COLLATE NOCASE')
    all_teams = cursor.fetchall()

    if is_admin():
        # Admin voit UNIQUEMENT le panneau League, mais avec TOUTES les équipes
        for tid, name, logo, side in all_teams:
            add_team_thumbnail(grid_league, tid, name, logo)
    elif is_captain():
        # Capitaine : panneau "My Team" = son équipe à lui seulement
        my_tid = get_captain_team_id(current_captain)
        if my_tid:
            cursor.execute('SELECT id,name,logo FROM Teams WHERE id=?', (my_tid,))
            t = cursor.fetchone()
            if t and grid_my is not None:
                add_team_thumbnail(grid_my, t[0], t[1], t[2])
        # Panneau League : toutes les équipes (incluant la sienne)
        for tid, name, logo, side in all_teams:
            add_team_thumbnail(grid_league, tid, name, logo)
    else:
        # Visiteur : seulement le panneau League
        for tid, name, logo, side in all_teams:
            add_team_thumbnail(grid_league, tid, name, logo)

    # Colonne droite : leaderboard (scrollable aussi)
    right_column = tk.Frame(body, bg=BG); right_column.pack(side='left', fill='both', expand=True, padx=(10, 0))
    leaderboard_outer = tk.Frame(right_column, bg=ACCENT, bd=1); leaderboard_outer.pack(fill='both', expand=True)
    leaderboard_inner = tk.Frame(leaderboard_outer, bg=BG); leaderboard_inner.pack(fill='both', expand=True, padx=4, pady=4)

    title_bar = tk.Frame(leaderboard_inner, bg=SUB_HDR); title_bar.pack(fill='x')
    tk.Label(title_bar, text='LEADERBOARD (Wins)', font=('Consolas', 16, 'bold'), bg=SUB_HDR, fg=FG).pack(pady=6)

    lb_wrap = tk.Frame(leaderboard_inner, bg=BG); lb_wrap.pack(fill='both', expand=True, pady=(4, 2))
    lb_canvas = tk.Canvas(lb_wrap, bg=BG, highlightthickness=0); lb_canvas.pack(side='left', fill='both', expand=True)
    lb_scroll = tk.Scrollbar(lb_wrap, orient='vertical', command=lb_canvas.yview); lb_scroll.pack(side='right', fill='y')
    lb_canvas.configure(yscrollcommand=lb_scroll.set)
    lb_frame = tk.Frame(lb_canvas, bg=BG); wid_lb = lb_canvas.create_window((0, 0), window=lb_frame, anchor='nw')
    lb_canvas.bind('<Configure>', lambda e: lb_canvas.itemconfig(wid_lb, width=lb_canvas.winfo_width()))
    lb_frame.bind('<Configure>', lambda e: lb_canvas.configure(scrollregion=lb_canvas.bbox('all')))

    # Remplir le tableau du leaderboard
    leaderboard = get_leaderboard()
    rank = 1
    for tid, name, logo, wins in leaderboard:
        row = tk.Frame(lb_frame, bg=BG, bd=1, highlightbackground=ACCENT, highlightthickness=1)
        row.pack(fill='x', pady=4, padx=6)
        tk.Label(row, text=f"{rank:>2}.", width=4, anchor='w', fg=FG, bg=BG,
                 font=('Consolas', 14, 'bold')).pack(side='left', padx=(6, 4))
        img_path = os.path.join(IMAGES_DIR, logo) if logo else os.path.join(IMAGES_DIR, 'anonymous.png')
        img_small = load_img(img_path, (32, 32))
        team_images[(tid, 'lb')] = img_small
        tk.Label(row, image=img_small, bg=BG).pack(side='left', padx=4)
        tk.Label(row, text=name, fg=FG, bg=BG, font=('Arial', 12, 'bold')).pack(side='left', padx=8)
        tk.Label(row, text=f"Wins: {wins}", fg=FG, bg=BG, font=('Consolas', 12)).pack(side='right', padx=8)
        # Clique sur la ligne = ouvre la fiche d’équipe
        row.bind('<Button-1>', lambda _e, i=tid: open_team(i))
        for child in row.winfo_children():
            child.bind('<Button-1>', lambda _e, i=tid: open_team(i))
        rank += 1

    # Bouton export global (réutilise export_overlay)
    tk.Button(root, text='Exporter', bg=ACCENT, fg='#04120d', bd=0, font=('Arial', 12, 'bold'),
              command=export_overlay).pack(pady=10)

# ======================================================================
# Boucle principale
# ======================================================================
# Au démarrage : écran de login d’abord (choix du rôle), ensuite mainloop.
show_login()
root.mainloop()


