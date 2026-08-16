#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AkibaCore — Système de Gestion AVEC (Version Production)
=========================================================
Conçu pour les Associations Villageoises d'Épargne et de Crédit
Fonctionne 100 % hors ligne | SQLite | Tkinter

Auteur  : AkibaCore Team
Version : 2.0.0
"""

import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import hashlib
import secrets
import os
import shutil
import csv
import json
import html
from datetime import datetime, date
from pathlib import Path


# ════════════════════════════════════════════════════════════════
#  CONFIGURATION GLOBALE
# ════════════════════════════════════════════════════════════════

APP_NOM      = "AkibaCore"
APP_VERSION  = "2.0.0"
DB_CHEMIN    = "akibacore.db"
BACKUP_DIR   = Path("sauvegardes")
BACKUP_MAX   = 15

TAUX_INTERET_DEFAUT  = 0.10   # 10 % annuel
TAUX_PENALITE_DEFAUT = 0.02   # 2 % / mois de retard
MONTANT_PART_DEFAUT  = 5_000  # FC

C = {                          # Palette de couleurs
    "bleu":    "#1A5276",
    "bleu_f":  "#154360",
    "vert":    "#1E8449",
    "vert_c":  "#2ECC71",
    "or":      "#D4AC0D",
    "rouge":   "#C0392B",
    "gris":    "#F4F6F7",
    "gris_f":  "#D5D8DC",
    "texte":   "#1C2833",
    "blanc":   "#FFFFFF",
    "ligne_p": "#EAF2FF",
    "ligne_i": "#FFFFFF",
}


# ════════════════════════════════════════════════════════════════
#  BASE DE DONNÉES
# ════════════════════════════════════════════════════════════════

class DB:
    """Gestionnaire SQLite centralisé (connexion unique, WAL, FK, Row factory)."""

    def __init__(self, chemin=DB_CHEMIN):
        self.chemin = chemin
        self._conn: sqlite3.Connection = None
        self._initialiser()

    # ── Connexion ────────────────────────────────────────────────
    def _ouvrir(self):
        if self._conn is None:
            self._conn = sqlite3.connect(
                self.chemin,
                detect_types=sqlite3.PARSE_DECLTYPES,
                check_same_thread=False,
            )
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._conn.execute("PRAGMA synchronous=NORMAL")
        return self._conn

    @property
    def conn(self):
        return self._ouvrir()

    # ── Raccourcis ───────────────────────────────────────────────
    def exec(self, sql, params=()):
        return self.conn.execute(sql, params)

    def un(self, sql, params=()):
        r = self.conn.execute(sql, params).fetchone()
        return dict(r) if r else None

    def tous(self, sql, params=()):
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def valeur(self, sql, params=()):
        r = self.conn.execute(sql, params).fetchone()
        return r[0] if r else None

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    # ── Audit ────────────────────────────────────────────────────
    def audit(self, uid, login, action, table=None, rid=None, details=None):
        try:
            self.exec(
                "INSERT INTO audit_log(uid,login,action,tbl,rid,details)"
                " VALUES(?,?,?,?,?,?)",
                (uid, login, action, table, rid,
                 json.dumps(details, ensure_ascii=False) if details else None),
            )
            self.commit()
        except Exception:
            pass  # L'audit ne doit jamais bloquer l'opération

    # ── Initialisation schéma ────────────────────────────────────
    def _initialiser(self):
        c = self._ouvrir()
        c.executescript("""
        PRAGMA journal_mode=WAL;
        PRAGMA foreign_keys=ON;

        CREATE TABLE IF NOT EXISTS utilisateur (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            nom           TEXT NOT NULL,
            login         TEXT UNIQUE NOT NULL,
            pwd_hash      TEXT NOT NULL,
            sel           TEXT NOT NULL,
            role          TEXT DEFAULT 'agent'
                          CHECK(role IN ('admin','agent','lecteur')),
            actif         INTEGER DEFAULT 1,
            cree_le       TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS avec (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            nom            TEXT NOT NULL,
            description    TEXT,
            montant_part   REAL DEFAULT 5000,
            taux_interet   REAL DEFAULT 0.10,
            taux_penalite  REAL DEFAULT 0.02,
            actif          INTEGER DEFAULT 1,
            cree_le        TEXT DEFAULT (date('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS membre (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            avec_id       INTEGER NOT NULL DEFAULT 1,
            numero        TEXT,
            nom           TEXT NOT NULL,
            prenom        TEXT,
            telephone     TEXT,
            adresse       TEXT,
            nb_parts      INTEGER DEFAULT 1,
            statut        TEXT DEFAULT 'actif'
                          CHECK(statut IN ('actif','suspendu','sorti')),
            date_adhesion TEXT DEFAULT (date('now','localtime')),
            notes         TEXT,
            cree_le       TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY(avec_id) REFERENCES avec(id)
        );

        CREATE TABLE IF NOT EXISTS session (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            avec_id        INTEGER NOT NULL DEFAULT 1,
            numero         INTEGER,
            date_reunion   TEXT NOT NULL,
            statut         TEXT DEFAULT 'ouverte'
                           CHECK(statut IN ('ouverte','fermee')),
            notes          TEXT,
            cree_par       INTEGER,
            cree_le        TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY(avec_id) REFERENCES avec(id),
            FOREIGN KEY(cree_par) REFERENCES utilisateur(id)
        );

        CREATE TABLE IF NOT EXISTS epargne (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            membre_id     INTEGER NOT NULL,
            session_id    INTEGER,
            montant       REAL NOT NULL CHECK(montant > 0),
            type          TEXT DEFAULT 'ordinaire'
                          CHECK(type IN ('ordinaire','solidarite','urgence')),
            date_op       TEXT DEFAULT (datetime('now','localtime')),
            description   TEXT,
            annule        INTEGER DEFAULT 0,
            cree_par      INTEGER,
            cree_le       TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY(membre_id)  REFERENCES membre(id),
            FOREIGN KEY(session_id) REFERENCES session(id),
            FOREIGN KEY(cree_par)   REFERENCES utilisateur(id)
        );

        CREATE TABLE IF NOT EXISTS credit (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            membre_id        INTEGER NOT NULL,
            session_id       INTEGER,
            principal        REAL NOT NULL CHECK(principal > 0),
            taux             REAL NOT NULL,
            duree_mois       INTEGER NOT NULL CHECK(duree_mois > 0),
            date_octroi      TEXT DEFAULT (date('now','localtime')),
            date_echeance    TEXT NOT NULL,
            montant_interet  REAL NOT NULL,
            montant_total    REAL NOT NULL,
            rembourse        REAL DEFAULT 0,
            statut           TEXT DEFAULT 'actif'
                             CHECK(statut IN ('actif','solde','en_retard','annule')),
            description      TEXT,
            cree_par         INTEGER,
            cree_le          TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY(membre_id)  REFERENCES membre(id),
            FOREIGN KEY(session_id) REFERENCES session(id),
            FOREIGN KEY(cree_par)   REFERENCES utilisateur(id)
        );

        CREATE TABLE IF NOT EXISTS remboursement (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            credit_id       INTEGER NOT NULL,
            membre_id       INTEGER NOT NULL,
            session_id      INTEGER,
            mont_principal  REAL DEFAULT 0 CHECK(mont_principal >= 0),
            mont_interet    REAL DEFAULT 0 CHECK(mont_interet >= 0),
            mont_penalite   REAL DEFAULT 0 CHECK(mont_penalite >= 0),
            montant_total   REAL NOT NULL  CHECK(montant_total > 0),
            date_paiement   TEXT DEFAULT (datetime('now','localtime')),
            description     TEXT,
            annule          INTEGER DEFAULT 0,
            cree_par        INTEGER,
            cree_le         TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY(credit_id)  REFERENCES credit(id),
            FOREIGN KEY(membre_id)  REFERENCES membre(id),
            FOREIGN KEY(session_id) REFERENCES session(id),
            FOREIGN KEY(cree_par)   REFERENCES utilisateur(id)
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            uid     INTEGER,
            login   TEXT,
            action  TEXT NOT NULL,
            tbl     TEXT,
            rid     INTEGER,
            details TEXT,
            ts      TEXT DEFAULT (datetime('now','localtime'))
        );
        """)
        c.commit()
        self._seeds()

    def _seeds(self):
        """Données initiales (admin + AVEC par défaut)."""
        if not self.valeur("SELECT COUNT(*) FROM utilisateur"):
            sel = secrets.token_hex(16)
            ph  = hashlib.pbkdf2_hmac('sha256', f"admin123{sel}".encode(), sel.encode(), 100000).hex()
            self.exec(
                "INSERT INTO utilisateur(nom,login,pwd_hash,sel,role)"
                " VALUES(?,?,?,?,?)",
                ("Administrateur", "admin", ph, sel, "admin"),
            )
        if not self.valeur("SELECT COUNT(*) FROM avec"):
            self.exec(
                "INSERT INTO avec(nom,description) VALUES(?,?)",
                ("AVEC Bukavu", "Association Villageoise d'Épargne et de Crédit"),
            )
        self.commit()


# ════════════════════════════════════════════════════════════════
#  LOGIQUE MÉTIER FINANCIÈRE
# ════════════════════════════════════════════════════════════════

class Finance:
    @staticmethod
    def interet_simple(principal, taux_annuel, duree_mois):
        return round(principal * taux_annuel * (duree_mois / 12), 2)

    @staticmethod
    def penalite(montant, taux_mensuel, jours):
        return round(montant * taux_mensuel * (jours / 30), 2)

    @staticmethod
    def jours_retard(date_echeance_str):
        try:
            ech = date.fromisoformat(str(date_echeance_str)[:10])
            return max(0, (date.today() - ech).days)
        except Exception:
            return 0

    @staticmethod
    def solde_credit(cr):
        return round(cr["montant_total"] - cr["rembourse"], 2)

    @staticmethod
    def solde_epargne(db, membre_id):
        return db.valeur(
            "SELECT COALESCE(SUM(montant),0) FROM epargne"
            " WHERE membre_id=? AND annule=0",
            (membre_id,),
        ) or 0

    @staticmethod
    def date_echeance(date_octroi: date, duree_mois: int) -> date:
        mois  = date_octroi.month + duree_mois
        annee = date_octroi.year + (mois - 1) // 12
        mois  = (mois - 1) % 12 + 1
        bissextile = annee % 4 == 0 and (annee % 100 != 0 or annee % 400 == 0)
        jour  = min(date_octroi.day,
                    [31, 29 if bissextile else 28, 31, 30, 31, 30,
                     31, 31, 30, 31, 30, 31][mois-1])
        return date(annee, mois, jour)

    @staticmethod
    def maj_statuts(db):
        """Met à jour automatiquement les statuts des crédits."""
        auj = date.today().isoformat()
        db.exec("""
            UPDATE credit SET statut='en_retard'
            WHERE statut='actif' AND date_echeance < ? AND rembourse < montant_total
        """, (auj,))
        db.exec("""
            UPDATE credit SET statut='solde'
            WHERE statut IN ('actif','en_retard') AND rembourse >= montant_total
        """)
        db.commit()

    @staticmethod
    def valider_date(s):
        if not s or not s.strip():
            raise ValueError("La date est obligatoire.")
        try:
            return date.fromisoformat(s.strip())
        except ValueError:
            raise ValueError(f"Format invalide : '{s}'. Utilisez AAAA-MM-JJ.")

    @staticmethod
    def valider_montant(s):
        if not s or not str(s).strip():
            raise ValueError("Le montant est obligatoire.")
        try:
            v = float(str(s).replace(" ", "").replace(",", "."))
            if v <= 0:
                raise ValueError("Le montant doit être strictement positif.")
            return v
        except ValueError as e:
            if "positif" in str(e):
                raise
            raise ValueError(f"Montant invalide : '{s}'.")


# ════════════════════════════════════════════════════════════════
#  AUTHENTIFICATION
# ════════════════════════════════════════════════════════════════

class Auth:
    def __init__(self, db):
        self.db   = db
        self.user = None          # dict de l'utilisateur connecté

    def connecter(self, login, mdp):
        u = self.db.un("SELECT * FROM utilisateur WHERE login=? AND actif=1", (login,))
        if not u:
            return False
        if hashlib.pbkdf2_hmac('sha256', f"{mdp}{u['sel']}".encode(), u['sel'].encode(), 100000).hex() == u["pwd_hash"]:
            self.user = u
            self.db.audit(u["id"], login, "CONNEXION")
            return True
        return False

    def changer_mdp(self, login, ancien, nouveau):
        if not self.connecter(login, ancien):
            raise ValueError("Ancien mot de passe incorrect.")
        sel = secrets.token_hex(16)
        ph  = hashlib.pbkdf2_hmac('sha256', f"{nouveau}{sel}".encode(), sel.encode(), 100000).hex()
        self.db.exec("UPDATE utilisateur SET pwd_hash=?,sel=? WHERE login=?", (ph, sel, login))
        self.db.commit()
        self.user = self.db.un("SELECT * FROM utilisateur WHERE login=?", (login,))

    @property
    def est_admin(self):
        return self.user and self.user["role"] == "admin"

    @property
    def uid(self):
        return self.user["id"] if self.user else None

    @property
    def ulogin(self):
        return self.user["login"] if self.user else None


# ════════════════════════════════════════════════════════════════
#  SAUVEGARDE AUTOMATIQUE
# ════════════════════════════════════════════════════════════════

class Backup:
    def __init__(self, db_chemin=DB_CHEMIN, rep=BACKUP_DIR):
        self.src = db_chemin
        self.rep = Path(rep)

    def sauvegarder(self):
        self.rep.mkdir(exist_ok=True)
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = self.rep / f"akibacore_{ts}.db"
        shutil.copy2(self.src, dest)
        # Supprimer les plus anciennes
        backups = sorted(self.rep.glob("akibacore_*.db"))
        while len(backups) > BACKUP_MAX:
            backups.pop(0).unlink(missing_ok=True)
        return str(dest)


# ════════════════════════════════════════════════════════════════
#  STYLES TTK
# ════════════════════════════════════════════════════════════════

def appliquer_styles(root):
    s = ttk.Style(root)
    s.theme_use("clam")

    s.configure("TFrame",        background=C["gris"])
    s.configure("Blanc.TFrame",  background=C["blanc"])
    s.configure("TLabel",        background=C["gris"], foreground=C["texte"], font=("Segoe UI", 10))
    s.configure("Titre.TLabel",  background=C["gris"], foreground=C["bleu"],
                                 font=("Segoe UI", 15, "bold"))
    s.configure("Sub.TLabel",    background=C["gris"], foreground=C["bleu"],
                                 font=("Segoe UI", 11, "bold"))
    s.configure("Bold.TLabel",   background=C["blanc"], foreground=C["texte"],
                                 font=("Segoe UI", 10, "bold"))

    s.configure("TButton",       font=("Segoe UI", 10), padding=6)
    s.configure("Bleu.TButton",  background=C["bleu"],  foreground=C["blanc"],
                                 font=("Segoe UI", 10, "bold"), padding=8)
    s.map("Bleu.TButton",  background=[("active", C["bleu_f"])])
    s.configure("Vert.TButton",  background=C["vert"],  foreground=C["blanc"],
                                 font=("Segoe UI", 10, "bold"), padding=8)
    s.map("Vert.TButton",  background=[("active", "#176338")])
    s.configure("Rouge.TButton", background=C["rouge"], foreground=C["blanc"],
                                 font=("Segoe UI", 10, "bold"), padding=8)
    s.map("Rouge.TButton", background=[("active", "#A93226")])

    s.configure("TNotebook",     background=C["gris"], borderwidth=0)
    s.configure("TNotebook.Tab", font=("Segoe UI", 10, "bold"), padding=(14, 7))
    s.map("TNotebook.Tab",
          background=[("selected", C["bleu"]), ("!selected", C["gris_f"])],
          foreground=[("selected", C["blanc"]), ("!selected", C["texte"])])

    s.configure("Treeview",          font=("Segoe UI", 10), rowheight=26,
                                     background=C["blanc"], foreground=C["texte"],
                                     fieldbackground=C["blanc"])
    s.configure("Treeview.Heading",  font=("Segoe UI", 10, "bold"),
                                     background=C["bleu"], foreground=C["blanc"])
    s.map("Treeview",                background=[("selected", C["or"])])
    s.configure("TEntry",            font=("Segoe UI", 10), padding=5)
    s.configure("TCombobox",         font=("Segoe UI", 10), padding=5)
    s.configure("TLabelframe",       background=C["gris"])
    s.configure("TLabelframe.Label", background=C["gris"], foreground=C["bleu"],
                                     font=("Segoe UI", 10, "bold"))


# ════════════════════════════════════════════════════════════════
#  WIDGETS RÉUTILISABLES
# ════════════════════════════════════════════════════════════════

def btn(parent, texte, cmd, style="TButton", l=None):
    b = ttk.Button(parent, text=texte, command=cmd, style=style)
    if l:
        b.config(width=l)
    return b


def champ(parent, label, row, defaut="", largeur=28, secret=False):
    ttk.Label(parent, text=label).grid(row=row, column=0, sticky="e", padx=(0, 8), pady=5)
    var = tk.StringVar(value=defaut)
    e   = ttk.Entry(parent, textvariable=var, width=largeur, show="*" if secret else "")
    e.grid(row=row, column=1, sticky="ew", pady=5)
    return var, e


def treeview(parent, cols, largeurs=None):
    """Crée un Treeview avec double scrollbar dans un Frame."""
    f   = ttk.Frame(parent)
    sv  = ttk.Scrollbar(f, orient="vertical")
    sh  = ttk.Scrollbar(f, orient="horizontal")
    lrg = largeurs or [100] * len(cols)
    tv  = ttk.Treeview(f, columns=cols, show="headings",
                       yscrollcommand=sv.set, xscrollcommand=sh.set,
                       selectmode="browse")
    sv.config(command=tv.yview)
    sh.config(command=tv.xview)
    for col, l in zip(cols, lrg):
        tv.heading(col, text=col, anchor="w")
        tv.column(col, width=l, minwidth=40, anchor="w")
    tv.grid(row=0, column=0, sticky="nsew")
    sv.grid(row=0, column=1, sticky="ns")
    sh.grid(row=1, column=0, sticky="ew")
    f.rowconfigure(0, weight=1)
    f.columnconfigure(0, weight=1)
    tv.tag_configure("p", background=C["ligne_p"])
    tv.tag_configure("i", background=C["ligne_i"])
    tv.tag_configure("rouge",  background="#FADBD8")
    tv.tag_configure("vert",   background="#D5F5E3")
    tv.tag_configure("orange", background="#FDEBD0")
    return tv, f


def sep(parent):
    ttk.Separator(parent, orient="horizontal").pack(fill="x", padx=12, pady=6)


def centrer(win, w, h):
    win.update_idletasks()
    x = (win.winfo_screenwidth()  - w) // 2
    y = (win.winfo_screenheight() - h) // 2
    win.geometry(f"{w}x{h}+{x}+{y}")


# ════════════════════════════════════════════════════════════════
#  ÉCRAN DE CONNEXION
# ════════════════════════════════════════════════════════════════

class EcranConnexion(tk.Toplevel):
    def __init__(self, parent, auth, callback):
        super().__init__(parent)
        self.auth     = auth
        self.callback = callback
        self.title(f"{APP_NOM} — Connexion sécurisée")
        self.resizable(False, False)
        self.configure(bg=C["bleu"])
        self.grab_set()
        self.focus_force()
        centrer(self, 400, 340)
        self._ui()

    def _ui(self):
        # En-tête
        tk.Label(self, text=APP_NOM, font=("Segoe UI", 28, "bold"),
                 fg=C["blanc"], bg=C["bleu"]).pack(pady=(30, 4))
        tk.Label(self, text="Gestion AVEC — Accès sécurisé",
                 font=("Segoe UI", 10), fg="#AED6F1", bg=C["bleu"]).pack(pady=(0, 16))

        # Formulaire blanc
        f = tk.Frame(self, bg=C["blanc"])
        f.pack(fill="x", padx=28)

        for row, (lbl, attr, show) in enumerate([
            ("Identifiant",   "v_login", ""),
            ("Mot de passe",  "v_mdp",   "*"),
        ]):
            tk.Label(f, text=lbl, bg=C["blanc"],
                     font=("Segoe UI", 10)).grid(row=row*2,   column=0, sticky="w", padx=12, pady=(10,2))
            setattr(self, attr, tk.StringVar())
            e = ttk.Entry(f, textvariable=getattr(self, attr), show=show, width=26)
            e.grid(row=row*2+1, column=0, padx=12, sticky="ew", pady=(0, 6))
            if show == "*":
                e.bind("<Return>", lambda ev: self._connecter())
        f.columnconfigure(0, weight=1)

        # Message
        self.v_msg = tk.StringVar()
        tk.Label(self, textvariable=self.v_msg, fg="#FADBD8",
                 bg=C["bleu"], font=("Segoe UI", 9)).pack(pady=(8, 0))

        tk.Button(self, text="SE CONNECTER", command=self._connecter,
                  bg=C["or"], fg=C["blanc"], font=("Segoe UI", 11, "bold"),
                  relief="flat", padx=24, pady=8, cursor="hand2",
                  activebackground="#B7950B").pack(pady=12)

        tk.Label(self, text="Compte par défaut : admin / admin123",
                 font=("Segoe UI", 8), fg="#AED6F1", bg=C["bleu"]).pack()

    def _connecter(self):
        login = self.v_login.get().strip()
        mdp   = self.v_mdp.get()
        if not login or not mdp:
            self.v_msg.set("Veuillez remplir tous les champs.")
            return
        if self.auth.connecter(login, mdp):
            self.destroy()
            self.callback()
        else:
            self.v_msg.set("Identifiant ou mot de passe incorrect.")
            self.v_mdp.set("")


# ════════════════════════════════════════════════════════════════
#  TABLEAU DE BORD
# ════════════════════════════════════════════════════════════════

class Dashboard(ttk.Frame):
    def __init__(self, parent, db, auth, avec_id=1):
        super().__init__(parent)
        self.db      = db
        self.auth    = auth
        self.avec_id = avec_id
        self.configure(style="TFrame")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self._ui()

    def _ui(self):
        hdr = ttk.Frame(self)
        hdr.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 6))
        ttk.Label(hdr, text=f"Tableau de Bord — {APP_NOM}", style="Titre.TLabel").pack(side="left")
        btn(hdr, "Actualiser", self.actualiser, "Bleu.TButton").pack(side="right")

        self.corps = ttk.Frame(self)
        self.corps.grid(row=1, column=0, sticky="nsew", padx=16, pady=8)
        for c in range(4):
            self.corps.columnconfigure(c, weight=1)
        self.actualiser()

    def actualiser(self):
        for w in self.corps.winfo_children():
            w.destroy()
        Finance.maj_statuts(self.db)
        s = self._stats()

        cartes = [
            ("Membres actifs",         str(s["membres"]),             C["bleu"]),
            ("Total Épargnes (FC)",     f"{s['epargnes']:,.0f}",       C["vert"]),
            ("Portefeuille Crédit (FC)",f"{s['credits_actifs']:,.0f}", "#7D6608"),
            ("Total Remboursé (FC)",    f"{s['rembs']:,.0f}",          "#6C3483"),
            ("Crédits en retard",       str(s["retards"]),             C["rouge"]),
            ("Sessions ouvertes",       str(s["sessions"]),            "#1A5276"),
            ("Solde net (FC)",          f"{s['solde']:,.0f}",          C["vert"] if s["solde"]>=0 else C["rouge"]),
            ("Membres sans crédit",     str(s["sans_credit"]),         "#117A65"),
        ]
        for i, (titre, valeur, coul) in enumerate(cartes):
            r, c = divmod(i, 4)
            self._carte(titre, valeur, coul, r, c)

        # Journal récent
        jf = ttk.LabelFrame(self.corps, text="Journal des 20 dernières actions", padding=6)
        jf.grid(row=2, column=0, columnspan=4, sticky="ew", padx=4, pady=(12, 4))
        cols = ("Horodatage", "Utilisateur", "Action", "Détails")
        tv, f = treeview(jf, cols, [130, 100, 120, 400])
        f.pack(fill="both", expand=True)
        logs = self.db.tous(
            "SELECT ts,login,action,details FROM audit_log ORDER BY id DESC LIMIT 20")
        for i, l in enumerate(logs):
            tag = "p" if i % 2 == 0 else "i"
            tv.insert("", "end", values=(l["ts"], l["login"] or "—",
                                         l["action"], l["details"] or ""), tags=(tag,))

    def _carte(self, titre, valeur, couleur, row, col):
        c = tk.Frame(self.corps, bg=couleur)
        c.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")
        tk.Label(c, text=valeur, font=("Segoe UI", 17, "bold"),
                 bg=couleur, fg=C["blanc"]).pack(padx=14, pady=(14, 2))
        tk.Label(c, text=titre, font=("Segoe UI", 9),
                 bg=couleur, fg=C["blanc"]).pack(padx=14, pady=(0, 14))

    def _stats(self):
        db, aid = self.db, self.avec_id
        membres = db.valeur(
            "SELECT COUNT(*) FROM membre WHERE statut='actif' AND avec_id=?", (aid,)) or 0
        epargnes = db.valeur(
            "SELECT COALESCE(SUM(e.montant),0) FROM epargne e"
            " JOIN membre m ON e.membre_id=m.id WHERE m.avec_id=? AND e.annule=0", (aid,)) or 0
        credits_a = db.valeur(
            "SELECT COALESCE(SUM(montant_total-rembourse),0) FROM credit c"
            " JOIN membre m ON c.membre_id=m.id"
            " WHERE m.avec_id=? AND c.statut IN ('actif','en_retard')", (aid,)) or 0
        rembs = db.valeur(
            "SELECT COALESCE(SUM(r.montant_total),0) FROM remboursement r"
            " JOIN membre m ON r.membre_id=m.id WHERE m.avec_id=? AND r.annule=0", (aid,)) or 0
        retards = db.valeur(
            "SELECT COUNT(*) FROM credit c JOIN membre m ON c.membre_id=m.id"
            " WHERE m.avec_id=? AND c.statut='en_retard'", (aid,)) or 0
        sessions = db.valeur(
            "SELECT COUNT(*) FROM session WHERE avec_id=? AND statut='ouverte'", (aid,)) or 0
        sans_c = db.valeur(
            "SELECT COUNT(*) FROM membre m WHERE avec_id=? AND statut='actif'"
            " AND id NOT IN (SELECT DISTINCT membre_id FROM credit WHERE statut IN ('actif','en_retard'))",
            (aid,)) or 0
        return dict(membres=membres, epargnes=epargnes, credits_actifs=credits_a,
                    rembs=rembs, retards=retards, sessions=sessions,
                    solde=epargnes - credits_a, sans_credit=sans_c)


# ════════════════════════════════════════════════════════════════
#  MEMBRES
# ════════════════════════════════════════════════════════════════

class OngletMembres(ttk.Frame):
    def __init__(self, parent, db, auth, avec_id=1):
        super().__init__(parent)
        self.db = db; self.auth = auth; self.avec_id = avec_id
        self.columnconfigure(0, weight=1); self.rowconfigure(2, weight=1)
        self._ui()
        self.actualiser()

    def _ui(self):
        # Barre
        bar = ttk.Frame(self)
        bar.grid(row=0, column=0, sticky="ew", padx=12, pady=8)
        ttk.Label(bar, text="Gestion des Membres", style="Titre.TLabel").pack(side="left")
        for txt, cmd, st in [
            ("+ Ajouter",  self.ajouter,  "Vert.TButton"),
            ("Modifier",   self.modifier, "Bleu.TButton"),
            ("Détail",     self.detail,   "TButton"),
            ("Actualiser", self.actualiser,"TButton"),
        ]:
            btn(bar, txt, cmd, st).pack(side="right", padx=3)

        # Recherche
        rech = ttk.Frame(self)
        rech.grid(row=1, column=0, sticky="ew", padx=12, pady=4)
        ttk.Label(rech, text="Rechercher :").pack(side="left")
        self.v_rech = tk.StringVar()
        self.v_rech.trace("w", lambda *a: self.actualiser())
        ttk.Entry(rech, textvariable=self.v_rech, width=32).pack(side="left", padx=8)

        # Tableau
        cols = ("ID","N° Membre","Nom complet","Téléphone","Parts",
                "Épargne FC","Crédit actif FC","Statut","Adhésion")
        lrg  = [40, 90, 170, 110, 55, 110, 120, 80, 100]
        self.tv, f = treeview(self, cols, lrg)
        f.grid(row=2, column=0, sticky="nsew", padx=12, pady=4)
        self.tv.bind("<Double-1>", lambda e: self.detail())

        # Résumé
        self.v_res = tk.StringVar()
        ttk.Label(self, textvariable=self.v_res,
                  font=("Segoe UI", 10, "bold")).grid(row=3, column=0, pady=6)

    def actualiser(self):
        for it in self.tv.get_children():
            self.tv.delete(it)
        terme = (self.v_rech.get() if hasattr(self, "v_rech") else "").strip().lower()
        membres = self.db.tous("""
            SELECT m.id, m.numero, m.nom, m.prenom, m.telephone, m.nb_parts, m.statut, m.date_adhesion
            FROM membre m WHERE m.avec_id=? ORDER BY m.nom, m.prenom
        """, (self.avec_id,))

        total_ep = 0
        nb = 0
        for i, m in enumerate(membres):
            nc = f"{m['nom']} {m['prenom'] or ''}".strip()
            if terme and terme not in (nc + (m["telephone"] or "")).lower():
                continue
            ep = Finance.solde_epargne(self.db, m["id"])
            cr = self.db.valeur(
                "SELECT COALESCE(SUM(montant_total-rembourse),0) FROM credit"
                " WHERE membre_id=? AND statut IN ('actif','en_retard')", (m["id"],)) or 0
            tag = "rouge" if m["statut"] != "actif" else ("p" if i%2==0 else "i")
            self.tv.insert("", "end", iid=str(m["id"]), tags=(tag,), values=(
                m["id"], m["numero"] or "—", nc, m["telephone"] or "—",
                m["nb_parts"], f"{ep:,.0f}", f"{cr:,.0f}" if cr else "—",
                m["statut"].upper(), m["date_adhesion"] or "—"))
            total_ep += ep
            nb += 1
        self.v_res.set(f"{nb} membre(s) affiché(s)  |  Épargnes totales : {total_ep:,.0f} FC")

    def _sel(self):
        s = self.tv.focus()
        if not s:
            messagebox.showwarning("Sélection", "Sélectionnez un membre.")
            return None
        return int(s)

    def ajouter(self):
        DlgMembre(self, self.db, self.auth, self.avec_id, callback=self.actualiser)

    def modifier(self):
        mid = self._sel()
        if mid:
            m = self.db.un("SELECT * FROM membre WHERE id=?", (mid,))
            DlgMembre(self, self.db, self.auth, self.avec_id, membre=m, callback=self.actualiser)

    def detail(self):
        mid = self._sel()
        if mid:
            m = self.db.un("SELECT * FROM membre WHERE id=?", (mid,))
            DlgDetailMembre(self, self.db, m)


class DlgMembre(tk.Toplevel):
    def __init__(self, parent, db, auth, avec_id, membre=None, callback=None):
        super().__init__(parent)
        self.db = db; self.auth = auth; self.avec_id = avec_id
        self.m = membre; self.cb = callback
        self.title("Modifier membre" if membre else "Ajouter un membre")
        self.resizable(False, False)
        self.grab_set()
        centrer(self, 450, 490)
        self._ui()

    def _ui(self):
        m   = self.m or {}
        frm = ttk.Frame(self, padding=20)
        frm.pack(fill="both", expand=True)
        frm.columnconfigure(1, weight=1)

        ttk.Label(frm, text="Informations du membre", style="Sub.TLabel").grid(
            row=0, column=0, columnspan=2, pady=(0, 14))

        self.vs = {}
        donnees = [
            ("nom",          "Nom *",                  m.get("nom", "")),
            ("prenom",       "Prénom",                 m.get("prenom", "")),
            ("telephone",    "Téléphone",               m.get("telephone", "")),
            ("adresse",      "Adresse",                 m.get("adresse", "")),
            ("numero",       "N° Membre",               m.get("numero", "")),
            ("nb_parts",     "Nombre de parts",         str(m.get("nb_parts", 1))),
            ("date_adhesion","Adhésion (AAAA-MM-JJ)",   m.get("date_adhesion",
                                                               date.today().isoformat())),
            ("notes",        "Notes",                   m.get("notes", "")),
        ]
        for r, (k, lbl, def_) in enumerate(donnees, 1):
            v, _ = champ(frm, lbl, r, def_)
            self.vs[k] = v

        r2 = len(donnees) + 1
        ttk.Label(frm, text="Statut").grid(row=r2, column=0, sticky="e", padx=(0,8), pady=5)
        self.v_statut = tk.StringVar(value=m.get("statut", "actif"))
        ttk.Combobox(frm, textvariable=self.v_statut,
                     values=["actif","suspendu","sorti"],
                     state="readonly", width=26).grid(row=r2, column=1, sticky="ew", pady=5)

        bf = ttk.Frame(frm)
        bf.grid(row=r2+1, column=0, columnspan=2, pady=16)
        btn(bf, "Enregistrer", self._sauver, "Vert.TButton").pack(side="left", padx=8)
        btn(bf, "Annuler", self.destroy).pack(side="left", padx=8)

    def _sauver(self):
        try:
            nom = self.vs["nom"].get().strip()
            if not nom:
                raise ValueError("Le nom est obligatoire.")
            nb  = int(self.vs["nb_parts"].get().strip() or 1)
            if nb < 1:
                raise ValueError("Le nombre de parts doit être >= 1.")
            dt  = Finance.valider_date(self.vs["date_adhesion"].get())
            d = dict(
                nom=nom,
                prenom=self.vs["prenom"].get().strip() or None,
                telephone=self.vs["telephone"].get().strip() or None,
                adresse=self.vs["adresse"].get().strip() or None,
                numero=self.vs["numero"].get().strip() or None,
                nb_parts=nb,
                date_adhesion=dt.isoformat(),
                statut=self.v_statut.get(),
                notes=self.vs["notes"].get().strip() or None,
                avec_id=self.avec_id,
            )
            if self.m:
                self.db.exec("""
                    UPDATE membre SET nom=:nom,prenom=:prenom,telephone=:telephone,
                    adresse=:adresse,numero=:numero,nb_parts=:nb_parts,
                    date_adhesion=:date_adhesion,statut=:statut,notes=:notes
                    WHERE id=:id
                """, {**d, "id": self.m["id"]})
                self.db.audit(self.auth.uid, self.auth.ulogin, "MODIFIER_MEMBRE",
                              "membre", self.m["id"])
            else:
                cur = self.db.exec("""
                    INSERT INTO membre(avec_id,nom,prenom,telephone,adresse,numero,
                    nb_parts,date_adhesion,statut,notes)
                    VALUES(:avec_id,:nom,:prenom,:telephone,:adresse,:numero,
                    :nb_parts,:date_adhesion,:statut,:notes)
                """, d)
                self.db.audit(self.auth.uid, self.auth.ulogin, "AJOUTER_MEMBRE",
                              "membre", cur.lastrowid, {"nom": nom})
            self.db.commit()
            if self.cb:
                self.cb()
            self.destroy()
        except (ValueError, sqlite3.Error) as e:
            messagebox.showerror("Erreur", str(e), parent=self)


class DlgDetailMembre(tk.Toplevel):
    def __init__(self, parent, db, m):
        super().__init__(parent)
        self.db = db; self.m = m
        self.title(f"Dossier — {m['nom']} {m.get('prenom') or ''}")
        centrer(self, 720, 580)
        self.grab_set()
        self._ui()

    def _ui(self):
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=8, pady=8)

        # ─ Infos ─
        fi = ttk.Frame(nb, padding=18)
        nb.add(fi, text="  Informations  ")
        for r, (lbl, val) in enumerate([
            ("Nom complet",    f"{self.m['nom']} {self.m.get('prenom') or ''}"),
            ("N° Membre",      self.m.get("numero") or "—"),
            ("Téléphone",      self.m.get("telephone") or "—"),
            ("Adresse",        self.m.get("adresse") or "—"),
            ("Nombre de parts",str(self.m.get("nb_parts", 1))),
            ("Adhésion",       self.m.get("date_adhesion") or "—"),
            ("Statut",         (self.m.get("statut") or "").upper()),
            ("Notes",          self.m.get("notes") or "—"),
        ]):
            ttk.Label(fi, text=f"{lbl} :", font=("Segoe UI", 10, "bold"), background=C["gris"]).grid(
                row=r, column=0, sticky="e", padx=(0, 14), pady=4)
            ttk.Label(fi, text=val).grid(row=r, column=1, sticky="w", pady=4)

        epargne_totale = Finance.solde_epargne(self.db, self.m["id"])
        ttk.Label(fi, text=f"Épargne totale : {epargne_totale:,.0f} FC",
                  font=("Segoe UI", 12, "bold"), foreground=C["vert"],
                  background=C["gris"]).grid(row=9, column=0, columnspan=2, pady=10)

        # ─ Épargnes ─
        fe = ttk.Frame(nb)
        nb.add(fe, text="  Épargnes  ")
        cols = ("Date", "Type", "Montant FC", "Description", "Statut")
        tv_e, frm_e = treeview(fe, cols, [140, 90, 110, 250, 70])
        frm_e.pack(fill="both", expand=True, padx=4, pady=4)
        eps = self.db.tous(
            "SELECT date_op,type,montant,description,annule FROM epargne"
            " WHERE membre_id=? AND annule=0 ORDER BY date_op DESC", (self.m["id"],))
        for i, e in enumerate(eps):
            tv_e.insert("", "end", tags=("p" if i%2==0 else "i",), values=(
                e["date_op"], e["type"], f"{e['montant']:,.0f}",
                e["description"] or "", "ANNULÉ" if e["annule"] else "✓"))

        # ─ Crédits ─
        fc = ttk.Frame(nb)
        nb.add(fc, text="  Crédits  ")
        cols2 = ("Octroi", "Principal FC","Intérêt FC","Total FC","Remboursé","Solde","Échéance","Statut")
        tv_c, frm_c = treeview(fc, cols2, [100,110,100,100,100,100,100,90])
        frm_c.pack(fill="both", expand=True, padx=4, pady=4)
        creds = self.db.tous(
            "SELECT date_octroi,principal,montant_interet,montant_total,rembourse,"
            "date_echeance,statut FROM credit WHERE membre_id=? ORDER BY date_octroi DESC",
            (self.m["id"],))
        for i, c in enumerate(creds):
            solde = c["montant_total"] - c["rembourse"]
            tag = "rouge" if c["statut"]=="en_retard" else ("vert" if c["statut"]=="solde" else ("p" if i%2==0 else "i"))
            tv_c.insert("", "end", tags=(tag,), values=(
                c["date_octroi"], f"{c['principal']:,.0f}", f"{c['montant_interet']:,.0f}",
                f"{c['montant_total']:,.0f}", f"{c['rembourse']:,.0f}", f"{solde:,.0f}",
                c["date_echeance"], c["statut"].upper()))


# ════════════════════════════════════════════════════════════════
#  ÉPARGNES
# ════════════════════════════════════════════════════════════════

class OngletEpargnes(ttk.Frame):
    def __init__(self, parent, db, auth, avec_id=1):
        super().__init__(parent)
        self.db = db; self.auth = auth; self.avec_id = avec_id
        self.columnconfigure(0, weight=1); self.rowconfigure(1, weight=1)
        self._ui(); self.actualiser()

    def _ui(self):
        bar = ttk.Frame(self)
        bar.grid(row=0, column=0, sticky="ew", padx=12, pady=8)
        ttk.Label(bar, text="Épargnes", style="Titre.TLabel").pack(side="left")
        for txt, cmd, st in [
            ("+ Enregistrer dépôt", self.ajouter,  "Vert.TButton"),
            ("Annuler opération",   self.annuler,  "Rouge.TButton"),
            ("Actualiser",          self.actualiser,"TButton"),
        ]:
            btn(bar, txt, cmd, st).pack(side="right", padx=3)

        cols = ("ID","Date","Membre","Type","Montant FC","Description","Statut")
        lrg  = [40, 140, 180, 90, 110, 240, 70]
        self.tv, f = treeview(self, cols, lrg)
        f.grid(row=1, column=0, sticky="nsew", padx=12, pady=4)

        self.v_res = tk.StringVar()
        ttk.Label(self, textvariable=self.v_res,
                  font=("Segoe UI", 10, "bold")).grid(row=2, column=0, pady=6)

    def actualiser(self):
        for it in self.tv.get_children():
            self.tv.delete(it)
        rows = self.db.tous("""
            SELECT e.id, e.date_op, m.nom, m.prenom, e.type, e.montant, e.description, e.annule
            FROM epargne e JOIN membre m ON e.membre_id=m.id
            WHERE m.avec_id=? ORDER BY e.date_op DESC LIMIT 600
        """, (self.avec_id,))
        total = 0
        for i, r in enumerate(rows):
            nc  = f"{r['nom']} {r['prenom'] or ''}".strip()
            tag = "rouge" if r["annule"] else ("p" if i%2==0 else "i")
            self.tv.insert("", "end", iid=str(r["id"]), tags=(tag,), values=(
                r["id"], r["date_op"], nc, r["type"],
                f"{r['montant']:,.0f}", r["description"] or "",
                "ANNULÉ" if r["annule"] else "✓"))
            if not r["annule"]:
                total += r["montant"]
        self.v_res.set(f"Total épargnes valides : {total:,.0f} FC")

    def ajouter(self):
        DlgEpargne(self, self.db, self.auth, self.avec_id, callback=self.actualiser)

    def annuler(self):
        s = self.tv.focus()
        if not s:
            messagebox.showwarning("Sélection", "Sélectionnez une opération."); return
        if not messagebox.askyesno("Confirmer annulation",
           "Annuler cette opération d'épargne ? Cette action est irréversible.", parent=self):
            return
        try:
            self.db.exec("UPDATE epargne SET annule=1 WHERE id=?", (int(s),))
            self.db.commit()
            self.db.audit(self.auth.uid, self.auth.ulogin, "ANNULER_EPARGNE", "epargne", int(s))
            self.actualiser()
        except sqlite3.Error as e:
            messagebox.showerror("Erreur", str(e))


class DlgEpargne(tk.Toplevel):
    def __init__(self, parent, db, auth, avec_id, callback=None):
        super().__init__(parent)
        self.db = db; self.auth = auth; self.avec_id = avec_id; self.cb = callback
        self.title("Enregistrer un dépôt d'épargne")
        self.resizable(False, False); self.grab_set()
        centrer(self, 440, 360)
        self._ui()

    def _ui(self):
        frm = ttk.Frame(self, padding=20)
        frm.pack(fill="both", expand=True)
        frm.columnconfigure(1, weight=1)
        ttk.Label(frm, text="Nouveau dépôt d'épargne", style="Sub.TLabel").grid(
            row=0, column=0, columnspan=2, pady=(0, 14))

        membres = self.db.tous(
            "SELECT id,nom,prenom FROM membre WHERE avec_id=? AND statut='actif' ORDER BY nom",
            (self.avec_id,))
        self.mmap = {f"{m['nom']} {m['prenom'] or ''}".strip(): m["id"] for m in membres}

        ttk.Label(frm, text="Membre *").grid(row=1, column=0, sticky="e", padx=(0,8), pady=5)
        self.v_m = tk.StringVar()
        ttk.Combobox(frm, textvariable=self.v_m, values=list(self.mmap.keys()),
                     state="readonly", width=26).grid(row=1, column=1, sticky="ew", pady=5)

        self.v_mt, _ = champ(frm, "Montant (FC) *",         2)
        self.v_dt, _ = champ(frm, "Date (AAAA-MM-JJ) *",    3, date.today().isoformat())

        ttk.Label(frm, text="Type").grid(row=4, column=0, sticky="e", padx=(0,8), pady=5)
        self.v_ty = tk.StringVar(value="ordinaire")
        ttk.Combobox(frm, textvariable=self.v_ty,
                     values=["ordinaire","solidarite","urgence"],
                     state="readonly", width=26).grid(row=4, column=1, sticky="ew", pady=5)

        self.v_dc, _ = champ(frm, "Description", 5)

        bf = ttk.Frame(frm)
        bf.grid(row=6, column=0, columnspan=2, pady=16)
        btn(bf, "Enregistrer", self._sauver, "Vert.TButton").pack(side="left", padx=8)
        btn(bf, "Annuler", self.destroy).pack(side="left", padx=8)

    def _sauver(self):
        try:
            nom = self.v_m.get()
            if not nom or nom not in self.mmap:
                raise ValueError("Sélectionnez un membre.")
            mt = Finance.valider_montant(self.v_mt.get())
            dt = Finance.valider_date(self.v_dt.get())
            cur = self.db.exec("""
                INSERT INTO epargne(membre_id,montant,type,date_op,description,cree_par)
                VALUES(?,?,?,?,?,?)
            """, (self.mmap[nom], mt, self.v_ty.get(), dt.isoformat(),
                  self.v_dc.get().strip() or None, self.auth.uid))
            self.db.commit()
            self.db.audit(self.auth.uid, self.auth.ulogin, "AJOUTER_EPARGNE",
                          "epargne", cur.lastrowid, {"membre": nom, "montant": mt})
            if self.cb: self.cb()
            self.destroy()
        except (ValueError, sqlite3.Error) as e:
            messagebox.showerror("Erreur", str(e), parent=self)


# ════════════════════════════════════════════════════════════════
#  CRÉDITS
# ════════════════════════════════════════════════════════════════

class OngletCredits(ttk.Frame):
    def __init__(self, parent, db, auth, avec_id=1):
        super().__init__(parent)
        self.db = db; self.auth = auth; self.avec_id = avec_id
        self.columnconfigure(0, weight=1); self.rowconfigure(1, weight=1)
        self._ui(); self.actualiser()

    def _ui(self):
        bar = ttk.Frame(self)
        bar.grid(row=0, column=0, sticky="ew", padx=12, pady=8)
        ttk.Label(bar, text="Crédits / Prêts", style="Titre.TLabel").pack(side="left")
        for txt, cmd, st in [
            ("+ Octroyer crédit", self.ajouter,   "Vert.TButton"),
            ("Actualiser",        self.actualiser, "TButton"),
        ]:
            btn(bar, txt, cmd, st).pack(side="right", padx=3)

        cols = ("ID","Membre","Principal FC","Intérêt FC","Total dû FC",
                "Remboursé FC","Solde FC","Durée","Échéance","Statut")
        lrg  = [40, 170, 110, 100, 100, 100, 100, 65, 100, 110]
        self.tv, f = treeview(self, cols, lrg)
        f.grid(row=1, column=0, sticky="nsew", padx=12, pady=4)

        self.v_res = tk.StringVar()
        ttk.Label(self, textvariable=self.v_res,
                  font=("Segoe UI", 10, "bold")).grid(row=2, column=0, pady=6)

    def actualiser(self):
        Finance.maj_statuts(self.db)
        for it in self.tv.get_children():
            self.tv.delete(it)
        rows = self.db.tous("""
            SELECT c.id, m.nom, m.prenom, c.principal, c.montant_interet, c.montant_total,
                   c.rembourse, c.duree_mois, c.date_echeance, c.statut
            FROM credit c JOIN membre m ON c.membre_id=m.id
            WHERE m.avec_id=? ORDER BY c.date_octroi DESC
        """, (self.avec_id,))
        total_pf = 0
        for i, r in enumerate(rows):
            solde = r["montant_total"] - r["rembourse"]
            nc    = f"{r['nom']} {r['prenom'] or ''}".strip()
            jr    = Finance.jours_retard(r["date_echeance"])
            statut_aff = r["statut"].upper()
            if r["statut"] == "en_retard":
                statut_aff = f"RETARD ({jr}j)"
            tag = ("rouge" if r["statut"]=="en_retard" else
                   "vert"  if r["statut"]=="solde"     else
                   "p" if i%2==0 else "i")
            self.tv.insert("", "end", iid=str(r["id"]), tags=(tag,), values=(
                r["id"], nc, f"{r['principal']:,.0f}", f"{r['montant_interet']:,.0f}",
                f"{r['montant_total']:,.0f}", f"{r['rembourse']:,.0f}", f"{solde:,.0f}",
                f"{r['duree_mois']} mois", r["date_echeance"], statut_aff))
            if r["statut"] in ("actif","en_retard"):
                total_pf += solde
        self.v_res.set(f"Portefeuille crédit actif : {total_pf:,.0f} FC")

    def ajouter(self):
        DlgCredit(self, self.db, self.auth, self.avec_id, callback=self.actualiser)


class DlgCredit(tk.Toplevel):
    def __init__(self, parent, db, auth, avec_id, callback=None):
        super().__init__(parent)
        self.db = db; self.auth = auth; self.avec_id = avec_id; self.cb = callback
        self.title("Octroyer un crédit")
        self.resizable(False, False); self.grab_set()
        centrer(self, 480, 440)
        self._ui()

    def _ui(self):
        frm = ttk.Frame(self, padding=20)
        frm.pack(fill="both", expand=True)
        frm.columnconfigure(1, weight=1)
        ttk.Label(frm, text="Octroyer un crédit", style="Sub.TLabel").grid(
            row=0, column=0, columnspan=2, pady=(0, 14))

        membres = self.db.tous(
            "SELECT id,nom,prenom FROM membre WHERE avec_id=? AND statut='actif' ORDER BY nom",
            (self.avec_id,))
        self.mmap = {f"{m['nom']} {m['prenom'] or ''}".strip(): m["id"] for m in membres}

        ttk.Label(frm, text="Membre *").grid(row=1, column=0, sticky="e", padx=(0,8), pady=5)
        self.v_m = tk.StringVar()
        ttk.Combobox(frm, textvariable=self.v_m, values=list(self.mmap.keys()),
                     state="readonly", width=26).grid(row=1, column=1, sticky="ew", pady=5)

        self.v_p, _  = champ(frm, "Montant principal (FC) *", 2)
        self.v_t, _  = champ(frm, "Taux annuel (ex: 0.10 = 10%) *", 3,
                             str(TAUX_INTERET_DEFAUT))
        self.v_d, _  = champ(frm, "Durée (mois) *", 4, "3")
        self.v_dt, _ = champ(frm, "Date d'octroi (AAAA-MM-JJ) *", 5, date.today().isoformat())
        self.v_dc, _ = champ(frm, "Description / Motif", 6)

        # Aperçu
        self.v_ap = tk.StringVar()
        ttk.Label(frm, textvariable=self.v_ap, foreground=C["bleu"],
                  font=("Segoe UI", 10, "italic"), background=C["gris"]).grid(
            row=7, column=0, columnspan=2, pady=4)
        for v in (self.v_p, self.v_t, self.v_d):
            v.trace("w", lambda *a: self._apercu())

        bf = ttk.Frame(frm)
        bf.grid(row=8, column=0, columnspan=2, pady=16)
        btn(bf, "Octroyer", self._sauver, "Vert.TButton").pack(side="left", padx=8)
        btn(bf, "Annuler", self.destroy).pack(side="left", padx=8)

    def _apercu(self):
        try:
            p = float(self.v_p.get() or 0)
            t = float(self.v_t.get() or 0)
            d = int(self.v_d.get() or 0)
            if p > 0 and 0 < t <= 1 and d > 0:
                inter = Finance.interet_simple(p, t, d)
                self.v_ap.set(f"Intérêt : {inter:,.0f} FC  |  Total : {p+inter:,.0f} FC")
        except Exception:
            self.v_ap.set("")

    def _sauver(self):
        try:
            nom = self.v_m.get()
            if not nom or nom not in self.mmap:
                raise ValueError("Sélectionnez un membre.")
            mid  = self.mmap[nom]
            p    = Finance.valider_montant(self.v_p.get())
            t    = float(self.v_t.get())
            if not (0 < t <= 1):
                raise ValueError("Le taux doit être entre 0 et 1 (ex: 0.10 pour 10%).")
            dur  = int(self.v_d.get())
            if dur < 1:
                raise ValueError("La durée doit être >= 1 mois.")
            do   = Finance.valider_date(self.v_dt.get())
            inter = Finance.interet_simple(p, t, dur)
            total = round(p + inter, 2)
            ech   = Finance.date_echeance(do, dur)

            # Vérifier que le membre n'a pas déjà un crédit actif trop élevé
            solde_actuel = self.db.valeur(
                "SELECT COALESCE(SUM(montant_total-rembourse),0) FROM credit"
                " WHERE membre_id=? AND statut IN ('actif','en_retard')", (mid,)) or 0
            if solde_actuel > 0:
                if not messagebox.askyesno("Attention",
                    f"Ce membre a déjà {solde_actuel:,.0f} FC de crédit actif.\n"
                    "Confirmer l'octroi d'un nouveau crédit ?", parent=self):
                    return

            cur = self.db.exec("""
                INSERT INTO credit(membre_id,principal,taux,duree_mois,date_octroi,date_echeance,
                montant_interet,montant_total,description,cree_par)
                VALUES(?,?,?,?,?,?,?,?,?,?)
            """, (mid, p, t, dur, do.isoformat(), ech.isoformat(),
                  inter, total, self.v_dc.get().strip() or None, self.auth.uid))
            self.db.commit()
            self.db.audit(self.auth.uid, self.auth.ulogin, "OCTROYER_CREDIT",
                          "credit", cur.lastrowid,
                          {"membre": nom, "principal": p, "taux": t, "echeance": ech.isoformat()})
            messagebox.showinfo("Crédit octroyé",
                f"Crédit enregistré avec succès.\n\n"
                f"Principal  : {p:,.0f} FC\n"
                f"Intérêt    : {inter:,.0f} FC\n"
                f"Total dû   : {total:,.0f} FC\n"
                f"Échéance   : {ech.isoformat()}", parent=self)
            if self.cb: self.cb()
            self.destroy()
        except (ValueError, sqlite3.Error) as e:
            messagebox.showerror("Erreur", str(e), parent=self)


# ════════════════════════════════════════════════════════════════
#  REMBOURSEMENTS
# ════════════════════════════════════════════════════════════════

class OngletRemboursements(ttk.Frame):
    def __init__(self, parent, db, auth, avec_id=1):
        super().__init__(parent)
        self.db = db; self.auth = auth; self.avec_id = avec_id
        self.columnconfigure(0, weight=1); self.rowconfigure(1, weight=1)
        self._ui(); self.actualiser()

    def _ui(self):
        bar = ttk.Frame(self)
        bar.grid(row=0, column=0, sticky="ew", padx=12, pady=8)
        ttk.Label(bar, text="Remboursements", style="Titre.TLabel").pack(side="left")
        for txt, cmd, st in [
            ("+ Enregistrer paiement", self.ajouter,   "Vert.TButton"),
            ("Actualiser",             self.actualiser, "TButton"),
        ]:
            btn(bar, txt, cmd, st).pack(side="right", padx=3)

        cols = ("ID","Date","Membre","Crédit#","Principal FC","Intérêt FC",
                "Pénalité FC","Total payé FC","Description")
        lrg  = [40, 140, 170, 65, 100, 100, 100, 120, 220]
        self.tv, f = treeview(self, cols, lrg)
        f.grid(row=1, column=0, sticky="nsew", padx=12, pady=4)

        self.v_res = tk.StringVar()
        ttk.Label(self, textvariable=self.v_res,
                  font=("Segoe UI", 10, "bold")).grid(row=2, column=0, pady=6)

    def actualiser(self):
        for it in self.tv.get_children():
            self.tv.delete(it)
        rows = self.db.tous("""
            SELECT r.id, r.date_paiement, m.nom, m.prenom, r.credit_id,
                   r.mont_principal, r.mont_interet, r.mont_penalite,
                   r.montant_total, r.description, r.annule
            FROM remboursement r JOIN membre m ON r.membre_id=m.id
            WHERE m.avec_id=? ORDER BY r.date_paiement DESC LIMIT 600
        """, (self.avec_id,))
        total = 0
        for i, r in enumerate(rows):
            nc  = f"{r['nom']} {r['prenom'] or ''}".strip()
            tag = "rouge" if r["annule"] else ("p" if i%2==0 else "i")
            self.tv.insert("", "end", iid=str(r["id"]), tags=(tag,), values=(
                r["id"], r["date_paiement"], nc, r["credit_id"],
                f"{r['mont_principal']:,.0f}", f"{r['mont_interet']:,.0f}",
                f"{r['mont_penalite']:,.0f}", f"{r['montant_total']:,.0f}",
                r["description"] or ""))
            if not r["annule"]:
                total += r["montant_total"]
        self.v_res.set(f"Total encaissé (remboursements valides) : {total:,.0f} FC")

    def ajouter(self):
        DlgRemboursement(self, self.db, self.auth, self.avec_id, callback=self.actualiser)


class DlgRemboursement(tk.Toplevel):
    def __init__(self, parent, db, auth, avec_id, callback=None):
        super().__init__(parent)
        self.db = db; self.auth = auth; self.avec_id = avec_id; self.cb = callback
        self.title("Enregistrer un remboursement")
        self.resizable(False, False); self.grab_set()
        centrer(self, 520, 500)
        self._cr = None  # crédit sélectionné
        self._ui()

    def _ui(self):
        frm = ttk.Frame(self, padding=20)
        frm.pack(fill="both", expand=True)
        frm.columnconfigure(1, weight=1)
        ttk.Label(frm, text="Remboursement de crédit", style="Sub.TLabel").grid(
            row=0, column=0, columnspan=2, pady=(0, 12))

        # Membres avec crédits actifs
        membres = self.db.tous("""
            SELECT DISTINCT m.id, m.nom, m.prenom FROM membre m
            JOIN credit c ON c.membre_id=m.id
            WHERE m.avec_id=? AND c.statut IN ('actif','en_retard') ORDER BY m.nom
        """, (self.avec_id,))
        self.mmap = {f"{m['nom']} {m['prenom'] or ''}".strip(): m["id"] for m in membres}

        ttk.Label(frm, text="Membre *").grid(row=1, column=0, sticky="e", padx=(0,8), pady=5)
        self.v_m = tk.StringVar()
        cb_m = ttk.Combobox(frm, textvariable=self.v_m, values=list(self.mmap.keys()),
                            state="readonly", width=28)
        cb_m.grid(row=1, column=1, sticky="ew", pady=5)
        cb_m.bind("<<ComboboxSelected>>", self._charger_credits)

        ttk.Label(frm, text="Crédit *").grid(row=2, column=0, sticky="e", padx=(0,8), pady=5)
        self.v_cr = tk.StringVar()
        self.cb_cr = ttk.Combobox(frm, textvariable=self.v_cr, state="readonly", width=28)
        self.cb_cr.grid(row=2, column=1, sticky="ew", pady=5)
        self.cb_cr.bind("<<ComboboxSelected>>", self._afficher_detail)
        self.crmap = {}

        # Détail crédit
        self.v_det = tk.StringVar()
        ttk.Label(frm, textvariable=self.v_det, foreground=C["bleu"],
                  font=("Segoe UI", 9, "italic"), background=C["gris"]).grid(
            row=3, column=0, columnspan=2, pady=2)

        self.v_mt, _  = champ(frm, "Montant payé (FC) *", 4)
        self.v_dt, _  = champ(frm, "Date paiement (AAAA-MM-JJ) *", 5, date.today().isoformat())
        self.v_dc, _  = champ(frm, "Description", 6)

        # Pénalité
        self.v_pen = tk.StringVar()
        ttk.Label(frm, textvariable=self.v_pen, foreground=C["rouge"],
                  font=("Segoe UI", 10, "bold"), background=C["gris"]).grid(
            row=7, column=0, columnspan=2, pady=4)

        bf = ttk.Frame(frm)
        bf.grid(row=8, column=0, columnspan=2, pady=14)
        btn(bf, "Enregistrer", self._sauver, "Vert.TButton").pack(side="left", padx=8)
        btn(bf, "Annuler", self.destroy).pack(side="left", padx=8)

    def _charger_credits(self, ev=None):
        nom = self.v_m.get()
        if nom not in self.mmap:
            return
        mid = self.mmap[nom]
        creds = self.db.tous("""
            SELECT id, principal, montant_interet, montant_total, rembourse,
                   date_octroi, date_echeance, statut
            FROM credit WHERE membre_id=? AND statut IN ('actif','en_retard')
        """, (mid,))
        self.crmap = {}
        for c in creds:
            solde = c["montant_total"] - c["rembourse"]
            lbl = f"Crédit #{c['id']} — Solde: {solde:,.0f} FC — Éch: {c['date_echeance']}"
            self.crmap[lbl] = c
        self.cb_cr["values"] = list(self.crmap.keys())
        if self.crmap:
            first = list(self.crmap.keys())[0]
            self.v_cr.set(first)
            self._afficher_detail()

    def _afficher_detail(self, ev=None):
        lbl = self.v_cr.get()
        if lbl not in self.crmap:
            return
        c = self.crmap[lbl]
        self._cr = c
        solde = c["montant_total"] - c["rembourse"]
        jr    = Finance.jours_retard(c["date_echeance"])
        self.v_det.set(
            f"Total dû: {c['montant_total']:,.0f} | Remboursé: {c['rembourse']:,.0f} | Solde: {solde:,.0f} FC")
        if jr > 0:
            pen = Finance.penalite(solde, TAUX_PENALITE_DEFAUT, jr)
            self.v_pen.set(f"Retard : {jr} jours — Pénalité estimée : {pen:,.0f} FC")
        else:
            self.v_pen.set("")

    def _sauver(self):
        try:
            if not self._cr:
                raise ValueError("Sélectionnez un crédit.")
            c    = self._cr
            mt   = Finance.valider_montant(self.v_mt.get())
            dt   = Finance.valider_date(self.v_dt.get())
            solde = c["montant_total"] - c["rembourse"]

            if mt > solde * 2:
                if not messagebox.askyesno("Attention",
                    f"Le montant payé ({mt:,.0f} FC) dépasse largement le solde ({solde:,.0f} FC).\nContinuer ?",
                    parent=self):
                    return

            jr  = Finance.jours_retard(c["date_echeance"])
            pen = Finance.penalite(solde, TAUX_PENALITE_DEFAUT, jr) if jr > 0 else 0

            # Imputation : pénalité → intérêt → principal
            pen_pay  = min(pen, mt)
            reste    = mt - pen_pay
            ratio_i  = c["montant_interet"] / c["montant_total"] if c["montant_total"] > 0 else 0
            int_pay  = round(reste * ratio_i, 2)
            prin_pay = round(reste - int_pay, 2)

            mid = self.db.valeur("SELECT membre_id FROM credit WHERE id=?", (c["id"],))
            self.db.exec("BEGIN")
            try:
                cur = self.db.exec("""
                    INSERT INTO remboursement
                    (credit_id,membre_id,mont_principal,mont_interet,mont_penalite,
                     montant_total,date_paiement,description,cree_par)
                    VALUES(?,?,?,?,?,?,?,?,?)
                """, (c["id"], mid, prin_pay, int_pay, pen_pay,
                      mt, dt.isoformat(), self.v_dc.get().strip() or None, self.auth.uid))

                nouveau_remb  = c["rembourse"] + mt
                nouveau_remb  = min(nouveau_remb, c["montant_total"])
                nouveau_statut = ("solde" if nouveau_remb >= c["montant_total"] else
                                  "en_retard" if jr > 0 else "actif")
                self.db.exec("UPDATE credit SET rembourse=?,statut=? WHERE id=?",
                             (nouveau_remb, nouveau_statut, c["id"]))
                self.db.commit()
            except Exception:
                self.db.rollback()
                raise
            self.db.audit(self.auth.uid, self.auth.ulogin, "REMBOURSEMENT",
                          "remboursement", cur.lastrowid,
                          {"credit_id": c["id"], "montant": mt})
            messagebox.showinfo("Remboursement enregistré",
                f"Principal  : {prin_pay:,.0f} FC\n"
                f"Intérêt    : {int_pay:,.0f} FC\n"
                f"Pénalité   : {pen_pay:,.0f} FC\n"
                f"Statut crédit : {nouveau_statut.upper()}", parent=self)
            if self.cb: self.cb()
            self.destroy()
        except (ValueError, sqlite3.Error) as e:
            messagebox.showerror("Erreur", str(e), parent=self)


# ════════════════════════════════════════════════════════════════
#  SESSIONS / RÉUNIONS
# ════════════════════════════════════════════════════════════════

class OngletSessions(ttk.Frame):
    def __init__(self, parent, db, auth, avec_id=1):
        super().__init__(parent)
        self.db = db; self.auth = auth; self.avec_id = avec_id
        self.columnconfigure(0, weight=1); self.rowconfigure(1, weight=1)
        self._ui(); self.actualiser()

    def _ui(self):
        bar = ttk.Frame(self)
        bar.grid(row=0, column=0, sticky="ew", padx=12, pady=8)
        ttk.Label(bar, text="Sessions / Réunions AVEC", style="Titre.TLabel").pack(side="left")
        for txt, cmd, st in [
            ("+ Nouvelle session", self.ajouter,   "Vert.TButton"),
            ("Clôturer session",   self.cloturer,  "Rouge.TButton"),
            ("Actualiser",         self.actualiser, "TButton"),
        ]:
            btn(bar, txt, cmd, st).pack(side="right", padx=3)

        cols = ("ID","N° Session","Date réunion","Statut","Notes","Créée par","Créée le")
        lrg  = [40, 80, 120, 80, 300, 100, 140]
        self.tv, f = treeview(self, cols, lrg)
        f.grid(row=1, column=0, sticky="nsew", padx=12, pady=4)

    def actualiser(self):
        for it in self.tv.get_children():
            self.tv.delete(it)
        rows = self.db.tous("""
            SELECT s.id, s.numero, s.date_reunion, s.statut, s.notes,
                   u.nom as agent, s.cree_le
            FROM session s LEFT JOIN utilisateur u ON s.cree_par=u.id
            WHERE s.avec_id=? ORDER BY s.date_reunion DESC
        """, (self.avec_id,))
        for i, r in enumerate(rows):
            tag = "vert" if r["statut"]=="ouverte" else ("p" if i%2==0 else "i")
            self.tv.insert("", "end", iid=str(r["id"]), tags=(tag,), values=(
                r["id"], r["numero"] or "—", r["date_reunion"],
                r["statut"].upper(), r["notes"] or "", r["agent"] or "—", r["cree_le"]))

    def ajouter(self):
        date_r = simpledialog.askstring("Nouvelle session",
            "Date de la réunion (AAAA-MM-JJ) :", parent=self,
            initialvalue=date.today().isoformat())
        if not date_r:
            return
        try:
            dt = Finance.valider_date(date_r)
            notes = simpledialog.askstring("Nouvelle session", "Notes (optionnel) :", parent=self)
            nb = (self.db.valeur("SELECT COUNT(*) FROM session WHERE avec_id=?",
                                 (self.avec_id,)) or 0) + 1
            self.db.exec(
                "INSERT INTO session(avec_id,numero,date_reunion,notes,cree_par)"
                " VALUES(?,?,?,?,?)",
                (self.avec_id, nb, dt.isoformat(), notes or None, self.auth.uid))
            self.db.commit()
            self.db.audit(self.auth.uid, self.auth.ulogin, "CREER_SESSION",
                          "session", details={"date": dt.isoformat()})
            self.actualiser()
        except ValueError as e:
            messagebox.showerror("Erreur", str(e))

    def cloturer(self):
        s = self.tv.focus()
        if not s:
            messagebox.showwarning("Sélection", "Sélectionnez une session."); return
        if not messagebox.askyesno("Confirmer", "Clôturer cette session ?", parent=self):
            return
        self.db.exec("UPDATE session SET statut='fermee' WHERE id=?", (int(s),))
        self.db.commit()
        self.db.audit(self.auth.uid, self.auth.ulogin, "CLOTURER_SESSION", "session", int(s))
        self.actualiser()


# ════════════════════════════════════════════════════════════════
#  RAPPORTS & EXPORTS
# ════════════════════════════════════════════════════════════════

class OngletRapports(ttk.Frame):
    def __init__(self, parent, db, auth, avec_id=1):
        super().__init__(parent)
        self.db = db; self.auth = auth; self.avec_id = avec_id
        self.bkp = Backup()
        self._ui()

    def _ui(self):
        ttk.Label(self, text="Rapports & Exports", style="Titre.TLabel").pack(
            anchor="w", padx=16, pady=(14, 6))

        grille = ttk.Frame(self)
        grille.pack(fill="x", padx=16, pady=6)
        for c in range(3):
            grille.columnconfigure(c, weight=1)

        actions = [
            ("Bilan financier",           self._bilan,        "Bleu.TButton"),
            ("Membres → CSV",             self._exp_membres,  "Bleu.TButton"),
            ("Épargnes → CSV",            self._exp_ep,       "Bleu.TButton"),
            ("Crédits → CSV",             self._exp_cr,       "Bleu.TButton"),
            ("Crédits en retard → CSV",   self._exp_retards,  "Rouge.TButton"),
            ("Journal d'audit → CSV",     self._exp_audit,    "TButton"),
            ("Rapport complet → HTML",    self._rapport_html, "Vert.TButton"),
            ("Sauvegarde base de données",self._sauver,       "Vert.TButton"),
        ]
        for i, (lbl, cmd, st) in enumerate(actions):
            r, c = divmod(i, 3)
            btn(grille, lbl, cmd, st, l=22).grid(row=r, column=c, padx=8, pady=8, sticky="ew")

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=14, pady=8)
        ttk.Label(self, text="Aperçu du bilan :", style="Sub.TLabel").pack(anchor="w", padx=16)
        self.txt = tk.Text(self, height=18, font=("Courier New", 10),
                           bg="#F8F9FA", fg=C["texte"], relief="flat", state="disabled")
        self.txt.pack(fill="both", expand=True, padx=16, pady=6)
        self._bilan()

    # ── Stats ─────────────────────────────────────────────────────
    def _get_stats(self):
        db, aid = self.db, self.avec_id
        Finance.maj_statuts(db)
        membres   = db.valeur("SELECT COUNT(*) FROM membre WHERE statut='actif' AND avec_id=?", (aid,)) or 0
        ep        = db.valeur("SELECT COALESCE(SUM(e.montant),0) FROM epargne e JOIN membre m ON e.membre_id=m.id WHERE m.avec_id=? AND e.annule=0", (aid,)) or 0
        cr_p      = db.valeur("SELECT COALESCE(SUM(principal),0) FROM credit c JOIN membre m ON c.membre_id=m.id WHERE m.avec_id=?", (aid,)) or 0
        cr_i      = db.valeur("SELECT COALESCE(SUM(montant_interet),0) FROM credit c JOIN membre m ON c.membre_id=m.id WHERE m.avec_id=?", (aid,)) or 0
        pf_actif  = db.valeur("SELECT COALESCE(SUM(montant_total-rembourse),0) FROM credit c JOIN membre m ON c.membre_id=m.id WHERE m.avec_id=? AND c.statut IN ('actif','en_retard')", (aid,)) or 0
        rembs     = db.valeur("SELECT COALESCE(SUM(r.montant_total),0) FROM remboursement r JOIN membre m ON r.membre_id=m.id WHERE m.avec_id=? AND r.annule=0", (aid,)) or 0
        retards   = db.valeur("SELECT COUNT(*) FROM credit c JOIN membre m ON c.membre_id=m.id WHERE m.avec_id=? AND c.statut='en_retard'", (aid,)) or 0
        sessions  = db.valeur("SELECT COUNT(*) FROM session WHERE avec_id=?", (aid,)) or 0
        return dict(membres=membres, ep=ep, cr_p=cr_p, cr_i=cr_i,
                    pf_actif=pf_actif, rembs=rembs, retards=retards, sessions=sessions)

    def _bilan(self):
        s = self._get_stats()
        solde = s["ep"] - s["pf_actif"]
        texte = f"""
{"═"*57}
      BILAN FINANCIER — {APP_NOM} v{APP_VERSION}
      Généré le : {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}
{"═"*57}

 MEMBRES
   Membres actifs                   : {s['membres']:>10}

 ÉPARGNES
   Total collecté (FC)              : {s['ep']:>14,.0f}

 CRÉDITS
   Total principal octroyé (FC)     : {s['cr_p']:>14,.0f}
   Total intérêts prévus (FC)       : {s['cr_i']:>14,.0f}
   Portefeuille actif (solde FC)    : {s['pf_actif']:>14,.0f}
   Nombre crédits en retard         : {s['retards']:>10}

 REMBOURSEMENTS
   Total encaissé (FC)              : {s['rembs']:>14,.0f}

 SESSIONS
   Total sessions tenues            : {s['sessions']:>10}

 SOLDE NET ESTIMÉ
   Épargnes — Portefeuille actif FC : {solde:>14,.0f}

{"═"*57}
"""
        self.txt.config(state="normal")
        self.txt.delete("1.0", "end")
        self.txt.insert("end", texte)
        self.txt.config(state="disabled")

    # ── Export CSV ────────────────────────────────────────────────
    def _csv(self, nom, en_tetes, lignes):
        p = filedialog.asksaveasfilename(
            defaultextension=".csv", initialfile=nom,
            filetypes=[("CSV", "*.csv"), ("Tous", "*.*")])
        if not p:
            return
        try:
            with open(p, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(en_tetes)
                w.writerows(lignes)
            self.db.audit(self.auth.uid, self.auth.ulogin, f"EXPORT_CSV",
                          details={"fichier": p, "lignes": len(lignes)})
            messagebox.showinfo("Export réussi", f"Fichier exporté :\n{p}")
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    def _exp_membres(self):
        rows = self.db.tous("""
            SELECT m.id, m.numero, m.nom, m.prenom, m.telephone, m.adresse,
                   m.nb_parts, m.statut, m.date_adhesion,
                   COALESCE(SUM(CASE WHEN e.annule=0 THEN e.montant END),0) as ep
            FROM membre m LEFT JOIN epargne e ON e.membre_id=m.id
            WHERE m.avec_id=? GROUP BY m.id ORDER BY m.nom
        """, (self.avec_id,))
        self._csv("membres.csv",
                  ["ID","N° Membre","Nom","Prénom","Téléphone","Adresse",
                   "Nb Parts","Statut","Adhésion","Épargne FC"],
                  [[r["id"],r["numero"],r["nom"],r["prenom"],r["telephone"],
                    r["adresse"],r["nb_parts"],r["statut"],r["date_adhesion"],
                    r["ep"]] for r in rows])

    def _exp_ep(self):
        rows = self.db.tous("""
            SELECT e.id, e.date_op, m.nom, m.prenom, e.type, e.montant,
                   e.description, e.annule
            FROM epargne e JOIN membre m ON e.membre_id=m.id
            WHERE m.avec_id=? ORDER BY e.date_op DESC
        """, (self.avec_id,))
        self._csv("epargnes.csv",
                  ["ID","Date","Nom","Prénom","Type","Montant FC","Description","Annulé"],
                  [[r["id"],r["date_op"],r["nom"],r["prenom"],r["type"],
                    r["montant"],r["description"],"Oui" if r["annule"] else "Non"]
                   for r in rows])

    def _exp_cr(self):
        rows = self.db.tous("""
            SELECT c.id, c.date_octroi, m.nom, m.prenom, c.principal,
                   c.taux, c.duree_mois, c.montant_interet, c.montant_total,
                   c.rembourse, c.date_echeance, c.statut
            FROM credit c JOIN membre m ON c.membre_id=m.id
            WHERE m.avec_id=? ORDER BY c.date_octroi DESC
        """, (self.avec_id,))
        self._csv("credits.csv",
                  ["ID","Date octroi","Nom","Prénom","Principal FC","Taux","Durée",
                   "Intérêt FC","Total FC","Remboursé FC","Solde FC","Échéance","Statut"],
                  [[r["id"],r["date_octroi"],r["nom"],r["prenom"],r["principal"],
                    f"{r['taux']*100:.1f}%",f"{r['duree_mois']} mois",
                    r["montant_interet"],r["montant_total"],r["rembourse"],
                    r["montant_total"]-r["rembourse"],r["date_echeance"],r["statut"]]
                   for r in rows])

    def _exp_retards(self):
        rows = self.db.tous("""
            SELECT c.id, m.nom, m.prenom, m.telephone, c.montant_total,
                   c.rembourse, c.date_echeance
            FROM credit c JOIN membre m ON c.membre_id=m.id
            WHERE m.avec_id=? AND c.statut='en_retard' ORDER BY c.date_echeance
        """, (self.avec_id,))
        self._csv("credits_en_retard.csv",
                  ["Crédit#","Nom","Prénom","Téléphone","Total FC","Remboursé FC",
                   "Solde FC","Échéance","Jours retard"],
                  [[r["id"],r["nom"],r["prenom"],r["telephone"],r["montant_total"],
                    r["rembourse"],r["montant_total"]-r["rembourse"],
                    r["date_echeance"],Finance.jours_retard(r["date_echeance"])]
                   for r in rows])

    def _exp_audit(self):
        rows = self.db.tous(
            "SELECT ts,login,action,tbl,rid,details FROM audit_log ORDER BY id DESC")
        self._csv("audit.csv",
                  ["Horodatage","Utilisateur","Action","Table","ID","Détails"],
                  [[r["ts"],r["login"],r["action"],r["tbl"],r["rid"],r["details"]]
                   for r in rows])

    def _rapport_html(self):
        s   = self._get_stats()
        solde = s["ep"] - s["pf_actif"]
        membres = self.db.tous("""
            SELECT m.nom, m.prenom, m.telephone, m.statut,
                   COALESCE(SUM(CASE WHEN e.annule=0 THEN e.montant END),0) as ep
            FROM membre m LEFT JOIN epargne e ON e.membre_id=m.id
            WHERE m.avec_id=? GROUP BY m.id ORDER BY m.nom
        """, (self.avec_id,))
        retards = self.db.tous("""
            SELECT m.nom, m.prenom, m.telephone, c.montant_total,
                   c.rembourse, c.date_echeance
            FROM credit c JOIN membre m ON c.membre_id=m.id
            WHERE m.avec_id=? AND c.statut='en_retard' ORDER BY c.date_echeance
        """, (self.avec_id,))

        def tr_m(m):
            nom = html.escape(f"{m['nom']} {m['prenom'] or ''}".strip())
            tel = html.escape(m['telephone'] or '')
            statut = html.escape(m['statut'])
            return (f"<tr><td>{nom}</td>"
                    f"<td>{tel}</td><td>{statut}</td>"
                    f"<td>{m['ep']:,.0f}</td></tr>")
        def tr_r(r):
            solde_cr = r["montant_total"] - r["rembourse"]
            jr = Finance.jours_retard(r["date_echeance"])
            nom = html.escape(f"{r['nom']} {r['prenom'] or ''}".strip())
            tel = html.escape(r['telephone'] or '')
            ech = html.escape(str(r['date_echeance']))
            return (f"<tr class='alerte'><td>{nom}</td>"
                    f"<td>{tel}</td>"
                    f"<td>{solde_cr:,.0f}</td><td>{ech}</td>"
                    f"<td>{jr}j</td></tr>")

        rapport = f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8">
<title>Rapport {APP_NOM}</title>
<style>
  body{{font-family:'Segoe UI',Arial,sans-serif;margin:32px;color:#1C2833;background:#fff}}
  h1{{color:#1A5276;border-bottom:3px solid #D4AC0D;padding-bottom:8px;font-size:1.8em}}
  h2{{color:#1A5276;margin-top:28px;font-size:1.2em}}
  .kpi{{display:flex;flex-wrap:wrap;gap:12px;margin:14px 0}}
  .k{{background:#1A5276;color:#fff;padding:14px 20px;border-radius:6px;min-width:160px;text-align:center}}
  .k .v{{font-size:1.5em;font-weight:700}}
  .k .l{{font-size:.85em;opacity:.85}}
  .alerte{{background:#FADBD8!important}}
  table{{border-collapse:collapse;width:100%;margin:10px 0}}
  th{{background:#1A5276;color:#fff;padding:8px 12px;text-align:left;font-size:.9em}}
  td{{padding:7px 12px;border-bottom:1px solid #D5D8DC;font-size:.9em}}
  tr:nth-child(even){{background:#EAF2FF}}
  @media print{{.noprint{{display:none}}}}
</style></head><body>
<h1>AkibaCore — Rapport Financier</h1>
<p>Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} | Version {APP_VERSION}</p>
<div class="kpi">
  <div class="k"><div class="v">{s['membres']}</div><div class="l">Membres actifs</div></div>
  <div class="k"><div class="v">{s['ep']:,.0f}</div><div class="l">Épargnes FC</div></div>
  <div class="k"><div class="v">{s['pf_actif']:,.0f}</div><div class="l">Portefeuille crédit FC</div></div>
  <div class="k"><div class="v">{s['rembs']:,.0f}</div><div class="l">Remboursements FC</div></div>
  <div class="k" style="background:{'#C0392B' if s['retards']>0 else '#1E8449'}">
    <div class="v">{s['retards']}</div><div class="l">Crédits en retard</div></div>
  <div class="k" style="background:{'#1E8449' if solde>=0 else '#C0392B'}">
    <div class="v">{solde:,.0f}</div><div class="l">Solde net FC</div></div>
</div>
<h2>Liste des membres</h2>
<table><tr><th>Nom complet</th><th>Téléphone</th><th>Statut</th><th>Épargne FC</th></tr>
{''.join(tr_m(m) for m in membres)}</table>
{'<h2>Crédits en retard</h2><table><tr><th>Nom</th><th>Téléphone</th><th>Solde FC</th><th>Échéance</th><th>Retard</th></tr>' + ''.join(tr_r(r) for r in retards) + '</table>' if retards else ''}
</body></html>"""

        p = filedialog.asksaveasfilename(
            defaultextension=".html", initialfile="rapport_akibacore.html",
            filetypes=[("HTML", "*.html"), ("Tous", "*.*")])
        if not p:
            return
        try:
            with open(p, "w", encoding="utf-8") as f:
                f.write(rapport)
            messagebox.showinfo("Rapport créé", f"Rapport HTML sauvegardé :\n{p}")
            self.db.audit(self.auth.uid, self.auth.ulogin, "EXPORT_HTML",
                          details={"fichier": p})
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    def _sauver(self):
        try:
            dest = self.bkp.sauvegarder()
            self.db.audit(self.auth.uid, self.auth.ulogin, "SAUVEGARDE",
                          details={"dest": dest})
            messagebox.showinfo("Sauvegarde réussie",
                f"Base de données sauvegardée :\n{dest}")
        except Exception as e:
            messagebox.showerror("Erreur sauvegarde", str(e))


# ════════════════════════════════════════════════════════════════
#  APPLICATION PRINCIPALE
# ════════════════════════════════════════════════════════════════

class AkibaCore(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NOM)
        self.configure(bg=C["gris"])
        self.withdraw()                      # Masqué jusqu'à la connexion

        # Maximiser selon le système
        try:
            self.state("zoomed")
        except tk.TclError:
            try:
                self.attributes("-zoomed", True)
            except tk.TclError:
                self.geometry("1200x700")

        appliquer_styles(self)
        self.db   = DB()
        self.auth = Auth(self.db)
        self.bkp  = Backup()
        self._backup_after_id = None

        self.protocol("WM_DELETE_WINDOW", self._quitter)
        self._lancer_connexion()

    # ── Flux connexion ────────────────────────────────────────────
    def _lancer_connexion(self):
        dlg = EcranConnexion(self, self.auth, self._post_connexion)
        self.wait_window(dlg)

    def _post_connexion(self):
        self.deiconify()
        self._construire()
        self._auto_backup()

    def _construire(self):
        # Détruire l'interface précédente si re-login
        for w in self.winfo_children():
            w.destroy()

        # ─ Barre supérieure ─
        top = tk.Frame(self, bg=C["bleu"], height=38)
        top.pack(fill="x", side="top")
        top.pack_propagate(False)
        tk.Label(top, text=f"  {APP_NOM}  v{APP_VERSION}",
                 fg=C["blanc"], bg=C["bleu"],
                 font=("Segoe UI", 12, "bold")).pack(side="left", pady=7)
        u = self.auth.user
        tk.Label(top,
                 text=f"{u['nom']}  |  {u['role'].upper()}  |  {date.today().strftime('%d/%m/%Y')}   ",
                 fg="#AED6F1", bg=C["bleu"], font=("Segoe UI", 9)).pack(side="right", pady=10)

        # ─ Notebook ─
        self.avec_id = 1
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=4, pady=4)

        onglets = [
            ("  Tableau de Bord  ", Dashboard),
            ("  Membres  ",         OngletMembres),
            ("  Épargnes  ",        OngletEpargnes),
            ("  Crédits  ",         OngletCredits),
            ("  Remboursements  ",  OngletRemboursements),
            ("  Sessions  ",        OngletSessions),
            ("  Rapports & Export  ",OngletRapports),
        ]
        for nom, Cls in onglets:
            f = Cls(nb, self.db, self.auth, self.avec_id)
            nb.add(f, text=nom)

        # ─ Barre inférieure ─
        bas = tk.Frame(self, bg=C["gris_f"], height=26)
        bas.pack(fill="x", side="bottom")
        bas.pack_propagate(False)
        self.v_statut = tk.StringVar(value="Prêt.")
        tk.Label(bas, textvariable=self.v_statut,
                 bg=C["gris_f"], font=("Segoe UI", 9)).pack(side="left", padx=10, pady=4)
        for lbl, cmd in [("Changer mot de passe", self._changer_mdp),
                          ("Se déconnecter",       self._deconnecter)]:
            tk.Button(bas, text=lbl, command=cmd, relief="flat",
                      bg=C["gris_f"], font=("Segoe UI", 9),
                      cursor="hand2").pack(side="right", padx=10, pady=4)

    def _auto_backup(self):
        try:
            self.bkp.sauvegarder()
        except Exception:
            pass
        self._backup_after_id = self.after(30 * 60 * 1000, self._auto_backup)   # toutes les 30 min

    # ── Actions utilisateur ───────────────────────────────────────
    def _changer_mdp(self):
        dlg = tk.Toplevel(self)
        dlg.title("Changer mon mot de passe")
        dlg.resizable(False, False)
        dlg.grab_set()
        centrer(dlg, 380, 250)
        frm = ttk.Frame(dlg, padding=20)
        frm.pack(fill="both", expand=True)
        frm.columnconfigure(1, weight=1)

        v_a, ea = champ(frm, "Ancien mot de passe", 0, secret=True)
        v_n, en = champ(frm, "Nouveau mot de passe", 1, secret=True)
        v_c, ec = champ(frm, "Confirmer nouveau",   2, secret=True)

        def _ok():
            if v_n.get() != v_c.get():
                messagebox.showerror("Erreur", "Les mots de passe ne correspondent pas.", parent=dlg)
                return
            if len(v_n.get()) < 4:
                messagebox.showerror("Erreur", "Minimum 4 caractères.", parent=dlg)
                return
            try:
                self.auth.changer_mdp(self.auth.ulogin, v_a.get(), v_n.get())
                messagebox.showinfo("Succès", "Mot de passe modifié.", parent=dlg)
                dlg.destroy()
            except ValueError as e:
                messagebox.showerror("Erreur", str(e), parent=dlg)

        bf = ttk.Frame(frm)
        bf.grid(row=3, column=0, columnspan=2, pady=14)
        btn(bf, "Changer",  _ok,         "Vert.TButton").pack(side="left", padx=8)
        btn(bf, "Annuler", dlg.destroy).pack(side="left", padx=8)

    def _deconnecter(self):
        if messagebox.askyesno("Déconnexion", "Se déconnecter de AkibaCore ?"):
            if self._backup_after_id is not None:
                self.after_cancel(self._backup_after_id)
                self._backup_after_id = None
            self.db.audit(self.auth.uid, self.auth.ulogin, "DÉCONNEXION")
            self.auth.user = None
            for w in self.winfo_children():
                w.destroy()
            self.withdraw()
            self._lancer_connexion()

    def _quitter(self):
        if self._backup_after_id is not None:
            self.after_cancel(self._backup_after_id)
            self._backup_after_id = None
        try:
            self.bkp.sauvegarder()
        except Exception:
            pass
        self.destroy()


# ════════════════════════════════════════════════════════════════
#  POINT D'ENTRÉE
# ════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = AkibaCore()
    app.mainloop()
