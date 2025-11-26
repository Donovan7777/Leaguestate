pip install pyperclip pillow matplotlib


Résumé simple et professionnel de ton application
1. Les rôles dans l’application
 Visiteurs
Peuvent naviguer dans l’application.


Peuvent voir :


Les équipes


Les joueurs


Les statistiques


L’analyse de performance de chaque joueur


Ils n’ont pas de permissions de gestion : ils observent seulement.



 Capitaines
Ont accès à tout ce qu’un visiteur peut voir (équipes, joueurs, statistiques).


Gèrent leur équipe :


Acheter des joueurs


Modifier les informations des joueurs


Supprimer des joueurs


Modifier le logo de l’équipe


Modifier les logos/particularités des joueurs


Mais :
  Ils ne deviennent capitaine d’une équipe que lorsque l’administrateur les assigne.
 (Pour éviter que n’importe qui crée des équipes inutiles.)



🔹 Administrateur
Rôle avec les permissions les plus élevées.


Est responsable de la ligue :


Créer les matchs


Entrer les statistiques de chaque match


Ajouter/supprimer des maps (Rust, Crash, Killhouse…)


Gérer les capitaines :


Lorsqu’un compte capitaine est créé, l’admin doit l’assigner à une équipe


Gère également quelle base de données est chargée (Call of Duty, CSGO, etc.).



2. Système multi-bases de données (Multi-Jeux)
L’application est faite pour fonctionner avec plusieurs jeux.


Exemple :


Si on charge la base de données Call of Duty, toutes les données (joueurs, équipes, statistiques) sont liées à CoD.


Deux minutes plus tard, on peut charger une base de données CSGO :
 → ce sera une base totalement différente
 (nouveaux joueurs, nouvelles équipes, nouveaux capitaines, nouveaux admins).


L’administrateur choisit :


Quelle base est active


Quelles maps sont disponibles selon le jeu


3. Installation des dépendances (pip install)

Tu DOIS installer seulement ces trois-là :
 Commande d’installation :
pip install Pillow
pip install matplotlib
pip install pyperclip



4. Comptes et connexion
Compte administrateur
Nom d’utilisateur : admin


Mot de passe : admin


Comptes capitaines

Nom d’utilisateur : cap1


Mot de passe : cap1


Nom d’utilisateur : cap2


Mot de passe : cap2

Nom d’utilisateur : cap3


Mot de passe : cap3

Nom d’utilisateur : cap4


Mot de passe : cap4


Nom d’utilisateur : cap5


Mot de passe : cap5


5. Première utilisation de l’application
Installer les 3 dépendances :

 pip install Pillow
pip install matplotlib
pip install pyperclip


Ouvrir l’application et se connecter en administrateur.
python main.py

Dans le menu admin, choisir charger une base de données.


Sélectionner :
 statteam.db


L’application se configure automatiquement selon cette base.

