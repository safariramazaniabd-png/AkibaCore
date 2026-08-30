#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AkibaCore — Système de Gestion AVEC (Version Production)
=========================================================
Conçu pour les Associations Villageoises d'Épargne et de Crédit
Fonctionne 100 % hors ligne | SQLite | Tkinter

Auteur  : AkibaCore Team
Version : 2.2.0
"""

import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import tkinter.font as tkFont
import hashlib
import secrets
import os
import sys
import shutil
import subprocess
import tempfile
import re
import zipfile
import csv
import json
import html
import math
from datetime import datetime, date
from pathlib import Path


# ════════════════════════════════════════════════════════════════
#  CONFIGURATION GLOBALE
# ════════════════════════════════════════════════════════════════

def _repertoire_application() -> Path:
    """Dossier de l'application (exe PyInstaller ou script), jamais le CWD.

    Garantit que la base et les sauvegardes sont toujours créées à côté
    du programme, quel que soit le répertoire de lancement de l'utilisateur.
    """
    if getattr(sys, "frozen", False):            # Exécutable PyInstaller
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _est_ecrivable(rep: Path) -> bool:
    """Vérifie si un dossier est réellement accessible en écriture."""
    try:
        rep.mkdir(parents=True, exist_ok=True)
        essai = rep / ".akiba_probe"
        with open(essai, "w", encoding="utf-8") as f:
            f.write("ok")
        essai.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def _repertoire_donnees() -> Path:
    """Dossier des données utilisateur (base + sauvegardes + documents).

    Priorité à côté du programme (portable) si ce dossier est accessible
    en écriture. Sinon — par exemple après une installation dans
    "C:\\Program Files\\AkibaCore" que Windows protège en écriture — on
    bascule vers un dossier personnel de l'utilisateur, lisible en écriture,
    afin de ne jamais échouer à l'enregistrement des données.
    """
    app = _repertoire_application()
    if _est_ecrivable(app):
        return app
    # Dossier personnel portable selon l'OS.
    for cle in ("LOCALAPPDATA", "APPDATA"):
        b = os.environ.get(cle)
        if b:
            try:
                return Path(b) / "AkibaCore"
            except Exception:
                pass
    return Path.home() / "Documents" / "AkibaCore"


APP_NOM      = "AkibaCore"
APP_VERSION = "2.2.0"
REPERTOIRE_APP = _repertoire_application()
REPERTOIRE_DONNEES = _repertoire_donnees()
DB_CHEMIN    = str(REPERTOIRE_DONNEES / "akibacore.db")
BACKUP_DIR   = REPERTOIRE_DONNEES / "sauvegardes"
BACKUP_MAX   = 15
MDP_DEFAUT   = "admin123"                        # Mot de passe initial admin

DOCUMENTS_DIR = REPERTOIRE_DONNEES / "documents"
DOC_IN  = DOCUMENTS_DIR / "modeles"
DOC_REC = DOCUMENTS_DIR / "recus"
DOC_RAP = DOCUMENTS_DIR / "rapports"
DOC_ARC = DOCUMENTS_DIR / "archives"
DOC_GEN = DOCUMENTS_DIR / "generes"

TAUX_INTERET_DEFAUT  = 0.10   # 10 % annuel
TAUX_PENALITE_DEFAUT = 0.02   # 2 % / mois de retard
MONTANT_PART_DEFAUT  = 5_000  # CDF

# ── Devises ──────────────────────────────────────────────────────
# AkibaCore supporte plusieurs devises jamais mélangées dans un calcul
# sans taux de change. Les soldes sont toujours affichés avec leur devise.
DEVISES            = ("CDF", "USD")                 # ordre d'affichage
DEVISE_DEFAUT      = DEVISES[0]                     # CDF — Franc congolais
DEVISES_AUTORISEES_DEFAUT = (DEVISE_DEFAUT,)        # une seule par défaut
TYPES_CREDIT       = ("ordinaire", "urgence", "investissement", "autre")
TYPES_CREDIT_DEFAUT = ("ordinaire", "urgence", "investissement")
TYPES_COMPTE       = ("epargne", "courant", "bloque", "credit")
STATUTS_COMPTE     = ("actif", "bloque", "suspendu")

C = {                          # Palette de couleurs etendue
    # Primary
    "bleu":       "#1A5276",
    "bleu_f":     "#154360",
    "bleu_clair": "#2980B9",
    "bleu_pale":  "#D6EAF8",
    # Accent
    "vert":       "#1E8449",
    "vert_c":     "#2ECC71",
    "or":         "#D4AC0D",
    "or_clair":   "#F9E79F",
    "rouge":      "#C0392B",
    "rouge_clair":"#E74C3C",
    "violet":     "#6C3483",
    # Neutre
    "gris":       "#F4F6F7",
    "gris_f":     "#D5D8DC",
    "gris_fonce": "#566573",
    "texte":      "#1C2833",
    "texte_mute": "#5D6D7E",
    "blanc":      "#FFFFFF",
    # Sidebar
    "sidebar_bg": "#1B2631",
    "sidebar_hl": "#2C3E50",
    "sidebar_tx": "#AEB6BF",
    "sidebar_act":"#2980B9",
    # Cards
    "ligne_p":    "#EAF2FF",
    "ligne_i":    "#FFFFFF",
}


FONT = None  # Resolu plus tard quand Tk est disponible

# Rate limiting pour la connexion
_TENTATIVES_CONNEXION = {}  # {login: (nb_tentatives, timestamp_premiere)}
_LOCKOUT_SECONDS = 30
_MAX_TENTATIVES = 5

# ── Permissions granulaires ──────────────────────────────────────
# Catalogue des permissions disponibles (code, libelle, groupe).
# L'admin possède TOUTES les permissions quelle que soit cette liste.
PERMISSIONS = [
    ("members.view",      "Consulter les membres",               "Membres"),
    ("members.create",    "Ajouter un membre",                   "Membres"),
    ("members.edit",      "Modifier un membre",                  "Membres"),

    ("savings.view",      "Consulter les épargnes",              "Épargnes"),
    ("savings.create",    "Enregistrer une épargne",             "Épargnes"),
    ("savings.cancel",    "Annuler une épargne",                 "Épargnes"),

    ("loans.view",        "Consulter les crédits",               "Crédits"),
    ("loans.create",      "Octroyer un crédit",                  "Crédits"),
    ("loans.edit",        "Modifier un crédit",                  "Crédits"),
    ("loans.cancel",      "Annuler un crédit",                   "Crédits"),

    ("repayments.view",   "Consulter les remboursements",        "Remboursements"),
    ("repayments.create", "Enregistrer un remboursement",        "Remboursements"),
    ("repayments.cancel", "Annuler un remboursement",            "Remboursements"),

    ("sessions.view",     "Consulter les sessions",              "Sessions"),
    ("sessions.create",   "Créer une session",                   "Sessions"),
    ("sessions.close",    "Clôturer une session",                "Sessions"),

    ("reports.view",      "Consulter les rapports",              "Rapports"),
    ("reports.generate",  "Générer les rapports",                "Rapports"),
    ("reports.export",    "Exporter (CSV / HTML)",               "Rapports"),

    ("receipts.view",     "Consulter les reçus",                 "Reçus"),
    ("receipts.print",    "Imprimer un reçu",                    "Reçus"),
    ("receipts.reprint",  "Réimprimer un ancien reçu",           "Reçus"),

    ("documents.view",    "Consulter les documents",             "Documents"),
    ("documents.add_template",    "Ajouter un modèle",           "Documents"),
    ("documents.edit_template",   "Modifier un modèle",          "Documents"),
    ("documents.delete_template", "Supprimer un modèle",         "Documents"),
    ("documents.generate", "Générer un document",                "Documents"),
    ("documents.print",    "Imprimer un document",               "Documents"),
    ("documents.export",   "Exporter un document (PDF)",         "Documents"),

    ("users.view",        "Consulter les utilisateurs",          "Utilisateurs"),
    ("users.create",      "Créer un utilisateur",                "Utilisateurs"),
    ("users.edit",        "Modifier un utilisateur",             "Utilisateurs"),
    ("users.disable",     "Désactiver / réactiver",              "Utilisateurs"),
    ("users.permissions", "Gérer les permissions",               "Utilisateurs"),

    ("backup.create",     "Créer une sauvegarde",                "Sauvegardes"),
    ("backup.restore",    "Restaurer une sauvegarde",            "Sauvegardes"),

    ("accounts.view",     "Consulter les comptes",               "Comptes"),
    ("accounts.block",    "Bloquer / débloquer / suspendre",     "Comptes"),

    ("audit.view",        "Consulter le journal d'activité",     "Audit"),
    ("settings.view",     "Consulter les paramètres",            "Paramètres"),
    ("settings.edit",     "Modifier les paramètres",             "Paramètres"),
    ("settings.financial.edit", "Modifier les paramètres financiers", "Paramètres"),
]

# Rôles prédéfinis (compatibles avec les anciens 'admin/agent/lecteur').
# Un rôle = un ensemble de permissions ; l'admin peut en créer d'autres.
ROLES_DEFAUTS = {
    "admin":   ("Administrateur", "Tous les droits", [p[0] for p in PERMISSIONS]),
    "agent":   ("Agent de terrain", "Opérations courantes sans administration",
                ["members.view", "members.create", "members.edit",
                 "savings.view", "savings.create", "savings.cancel",
                 "loans.view", "loans.create", "loans.edit", "loans.cancel",
                 "repayments.view", "repayments.create", "repayments.cancel",
                 "sessions.view", "sessions.create", "sessions.close",
                 "reports.view", "reports.generate", "reports.export",
                 "receipts.view", "receipts.print", "receipts.reprint",
                 "documents.view", "documents.generate", "documents.print",
                 "documents.export",
                 "backup.create", "accounts.view", "audit.view", "settings.view"]),
    "lecteur": ("Lecteur", "Consultation seule",
                ["members.view", "savings.view", "loans.view", "repayments.view",
                 "sessions.view", "reports.view", "receipts.view",
                 "documents.view", "audit.view"]),
    "caissier": ("Caissier", "Épargne, remboursements et reçus",
                 ["members.view", "savings.view", "savings.create",
                  "loans.view", "repayments.view", "repayments.create",
                  "sessions.view", "reports.view", "receipts.view",
                  "receipts.print", "documents.view", "documents.generate"]),
    "gestionnaire_credit": ("Gestionnaire des crédits", "Crédits et remboursements",
                 ["members.view", "savings.view", "loans.view", "loans.create",
                  "repayments.view", "repayments.create", "repayments.cancel",
                  "sessions.view", "sessions.create",
                  "reports.view", "receipts.view", "documents.view"]),
    "secretaire": ("Secrétaire", "Membres, sessions, documents",
                 ["members.view", "members.create", "members.edit",
                  "sessions.view", "sessions.create", "sessions.close",
                  "reports.view", "reports.generate",
                  "documents.view", "documents.add_template",
                  "documents.edit_template", "documents.generate",
                  "documents.print", "documents.export", "receipts.view"]),
    "auditeur":  ("Auditeur", "Lecture et rapports",
                 ["members.view", "savings.view", "loans.view", "repayments.view",
                  "sessions.view", "reports.view", "reports.generate",
                  "reports.export", "audit.view", "receipts.view",
                  "accounts.view", "documents.view"]),
}

FORMATS_MODELES = {"docx", "odt", "html", "htm", "txt"}

def _resoudre_font(root=None):
    """Choisir la meilleure police disponible selon la plateforme (appele apres Tk init)."""
    global FONT
    if FONT is not None:
        return FONT
    try:
        available = set(tkFont.families())
        for name in ("Segoe UI", "Noto Sans", "DejaVu Sans", "Liberation Sans", "Arial"):
            if name in available:
                FONT = name
                return FONT
    except Exception:
        pass
    FONT = "TkDefaultFont"
    return FONT


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
            type_compte   TEXT DEFAULT 'epargne'
                          CHECK(type_compte IN ('epargne','courant','bloque','credit')),
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

        CREATE TABLE IF NOT EXISTS permission (
            code    TEXT PRIMARY KEY,
            libelle TEXT NOT NULL,
            groupe  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS role (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nom         TEXT UNIQUE NOT NULL,
            description TEXT,
            systeme     INTEGER DEFAULT 0,
            cree_le     TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS role_permission (
            role_id INTEGER NOT NULL REFERENCES role(id) ON DELETE CASCADE,
            code    TEXT    NOT NULL REFERENCES permission(code) ON DELETE CASCADE,
            PRIMARY KEY(role_id, code)
        );

        CREATE TABLE IF NOT EXISTS user_permission (
            utilisateur_id INTEGER NOT NULL REFERENCES utilisateur(id) ON DELETE CASCADE,
            code           TEXT    NOT NULL REFERENCES permission(code) ON DELETE CASCADE,
            PRIMARY KEY(utilisateur_id, code)
        );

        CREATE TABLE IF NOT EXISTS receipt (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            recu_no      TEXT UNIQUE NOT NULL,
            type         TEXT NOT NULL,
            operation    TEXT NOT NULL,
            operation_id INTEGER,
            membre_id    INTEGER,
            avec_id      INTEGER DEFAULT 1,
            montant      REAL,
            details      TEXT,
            cree_par     INTEGER,
            cree_le      TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY(membre_id) REFERENCES membre(id),
            FOREIGN KEY(cree_par)  REFERENCES utilisateur(id)
        );

        CREATE TABLE IF NOT EXISTS document_template (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            avec_id     INTEGER NOT NULL DEFAULT 1,
            nom         TEXT NOT NULL,
            type        TEXT NOT NULL,
            format      TEXT NOT NULL,
            fichier     TEXT,
            contenu     TEXT,
            par_defaut  INTEGER DEFAULT 0,
            cree_par    INTEGER,
            cree_le     TEXT DEFAULT (datetime('now','localtime')),
            modifie_le  TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY(avec_id) REFERENCES avec(id)
        );

        CREATE TABLE IF NOT EXISTS document_genere (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            avec_id      INTEGER NOT NULL DEFAULT 1,
            template_id  INTEGER,
            type         TEXT,
            nom_fichier  TEXT,
            variables    TEXT,
            cree_par     INTEGER,
            cree_le      TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY(template_id) REFERENCES document_template(id)
        );

        CREATE TABLE IF NOT EXISTS compteur (
            nom    TEXT PRIMARY KEY,
            valeur INTEGER NOT NULL DEFAULT 0
        );
        """)
        c.commit()
        # Index pour performance
        for idx_sql in [
            "CREATE INDEX IF NOT EXISTS idx_epargne_membre ON epargne(membre_id)",
            "CREATE INDEX IF NOT EXISTS idx_epargne_session ON epargne(session_id)",
            "CREATE INDEX IF NOT EXISTS idx_credit_membre ON credit(membre_id)",
            "CREATE INDEX IF NOT EXISTS idx_credit_statut ON credit(statut)",
            "CREATE INDEX IF NOT EXISTS idx_credit_echeance ON credit(date_echeance)",
            "CREATE INDEX IF NOT EXISTS idx_remboursement_credit ON remboursement(credit_id)",
            "CREATE INDEX IF NOT EXISTS idx_remboursement_membre ON remboursement(membre_id)",
            "CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_log(ts)",
            "CREATE INDEX IF NOT EXISTS idx_receipt_membre ON receipt(membre_id)",
            "CREATE INDEX IF NOT EXISTS idx_receipt_avec ON receipt(avec_id)",
            "CREATE INDEX IF NOT EXISTS idx_doc_avec ON document_template(avec_id)",
            "CREATE INDEX IF NOT EXISTS idx_doc_gen_avec ON document_genere(avec_id)",
        ]:
            c.execute(idx_sql)
        c.commit()
        self._migrer()
        self._seeds()
        self._seeds_permissions()

    def _seeds(self):
        """Données initiales (admin + AVEC par défaut)."""
        # L'AVEC est initialisée AVANT l'administrateur : utilisateur.avec_id
        # est une clé étrangère NOT NULL DEFAULT 1 → la ligne avec(id=1) doit
        # déjà exister au moment de l'insertion.
        if not self.valeur("SELECT COUNT(*) FROM avec"):
            self.exec(
                "INSERT INTO avec(nom,description) VALUES(?,?)",
                ("AVEC Bukavu", "Association Villageoise d'Épargne et de Crédit"),
            )
        if not self.valeur("SELECT COUNT(*) FROM utilisateur"):
            sel = secrets.token_hex(16)
            ph  = hashlib.pbkdf2_hmac('sha256', f"admin123{sel}".encode(), sel.encode(), 100000).hex()
            self.exec(
                "INSERT INTO utilisateur(nom,login,pwd_hash,sel,role)"
                " VALUES(?,?,?,?,?)",
                ("Administrateur", "admin", ph, sel, "admin"),
            )
        self.commit()

    def _migrer(self):
        """Migrations SQLite propres, pilotees par PRAGMA user_version.

        La version 0 (base v2.0.0) migre vers la version 1 :
          - utilisateur : nouveau champ 'derniere_connexion' + 'avec_id',
            suppression du CHECK limitant les rôles (roles personnalisés) ;
          - avec : infos complementaires (adresse, telephone, email,
            devise, logo, impression_auto) ;
          - nouvelles tables creees par le schema de base.
        La version 1 migre vers la version 2 (multi-devises + comptes) :
          - epargne/credit/remboursement/receipt : colonne 'devise' (CDF par défaut) ;
          - credit : 'type_credit' (ordinaire/urgence/investissement/autre)
            et 'taux_penalite' (taux figé au moment de l'octroi) ;
          - avec : taux par type de crédit, devises autorisées, types actifs ;
          - remplacement de la devise historique 'FC' par 'CDF' ;
          - nouvelles tables comptes (compte, compte_evenement, compte_mouvement).
        Aucune donnee existante n'est perdue ; les cles etrangeres restent
        verifiees a la fin (PRAGMA foreign_key_check).
        """
        version = self.valeur("PRAGMA user_version") or 0
        # ── v0 → v1 ────────────────────────────────────────────────
        if version < 1:
            c = self.conn
            c.execute("PRAGMA foreign_keys=OFF")
            try:
                c.execute("BEGIN")
                # Reconstruit utilisation (sans CHECK restrictif, + colonnes)
                c.execute("""
                    CREATE TABLE utilisateur_new (
                        id            INTEGER PRIMARY KEY AUTOINCREMENT,
                        nom           TEXT NOT NULL,
                        login         TEXT UNIQUE NOT NULL,
                        pwd_hash      TEXT NOT NULL,
                        sel           TEXT NOT NULL,
                        role          TEXT NOT NULL DEFAULT 'agent',
                        actif         INTEGER DEFAULT 1,
                        avec_id       INTEGER NOT NULL DEFAULT 1,
                        derniere_connexion TEXT,
                        cree_le       TEXT DEFAULT (datetime('now','localtime')),
                        FOREIGN KEY(avec_id) REFERENCES avec(id)
                    )
                """)
                c.execute("""
                    INSERT INTO utilisateur_new(id,nom,login,pwd_hash,sel,role,actif,cree_le)
                    SELECT id,nom,login,pwd_hash,sel,role,actif,cree_le FROM utilisateur
                """)
                c.execute("DROP TABLE utilisateur")
                c.execute("ALTER TABLE utilisateur_new RENAME TO utilisateur")
                # Colonnes complementaires sur 'avec' (si absentes)
                colonnes = {r[1] for r in c.execute("PRAGMA table_info(avec)")}
                for col, decl in [
                    ("adresse", "TEXT"),
                    ("telephone", "TEXT"),
                    ("email", "TEXT"),
                    ("devise", "TEXT DEFAULT 'CDF'"),
                    ("logo", "TEXT"),
                    ("impression_auto", "INTEGER DEFAULT 0"),
                ]:
                    if col not in colonnes:
                        c.execute(f"ALTER TABLE avec ADD COLUMN {col} {decl}")
                c.execute("PRAGMA user_version = 1")
                c.commit()
                # Verification d'integrite des cles etrangeres
                anomalies = c.execute("PRAGMA foreign_key_check").fetchall()
                if anomalies:
                    c.rollback()
            except Exception:
                c.rollback()
                raise
            finally:
                c.execute("PRAGMA foreign_keys=ON")

        # ── v1 → v2 : multi-devises + comptes ─────────────────────
        if version < 2:
            c = self.conn
            c.execute("PRAGMA foreign_keys=OFF")
            try:
                c.execute("BEGIN")
                # Colonnes de devise sur les opérations (CDF par défaut :
                # les lignes existantes étaient toutes libellées en FC).
                for tbl, col, decl in [
                    ("epargne",      "devise",       "TEXT NOT NULL DEFAULT 'CDF'"),
                    ("credit",       "devise",       "TEXT NOT NULL DEFAULT 'CDF'"),
                    ("credit",       "type_credit",  "TEXT NOT NULL DEFAULT 'ordinaire'"),
                    ("credit",       "taux_penalite","REAL NOT NULL DEFAULT 0.02"),
                    ("remboursement","devise",       "TEXT NOT NULL DEFAULT 'CDF'"),
                    ("receipt",      "devise",       "TEXT NOT NULL DEFAULT 'CDF'"),
                ]:
                    exist = {r[1] for r in c.execute(f"PRAGMA table_info({tbl})")}
                    if col not in exist:
                        c.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} {decl}")
                # Paramètres financiers AVEC (multi-devises, taux par type)
                colonnes_avec = {r[1] for r in c.execute("PRAGMA table_info(avec)")}
                for col, decl in [
                    ("taux_interet_urgence", "REAL DEFAULT 0.15"),
                    ("taux_interet_investissement", "REAL DEFAULT 0.10"),
                    ("devises_autorisees",
                     "TEXT NOT NULL DEFAULT '[\"CDF\"]'"),
                    ("types_credit",
                     "TEXT NOT NULL DEFAULT '[\"ordinaire\",\"urgence\",\"investissement\"]'"),
                ]:
                    if col not in colonnes_avec:
                        c.execute(f"ALTER TABLE avec ADD COLUMN {col} {decl}")
                # La devise historique 'FC' vaut désormais 'CDF' (même monnaie).
                c.execute("UPDATE avec SET devise='CDF' WHERE devise IN ('FC','')")
                # Figer la pénalité existante sur les crédits antérieurs
                # à la v2 (aucun snapshot stocké) : on hérite du taux AVEC.
                c.execute(
                    "UPDATE credit SET taux_penalite = COALESCE("
                    " (SELECT a.taux_penalite FROM avec a ORDER BY a.id LIMIT 1),"
                    " 0.02)")
                # Comptes membres (épargne / courant / bloqué / crédit)
                c.execute("""
                    CREATE TABLE IF NOT EXISTS compte (
                        id           INTEGER PRIMARY KEY AUTOINCREMENT,
                        membre_id    INTEGER NOT NULL,
                        type_compte  TEXT NOT NULL
                                     CHECK(type_compte IN ('epargne','courant','bloque','credit')),
                        devise       TEXT NOT NULL DEFAULT 'CDF',
                        statut       TEXT NOT NULL DEFAULT 'actif'
                                     CHECK(statut IN ('actif','bloque','suspendu')),
                        description  TEXT,
                        cree_par     INTEGER,
                        cree_le      TEXT DEFAULT (datetime('now','localtime')),
                        FOREIGN KEY(membre_id) REFERENCES membre(id),
                        FOREIGN KEY(cree_par)  REFERENCES utilisateur(id),
                        UNIQUE(membre_id, type_compte, devise)
                    )
                """)
                c.execute("""
                    CREATE TABLE IF NOT EXISTS compte_evenement (
                        id            INTEGER PRIMARY KEY AUTOINCREMENT,
                        compte_id     INTEGER NOT NULL,
                        type_evenement TEXT NOT NULL
                                       CHECK(type_evenement IN
                                         ('CREATION','BLOCAGE','DEBLOCAGE',
                                          'SUSPENSION','REACTIVATION')),
                        note          TEXT,
                        cree_par      INTEGER,
                        cree_le       TEXT DEFAULT (datetime('now','localtime')),
                        FOREIGN KEY(compte_id) REFERENCES compte(id) ON DELETE CASCADE,
                        FOREIGN KEY(cree_par)  REFERENCES utilisateur(id)
                    )
                """)
                c.execute("""
                    CREATE TABLE IF NOT EXISTS compte_mouvement (
                        id            INTEGER PRIMARY KEY AUTOINCREMENT,
                        compte_id     INTEGER NOT NULL,
                        type_mouvement TEXT NOT NULL
                                       CHECK(type_mouvement IN
                                         ('depot','retrait','ajustement')),
                        montant       REAL NOT NULL CHECK(montant <> 0),
                        note          TEXT,
                        cree_par      INTEGER,
                        cree_le       TEXT DEFAULT (datetime('now','localtime')),
                        FOREIGN KEY(compte_id) REFERENCES compte(id) ON DELETE CASCADE,
                        FOREIGN KEY(cree_par)  REFERENCES utilisateur(id)
                    )
                """)
                for idx_sql in [
                    "CREATE INDEX IF NOT EXISTS idx_compte_membre ON compte(membre_id)",
                    "CREATE INDEX IF NOT EXISTS idx_cm_compte ON compte_mouvement(compte_id)",
                    "CREATE INDEX IF NOT EXISTS idx_ce_compte ON compte_evenement(compte_id)",
                    "CREATE INDEX IF NOT EXISTS idx_epargne_devise ON epargne(devise)",
                    "CREATE INDEX IF NOT EXISTS idx_credit_devise ON credit(devise)",
                ]:
                    c.execute(idx_sql)
                c.execute("PRAGMA user_version = 2")
                c.commit()
                anomalies = c.execute("PRAGMA foreign_key_check").fetchall()
                if anomalies:
                    c.rollback()
            except Exception:
                c.rollback()
                raise
            finally:
                c.execute("PRAGMA foreign_keys=ON")

        # ── v2 → v3 : type de compte informatif sur le membre ──────
        if version < 3:
            c = self.conn
            c.execute("PRAGMA foreign_keys=OFF")
            try:
                c.execute("BEGIN")
                cols = [r["name"] for r in c.execute("PRAGMA table_info(membre)").fetchall()]
                if "type_compte" not in cols:
                    c.execute("""
                        ALTER TABLE membre ADD COLUMN type_compte TEXT DEFAULT 'epargne'
                    """)
                c.execute("PRAGMA user_version = 3")
                c.commit()
                anomalies = c.execute("PRAGMA foreign_key_check").fetchall()
                if anomalies:
                    c.rollback()
            except Exception:
                c.rollback()
                raise
            finally:
                c.execute("PRAGMA foreign_keys=ON")

    def _seeds_permissions(self):
        """Catalogue des permissions + rôles prédéfinis (idempotent).

        Réinsérable à volonté : INSERT OR IGNORE pour ne jamais écraser une
        permission ou un droit existant, tout en ajoutant les nouveaux codes
        sur les bases déjà en production (ex. settings.financial.edit).
        """
        for code, lib, grp in PERMISSIONS:
            self.exec("INSERT OR IGNORE INTO permission(code,libelle,groupe) VALUES(?,?,?)",
                      (code, lib, grp))
        for nom, (desc, _syst, codes) in ROLES_DEFAUTS.items():
            role = self.un("SELECT id FROM role WHERE nom=?", (nom,))
            if not role:
                self.exec("INSERT INTO role(nom,description,systeme) VALUES(?,?,?)",
                          (nom, desc, 1))
                self.commit()
                role = self.un("SELECT id FROM role WHERE nom=?", (nom,))
            for code in codes:
                if code in _CODES_PERMISSIONS:
                    self.exec("INSERT OR IGNORE INTO role_permission(role_id,code) VALUES(?,?)",
                              (role["id"], code))
        self.commit()


_CODES_PERMISSIONS = {p[0] for p in PERMISSIONS}


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
    def solde_epargne(db, membre_id, devise=None):
        """Épargne valide (non annulée) d'un membre, toutes devises ou une seule."""
        if devise:
            return db.valeur(
                "SELECT COALESCE(SUM(montant),0) FROM epargne"
                " WHERE membre_id=? AND annule=0 AND devise=?",
                (membre_id, devise)) or 0
        return db.valeur(
            "SELECT COALESCE(SUM(montant),0) FROM epargne"
            " WHERE membre_id=? AND annule=0",
            (membre_id,)) or 0

    @staticmethod
    def solde_compte(db, membre_id, type_compte, devise):
        """Solde d'un compte membre (épargne/courant/bloqué/crédit) par devise.

        Les soldes des comptes épargne et crédit sont dérivés des tables
        métier (jamais mélangés entre devises) ; les comptes courant et
        bloqué s'appuient sur la table compte_mouvement.
        """
        if type_compte == "epargne":
            return Finance.solde_epargne(db, membre_id, devise)
        if type_compte == "credit":
            return round(db.valeur(
                "SELECT COALESCE(SUM(montant_total - rembourse),0) FROM credit"
                " WHERE membre_id=? AND devise=? AND statut IN ('actif','en_retard')",
                (membre_id, devise)) or 0, 2)
        return round(db.valeur("""
            SELECT COALESCE(SUM(cm.montant),0) FROM compte_mouvement cm
            JOIN compte c ON cm.compte_id = c.id
            WHERE c.membre_id=? AND c.type_compte=? AND c.devise=?
        """, (membre_id, type_compte, devise)) or 0, 2)

    @staticmethod
    def avoir_compte(db, uid, membre_id, type_compte, devise):
        """Garantit l'existence du compte membre (type + devise) et son
        évènement de création. Employé à chaque opération financière pour
        que tous les comptes apparaissent dans l'écran Comptes."""
        devise = (devise or DEVISE_DEFAUT).upper()
        if devise not in DEVISES:
            devise = DEVISE_DEFAUT
        db.exec("""
            INSERT OR IGNORE INTO compte(membre_id,type_compte,devise,statut,description,cree_par)
            VALUES(?,?,?,?,?,?)
        """, (membre_id, type_compte, devise, "actif",
              "Créé automatiquement lors d'une opération", uid))
        db.commit()
        compte = db.un(
            "SELECT * FROM compte WHERE membre_id=? AND type_compte=? AND devise=?",
            (membre_id, type_compte, devise))
        if compte and not db.valeur(
                "SELECT 1 FROM compte_evenement WHERE compte_id=? AND type_evenement='CREATION'",
                (compte["id"],)):
            db.exec("INSERT INTO compte_evenement(compte_id,type_evenement,note,cree_par)"
                    " VALUES(?,'CREATION',?,?)",
                    (compte["id"], "Compte créé", uid))
            db.commit()
        return compte

    @staticmethod
    def compte_bloque(db, membre_id, type_compte, devise):
        """True si le compte membre (type+devise) est bloqué ou suspendu."""
        return bool(db.valeur(
            "SELECT 1 FROM compte WHERE membre_id=? AND type_compte=? AND devise=?"
            " AND statut IN ('bloque','suspendu')",
            (membre_id, type_compte, devise.upper() if isinstance(devise, str) else devise)))

    @staticmethod
    def impliquer_compte(db, uid, membre_id, type_compte, devise,
                         type_mouvement, montant, note=None):
        """Assure le compte puis enregistre un mouvement (depot/retrait/ajustement).

        Retourne le compte ciblé. L'appelant gère la transaction métier ;
        ce helper ne commit PAS d'opération métier, seulement la création
        de compte + son événement de création quand nécessaire."""
        comp = Finance.avoir_compte(db, uid, membre_id, type_compte, devise)
        if type_mouvement in ("depot", "retrait", "ajustement"):
            db.exec("""
                INSERT INTO compte_mouvement(compte_id,type_mouvement,montant,note,cree_par)
                VALUES(?,?,?,?,?)
            """, (comp["id"], type_mouvement,
                  abs(montant) if type_mouvement == "depot" else -abs(montant),
                  note, uid))
            db.commit()
        return comp

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
        self._perms = frozenset() # permissions effectives (rôle + individuelles)

    def connecter(self, login, mdp):
        u = self.db.un("SELECT * FROM utilisateur WHERE login=? AND actif=1", (login,))
        if not u:
            return False
        if hashlib.pbkdf2_hmac('sha256', f"{mdp}{u['sel']}".encode(), u['sel'].encode(), 100000).hex() == u["pwd_hash"]:
            self.user = u
            self._charger_permissions()
            try:
                self.db.exec("UPDATE utilisateur SET derniere_connexion=datetime('now','localtime') WHERE id=?", (u["id"],))
                self.db.commit()
            except sqlite3.Error:
                pass
            self.db.audit(u["id"], login, "CONNEXION")
            return True
        return False

    def _charger_permissions(self):
        """Permissions effectives = rôle (admin ⇒ toutes) + permissions individuelles."""
        if not self.user:
            self._perms = frozenset()
            return
        self.user = self.db.un("SELECT * FROM utilisateur WHERE id=?", (self.user["id"],))
        if self.user["role"] == "admin":
            self._perms = frozenset(p["code"] for p in self.db.tous("SELECT code FROM permission"))
            return
        codes = [p["code"] for p in self.db.tous("""
            SELECT DISTINCT rp.code FROM role_permission rp
            JOIN role r ON rp.role_id = r.id WHERE r.nom = ?""", (self.user["role"],))]
        codes += [p["code"] for p in self.db.tous(
            "SELECT code FROM user_permission WHERE utilisateur_id=?", (self.user["id"],))]
        self._perms = frozenset(codes)

    def permis(self, code):
        """L'utilisateur connecté possède-t-il cette permission ?"""
        return bool(self.user) and (self.user["role"] == "admin" or code in self._perms)

    def exiger(self, code, contexte=None, auditer=True):
        """Contrôle de permission DANS la logique métier (jamais seulement l'UI).

        Lève PermissionError si l'action est interdite et écrit un REFUS_ACTION
        dans le journal d'audit pour traçabilité.
        """
        if not self.permis(code):
            if auditer:
                self.db.audit(self.uid, self.ulogin, "REFUS_ACTION",
                              details={"permission": code, "contexte": contexte})
            raise PermissionError(
                f"Accès refusé : vous n'avez pas la permission « {code} ».\n"
                "Contactez l'administrateur de l'AVEC.")

    def permissions_effectives(self):
        return self._perms

    def changer_mdp(self, login, ancien, nouveau):
        if not self.connecter(login, ancien):
            raise ValueError("Ancien mot de passe incorrect.")
        sel = secrets.token_hex(16)
        ph  = hashlib.pbkdf2_hmac('sha256', f"{nouveau}{sel}".encode(), sel.encode(), 100000).hex()
        self.db.exec("UPDATE utilisateur SET pwd_hash=?,sel=? WHERE login=?", (ph, sel, login))
        self.db.commit()
        self.user = self.db.un("SELECT * FROM utilisateur WHERE login=?", (login,))
        self._charger_permissions()

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
        self.rep.mkdir(parents=True, exist_ok=True)
        # Checkpoint WAL : garantir que le fichier .db contient toutes les
        # écritures récentes avant la copie (sinon sauvegarde incomplète).
        try:
            conn = sqlite3.connect(self.src)
            try:
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            finally:
                conn.close()
        except Exception:
            pass  # La sauvegarde ne doit jamais être bloquée
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = self.rep / f"akibacore_{ts}.db"
        shutil.copy2(self.src, dest)
        # Supprimer les plus anciennes
        backups = sorted(self.rep.glob("akibacore_*.db"))
        while len(backups) > BACKUP_MAX:
            backups.pop(0).unlink(missing_ok=True)
        return str(dest)

    @staticmethod
    def derniere_sauvegarde(rep=BACKUP_DIR):
        """Chemin de la sauvegarde la plus récente, ou None."""
        backups = sorted(Path(rep).glob("akibacore_*.db"))
        return str(backups[-1]) if backups else None

    @staticmethod
    def restaurer(db_chemin=DB_CHEMIN, rep=BACKUP_DIR):
        """Restaure la dernière sauvegarde vers le chemin de la base.

        Retourne le chemin du fichier restauré, ou None si aucun backup.
        Ne supprime jamais la base actuelle sans l'écraser par un backup.
        """
        src = Backup.derniere_sauvegarde(rep)
        if not src:
            return None
        shutil.copy2(src, db_chemin)
        # Supprimer les fichiers WAL/SHM obsolètes liés à l'ancienne base
        for suffixe in ("-wal", "-shm"):
            try:
                Path(str(db_chemin) + suffixe).unlink(missing_ok=True)
            except OSError:
                pass
        return src


# ════════════════════════════════════════════════════════════════
#  IMPRESSION PORTABLE (Windows / Linux CUPS) + PDF MINIMAL
# ════════════════════════════════════════════════════════════════

class PDFGen:
    """Générateur PDF hors ligne (polices base-14, zero dependance)."""

    LARGEUR, HAUTEUR = 595, 842          # A4 portrait
    MARGES = 40
    TAILLE = 9                            # Courier 9pt
    INTERLIGNE = 13

    @staticmethod
    def _ch(texte):
        return (texte or "").encode("cp1252", errors="replace").decode("latin-1")

    @classmethod
    def generer(cls, lignes, chemin):
        """lignes : liste de (texte, bold) ou str simples. Écrit un PDF valide."""
        items = []
        for ln in lignes:
            if isinstance(ln, (tuple, list)):
                items.append((str(ln[0]), bool(ln[1]) if len(ln) > 1 else False))
            else:
                items.append((str(ln), False))
        max_car = int((cls.LARGEUR - 2 * cls.MARGES) / (cls.TAILLE * 0.6))
        flux = []
        for txt, bold in items:
            if len(txt) <= max_car:
                flux.append((txt, bold))
                continue
            while len(txt) > max_car:
                flux.append((txt[:max_car], bold))
                txt = txt[max_car:]
            flux.append((txt, bold))

        ligne_par_page = int((cls.HAUTEUR - 2 * cls.MARGES) / cls.INTERLIGNE)
        pages = [flux[i:i + ligne_par_page]
                 for i in range(0, len(flux), ligne_par_page)] or [[]]

        contenus = []
        for page in pages:
            ops = []
            y = cls.HAUTEUR - cls.MARGES - 6
            for txt, bold in page:
                tx = cls._ch(txt)
                font = "F2" if bold else "F1"
                ops.append(f"BT /{font} {cls.TAILLE} Tf 1 0 0 1 {cls.MARGES} {y} Tm ({tx}) Tj ET")
                y -= cls.INTERLIGNE
            contenus.append("\n".join(ops).encode("latin-1"))

        n = len(pages)
        p_ids = list(range(5, 5 + n))
        c_ids = list(range(5 + n, 5 + 2 * n))
        objets = []
        objets.append("<< /Type /Catalog /Pages 2 0 R >>")
        objets.append(f"<< /Type /Pages /Count {n} /Kids [{' '.join(f'{i} 0 R' for i in p_ids)}] >>")
        objets.append("<< /Type /Font /Subtype /Type1 /BaseFont /Courier /Encoding /WinAnsiEncoding >>")
        objets.append("<< /Type /Font /Subtype /Type1 /BaseFont /Courier-Bold /Encoding /WinAnsiEncoding >>")
        for i in range(n):
            objets.append(
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {cls.LARGEUR} {cls.HAUTEUR}] "
                f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {c_ids[i]} 0 R >>")
        for i, data in enumerate(contenus):
            objets.append((f"<< /Length {len(data)} >>\nstream\n".encode("latin-1")
                           + data + b"\nendstream"))
        cls._assembler(objets, chemin)

    @staticmethod
    def _assembler(objets, chemin):
        pdf  = b"%PDF-1.4\n"
        offsets = []
        for i, o in enumerate(objets, start=1):
            offsets.append(len(pdf))
            if isinstance(o, bytes):
                pdf += b"%d 0 obj\n" % i + o + b"\nendobj\n"
            else:
                pdf += ("%d 0 obj\n" % i + str(o) + "\nendobj\n").encode("latin-1")
        xref = len(pdf)
        pdf += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objets) + 1)
        for off in offsets:
            pdf += ("%010d 00000 n \n" % off).encode("ascii")
        pdf += ("trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
                % (len(objets) + 1, xref)).encode("ascii")
        Path(chemin).parent.mkdir(parents=True, exist_ok=True)
        Path(chemin).write_bytes(pdf)


class Imprimeur:
    """Envoie un fichier vers l'imprimante du système (hors ligne)."""

    @staticmethod
    def imprimer(chemin):
        if sys.platform == "win32":
            try:
                os.startfile(str(chemin), "print")
                return True
            except OSError:
                return False
        for cmd in (["lp", "-s"], ["lpr"]) if sys.platform != "darwin" else (["lp", "-s"],):
            try:
                r = subprocess.run(cmd + [str(chemin)],
                                   capture_output=True, timeout=120)
                if r.returncode == 0:
                    return True
            except (OSError, subprocess.TimeoutExpired):
                continue
        return False

    @staticmethod
    def ouvrir(chemin):
        if sys.platform == "win32":
            os.startfile(str(chemin))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(chemin)])
        else:
            subprocess.Popen(["xdg-open", str(chemin)])


# ════════════════════════════════════════════════════════════════
#  REÇUS — NUMÉROTATION, GÉNÉRATION, IMPRESSION
# ════════════════════════════════════════════════════════════════

class Recep:
    """Reçus financiers traçables (numérotation jamais réutilisée)."""

    NEANT = "\u2014"
    LARGEUR = 40

    @staticmethod
    def numero_suivant(db, annee=None):
        """REC-AAAA-NNNNNN unique, jamais réutilisé (compteur persistant).

        Le compteur n'est JAMAIS décrémenté : même si un reçu est supprimé de
        la base, aucun numéro n'est réattribué — la traçabilité est préservée.
        Un compteur par année ; si la table compteur est vide (base existante
        avec des reçus), il est initialisé à partir du maximum déjà émis.
        """
        annee = annee or date.today().year
        prefix = f"REC-{annee}-"
        nom = f"recu_{annee}"
        db.exec(
            "INSERT OR IGNORE INTO compteur(nom,valeur) SELECT ?,"
            " COALESCE(MAX(CAST(SUBSTR(recu_no,10) AS INTEGER)),0)"
            " FROM receipt WHERE recu_no LIKE ?",
            (nom, prefix + "%"))
        db.commit()
        valeur = db.valeur("SELECT valeur FROM compteur WHERE nom=?", (nom,)) + 1
        db.exec("UPDATE compteur SET valeur=? WHERE nom=?", (valeur, nom))
        db.commit()
        return f"{prefix}{valeur:06d}"

    @staticmethod
    def enregistrer(db, uid, ulogin, type_, operation, operation_id,
                    membre_id, montant, details=None, avec_id=1, devise=None):
        no = Recep.numero_suivant(db)
        cur = db.exec(
            "INSERT INTO receipt(recu_no,type,operation,operation_id,membre_id,"
            "avec_id,montant,details,devise,cree_par) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (no, type_, operation, operation_id, membre_id, avec_id, montant,
             json.dumps(details, ensure_ascii=False) if details else None,
             (devise or DEVISE_DEFAUT).upper(), uid))
        db.commit()
        db.audit(uid, ulogin, "CREER_RECU", "receipt", cur.lastrowid,
                 {"recu_no": no, "type": type_, "montant": montant,
                  "devise": (devise or DEVISE_DEFAUT).upper()})
        return db.un("SELECT * FROM receipt WHERE id=?", (cur.lastrowid,))

    @staticmethod
    def ligne(type_):
        lib = {"EPARGNE": "DÉPÔT D'ÉPARGNE",
               "REMBOURSEMENT": "REMBOURSEMENT DE CRÉDIT",
               "CREDIT": "OCTROI DE CRÉDIT"}
        return lib.get(type_, type_)

    @staticmethod
    def texte(r, avec, membre, details=None, utilisateur_nom="",
              utilisateur_role=""):
        if not details:
            # Relecture depuis la base (réimpression, export) : le détail de
            # la répartition est stocké en JSON au moment de l'opération.
            try:
                details = json.loads(r.get("details") or "{}")
            except (ValueError, TypeError):
                details = {}
        dev = (r.get("devise") or avec.get("devise") or DEVISE_DEFAUT).strip() \
            or DEVISE_DEFAUT
        L = []
        L.append("=" * Recep.LARGEUR)
        L.append(("    %s" % APP_NOM).ljust(Recep.LARGEUR + 4)[:Recep.LARGEUR])
        L.append(("SYSTÈME AVEC").center(Recep.LARGEUR).strip())
        L.append("=" * Recep.LARGEUR)
        L.append((avec.get("nom") or "").center(Recep.LARGEUR).strip())
        if avec.get("adresse"):
            L.append(avec["adresse"])
        if avec.get("telephone"):
            L.append("Tél : %s" % avec["telephone"])
        L.append("-" * Recep.LARGEUR)
        L.append("REÇU N° : %s" % r["recu_no"])
        ts = r["cree_le"] or ""
        L.append("Date : %s   Heure : %s" %
                 (ts[:10] if ts else Recep.NEANT,
                  ts[11:19] if len(ts) > 11 else Recep.NEANT))
        L.append("-" * Recep.LARGEUR)
        L.append("MEMBRE :")
        L.append("%s — %s" % (membre.get("numero") or Recep.NEANT,
                              f"{membre['nom']} {membre.get('prenom') or ''}".strip()))
        L.append("OPÉRATION :")
        L.append(Recep.ligne(r["type"]))
        L.append("TYPE : %s" % (r.get("operation") or r["type"]))
        L.append("MONTANT :")
        if details and "montant_impute" in details:
            L.append("%s %s" % (f"{details['montant_impute']:,.0f}", dev))
        else:
            L.append("%s %s" % (f"{r['montant'] or 0:,.0f}", dev))
        if details:
            for cle, lib in (("penalite", "Pénalité"), ("interet", "Intérêt"),
                             ("principal", "Principal")):
                if details.get(cle) is not None:
                    L.append("%s : %s %s" % (lib, f"{details[cle]:,.0f}", dev))
            if "solde" in details:
                L.append("Solde restant : %s %s" % (f"{details['solde']:,.0f}", dev))
            if "credit_id" in details:
                L.append("Crédit : CR-%04d" % details["credit_id"])
            if "date_paiement" in details:
                L.append("Date paiement : %s" % details["date_paiement"])
        L.append("-" * Recep.LARGEUR)
        L.append("Utilisateur : %s %s" % (utilisateur_nom,
                  f"({utilisateur_role})" if utilisateur_role else ""))
        L.append("=" * Recep.LARGEUR)
        L.append(("Merci pour votre confiance.").center(Recep.LARGEUR).strip())
        L.append(("=" * Recep.LARGEUR))
        return "\n".join(L)


def imprimer_recu(parent, auth, recu, avec, membre, details=None,
                  utilisateur_nom="", utilisateur_role="", reimprime=False):
    """Affiche la boite reçu : imprimer / voir / PDF / ne pas imprimer.

    Le reçu est un vrai fichier PDF (documents/recus/…) ; l'impression passe
    par les imprimantes du système. Jamais d'annulation d'une transaction :
    l'échec d'impression n'affecte PAS la transaction déjà validée.
    """
    from tkinter import scrolledtext
    texte = Recep.texte(recu, avec, membre, details or {},
                        utilisateur_nom, utilisateur_role)
    lignes_pdf = texte.split("\n")

    dlg = tk.Toplevel(parent)
    dlg.title("Reçu généré")
    dlg.resizable(False, False)
    dlg.configure(bg=C["blanc"])
    dlg.grab_set()
    centrer(dlg, 560, 440)

    tk.Label(dlg, text="Opération enregistrée avec succès.",
             font=(FONT, 13, "bold"), bg=C["blanc"], fg=C["vert"]).pack(pady=(14, 2))
    tk.Label(dlg, text="Reçu n° %s — %s" % (recu["recu_no"],
             Recep.ligne(recu["type"])), font=(FONT, 10), bg=C["blanc"],
             fg=C["texte_mute"]).pack(pady=(0, 6))

    apercu = scrolledtext.ScrolledText(dlg, width=62, height=14, font=("Courier", 9),
                                       bg=C["blanc"], fg=C["texte"], relief="flat")
    apercu.pack(fill="both", expand=True, padx=16)
    apercu.insert("1.0", texte)
    apercu.config(state="disabled")

    bande = tk.Frame(dlg, bg=C["blanc"])
    bande.pack(fill="x", padx=16, pady=12)

    def chemin_pdf():
        return str(DOC_REC / (recu["recu_no"] + ".pdf"))

    def _imprimer():
        if reimprime:
            auth.exiger("receipts.reprint", contexte="réimpression reçu")
        else:
            auth.exiger("receipts.print", contexte="impression reçu")
        pdf_path = chemin_pdf()
        PDFGen.generer(lignes_pdf, pdf_path)
        if Imprimeur.imprimer(pdf_path):
            action = "RECU_REIMPRIME" if reimprime else "RECU_IMPRIME"
            auth.db.audit(auth.uid, auth.ulogin, action, "receipt", recu["id"],
                          {"recu_no": recu["recu_no"]})
            messagebox.showinfo("Impression",
                                "Reçu envoyé à l'imprimante.", parent=dlg)
        else:
            messagebox.showwarning(
                "Impression indisponible",
                "Le reçu n'a pas pu être imprimé (aucune imprimante détectée).\n"
                "La transaction reste enregistrée.\n\n"
                "Vous pouvez le voir ou l'enregistrer en PDF.", parent=dlg)

    def _voir():
        pdf_path = chemin_pdf()
        PDFGen.generer(lignes_pdf, pdf_path)
        try:
            Imprimeur.ouvrir(pdf_path)
        except Exception:
            messagebox.showinfo("Reçu", texte, parent=dlg)

    def _pdf():
        pdf_path = chemin_pdf()
        PDFGen.generer(lignes_pdf, pdf_path)
        auth.db.audit(auth.uid, auth.ulogin, "RECU_EXPORT_PDF", "receipt",
                      recu["id"], {"recu_no": recu["recu_no"]})
        messagebox.showinfo("Export PDF",
                            "Reçu enregistré dans :\n%s" % pdf_path, parent=dlg)

    b1 = ttk.Button(bande, text="Imprimer le reçu", command=_imprimer, style="Vert.TButton")
    b1.pack(side="left", padx=4)
    ttk.Button(bande, text="Voir le reçu", command=_voir,
               style="Bleu.TButton").pack(side="left", padx=4)
    ttk.Button(bande, text="Enregistrer en PDF", command=_pdf).pack(side="left", padx=4)
    ttk.Button(bande, text="Ne pas imprimer", command=dlg.destroy).pack(side="left", padx=4)

    if not (auth.permis("receipts.print" if not reimprime else "receipts.reprint")):
        b1.config(state="disabled")


def gerer_recu_operation(parent, auth, db, avec, membre, type_,
                         operation, operation_id, montant, details=None,
                         devise=None):
    """Flux standard après une opération financière validée (COMMIT déjà fait).

    La transaction est PRIORITAIRE : on ne revient jamais dessus, même si
    l'impression échoue. Le reçu est stocké (numéro unique) puis :
      - impression automatique si paramétré ;
      - sinon boite de dialogue imprimer / voir / PDF / ne pas imprimer.
    """
    recu = Recep.enregistrer(db, auth.uid, auth.ulogin, type_, operation,
                             operation_id, membre["id"], montant, details,
                             avec["id"], devise)
    if not auth.permis("receipts.print"):
        return recu
    nom_user = (auth.user or {}).get("nom", "")
    role_user = (auth.user or {}).get("role", "")
    if int(avec.get("impression_auto") or 0):
        texte = Recep.texte(recu, avec, membre, details or {}, nom_user, role_user)
        pdf_path = str(DOC_REC / (recu["recu_no"] + ".pdf"))
        try:
            PDFGen.generer(texte.split("\n"), pdf_path)
            ok = Imprimeur.imprimer(pdf_path)
        except Exception:
            ok = False
        if ok:
            auth.db.audit(auth.uid, auth.ulogin, "RECU_IMPRIME", "receipt",
                          recu["id"], {"recu_no": recu["recu_no"]})
            messagebox.showinfo("Reçu imprimé",
                                "Le reçu %s a été imprimé automatiquement."
                                % recu["recu_no"], parent=parent)
        else:
            imprimer_recu(parent, auth, recu, avec, membre, details,
                          nom_user, role_user)
    else:
        imprimer_recu(parent, auth, recu, avec, membre, details,
                      nom_user, role_user)
    return recu


# ════════════════════════════════════════════════════════════════
#  MODÈLES DE DOCUMENTS PERSONNALISABLES
# ════════════════════════════════════════════════════════════════

class Modeles:
    """Modèles de documents fournis par l'AVEC (DOCX / ODT / HTML / TXT).

    Chaque modèle est copié dans documents/modeles/ (l'application continue de
    fonctionner même si le fichier d'origine est déplacé). Les champs {{VAR}}
    sont remplacés lors de la génération. Un modèle par défaut peut être défini
    pour chaque type de document.
    """

    TYPES = ("Reçu", "Attestation", "Rapport financier", "Relevé membre",
             "Bilan", "Procès-verbal")

    NAUT = [f"{{{{{p[0]}}}}}".ljust(26) + p[1] for p in [
        ("AVEC_NOM", "Nom de l'AVEC"),
        ("AVEC_ADRESSE", "Adresse de l'AVEC"),
        ("AVEC_TELEPHONE", "Téléphone de l'AVEC"),
        ("AVEC_EMAIL", "E-mail de l'AVEC"),
        ("AVEC_DEVISE", "Devise (ex : CDF, USD)"),
        ("AVEC_DESCRIPTION", "Description de l'AVEC"),
        ("MEMBRE_NUMERO", "N° du membre"),
        ("MEMBRE_NOM", "Nom du membre"),
        ("MEMBRE_PRENOM", "Prénom du membre"),
        ("MEMBRE_TELEPHONE", "Téléphone du membre"),
        ("MEMBRE_ADRESSE", "Adresse du membre"),
        ("MEMBRE_PARTS", "Nombre de parts"),
        ("RECU_NUMERO", "N° du reçu"),
        ("DATE", "Date du jour"),
        ("HEURE", "Heure actuelle"),
        ("TYPE_OPERATION", "Type d'opération"),
        ("MONTANT", "Montant en chiffres"),
        ("CREDIT_NUMERO", "N° du crédit"),
        ("INTERET", "Intérêt (montant)"),
        ("PENALITE", "Pénalité (montant)"),
        ("PRINCIPAL", "Principal (montant)"),
        ("SOLDE", "Solde restant"),
        ("UTILISATEUR", "Login de l'utilisateur"),
        ("UTILISATEUR_NOM", "Nom complet de l'utilisateur"),
        ("UTILISATEUR_ROLE", "Rôle de l'utilisateur"),
        ("SESSION_NUMERO", "N° de session"),
        ("DATE_REUNION", "Date de réunion"),
        ("DEVISE", "Devise de l'opération (CDF / USD)"),
    ]]

    @staticmethod
    def _creer_dossiers():
        for d in (DOC_IN, DOC_REC, DOC_RAP, DOC_ARC, DOC_GEN):
            try:
                d.mkdir(parents=True, exist_ok=True)
            except OSError:
                pass

    @staticmethod
    def lire_contenu(chemin):
        ext = Path(chemin).suffix.lower().lstrip(".")
        if ext == "docx":
            with zipfile.ZipFile(str(chemin)) as z:
                return z.read("word/document.xml").decode("utf-8", "replace")
        if ext == "odt":
            with zipfile.ZipFile(str(chemin)) as z:
                return z.read("content.xml").decode("utf-8", "replace")
        return Path(chemin).read_text(encoding="utf-8", errors="replace")

    @staticmethod
    def importer(db, chemin_source, avec_id, nom, type_, cree_par, par_defaut=0):
        ext = Path(chemin_source).suffix.lower().lstrip(".")
        if ext not in FORMATS_MODELES:
            raise ValueError(
                f"Format « {ext} » non supporté.\nFormats acceptés : {', '.join(sorted(FORMATS_MODELES))}.")
        if not Path(chemin_source).is_file():
            raise ValueError("Fichier introuvable.")
        nom_mod = nom.strip() or Path(chemin_source).stem
        Modeles._creer_dossiers()
        horodatage = datetime.now().strftime("%Y%m%d_%H%M%S")
        nom_fich = re.sub(r"[^A-Za-z0-9_\-]", "_", nom_mod)
        dest = DOC_IN / f"{avec_id}_{horodatage}_{nom_fich}.{ext}"
        shutil.copy2(chemin_source, dest)
        contenu = Modeles.lire_contenu(dest)
        if par_defaut:
            db.exec("UPDATE document_template SET par_defaut=0 WHERE avec_id=? AND type=?",
                    (avec_id, type_))
        cur = db.exec("""
            INSERT INTO document_template(avec_id,nom,type,format,fichier,contenu,par_defaut,cree_par)
            VALUES(?,?,?,?,?,?,?,?)""",
            (avec_id, nom_mod, type_, ext, str(dest), contenu, 1 if par_defaut else 0, cree_par))
        db.commit()
        db.audit(cree_par,
                 db.un("SELECT login FROM utilisateur WHERE id=?", (cree_par,))["login"] if db.un(
                     "SELECT login FROM utilisateur WHERE id=?", (cree_par,)) else None,
                 "AJOUTER_MODELE", "document_template", cur.lastrowid,
                 {"nom": nom_mod, "type": type_, "format": ext})
        return cur.lastrowid

    @staticmethod
    def valeurs_standard(avec, membre=None, recu=None, credit=None,
                         contexte=None, auth=None):
        vals = {
            "AVEC_NOM": avec.get("nom") or "",
            "AVEC_ADRESSE": avec.get("adresse") or "",
            "AVEC_TELEPHONE": avec.get("telephone") or "",
            "AVEC_EMAIL": avec.get("email") or "",
            "AVEC_DEVISE": (avec.get("devise") or DEVISE_DEFAUT),
            "AVEC_DESCRIPTION": avec.get("description") or "",
            "DATE": date.today().strftime("%d/%m/%Y"),
            "HEURE": datetime.now().strftime("%H:%M"),
        }
        if membre:
            vals.update({
                "MEMBRE_NUMERO": membre.get("numero") or "",
                "MEMBRE_NOM": membre.get("nom") or "",
                "MEMBRE_PRENOM": membre.get("prenom") or "",
                "MEMBRE_TELEPHONE": membre.get("telephone") or "",
                "MEMBRE_ADRESSE": membre.get("adresse") or "",
                "MEMBRE_PARTS": str(membre.get("nb_parts", "")),
            })
        if recu:
            dev = (recu.get("devise") or avec.get("devise") or DEVISE_DEFAUT)
            vals.update({
                "RECU_NUMERO": recu.get("recu_no") or "",
                "TYPE_OPERATION": Recep.ligne(recu.get("type", "")),
                "MONTANT": f"{recu.get('montant') or 0:,.0f}" if recu.get("montant") else "",
                "DEVISE": dev,
            })
            if recu.get("details"):
                try:
                    det = json.loads(recu["details"]) or {}
                    for cle, fct in (("PENALITE", None), ("INTERET", None),
                                     ("PRINCIPAL", None), ("SOLDE", None)):
                        if det.get(cle.lower()) is not None:
                            vals[cle] = f"{det[cle.lower()]:,.0f}"
                except Exception:
                    pass
        if credit:
            vals.update({
                "CREDIT_NUMERO": str(credit.get("id") or ""),
                "INTERET": f"{credit.get('montant_interet') or 0:,.0f}" if credit.get("montant_interet") else "",
                "PRINCIPAL": f"{credit.get('principal') or 0:,.0f}" if credit.get("principal") else "",
                "SOLDE": f"{Finance.solde_credit(credit):,.0f}" if credit.get("montant_total") is not None else "",
                "DEVISE": credit.get("devise") or avec.get("devise") or DEVISE_DEFAUT,
            })
        if auth and auth.user:
            vals.update({
                "UTILISATEUR": auth.ulogin or "",
                "UTILISATEUR_NOM": auth.user.get("nom") or "",
                "UTILISATEUR_ROLE": auth.user.get("role") or "",
            })
        if contexte:
            vals.update(contexte)
        if "DEVISE" not in vals:
            vals["DEVISE"] = avec.get("devise") or DEVISE_DEFAUT
        return vals

    @staticmethod
    def substituer(contenu, valeurs):
        def repl(m):
            cle = m.group(1).strip()
            if cle not in valeurs:
                return m.group(0)
            return html.escape(str(valeurs[cle]), quote=False)
        return re.sub(r"\{\{\s*([A-Z_0-9]+)\s*\}\}", repl, contenu)

    @staticmethod
    def generer(ml, valeurs, sortie):
        """Applique les variables au modèle stocké et écrit un nouveau fichier."""
        chemin = ml["fichier"]
        if isinstance(chemin, str) and not Path(chemin).is_file():
            raise ValueError(
                "Le fichier modèle est introuvable sur le disque.\n"
                "Le modèle a peut-être été supprimé. Réimportez-le depuis la liste.")
        ext = str(ml["format"] or "").lower().lstrip(".") or \
              Path(chemin).suffix.lower().lstrip(".")
        try:
            contenu = Modeles.lire_contenu(chemin)
        except OSError:
            raise ValueError(
                "Impossible de lire le fichier modèle sur le disque.\n"
                "Réimportez le modèle pour continuer.")
        substitue = Modeles.substituer(contenu, valeurs)
        Path(sortie).parent.mkdir(parents=True, exist_ok=True)
        if ext in ("docx", "odt"):
            cible = "word/document.xml" if ext == "docx" else "content.xml"
            with zipfile.ZipFile(str(chemin)) as zin:
                donnees = {i.filename: zin.read(i.filename) for i in zin.infolist()}
            import io
            with zipfile.ZipFile(sortie, "w", zipfile.ZIP_DEFLATED) as zout:
                for nomf, data in donnees.items():
                    if nomf == cible:
                        data = substitue.encode("utf-8")
                    zout.writestr(nomf, data)
            return sortie
        Path(sortie).write_text(substitue, encoding="utf-8")
        return sortie

    @staticmethod
    def texte_apercu(contenu, format_):
        if format_ in ("html", "htm"):
            txt = re.sub(r"<script[\s\S]*?</script>", " ", contenu, flags=re.I)
            txt = re.sub(r"<[^>]+>", " ", txt)
            return html.unescape(re.sub(r"[ \t]+", " ", txt))
        txt = contenu.replace("</w:p>", "\n").replace("</text:p>", "\n")
        txt = re.sub(r"<[^>]+>", "", txt)
        return html.unescape(re.sub(r"[ \t]+", " ", txt))


# ════════════════════════════════════════════════════════════════
#  MOTEUR DE GRAPHIQUES (Canvas pur, zero dependance)
# ════════════════════════════════════════════════════════════════

class ChartEngine:
    """Graphiques statiques dessines sur un tk.Canvas."""

    @staticmethod
    def bar(canvas, data, hauteur=180, padding=40):
        """
        Diagramme en barres.
        data : [(label, valeur, couleur), ...]
        """
        canvas.delete("all")
        canvas.update_idletasks()
        w = max(canvas.winfo_width(), 300)
        h = hauteur
        canvas.config(height=h)
        if not data:
            return
        max_val = max(v for _, v, _ in data) or 1
        nb = len(data)
        zone_w = w - padding * 2
        bar_w = max(zone_w // (nb * 2), 20)
        echelle = (h - 50) / max_val

        # Ligne de base
        canvas.create_line(padding, h - 30, w - padding, h - 30, fill=C["gris_f"])

        for i, (label, valeur, couleur) in enumerate(data):
            x = padding + i * (zone_w // nb) + (zone_w // nb - bar_w) // 2
            bh = max(int(valeur * echelle), 2)
            y_top = h - 30 - bh
            # Barre
            canvas.create_rectangle(x, y_top, x + bar_w, h - 30,
                                    fill=couleur, outline="", width=0)
            # Valeur
            canvas.create_text(x + bar_w // 2, y_top - 6,
                               text=f"{valeur:,.0f}", anchor="s",
                               fill=C["texte"], font=(FONT, 8, "bold"))
            # Label
            canvas.create_text(x + bar_w // 2, h - 14,
                               text=label, anchor="n",
                               fill=C["texte_mute"], font=(FONT, 8))

    @staticmethod
    def pie(canvas, data, rayon=None):
        """
        Diagramme circulaire.
        data : [(label, valeur, couleur), ...]
        """
        canvas.delete("all")
        canvas.update_idletasks()
        w = max(canvas.winfo_width(), 250)
        h = max(canvas.winfo_height(), 200)
        canvas.config(height=h)
        if not data:
            return
        total = sum(v for _, v, _ in data)
        if total == 0:
            return
        cx, cy = w // 2 - 40, h // 2
        r = rayon or min(cx - 10, cy - 10, 80)
        angle = 0
        for label, valeur, couleur in data:
            extent = (valeur / total) * 360
            if extent > 0.5:
                canvas.create_arc(cx - r, cy - r, cx + r, cy + r,
                                  start=angle, extent=extent,
                                  fill=couleur, outline=C["blanc"], style="pieslice")
            angle += extent

        # Legende a droite
        lx = cx + r + 20
        ly = cy - (len(data) * 14) // 2
        for i, (label, valeur, couleur) in enumerate(data):
            y = ly + i * 18
            canvas.create_rectangle(lx, y, lx + 10, y + 10, fill=couleur, outline="")
            pct = (valeur / total) * 100
            canvas.create_text(lx + 16, y + 5, anchor="w",
                               text=f"{label} ({pct:.0f}%)",
                               fill=C["texte"], font=(FONT, 8))

    @staticmethod
    def line(canvas, data, hauteur=160, padding=40):
        """
        Courbe d'evolution.
        data : [(label, valeur), ...] — les labels servent d'axe X
        """
        canvas.delete("all")
        canvas.update_idletasks()
        w = max(canvas.winfo_width(), 300)
        h = hauteur
        canvas.config(height=h)
        if len(data) < 2:
            return
        valeurs = [v for _, v in data]
        max_val = max(valeurs) or 1
        min_val = min(valeurs)
        echelle = (h - 50) / (max_val - min_val if max_val != min_val else 1)
        zone_w = w - padding * 2

        # Ligne de base + grille
        canvas.create_line(padding, h - 30, w - padding, h - 30, fill=C["gris_f"])
        for i in range(4):
            y = h - 30 - int(i * (h - 50) / 3)
            canvas.create_line(padding, y, w - padding, y,
                               fill=C["gris_f"], dash=(2, 4))

        # Points et lignes
        points = []
        for i, (label, valeur) in enumerate(data):
            x = padding + int(i * zone_w / (len(data) - 1))
            y = h - 30 - int((valeur - min_val) * echelle)
            points.append((x, y))
            # Label X
            if len(data) <= 12 or i % max(1, len(data) // 6) == 0:
                canvas.create_text(x, h - 14, text=label, anchor="n",
                                   fill=C["texte_mute"], font=(FONT, 7))

        # Remplissage sous la courbe
        fill_pts = [(points[0][0], h - 30)] + points + [(points[-1][0], h - 30)]
        flat = [c for p in fill_pts for c in p]
        canvas.create_polygon(flat, fill=C["bleu_pale"], outline="", smooth=False)

        # Ligne de la courbe
        for i in range(len(points) - 1):
            canvas.create_line(points[i], points[i + 1],
                               fill=C["bleu"], width=2, smooth=True)
        # Dots
        for x, y in points:
            canvas.create_oval(x - 3, y - 3, x + 3, y + 3,
                               fill=C["bleu"], outline=C["blanc"], width=1)

    @staticmethod
    def svg_bar(data, w=480, h=200):
        """Génère un diagramme en barres SVG inline."""
        if not data:
            return ""
        max_val = max(v for _, v, _ in data) or 1
        nb = len(data)
        bw = max((w - 60) // (nb * 2), 24)
        echelle = (h - 45) / max_val
        parts = [f'<svg width="{w}" height="{h}" xmlns="http://www.w3.org/2000/svg">']
        parts.append(f'<line x1="30" y1="{h-25}" x2="{w-10}" y2="{h-25}" stroke="#D5D8DC" stroke-width="1"/>')
        for i, (label, value, color) in enumerate(data):
            x = 40 + i * ((w - 60) // nb) + ((w - 60) // nb - bw) // 2
            bh = max(int(value * echelle), 2)
            y_top = h - 25 - bh
            parts.append(f'<rect x="{x}" y="{y_top}" width="{bw}" height="{bh}" fill="{color}" rx="3"/>')
            parts.append(f'<text x="{x + bw // 2}" y="{y_top - 4}" text-anchor="middle" '
                         f'font-size="10" font-weight="bold" fill="{color}">{value:,.0f}</text>')
            parts.append(f'<text x="{x + bw // 2}" y="{h - 8}" text-anchor="middle" '
                         f'font-size="9" fill="#566573">{label}</text>')
        parts.append('</svg>')
        return '\n'.join(parts)

    @staticmethod
    def svg_pie(data, size=200):
        """Génère un diagramme circulaire SVG inline."""
        if not data:
            return ""
        total = sum(v for _, v, _ in data)
        if total == 0:
            return ""
        cx, cy, r = size // 2 + 20, size // 2, size // 2 - 20
        parts = [f'<svg width="{size + 140}" height="{size}" xmlns="http://www.w3.org/2000/svg">']
        angle = -90
        for label, value, color in data:
            pct = value / total
            if pct < 0.001:
                continue
            end_angle = angle + pct * 360
            a1 = math.radians(angle)
            a2 = math.radians(end_angle)
            x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
            x2, y2 = cx + r * math.cos(a2), cy + r * math.sin(a2)
            large = 1 if pct > 0.5 else 0
            parts.append(
                f'<path d="M{cx},{cy} L{x1:.1f},{y1:.1f} '
                f'A{r},{r} 0 {large},1 {x2:.1f},{y2:.1f} Z" '
                f'fill="{color}" stroke="#fff" stroke-width="1.5"/>')
            angle = end_angle
        for i, (label, value, color) in enumerate(data):
            y = 20 + i * 22
            lx = size + 30
            pct = (value / total) * 100
            parts.append(f'<rect x="{lx}" y="{y}" width="12" height="12" fill="{color}" rx="2"/>')
            parts.append(f'<text x="{lx + 18}" y="{y + 10}" font-size="10" fill="#1C2833">'
                         f'{label} ({pct:.0f}%)</text>')
        parts.append('</svg>')
        return '\n'.join(parts)


# ════════════════════════════════════════════════════════════════
#  STYLES TTK
# ════════════════════════════════════════════════════════════════

def appliquer_styles(root):
    _resoudre_font(root)
    s = ttk.Style(root)
    s.theme_use("clam")

    s.configure("TFrame",        background=C["gris"])
    s.configure("Blanc.TFrame",  background=C["blanc"])
    s.configure("TLabel",        background=C["gris"], foreground=C["texte"],
                                 font=(FONT, 10))
    s.configure("Titre.TLabel",  background=C["gris"], foreground=C["bleu"],
                                 font=(FONT, 15, "bold"))
    s.configure("Sub.TLabel",    background=C["gris"], foreground=C["bleu"],
                                 font=(FONT, 11, "bold"))
    s.configure("Bold.TLabel",   background=C["blanc"], foreground=C["texte"],
                                 font=(FONT, 10, "bold"))

    s.configure("TButton",       font=(FONT, 10), padding=6)
    s.configure("Bleu.TButton",  background=C["bleu"],  foreground=C["blanc"],
                                 font=(FONT, 10, "bold"), padding=8)
    s.map("Bleu.TButton",  background=[("active", C["bleu_f"])])
    s.configure("Vert.TButton",  background=C["vert"],  foreground=C["blanc"],
                                 font=(FONT, 10, "bold"), padding=8)
    s.map("Vert.TButton",  background=[("active", "#176338")])
    s.configure("Rouge.TButton", background=C["rouge"], foreground=C["blanc"],
                                 font=(FONT, 10, "bold"), padding=8)
    s.map("Rouge.TButton", background=[("active", "#A93226")])

    s.configure("TNotebook",     background=C["gris"], borderwidth=0)
    s.configure("TNotebook.Tab", font=(FONT, 10, "bold"), padding=(14, 7))
    s.map("TNotebook.Tab",
          background=[("selected", C["bleu"]), ("!selected", C["gris_f"])],
          foreground=[("selected", C["blanc"]), ("!selected", C["texte"])])

    s.configure("Treeview",          font=(FONT, 10), rowheight=26,
                                     background=C["blanc"], foreground=C["texte"],
                                     fieldbackground=C["blanc"])
    s.configure("Treeview.Heading",  font=(FONT, 10, "bold"),
                                     background=C["bleu"], foreground=C["blanc"])
    s.map("Treeview",                background=[("selected", C["or"])])
    s.configure("TEntry",            font=(FONT, 10), padding=5)
    s.configure("TCombobox",         font=(FONT, 10), padding=5)
    s.configure("TLabelframe",       background=C["gris"])
    s.configure("TLabelframe.Label", background=C["gris"], foreground=C["bleu"],
                                     font=(FONT, 10, "bold"))


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
    tv.tag_configure("gris",   background="#E5E8E8")
    return tv, f


def sep(parent):
    ttk.Separator(parent, orient="horizontal").pack(fill="x", padx=12, pady=6)


def centrer(win, w, h):
    win.update_idletasks()
    x = (win.winfo_screenwidth()  - w) // 2
    y = (win.winfo_screenheight() - h) // 2
    win.geometry(f"{w}x{h}+{x}+{y}")


# ════════════════════════════════════════════════════════════════
#  BARRE LATÉRALE DE NAVIGATION
# ════════════════════════════════════════════════════════════════

class Sidebar(tk.Frame):
    """Barre latérale de navigation remplaçant le Notebook."""

    def __init__(self, parent, items, callback):
        """
        items   : [(nom_affiche, icone_unicode), ...]
        callback(index) : appele quand un item est clique
        """
        super().__init__(parent, bg=C["sidebar_bg"], width=210)
        self.pack_propagate(False)
        self._items = []
        self._callback = callback
        self._actif = -1

        # Logo / Titre
        tk.Label(self, text=APP_NOM, bg=C["sidebar_bg"], fg=C["blanc"],
                 font=(FONT, 14, "bold"), pady=14).pack(fill="x")
        tk.Frame(self, bg=C["sidebar_hl"], height=1).pack(fill="x", padx=12)

        for i, (nom, icone) in enumerate(items):
            self._ajouter_item(i, nom, icone)

    def _ajouter_item(self, index, nom, icone):
        f = tk.Frame(self, bg=C["sidebar_bg"], cursor="hand2")
        f.pack(fill="x", padx=0, pady=1)

        lbl_icone = tk.Label(f, text=icone, bg=C["sidebar_bg"],
                             fg=C["sidebar_tx"], font=(FONT, 14), width=3)
        lbl_icone.pack(side="left", padx=(12, 4), pady=8)

        lbl_texte = tk.Label(f, text=nom, bg=C["sidebar_bg"],
                             fg=C["sidebar_tx"], font=(FONT, 11))
        lbl_texte.pack(side="left", padx=4, pady=8)

        self._items.append((f, lbl_icone, lbl_texte))

        for w in (f, lbl_icone, lbl_texte):
            w.bind("<Enter>", lambda e, idx=index: self._on_hover(idx, True))
            w.bind("<Leave>", lambda e, idx=index: self._on_hover(idx, False))
            w.bind("<Button-1>", lambda e, idx=index: self.selectionner(idx))

    def _on_hover(self, index, entree):
        if index == self._actif:
            return
        _, li, lt = self._items[index]
        bg = C["sidebar_hl"] if entree else C["sidebar_bg"]
        fg = C["blanc"] if entree else C["sidebar_tx"]
        for w in (li, lt):
            w.config(bg=bg, fg=fg)

    def selectionner(self, index):
        if index == self._actif:
            return
        # Desactiver ancien
        if 0 <= self._actif < len(self._items):
            _, li, lt = self._items[self._actif]
            for w in (li, lt):
                w.config(bg=C["sidebar_bg"], fg=C["sidebar_tx"])
        # Activer nouveau
        f, li, lt = self._items[index]
        for w in (li, lt):
            w.config(bg=C["sidebar_act"], fg=C["blanc"])
        self._actif = index
        self._callback(index)


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
        tk.Label(self, text=APP_NOM, font=(FONT, 28, "bold"),
                 fg=C["blanc"], bg=C["bleu"]).pack(pady=(30, 4))
        tk.Label(self, text="Gestion AVEC — Accès sécurisé",
                 font=(FONT, 10), fg="#AED6F1", bg=C["bleu"]).pack(pady=(0, 16))

        # Formulaire blanc
        f = tk.Frame(self, bg=C["blanc"])
        f.pack(fill="x", padx=28)

        for row, (lbl, attr, show) in enumerate([
            ("Identifiant",   "v_login", ""),
            ("Mot de passe",  "v_mdp",   "*"),
        ]):
            tk.Label(f, text=lbl, bg=C["blanc"],
                     font=(FONT, 10)).grid(row=row*2,   column=0, sticky="w", padx=12, pady=(10,2))
            setattr(self, attr, tk.StringVar())
            e = ttk.Entry(f, textvariable=getattr(self, attr), show=show, width=26)
            e.grid(row=row*2+1, column=0, padx=12, sticky="ew", pady=(0, 6))
            if show == "*":
                e.bind("<Return>", lambda ev: self._connecter())
        f.columnconfigure(0, weight=1)

        # Message
        self.v_msg = tk.StringVar()
        tk.Label(self, textvariable=self.v_msg, fg="#FADBD8",
                 bg=C["bleu"], font=(FONT, 9)).pack(pady=(8, 0))

        tk.Button(self, text="SE CONNECTER", command=self._connecter,
                  bg=C["or"], fg=C["blanc"], font=(FONT, 11, "bold"),
                  relief="flat", padx=24, pady=8, cursor="hand2",
                  activebackground="#B7950B").pack(pady=12)

        tk.Label(self, text="Compte par défaut : admin / admin123",
                 font=(FONT, 8), fg="#AED6F1", bg=C["bleu"]).pack()

    def _connecter(self):
        global _TENTATIVES_CONNEXION
        login = self.v_login.get().strip()
        mdp   = self.v_mdp.get()
        if not login or not mdp:
            self.v_msg.set("Veuillez remplir tous les champs.")
            return
        # Rate limiting
        now = datetime.now().timestamp()
        if login in _TENTATIVES_CONNEXION:
            nb, debut = _TENTATIVES_CONNEXION[login]
            if nb >= _MAX_TENTATIVES:
                ecoule = now - debut
                if ecoule < _LOCKOUT_SECONDS:
                    restant = int(_LOCKOUT_SECONDS - ecoule)
                    self.v_msg.set(f"Compte bloqué. Réessayez dans {restant}s.")
                    return
                else:
                    _TENTATIVES_CONNEXION[login] = (0, now)
        if self.auth.connecter(login, mdp):
            _TENTATIVES_CONNEXION.pop(login, None)
            if mdp == MDP_DEFAUT:
                # Sécurité : interdire l'usage permanent du mot de passe usine
                self._forcer_changement_mdp(login, mdp)
                return
            self.destroy()
            self.callback()
        else:
            nb, debut = _TENTATIVES_CONNEXION.get(login, (0, now))
            _TENTATIVES_CONNEXION[login] = (nb + 1, debut if nb > 0 else now)
            reste = _MAX_TENTATIVES - nb - 1
            if reste > 0:
                self.v_msg.set(f"Identifiant ou mot de passe incorrect. ({reste} tentative(s) restante(s))")
            else:
                self.v_msg.set(f"Compte bloqué {_LOCKOUT_SECONDS}s après {_MAX_TENTATIVES} échecs.")
            self.v_mdp.set("")

    def _forcer_changement_mdp(self, login, mdp_actuel):
        """Dialogue modal non-fermable : le mot de passe usine doit être remplacé."""
        self.withdraw()
        dlg = tk.Toplevel(self)
        dlg.title("Sécurité — Changement obligatoire")
        dlg.resizable(False, False)
        dlg.configure(bg=C["blanc"])
        dlg.grab_set()
        dlg.protocol("WM_DELETE_WINDOW", lambda: None)   # Fermeture interdite
        centrer(dlg, 420, 330)

        tk.Label(dlg, text="⚠ Sécurité requise", font=(FONT, 13, "bold"),
                 bg=C["blanc"], fg="#B7950B").pack(pady=(18, 2))
        tk.Label(dlg, text="Vous utilisez encore le mot de passe par défaut.\n"
                           "Choisissez un nouveau mot de passe pour continuer.",
                 font=(FONT, 9), bg=C["blanc"], fg=C["gris"], justify="center").pack(pady=(0, 10))

        frm = tk.Frame(dlg, bg=C["blanc"])
        frm.pack(fill="x", padx=26)
        frm.columnconfigure(1, weight=1)

        vars_ = {}
        for row, (lbl, cle) in enumerate([
            ("Nouveau mot de passe",   "n"),
            ("Confirmer le nouveau",   "c"),
        ]):
            tk.Label(frm, text=lbl, bg=C["blanc"], font=(FONT, 10)).grid(
                row=row*2, column=0, columnspan=2, sticky="w", pady=(8, 1))
            vars_[cle] = tk.StringVar()
            ttk.Entry(frm, textvariable=vars_[cle], show="*", width=24).grid(
                row=row*2+1, column=0, columnspan=2, sticky="ew", pady=(0, 4))

        v_msg = tk.StringVar()
        tk.Label(dlg, textvariable=v_msg, fg="#C0392B", bg=C["blanc"],
                 font=(FONT, 9)).pack(pady=(6, 0))

        def _valider():
            n, c = vars_["n"].get(), vars_["c"].get()
            if len(n) < 4:
                v_msg.set("Le mot de passe doit contenir au moins 4 caractères.")
                return
            if n == MDP_DEFAUT:
                v_msg.set("Le nouveau mot de passe ne peut pas être identique à l'ancien.")
                return
            if n != c:
                v_msg.set("Les mots de passe ne correspondent pas.")
                return
            try:
                self.auth.changer_mdp(login, mdp_actuel, n)
                self.auth.connecter(login, n)      # Re-synchroniser la session
                self.auth.db.audit(self.auth.uid, login, "MDP_INITIAL_CHANGE")
                messagebox.showinfo(
                    "Mot de passe modifié",
                    "Votre mot de passe a été mis à jour.\nBienvenue dans AkibaCore !",
                    parent=dlg)
                dlg.destroy()
                self.destroy()
                self.callback()
            except ValueError as e:
                v_msg.set(str(e))

        tk.Button(dlg, text="DÉFINIR LE NOUVEAU MOT DE PASSE", command=_valider,
                  bg=C["or"], fg=C["blanc"], font=(FONT, 10, "bold"),
                  relief="flat", padx=18, pady=7, cursor="hand2",
                  activebackground="#B7950B").pack(pady=14)


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

        # Zone scrollable : Canvas + barre verticale + molette
        zone = tk.Frame(self, bg=C["gris"])
        zone.grid(row=1, column=0, sticky="nsew", padx=16, pady=8)
        zone.rowconfigure(0, weight=1)
        zone.columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(zone, bg=C["gris"], highlightthickness=0,
                                yscrollincrement=40)
        vsb = ttk.Scrollbar(zone, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=vsb.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        self.corps = tk.Frame(self.canvas, bg=C["gris"])
        self.corps.columnconfigure(0, weight=1)
        self._fen_corps = self.canvas.create_window(
            (0, 0), window=self.corps, anchor="nw")
        self.corps.bind("<Configure>",
                        lambda e: self.canvas.configure(
                            scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfigure(
                             self._fen_corps, width=e.width))
        self.actualiser()

    def _molette(self, event):
        """Fait défiler le tableau de bord avec la molette."""
        if getattr(event, "num", None) == 4:
            pas = -2
        elif getattr(event, "num", None) == 5:
            pas = 2
        else:
            d = getattr(event, "delta", 0)
            if d == 0:
                return
            pas = -2 if d > 0 else 2
        try:
            self.canvas.yview_scroll(pas, "units")
        except tk.TclError:
            pass

    def _lier_molette(self):
        """Attache la molette à tous les enfants sauf les zones déjà
        défilables d'elles-mêmes (Treeview, Listbox, Text)."""
        def lier(w):
            if isinstance(w, (ttk.Treeview, tk.Listbox, tk.Text)):
                return
            w.bind("<Button-4>", self._molette)
            w.bind("<Button-5>", self._molette)
            w.bind("<MouseWheel>", self._molette)
            for e in w.winfo_children():
                lier(e)
        for enfant in self.corps.winfo_children():
            lier(enfant)

    def _lib_par_devise(d, unite=""):
        """'1 234 CDF | 50 USD' à partir d'un dict {devise: montant}."""
        return " | ".join(f"{v:,.0f} {k}" for k, v in sorted(d.items())) if d else f"0 {unite}"

    def actualiser(self):
        for w in self.corps.winfo_children():
            w.destroy()
        Finance.maj_statuts(self.db)
        s = self._stats()
        devises = sorted(set(list(s["epargnes"]) + list(s["rembs"]))
                         or [DEVISE_DEFAUT])

        # ── Ligne 1 : KPI Cards ──
        lbl_frame = tk.Frame(self.corps, bg=C["gris"])
        lbl_frame.grid(row=0, column=0, sticky="ew")
        for c in range(4):
            lbl_frame.columnconfigure(c, weight=1)

        cartes = [
            ("\u263A", "Membres actifs",         str(s["membres"]),             C["bleu"]),
        ]
        for d in devises:
            cartes.append(("\u25C7", f"Épargnes {d}",
                           f"{s['epargnes'].get(d,0):,.0f}", C["vert"]))
        for d in devises:
            cartes.append(("\u25B6", f"Crédit actif {d}",
                           f"{s['credits_actifs'].get(d,0):,.0f}", "#7D6608"))
        for d in devises:
            cartes.append(("\u25C0", f"Remboursé {d}",
                           f"{s['rembs'].get(d,0):,.0f}", "#6C3483"))
        cartes += [
            ("\u26A0", "Crédits en retard",        str(s["retards"]),             C["rouge"]),
            ("\u25A0", "Sessions ouvertes",        str(s["sessions"]),            "#1A5276"),
            ("\u25CF", "Solde net",                f"{s['solde']:,.0f}",
             C["vert"] if s["solde"] >= 0 else C["rouge"]),
            ("\u25CB", "Membres sans crédit",      str(s["sans_credit"]),         "#117A65"),
        ]
        for i, (icone, titre, valeur, coul) in enumerate(cartes):
            r, c = divmod(i, 4)
            self._carte(icone, titre, valeur, coul, lbl_frame, r, c)

        # ── Ligne 2 : Graphiques ──
        charts = tk.Frame(self.corps, bg=C["gris"])
        charts.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        charts.columnconfigure(0, weight=1)
        charts.columnconfigure(1, weight=1)

        # Bar chart : épargnes vs crédit vs remboursé (par devise)
        bar_box = tk.Frame(charts, bg=C["blanc"], highlightbackground=C["gris_f"],
                           highlightthickness=1)
        bar_box.grid(row=0, column=0, padx=(0, 6), sticky="nsew")
        tk.Label(bar_box, text="Vue financière", bg=C["blanc"],
                 fg=C["texte"], font=(FONT, 10, "bold"), anchor="w").pack(
                     fill="x", padx=12, pady=(8, 0))
        bar_canvas = tk.Canvas(bar_box, bg=C["blanc"], highlightthickness=0, height=190)
        bar_canvas.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        series_bar = []
        for d in devises:
            series_bar.append((f"Épargnes {d}", s["epargnes"].get(d, 0), C["vert"]))
        for d in devises:
            series_bar.append((f"Crédit {d}", s["credits_actifs"].get(d, 0), "#7D6608"))
        for d in devises:
            series_bar.append((f"Remb. {d}", s["rembs"].get(d, 0), "#6C3483"))
        series_bar.append(("Solde net", max(s["solde"], 0), C["bleu_clair"]))
        ChartEngine.bar(bar_canvas, series_bar)

        # Pie chart : répartition des crédits
        pie_box = tk.Frame(charts, bg=C["blanc"], highlightbackground=C["gris_f"],
                           highlightthickness=1)
        pie_box.grid(row=0, column=1, padx=(6, 0), sticky="nsew")
        tk.Label(pie_box, text="Statut des crédits", bg=C["blanc"],
                 fg=C["texte"], font=(FONT, 10, "bold"), anchor="w").pack(
                     fill="x", padx=12, pady=(8, 0))
        credits_actifs = s["credits_actifs_count"]
        nb_soldes = self.db.valeur(
            "SELECT COUNT(*) FROM credit c JOIN membre m ON c.membre_id=m.id"
            " WHERE m.avec_id=? AND c.statut='solde'", (self.avec_id,)) or 0
        nb_retards = s["retards"]
        pie_canvas = tk.Canvas(pie_box, bg=C["blanc"], highlightthickness=0, height=190)
        pie_canvas.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        ChartEngine.pie(pie_canvas, [
            ("Actifs",  credits_actifs, C["bleu_clair"]),
            ("Retard",  nb_retards,     C["rouge"]),
            ("Soldés",  nb_soldes,      C["vert"]),
        ])

        # ── Ligne 3 : Journal ──
        jf = ttk.LabelFrame(self.corps, text="Journal des 20 dernières actions", padding=6)
        jf.grid(row=2, column=0, sticky="ew", padx=0, pady=(12, 4))
        cols = ("Horodatage", "Utilisateur", "Action", "Détails")
        tv, f = treeview(jf, cols, [130, 100, 120, 400])
        f.pack(fill="both", expand=True)
        logs = self.db.tous(
            "SELECT ts,login,action,details FROM audit_log ORDER BY id DESC LIMIT 20")
        for i, l in enumerate(logs):
            tag = "p" if i % 2 == 0 else "i"
            tv.insert("", "end", values=(l["ts"], l["login"] or "—",
                                         l["action"], l["details"] or ""), tags=(tag,))

        # Molette active sur tout le tableau de bord ; retour en haut
        self._lier_molette()
        self.canvas.yview_moveto(0)

    def _carte(self, icone, titre, valeur, couleur, parent, row, col):
        c = tk.Frame(parent, bg=couleur)
        c.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")
        tk.Label(c, text=icone, font=(FONT, 14),
                 bg=couleur, fg=C["blanc"]).pack(padx=14, pady=(10, 0))
        tk.Label(c, text=valeur, font=(FONT, 17, "bold"),
                 bg=couleur, fg=C["blanc"]).pack(padx=14, pady=(2, 2))
        tk.Label(c, text=titre, font=(FONT, 9),
                 bg=couleur, fg=C["blanc"]).pack(padx=14, pady=(0, 10))

    def _stats(self):
        db, aid = self.db, self.avec_id
        membres = db.valeur(
            "SELECT COUNT(*) FROM membre WHERE statut='actif' AND avec_id=?", (aid,)) or 0
        epargnes = {r["devise"] or DEVISE_DEFAUT: r["t"] for r in db.tous(
            "SELECT e.devise AS devise, SUM(e.montant) AS t FROM epargne e"
            " JOIN membre m ON e.membre_id=m.id WHERE m.avec_id=? AND e.annule=0"
            " GROUP BY e.devise", (aid,))}
        credits_a = {r["devise"] or DEVISE_DEFAUT: r["t"] for r in db.tous(
            "SELECT c.devise AS devise, SUM(c.montant_total-c.rembourse) AS t"
            " FROM credit c JOIN membre m ON c.membre_id=m.id"
            " WHERE m.avec_id=? AND c.statut IN ('actif','en_retard')"
            " GROUP BY c.devise", (aid,))}
        credits_actifs_count = db.valeur(
            "SELECT COUNT(*) FROM credit c JOIN membre m ON c.membre_id=m.id"
            " WHERE m.avec_id=? AND c.statut='actif'", (aid,)) or 0
        rembs = {r["devise"] or DEVISE_DEFAUT: r["t"] for r in db.tous(
            "SELECT r.devise AS devise, SUM(r.montant_total) AS t"
            " FROM remboursement r JOIN membre m ON r.membre_id=m.id"
            " WHERE m.avec_id=? AND r.annule=0 GROUP BY r.devise", (aid,))}
        retards = db.valeur(
            "SELECT COUNT(*) FROM credit c JOIN membre m ON c.membre_id=m.id"
            " WHERE m.avec_id=? AND c.statut='en_retard'", (aid,)) or 0
        sessions = db.valeur(
            "SELECT COUNT(*) FROM session WHERE avec_id=? AND statut='ouverte'", (aid,)) or 0
        sans_c = db.valeur(
            "SELECT COUNT(*) FROM membre m WHERE avec_id=? AND statut='actif'"
            " AND id NOT IN (SELECT DISTINCT membre_id FROM credit WHERE statut IN ('actif','en_retard'))",
            (aid,)) or 0
        epid = {}; pid = {}
        for d in set(list(epargnes) + list(credits_a)):
            epid[d] = epargnes.get(d, 0)
            pid[d] = credits_a.get(d, 0)
        solde = sum(epid.values()) - sum(pid.values())
        return dict(membres=membres, epargnes=epid, credits_actifs=pid,
                    credits_actifs_count=credits_actifs_count,
                    rembs=rembs, retards=retards, sessions=sessions,
                    solde=solde, sans_credit=sans_c)


# ════════════════════════════════════════════════════════════════
#  MEMBRES
# ════════════════════════════════════════════════════════════════

def _soldes_membres(db, avec_id):
    """Soldes épargne et crédit actifs par membre et par devise (pré-agrégés)."""
    ep, cr = {}, {}
    for r in db.tous("""
            SELECT m.id, e.devise, SUM(e.montant) AS t FROM epargne e
            JOIN membre m ON e.membre_id=m.id
            WHERE m.avec_id=? AND e.annule=0
            GROUP BY m.id, e.devise""", (avec_id,)):
        ep[(r["id"], r["devise"] or DEVISE_DEFAUT)] = r["t"]
    for r in db.tous("""
            SELECT m.id, c.devise, SUM(c.montant_total-c.rembourse) AS t
            FROM credit c JOIN membre m ON c.membre_id=m.id
            WHERE m.avec_id=? AND c.statut IN ('actif','en_retard')
            GROUP BY m.id, c.devise""", (avec_id,)):
        cr[(r["id"], r["devise"] or DEVISE_DEFAUT)] = r["t"]
    return ep, cr


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
        for txt, cmd, st, perm in [
            ("+ Ajouter",  self.ajouter,  "Vert.TButton",  "members.create"),
            ("Modifier",   self.modifier, "Bleu.TButton",  "members.edit"),
            ("Détail",     self.detail,   "TButton",       "members.view"),
            ("Actualiser", self.actualiser,"TButton",      "members.view"),
        ]:
            if not self.auth.permis(perm):
                continue
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
                "Épargne","Crédit actif","Statut","Adhésion")
        lrg  = [40, 90, 165, 100, 50, 130, 130, 75, 95]
        self.tv, f = treeview(self, cols, lrg)
        f.grid(row=2, column=0, sticky="nsew", padx=12, pady=4)
        self.tv.bind("<Double-1>", lambda e: self.detail())

        # Résumé
        self.v_res = tk.StringVar()
        ttk.Label(self, textvariable=self.v_res,
                  font=(FONT, 10, "bold")).grid(row=3, column=0, pady=6)

    def actualiser(self):
        for it in self.tv.get_children():
            self.tv.delete(it)
        terme = (self.v_rech.get() if hasattr(self, "v_rech") else "").strip().lower()
        membres = self.db.tous("""
            SELECT m.id, m.numero, m.nom, m.prenom, m.telephone, m.nb_parts, m.statut, m.date_adhesion
            FROM membre m WHERE m.avec_id=? ORDER BY m.nom, m.prenom
        """, (self.avec_id,))
        ep, cr = _soldes_membres(self.db, self.avec_id)

        totaux = {}
        nb = 0
        for i, m in enumerate(membres):
            nc = f"{m['nom']} {m['prenom'] or ''}".strip()
            if terme and terme not in (nc + (m["telephone"] or "")).lower():
                continue
            mes_ep = {d: v for (mid, d), v in ep.items() if mid == m["id"]}
            mes_cr = {d: v for (mid, d), v in cr.items() if mid == m["id"]}
            lab_ep = "  |  ".join(f"{v:,.0f} {d}" for d, v in sorted(mes_ep.items())) \
                if mes_ep else "—"
            lab_cr = "  |  ".join(f"{v:,.0f} {d}" for d, v in sorted(mes_cr.items())) \
                if mes_cr else "—"
            tag = "rouge" if m["statut"] != "actif" else ("p" if i%2==0 else "i")
            self.tv.insert("", "end", iid=str(m["id"]), tags=(tag,), values=(
                m["id"], m["numero"] or "—", nc, m["telephone"] or "—",
                m["nb_parts"], lab_ep, lab_cr,
                m["statut"].upper(), m["date_adhesion"] or "—"))
            for d, v in mes_ep.items():
                totaux[d] = totaux.get(d, 0) + v
            nb += 1
        aff = "  ·  ".join(f"{v:,.0f} {k}" for k, v in sorted(totaux.items()))
        self.v_res.set(f"{nb} membre(s) affiché(s)  |  Épargnes totales : {aff or '0'}")

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
        centrer(self, 450, 530)
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

        choix_type = [(lib, code) for code, lib in _LIBELLES_COMPTE.items()]
        self.v_type = tk.StringVar(
            value=next((lib for lib, code in choix_type
                        if code == m.get("type_compte")), _LIBELLES_COMPTE["epargne"]))
        ttk.Label(frm, text="Type de compte").grid(
            row=r2+1, column=0, sticky="e", padx=(0,8), pady=5)
        ttk.Combobox(frm, textvariable=self.v_type,
                     values=[lib for lib, _c in choix_type],
                     state="readonly", width=26).grid(
            row=r2+1, column=1, sticky="ew", pady=5)

        bf = ttk.Frame(frm)
        bf.grid(row=r2+2, column=0, columnspan=2, pady=16)
        btn(bf, "Enregistrer", self._sauver, "Vert.TButton").pack(side="left", padx=8)
        btn(bf, "Annuler", self.destroy).pack(side="left", padx=8)

    def _sauver(self):
        try:
            if self.m:
                self.auth.exiger("members.edit", contexte="modification membre")
            else:
                self.auth.exiger("members.create", contexte="création membre")
            nom = self.vs["nom"].get().strip()
            if not nom:
                raise ValueError("Le nom est obligatoire.")
            nb  = int(self.vs["nb_parts"].get().strip() or 1)
            if nb < 1:
                raise ValueError("Le nombre de parts doit être >= 1.")
            dt  = Finance.valider_date(self.vs["date_adhesion"].get())
            code_type = next(
                (code for code, lib in _LIBELLES_COMPTE.items()
                 if lib == self.v_type.get()), "epargne")
            d = dict(
                nom=nom,
                prenom=self.vs["prenom"].get().strip() or None,
                telephone=self.vs["telephone"].get().strip() or None,
                adresse=self.vs["adresse"].get().strip() or None,
                numero=self.vs["numero"].get().strip() or None,
                nb_parts=nb,
                date_adhesion=dt.isoformat(),
                statut=self.v_statut.get(),
                type_compte=code_type,
                notes=self.vs["notes"].get().strip() or None,
                avec_id=self.avec_id,
            )
            if self.m:
                self.db.exec("""
                    UPDATE membre SET nom=:nom,prenom=:prenom,telephone=:telephone,
                    adresse=:adresse,numero=:numero,nb_parts=:nb_parts,
                    date_adhesion=:date_adhesion,statut=:statut,
                    type_compte=:type_compte,notes=:notes
                    WHERE id=:id
                """, {**d, "id": self.m["id"]})
                self.db.audit(self.auth.uid, self.auth.ulogin, "MODIFIER_MEMBRE",
                              "membre", self.m["id"])
            else:
                cur = self.db.exec("""
                    INSERT INTO membre(avec_id,nom,prenom,telephone,adresse,numero,
                    nb_parts,date_adhesion,statut,type_compte,notes)
                    VALUES(:avec_id,:nom,:prenom,:telephone,:adresse,:numero,
                    :nb_parts,:date_adhesion,:statut,:type_compte,:notes)
                """, d)
                self.db.audit(self.auth.uid, self.auth.ulogin, "AJOUTER_MEMBRE",
                              "membre", cur.lastrowid, {"nom": nom})
            self.db.commit()
            if self.cb:
                self.cb()
            self.destroy()
        except (PermissionError, ValueError, sqlite3.Error) as e:
            messagebox.showerror("Erreur", str(e), parent=self)


class DlgDetailMembre(tk.Toplevel):
    def __init__(self, parent, db, m):
        super().__init__(parent)
        self.db = db; self.m = m
        self.title(f"Dossier — {m['nom']} {m.get('prenom') or ''}")
        centrer(self, 720, 600)
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
            ("Type de compte", _libelle_compte(self.m.get("type_compte"))),
            ("Adhésion",       self.m.get("date_adhesion") or "—"),
            ("Statut",         (self.m.get("statut") or "").upper()),
            ("Notes",          self.m.get("notes") or "—"),
        ]):
            ttk.Label(fi, text=f"{lbl} :", font=(FONT, 10, "bold"), background=C["gris"]).grid(
                row=r, column=0, sticky="e", padx=(0, 14), pady=4)
            ttk.Label(fi, text=val).grid(row=r, column=1, sticky="w", pady=4)

        devises_ep = [r["devise"] for r in self.db.tous(
            "SELECT DISTINCT devise FROM epargne WHERE membre_id=? AND annule=0",
            (self.m["id"],))] or [DEVISE_DEFAUT]
        lib_ep = "  ·  ".join(
            f"{Finance.solde_epargne(self.db, self.m['id'], d):,.0f} {d}"
            for d in sorted(set(devises_ep)))
        ttk.Label(fi, text=f"Épargne totale : {lib_ep}",
                  font=(FONT, 12, "bold"), foreground=C["vert"],
                  background=C["gris"]).grid(row=9, column=0, columnspan=2, pady=10)
        dev_cr = [r["devise"] for r in self.db.tous(
            "SELECT DISTINCT devise FROM credit WHERE membre_id=?", (self.m["id"],))]
        lib_cr = "  ·  ".join(
            f"{Finance.solde_compte(self.db, self.m['id'], 'credit', d):,.0f} {d}"
            for d in dev_cr) or "0"
        has_debt = any(Finance.solde_compte(self.db, self.m['id'], 'credit', d) > 0
                       for d in dev_cr)
        ttk.Label(fi, text=f"Solde crédit actif : {lib_cr}",
                  font=(FONT, 10, "bold"),
                  foreground=C["rouge"] if has_debt else C["vert"],
                  background=C["gris"]).grid(row=10, column=0, columnspan=2, pady=2)

        # ─ Épargnes ─
        fe = ttk.Frame(nb)
        nb.add(fe, text="  Épargnes  ")
        cols = ("Date", "Type", "Montant", "Devise", "Description", "Statut")
        tv_e, frm_e = treeview(fe, cols, [140, 90, 110, 65, 220, 70])
        frm_e.pack(fill="both", expand=True, padx=4, pady=4)
        eps = self.db.tous(
            "SELECT date_op,type,montant,devise,description FROM epargne"
            " WHERE membre_id=? AND annule=0 ORDER BY date_op DESC", (self.m["id"],))
        for i, e in enumerate(eps):
            tv_e.insert("", "end", tags=("p" if i%2==0 else "i",), values=(
                e["date_op"], e["type"], f"{e['montant']:,.0f}",
                e["devise"] or DEVISE_DEFAUT,
                e["description"] or "", "✓"))

        # ─ Crédits ─
        fc = ttk.Frame(nb)
        nb.add(fc, text="  Crédits  ")
        cols2 = ("Octroi","Type","Principal","Intérêt","Total","Remboursé","Solde","Devise","Échéance","Statut")
        tv_c, frm_c = treeview(fc, cols2, [100,110,100,90,100,100,100,60,100,90])
        frm_c.pack(fill="both", expand=True, padx=4, pady=4)
        creds = self.db.tous(
            "SELECT date_octroi,principal,montant_interet,montant_total,rembourse,"
            "date_echeance,statut,devise,type_credit FROM credit WHERE membre_id=? "
            "ORDER BY date_octroi DESC",
            (self.m["id"],))
        for i, c in enumerate(creds):
            solde = c["montant_total"] - c["rembourse"]
            tag = "rouge" if c["statut"]=="en_retard" else ("vert" if c["statut"]=="solde" else ("p" if i%2==0 else "i"))
            tv_c.insert("", "end", tags=(tag,), values=(
                c["date_octroi"], _le_libelle_type_credit(c["type_credit"]),
                f"{c['principal']:,.0f}", f"{c['montant_interet']:,.0f}",
                f"{c['montant_total']:,.0f}", f"{c['rembourse']:,.0f}", f"{solde:,.0f}",
                c["devise"] or DEVISE_DEFAUT,
                c["date_echeance"], c["statut"].upper()))


# ════════════════════════════════════════════════════════════════
#  ÉPARGNES
# ════════════════════════════════════════════════════════════════

def _devises_autorisees(avec):
    """Codes devises autorisées pour une AVEC (colonne JSON ou texte, fallback sûr)."""
    brut = avec.get("devises_autorisees") or ""
    brut = brut.strip()
    if brut.startswith("["):
        try:
            brut = ",".join(json.loads(brut))
        except Exception:
            brut = ""
    codes = [c.strip().upper() for c in brut.split(",") if c.strip().upper() in DEVISES]
    if not codes:
        codes = list(DEVISES_AUTORISEES_DEFAUT)
    dev = (avec.get("devise") or DEVISE_DEFAUT).upper()
    if dev not in codes:
        codes.insert(0, dev)
    return codes


def _types_credit_avec(avec):
    """Types de crédit autorisés pour une AVEC (colonne JSON ou texte)."""
    brut = avec.get("types_credit") or ""
    brut = brut.strip()
    if brut.startswith("["):
        try:
            brut = ",".join(json.loads(brut))
        except Exception:
            brut = ""
    types = [t.strip() for t in brut.split(",") if t.strip() in TYPES_CREDIT]
    return types or list(TYPES_CREDIT_DEFAUT)


def _le_libelle_type_credit(type_):
    """Libellé français d'un type de crédit."""
    return {
        "ordinaire": "Ordinaire",
        "urgence": "Urgence",
        "investissement": "Investissement",
        "autre": "Autre",
    }.get(type_, type_ or "Ordinaire")


_LIBELLES_COMPTE = {
    "epargne": "Compte épargne",
    "courant": "Compte courant",
    "bloque": "Compte bloqué",
    "credit": "Compte crédit",
}


def _libelle_compte(type_compte):
    return _LIBELLES_COMPTE.get(type_compte, type_compte or "—")


def _libelle_statut_compte(statut):
    return {"actif": "Actif", "bloque": "Bloqué",
            "suspendu": "Suspendu"}.get(statut, statut or "—")


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
        for txt, cmd, st, perm in [
            ("+ Enregistrer dépôt", self.ajouter,  "Vert.TButton",   "savings.create"),
            ("Annuler opération",   self.annuler,  "Rouge.TButton",  "savings.cancel"),
            ("Actualiser",          self.actualiser,"TButton",       "savings.view"),
        ]:
            if not self.auth.permis(perm):
                continue
            btn(bar, txt, cmd, st).pack(side="right", padx=3)

        cols = ("ID","Date","Membre","Type","Montant","Devise","Description","Statut")
        lrg  = [40, 140, 180, 90, 120, 70, 220, 70]
        self.tv, f = treeview(self, cols, lrg)
        f.grid(row=1, column=0, sticky="nsew", padx=12, pady=4)

        self.v_res = tk.StringVar()
        ttk.Label(self, textvariable=self.v_res,
                  font=(FONT, 10, "bold")).grid(row=2, column=0, pady=6)

    def actualiser(self):
        for it in self.tv.get_children():
            self.tv.delete(it)
        rows = self.db.tous("""
            SELECT e.id, e.date_op, m.nom, m.prenom, e.type, e.montant,
                   e.devise, e.description, e.annule
            FROM epargne e JOIN membre m ON e.membre_id=m.id
            WHERE m.avec_id=? ORDER BY e.date_op DESC LIMIT 600
        """, (self.avec_id,))
        totaux = {}
        for i, r in enumerate(rows):
            nc  = f"{r['nom']} {r['prenom'] or ''}".strip()
            dev = r["devise"] or DEVISE_DEFAUT
            tag = "rouge" if r["annule"] else ("p" if i%2==0 else "i")
            self.tv.insert("", "end", iid=str(r["id"]), tags=(tag,), values=(
                r["id"], r["date_op"], nc, r["type"],
                f"{r['montant']:,.0f}", dev, r["description"] or "",
                "ANNULÉ" if r["annule"] else "✓"))
            if not r["annule"]:
                totaux[dev] = totaux.get(dev, 0) + r["montant"]
        aff = "  ·  ".join(f"{v:,.0f} {k}" for k, v in sorted(totaux.items()))
        self.v_res.set(f"Total épargnes valides : {aff or '0'}")

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
            self.auth.exiger("savings.cancel", contexte="annulation épargne")
            self.db.exec("UPDATE epargne SET annule=1 WHERE id=?", (int(s),))
            self.db.commit()
            self.db.audit(self.auth.uid, self.auth.ulogin, "ANNULER_EPARGNE", "epargne", int(s))
            self.actualiser()
        except (PermissionError, sqlite3.Error) as e:
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

        self.avec = self.db.un("SELECT * FROM avec WHERE id=?", (self.avec_id,)) or {}

        ttk.Label(frm, text="Membre *").grid(row=1, column=0, sticky="e", padx=(0,8), pady=5)
        self.v_m = tk.StringVar()
        ttk.Combobox(frm, textvariable=self.v_m, values=list(self.mmap.keys()),
                     state="readonly", width=26).grid(row=1, column=1, sticky="ew", pady=5)

        ttk.Label(frm, text="Devise *").grid(row=2, column=0, sticky="e", padx=(0,8), pady=5)
        self.v_dev = tk.StringVar(value=(self.avec.get("devise") or DEVISE_DEFAUT).upper())
        ttk.Combobox(frm, textvariable=self.v_dev,
                     values=_devises_autorisees(self.avec),
                     state="readonly", width=26).grid(row=2, column=1, sticky="ew", pady=5)

        self.v_mt, _ = champ(frm, "Montant *",                 3)
        self.v_dt, _ = champ(frm, "Date (AAAA-MM-JJ) *",       4, date.today().isoformat())

        ttk.Label(frm, text="Type").grid(row=5, column=0, sticky="e", padx=(0,8), pady=5)
        self.v_ty = tk.StringVar(value="ordinaire")
        ttk.Combobox(frm, textvariable=self.v_ty,
                     values=["ordinaire","solidarite","urgence"],
                     state="readonly", width=26).grid(row=5, column=1, sticky="ew", pady=5)

        self.v_dc, _ = champ(frm, "Description", 6)

        bf = ttk.Frame(frm)
        bf.grid(row=7, column=0, columnspan=2, pady=16)
        btn(bf, "Enregistrer", self._sauver, "Vert.TButton").pack(side="left", padx=8)
        btn(bf, "Annuler", self.destroy).pack(side="left", padx=8)

    def _sauver(self):
        try:
            self.auth.exiger("savings.create", contexte="dépôt épargne")
            nom = self.v_m.get()
            if not nom or nom not in self.mmap:
                raise ValueError("Sélectionnez un membre.")
            mid = self.mmap[nom]
            mt = Finance.valider_montant(self.v_mt.get())
            dt = Finance.valider_date(self.v_dt.get())
            devise = self.v_dev.get().strip().upper() or DEVISE_DEFAUT
            if Finance.compte_bloque(self.db, mid, "epargne", devise):
                raise ValueError(
                    f"Opération impossible : le compte épargne {devise} du membre "
                    "est bloqué ou suspendu.")
            cur = self.db.exec("""
                INSERT INTO epargne(membre_id,montant,type,date_op,description,
                                    cree_par,devise)
                VALUES(?,?,?,?,?,?,?)
            """, (mid, mt, self.v_ty.get(), dt.isoformat(),
                  self.v_dc.get().strip() or None, self.auth.uid, devise))
            self.db.commit()
            Finance.impliquer_compte(self.db, self.auth.uid, mid, "epargne",
                                     devise, "depot", mt,
                                     f"Dépôt d'épargne ({nom})")
            self.db.audit(self.auth.uid, self.auth.ulogin, "AJOUTER_EPARGNE",
                          "epargne", cur.lastrowid,
                          {"membre": nom, "montant": mt, "devise": devise})
            membre = self.db.un("SELECT * FROM membre WHERE id=?", (mid,))
            avec   = self.db.un("SELECT * FROM avec WHERE id=?", (self.avec_id,))
            gerer_recu_operation(self, self.auth, self.db, avec, membre,
                                 "EPARGNE", self.v_ty.get(), cur.lastrowid, mt,
                                 {"membre": nom, "montant": mt, "devise": devise,
                                  "date_paiement": dt.isoformat()},
                                 devise=devise)
            if self.cb: self.cb()
            self.destroy()
        except (PermissionError, ValueError, sqlite3.Error) as e:
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
        for txt, cmd, st, perm in [
            ("+ Octroyer crédit", self.ajouter,   "Vert.TButton",   "loans.create"),
            ("Annuler crédit",    self.annuler,   "Rouge.TButton",  "loans.cancel"),
            ("Actualiser",        self.actualiser, "TButton",       "loans.view"),
        ]:
            if not self.auth.permis(perm):
                continue
            btn(bar, txt, cmd, st).pack(side="right", padx=3)

        cols = ("ID","Membre","Type","Principal","Intérêt","Total dû","Remboursé",
            "Solde","Devise","Durée","Échéance","Statut")
        lrg  = [40, 160, 110, 100, 90, 100, 100, 100, 60, 60, 90, 105]
        self.tv, f = treeview(self, cols, lrg)
        f.grid(row=1, column=0, sticky="nsew", padx=12, pady=4)

        self.v_res = tk.StringVar()
        ttk.Label(self, textvariable=self.v_res,
                  font=(FONT, 10, "bold")).grid(row=2, column=0, pady=6)

    def actualiser(self):
        Finance.maj_statuts(self.db)
        for it in self.tv.get_children():
            self.tv.delete(it)
        rows = self.db.tous("""
            SELECT c.id, m.nom, m.prenom, c.principal, c.montant_interet, c.montant_total,
                   c.rembourse, c.duree_mois, c.date_echeance, c.statut, c.devise, c.type_credit
            FROM credit c JOIN membre m ON c.membre_id=m.id
            WHERE m.avec_id=? ORDER BY c.date_octroi DESC
        """, (self.avec_id,))
        totaux = {}
        for i, r in enumerate(rows):
            solde = r["montant_total"] - r["rembourse"]
            nc    = f"{r['nom']} {r['prenom'] or ''}".strip()
            dev   = r["devise"] or DEVISE_DEFAUT
            jr    = Finance.jours_retard(r["date_echeance"])
            statut_aff = r["statut"].upper()
            if r["statut"] == "en_retard":
                statut_aff = f"RETARD ({jr}j)"
            tag = ("rouge" if r["statut"]=="en_retard" else
                   "vert"  if r["statut"]=="solde"     else
                   "p" if i%2==0 else "i")
            self.tv.insert("", "end", iid=str(r["id"]), tags=(tag,), values=(
                r["id"], nc, _le_libelle_type_credit(r["type_credit"]),
                f"{r['principal']:,.0f}", f"{r['montant_interet']:,.0f}",
                f"{r['montant_total']:,.0f}", f"{r['rembourse']:,.0f}", f"{solde:,.0f}",
                dev, f"{r['duree_mois']} mois", r["date_echeance"], statut_aff))
            if r["statut"] in ("actif","en_retard"):
                totaux[dev] = totaux.get(dev, 0) + solde
        aff = "  ·  ".join(f"{v:,.0f} {k}" for k, v in sorted(totaux.items()))
        self.v_res.set(f"Portefeuille crédit actif : {aff or '0'}")

    def ajouter(self):
        DlgCredit(self, self.db, self.auth, self.avec_id, callback=self.actualiser)

    def annuler(self):
        s = self.tv.focus()
        if not s:
            messagebox.showwarning("Sélection", "Sélectionnez un crédit."); return
        cr = self.db.un("SELECT * FROM credit WHERE id=?", (int(s),))
        if not cr:
            return
        if cr["statut"] not in ("actif", "en_retard"):
            messagebox.showwarning("Annulation",
                                   "Ce crédit n'est plus actif (annulé/soldé).")
            return
        if not messagebox.askyesno(
                "Confirmer annulation",
                "Annuler ce crédit ? Le montant reste traçable dans l'historique.\n"
                "Cette action est irréversible.", parent=self):
            return
        try:
            self.auth.exiger("loans.cancel", contexte="annulation crédit")
            self.db.exec("UPDATE credit SET statut='annule' WHERE id=? AND "
                         "statut IN ('actif','en_retard')", (int(s),))
            self.db.commit()
            self.db.audit(self.auth.uid, self.auth.ulogin, "ANNULER_CREDIT",
                          "credit", int(s), {"membre_id": cr["membre_id"]})
            self.actualiser()
        except (PermissionError, sqlite3.Error) as e:
            messagebox.showerror("Erreur", str(e))


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

        self.avec = self.db.un("SELECT * FROM avec WHERE id=?", (self.avec_id,)) or {}

        membres = self.db.tous(
            "SELECT id,nom,prenom FROM membre WHERE avec_id=? AND statut='actif' ORDER BY nom",
            (self.avec_id,))
        self.mmap = {f"{m['nom']} {m['prenom'] or ''}".strip(): m["id"] for m in membres}

        ttk.Label(frm, text="Membre *").grid(row=1, column=0, sticky="e", padx=(0,8), pady=5)
        self.v_m = tk.StringVar()
        ttk.Combobox(frm, textvariable=self.v_m, values=list(self.mmap.keys()),
                     state="readonly", width=26).grid(row=1, column=1, sticky="ew", pady=5)

        ttk.Label(frm, text="Devise *").grid(row=2, column=0, sticky="e", padx=(0,8), pady=5)
        self.v_dev = tk.StringVar(value=(self.avec.get("devise") or DEVISE_DEFAUT).upper())
        ttk.Combobox(frm, textvariable=self.v_dev,
                     values=_devises_autorisees(self.avec),
                     state="readonly", width=26).grid(row=2, column=1, sticky="ew", pady=5)

        ttk.Label(frm, text="Type de crédit *").grid(row=3, column=0, sticky="e", padx=(0,8), pady=5)
        self.type_map = {t: _le_libelle_type_credit(t) for t in _types_credit_avec(self.avec)}
        self.v_ty = tk.StringVar()
        self.cb_ty = ttk.Combobox(frm, textvariable=self.v_ty,
                                  values=[f"{c} — {l}" for c, l in self.type_map.items()],
                                  state="readonly", width=26)
        self.cb_ty.grid(row=3, column=1, sticky="ew", pady=5)
        if self.type_map:
            self.v_ty.set(f"{list(self.type_map.items())[0][0]} — {list(self.type_map.items())[0][1]}")

        self.v_p, _  = champ(frm, "Montant principal *", 4)
        self.v_t, _  = champ(frm, "Taux annuel (ex: 0.10 = 10%) *", 5,
                             str(self.avec.get("taux_interet") or TAUX_INTERET_DEFAUT))
        self.v_d, _  = champ(frm, "Durée (mois) *", 6, "3")
        self.v_dt, _ = champ(frm, "Date d'octroi (AAAA-MM-JJ) *", 7, date.today().isoformat())

        self.v_pen_info = tk.StringVar(
            value=f"Pénalité de retard figée à l'octroi : "
                  f"{float(self.avec.get('taux_penalite') or TAUX_PENALITE_DEFAUT)*100:.2f} %/mois")
        ttk.Label(frm, textvariable=self.v_pen_info, foreground=C["bleu"],
                  font=(FONT, 9, "italic"), background=C["gris"]).grid(
            row=8, column=0, columnspan=2, pady=2)

        self.v_dc, _ = champ(frm, "Description / Motif", 9)

        # Aperçu
        self.v_ap = tk.StringVar()
        ttk.Label(frm, textvariable=self.v_ap, foreground=C["bleu"],
                  font=(FONT, 10, "italic"), background=C["gris"]).grid(
            row=10, column=0, columnspan=2, pady=4)
        for v in (self.v_p, self.v_t, self.v_d):
            v.trace("w", lambda *a: self._apercu())
        self.cb_ty.bind("<<ComboboxSelected>>", lambda e: (self._taux_par_type(), self._apercu()))

        bf = ttk.Frame(frm)
        bf.grid(row=11, column=0, columnspan=2, pady=16)
        btn(bf, "Octroyer", self._sauver, "Vert.TButton").pack(side="left", padx=8)
        btn(bf, "Annuler", self.destroy).pack(side="left", padx=8)

    def _type_selectionne(self):
        typ = self.v_ty.get().split(" — ")[0].strip()
        return typ if typ in TYPES_CREDIT else "ordinaire"

    def _taux_par_type(self):
        with_atuts = self.avec.get("taux_interet") or TAUX_INTERET_DEFAUT
        tax = {
            "ordinaire": with_atuts,
            "urgence": self.avec.get("taux_interet_urgence") or TAUX_INTERET_DEFAUT + 0.05,
            "investissement": self.avec.get("taux_interet_investissement")
                              or with_atuts,
            "autre": with_atuts,
        }
        taux = tax.get(self._type_selectionne(), with_atuts)
        self.v_t.set(str(taux))

    def _apercu(self):
        try:
            p = float(self.v_p.get() or 0)
            t = float(self.v_t.get() or 0)
            d = int(self.v_d.get() or 0)
            if p > 0 and 0 < t <= 1 and d > 0:
                inter = Finance.interet_simple(p, t, d)
                dev   = self.v_dev.get().strip().upper() or DEVISE_DEFAUT
                self.v_ap.set(
                    f"Intérêt : {inter:,.0f} {dev}  |  Total dû : {p+inter:,.0f} {dev}"
                    f"  —  {_le_libelle_type_credit(self._type_selectionne())}")
        except Exception:
            self.v_ap.set("")

    def _sauver(self):
        try:
            self.auth.exiger("loans.create", contexte="octroi crédit")
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
            devise = self.v_dev.get().strip().upper() or DEVISE_DEFAUT
            typ  = self._type_selectionne()
            if Finance.compte_bloque(self.db, mid, "credit", devise):
                raise ValueError(
                    f"Impossible d'octroyer un crédit : le compte crédit {devise} "
                    "du membre est bloqué ou suspendu.")
            taux_pen = self.avec.get("taux_penalite") \
                if self.avec.get("taux_penalite") else TAUX_PENALITE_DEFAUT
            inter = Finance.interet_simple(p, t, dur)
            total = round(p + inter, 2)
            ech   = Finance.date_echeance(do, dur)

            # Vérifier que le membre n'a pas déjà un crédit actif dans la même
            # devise (blocage dur) — les devises restent indépendantes.
            solde_actuel = self.db.valeur(
                "SELECT COALESCE(SUM(montant_total-rembourse),0) FROM credit"
                " WHERE membre_id=? AND devise=? AND statut IN ('actif','en_retard')",
                (mid, devise)) or 0
            if solde_actuel > 0:
                raise ValueError(
                    f"Impossible d'octroyer un nouveau crédit en {devise}.\n"
                    f"Ce membre a déjà {solde_actuel:,.0f} {devise} de crédit actif.\n"
                    "Le crédit actuel doit être soldé avant d'en obtenir un nouveau.")

            cur = self.db.exec("""
                INSERT INTO credit(membre_id,principal,taux,duree_mois,date_octroi,date_echeance,
                montant_interet,montant_total,description,cree_par,devise,type_credit,taux_penalite)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (mid, p, t, dur, do.isoformat(), ech.isoformat(),
                  inter, total, self.v_dc.get().strip() or None, self.auth.uid,
                  devise, typ, taux_pen))
            self.db.commit()
            Finance.impliquer_compte(self.db, self.auth.uid, mid, "credit",
                                     devise, "ajustement", -p,
                                     f"Octroi de crédit {typ}")
            self.db.audit(self.auth.uid, self.auth.ulogin, "OCTROYER_CREDIT",
                          "credit", cur.lastrowid,
                          {"membre": nom, "principal": p, "taux": t,
                           "type": typ, "devise": devise,
                           "echeance": ech.isoformat()})
            messagebox.showinfo("Crédit octroyé",
                f"Crédit enregistré avec succès.\n\n"
                f"Type      : {_le_libelle_type_credit(typ)}\n"
                f"Principal : {p:,.0f} {devise}\n"
                f"Intérêt   : {inter:,.0f} {devise}\n"
                f"Total dû  : {total:,.0f} {devise}\n"
                f"Échéance  : {ech.isoformat()}", parent=self)
            membre = self.db.un("SELECT * FROM membre WHERE id=?", (mid,))
            avec   = self.db.un("SELECT * FROM avec WHERE id=?", (self.avec_id,))
            gerer_recu_operation(self, self.auth, self.db, avec, membre,
                                 "CREDIT", "Octroi de crédit", cur.lastrowid, p,
                                 {"credit_id": cur.lastrowid, "principal": p,
                                  "interet": inter, "solde": total,
                                  "type": typ, "devise": devise,
                                  "date_octroi": do.isoformat()},
                                 devise=devise)
            if self.cb: self.cb()
            self.destroy()
        except (PermissionError, ValueError, sqlite3.Error) as e:
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
        for txt, cmd, st, perm in [
            ("+ Enregistrer paiement", self.ajouter,   "Vert.TButton",   "repayments.create"),
            ("Annuler opération",     self.annuler,    "Rouge.TButton",  "repayments.cancel"),
            ("Actualiser",             self.actualiser, "TButton",       "repayments.view"),
        ]:
            if not self.auth.permis(perm):
                continue
            btn(bar, txt, cmd, st).pack(side="right", padx=3)

        cols = ("ID","Date","Membre","Crédit#","Principal","Intérêt",
                "Pénalité","Total payé","Devise","Description")
        lrg  = [40, 140, 170, 65, 100, 90, 90, 110, 60, 220]
        self.tv, f = treeview(self, cols, lrg)
        f.grid(row=1, column=0, sticky="nsew", padx=12, pady=4)

        self.v_res = tk.StringVar()
        ttk.Label(self, textvariable=self.v_res,
                  font=(FONT, 10, "bold")).grid(row=2, column=0, pady=6)

    def actualiser(self):
        for it in self.tv.get_children():
            self.tv.delete(it)
        rows = self.db.tous("""
            SELECT r.id, r.date_paiement, m.nom, m.prenom, r.credit_id,
                   r.mont_principal, r.mont_interet, r.mont_penalite,
                   r.montant_total, r.devise, r.description, r.annule
            FROM remboursement r JOIN membre m ON r.membre_id=m.id
            WHERE m.avec_id=? ORDER BY r.date_paiement DESC LIMIT 600
        """, (self.avec_id,))
        totaux = {}
        for i, r in enumerate(rows):
            nc  = f"{r['nom']} {r['prenom'] or ''}".strip()
            dev = r["devise"] or DEVISE_DEFAUT
            tag = "rouge" if r["annule"] else ("p" if i%2==0 else "i")
            self.tv.insert("", "end", iid=str(r["id"]), tags=(tag,), values=(
                r["id"], r["date_paiement"], nc, r["credit_id"],
                f"{r['mont_principal']:,.0f}", f"{r['mont_interet']:,.0f}",
                f"{r['mont_penalite']:,.0f}", f"{r['montant_total']:,.0f}", dev,
                r["description"] or ""))
            if not r["annule"]:
                totaux[dev] = totaux.get(dev, 0) + r["montant_total"]
        aff = "  ·  ".join(f"{v:,.0f} {k}" for k, v in sorted(totaux.items()))
        self.v_res.set(f"Total encaissé (remboursements valides) : {aff or '0'}")

    def ajouter(self):
        DlgRemboursement(self, self.db, self.auth, self.avec_id, callback=self.actualiser)

    def annuler(self):
        s = self.tv.focus()
        if not s:
            messagebox.showwarning("Sélection", "Sélectionnez une opération."); return
        rem = self.db.un("SELECT r.*, r.credit_id AS cid FROM remboursement r WHERE id=?",
                         (int(s),))
        if not rem:
            return
        if rem["annule"]:
            messagebox.showwarning("Annulation", "Cette opération est déjà annulée.")
            return
        if not messagebox.askyesno(
                "Confirmer annulation",
                "Annuler ce remboursement ? Le crédit sera recalculé.\n"
                "Cette action reste traçable.", parent=self):
            return
        try:
            self.auth.exiger("repayments.cancel", contexte="annulation remboursement")
            self.db.exec("BEGIN")
            cid = rem["cid"]
            self.db.exec("UPDATE remboursement SET annule=1 WHERE id=?", (int(s),))
            self.db.exec("""
                UPDATE credit SET rembourse=COALESCE(
                  (SELECT SUM(montant_total) FROM remboursement
                   WHERE credit_id=? AND annule=0), 0)
                WHERE id=?
            """, (cid, cid))
            self.db.commit()
            self.db.audit(self.auth.uid, self.auth.ulogin, "ANNULER_REMBOURSEMENT",
                          "remboursement", int(s), {"credit_id": cid})
            Finance.maj_statuts(self.db)
            self.actualiser()
        except (PermissionError, sqlite3.Error) as e:
            try:
                self.db.rollback()
            except Exception:
                pass
            messagebox.showerror("Erreur", str(e))


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
                  font=(FONT, 9, "italic"), background=C["gris"]).grid(
            row=3, column=0, columnspan=2, pady=2)

        self.v_mt, _  = champ(frm, "Montant payé *", 4)
        self.v_dt, _  = champ(frm, "Date paiement (AAAA-MM-JJ) *", 5, date.today().isoformat())
        self.v_dc, _  = champ(frm, "Description", 6)

        # Pénalité
        self.v_pen = tk.StringVar()
        ttk.Label(frm, textvariable=self.v_pen, foreground=C["rouge"],
                  font=(FONT, 10, "bold"), background=C["gris"]).grid(
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
                   date_octroi, date_echeance, statut, devise, taux_penalite
            FROM credit WHERE membre_id=? AND statut IN ('actif','en_retard')
        """, (mid,))
        self.crmap = {}
        for c in creds:
            solde = c["montant_total"] - c["rembourse"]
            dev   = c["devise"] or DEVISE_DEFAUT
            lbl = f"Crédit #{c['id']} — Solde: {solde:,.0f} {dev} — Éch: {c['date_echeance']}"
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
        dev   = c["devise"] or DEVISE_DEFAUT
        self.v_det.set(
            f"Total dû: {c['montant_total']:,.0f} {dev} | Remboursé: {c['rembourse']:,.0f} "
            f"{dev} | Solde: {solde:,.0f} {dev}")
        if jr > 0:
            taux_pen = c.get("taux_penalite") or TAUX_PENALITE_DEFAUT
            pen = Finance.penalite(solde, taux_pen, jr)
            self.v_pen.set(f"Retard : {jr} jours — Pénalité estimée : {pen:,.0f} {dev} "
                           f"({taux_pen*100:.2f} %/mois)")
        else:
            self.v_pen.set("")

    def _sauver(self):
        try:
            self.auth.exiger("repayments.create", contexte="remboursement")
            if not self._cr:
                raise ValueError("Sélectionnez un crédit.")
            c    = self._cr
            mt   = Finance.valider_montant(self.v_mt.get())
            dt   = Finance.valider_date(self.v_dt.get())
            solde = c["montant_total"] - c["rembourse"]
            dev   = c["devise"] or DEVISE_DEFAUT
            taux_pen = c.get("taux_penalite") or TAUX_PENALITE_DEFAUT

            if mt > solde * 2:
                if not messagebox.askyesno("Attention",
                    f"Le montant payé ({mt:,.0f} {dev}) dépasse largement le solde "
                    f"({solde:,.0f} {dev}).\nContinuer ?",
                    parent=self):
                    return

            jr  = Finance.jours_retard(c["date_echeance"])
            pen = Finance.penalite(solde, taux_pen, jr) if jr > 0 else 0

            # Imputation : pénalité → intérêt → principal (basé sur montants restants)
            pen_pay  = min(pen, mt)
            reste    = mt - pen_pay
            # Calculer les intérêts et principal restants à payer
            ratio_total = c["montant_total"] if c["montant_total"] > 0 else 1
            interet_restant = max(0, c["montant_interet"] * (1 - c["rembourse"] / ratio_total))
            principal_restant = max(0, c["montant_total"] - c["rembourse"] - interet_restant)
            total_restant = interet_restant + principal_restant
            if total_restant > 0:
                ratio_i = interet_restant / total_restant
            else:
                ratio_i = 0
            int_pay  = round(reste * ratio_i, 2)
            prin_pay = round(reste - int_pay, 2)

            mid = self.db.valeur("SELECT membre_id FROM credit WHERE id=?", (c["id"],))
            self.db.exec("BEGIN")
            try:
                cur = self.db.exec("""
                    INSERT INTO remboursement
                    (credit_id,membre_id,mont_principal,mont_interet,mont_penalite,
                     montant_total,date_paiement,description,cree_par,devise)
                    VALUES(?,?,?,?,?,?,?,?,?,?)
                """, (c["id"], mid, prin_pay, int_pay, pen_pay,
                      mt, dt.isoformat(), self.v_dc.get().strip() or None,
                      self.auth.uid, dev))

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
                          {"credit_id": c["id"], "montant": mt, "devise": dev})
            membre = self.db.un("SELECT * FROM membre WHERE id=?", (mid,))
            avec   = self.db.un("SELECT * FROM avec WHERE id=?", (self.avec_id,))
            gerer_recu_operation(
                self, self.auth, self.db, avec, membre,
                "REMBOURSEMENT", "Remboursement de crédit", cur.lastrowid, mt,
                {"credit_id": c["id"], "montant_impute": mt,
                 "penalite": pen_pay, "interet": int_pay, "principal": prin_pay,
                 "solde": nouveau_remb, "date_paiement": dt.isoformat(),
                 "devise": dev},
                devise=dev)
            if self.cb: self.cb()
            self.destroy()
        except (PermissionError, ValueError, sqlite3.Error) as e:
            messagebox.showerror("Erreur", str(e), parent=self)


# ════════════════════════════════════════════════════════════════
#  COMPTES MEMBRES
# ════════════════════════════════════════════════════════════════

class OngletComptes(ttk.Frame):
    """Comptes membres (épargne, courant, bloqué, crédit) par devise :
    soldes, statuts (actif / bloqué / suspendu), historique des événements."""

    def __init__(self, parent, db, auth, avec_id=1):
        super().__init__(parent)
        self.db = db; self.auth = auth; self.avec_id = avec_id
        self.columnconfigure(0, weight=1); self.rowconfigure(2, weight=1)
        self._ui(); self.actualiser()

    def _ui(self):
        bar = ttk.Frame(self)
        bar.grid(row=0, column=0, sticky="ew", padx=12, pady=8)
        ttk.Label(bar, text="Comptes membres", style="Titre.TLabel").pack(side="left")
        self._btns = {}
        for txt, cmd, st, perm in [
            ("Bloquer",     self._bloquer,       "Rouge.TButton",  "accounts.block"),
            ("Débloquer",   self._debloquer,     "Vert.TButton",   "accounts.block"),
            ("Suspendre",   self._suspendre,     "Rouge.TButton",  "accounts.block"),
            ("Réactiver",   self._reactiver,     "Vert.TButton",   "accounts.block"),
            ("Détail",      self.detail,         "Bleu.TButton",   "accounts.view"),
            ("Actualiser",  self.actualiser,     "TButton",        "accounts.view"),
        ]:
            if not self.auth.permis(perm):
                continue
            self._btns[txt] = btn(bar, txt, cmd, st)
            self._btns[txt].pack(side="right", padx=3)

        rech = ttk.Frame(self)
        rech.grid(row=1, column=0, sticky="ew", padx=12, pady=2)
        ttk.Label(rech, text="Rechercher :").pack(side="left")
        self.v_rech = tk.StringVar()
        self.v_rech.trace("w", lambda *a: self.actualiser())
        ttk.Entry(rech, textvariable=self.v_rech, width=30).pack(side="left", padx=8)
        ttk.Label(rech, text="Devise :").pack(side="left", padx=(12, 0))
        self.v_dev = tk.StringVar(value="TOUTES")
        self.cb_dev = ttk.Combobox(rech, textvariable=self.v_dev,
                                   state="readonly", width=8)
        self.cb_dev["values"] = ["TOUTES"] + list(DEVISES)
        self.cb_dev.pack(side="left", padx=6)
        self.cb_dev.bind("<<ComboboxSelected>>", lambda e: self.actualiser())

        cols = ("Compte#","Membre","Type de compte","Devise","Solde",
                "Statut","Description","Créé le")
        lrg  = [60, 180, 130, 60, 120, 90, 220, 140]
        self.tv, f = treeview(self, cols, lrg)
        f.grid(row=2, column=0, sticky="nsew", padx=12, pady=4)
        self.tv.bind("<Double-1>", lambda e: self.detail())

        self.v_res = tk.StringVar()
        ttk.Label(self, textvariable=self.v_res,
                  font=(FONT, 10, "bold")).grid(row=3, column=0, pady=6)
        self.tv.bind("<<TreeviewSelect>>", self._actualiser_boutons)

    def _acompte(self):
        s = self.tv.focus()
        if not s:
            return None
        return self.db.un("SELECT * FROM compte WHERE id=?", (int(s),))

    def _sel(self):
        c = self._acompte()
        if not c:
            messagebox.showwarning("Sélection",
                                   "Sélectionnez un compte membre.")
        return c

    def actualiser(self):
        for it in self.tv.get_children():
            self.tv.delete(it)
        terme = (self.v_rech.get() if hasattr(self, "v_rech") else "").strip().lower()
        devf  = (self.v_dev.get() if hasattr(self, "v_dev") else "").strip()
        rows = self.db.tous("""
            SELECT c.*, m.nom, m.prenom FROM compte c JOIN membre m ON c.membre_id=m.id
            WHERE m.avec_id=? ORDER BY m.nom, c.type_compte, c.devise
        """, (self.avec_id,))
        self.acomptes = {}
        nb = 0
        for i, c in enumerate(rows):
            nc = f"{c['nom']} {c['prenom'] or ''}".strip()
            if terme and terme not in nc.lower():
                continue
            if devf and devf != "TOUTES" and (c["devise"] or DEVISE_DEFAUT) != devf:
                continue
            solde = Finance.solde_compte(self.db, c["membre_id"], c["type_compte"],
                                         c["devise"] or DEVISE_DEFAUT)
            tag = ("rouge" if c["statut"] == "bloque" else
                   "gris" if c["statut"] == "suspendu" else
                   "vert" if solde > 0 else
                   "p" if i % 2 == 0 else "i")
            self.tv.insert("", "end", iid=str(c["id"]), tags=(tag,), values=(
                c["id"], nc, _libelle_compte(c["type_compte"]),
                c["devise"] or DEVISE_DEFAUT,
                f"{solde:,.0f}" if solde else "0",
                _libelle_statut_compte(c["statut"]),
                c["description"] or "", c["cree_le"]))
            self.acomptes[c["id"]] = c
            nb += 1
        self.v_res.set(f"{nb} compte(s) affiché(s)")
        self._actualiser_boutons()

    def _actualiser_boutons(self, ev=None):
        """Active/désactive les boutons selon le statut du compte sélectionné.
        Les comptes épargne/crédit dérivés ne sont pas gérables ici : leurs
        mouvements passent par les onglets Épargnes/Crédits."""
        for nom, cible in (("Bloquer", "bloque"), ("Débloquer", "actif"),
                           ("Suspendre", "suspendu"), ("Réactiver", "actif")):
            b = self._btns.get(nom)
            if not b:
                continue
            c = self.tv.focus()
            bloquable = (self.acomptes.get(int(c)) if c else None)
            elig = False
            if isinstance(bloquable, dict):
                st = bloquable.get("statut")
                if nom in ("Bloquer", "Débloquer"):
                    elig = st == "actif" and nom == "Bloquer" or \
                           st == "bloque" and nom == "Débloquer"
                else:
                    elig = (st in ("actif", "bloque") and nom == "Suspendre") or \
                           (st == "suspendu" and nom == "Réactiver")
            b.config(state=("normal" if elig else "disabled"))

    def _action_statut(self, cible, evenement, lib_action):
        c = self._sel()
        if not c:
            return
        if c["statut"] == cible:
            messagebox.showwarning("Compte",
                f"Ce compte est déjà {_libelle_statut_compte(cible).lower()}.")
            return
        try:
            self.auth.exiger("accounts.block",
                             contexte=f"{lib_action} du compte #{c['id']}")
        except PermissionError as e:
            messagebox.showerror("Erreur", str(e)); return
        if not messagebox.askyesno(
                "Confirmer",
                f"{lib_action} le compte {_libelle_compte(c['type_compte'])} "
                f"({c['devise']}) de « {c['nom']} {c['prenom'] or ''} » ?\n\n"
                f"Statut actuel : {_libelle_statut_compte(c['statut'])} "
                f"→ {_libelle_statut_compte(cible)}.", parent=self):
            return
        try:
            self.db.exec("UPDATE compte SET statut=? WHERE id=?", (cible, c["id"]))
            self.db.exec("INSERT INTO compte_evenement(compte_id,type_evenement,note,cree_par)"
                         " VALUES(?,?,?,?)",
                         (c["id"], evenement, f"Action {lib_action}", self.auth.uid))
            self.db.commit()
            self.db.audit(self.auth.uid, self.auth.ulogin, "MODIFIER_COMPTE",
                          "compte", c["id"],
                          {"membre_id": c["membre_id"],
                           "type_compte": c["type_compte"], "devise": c["devise"],
                           "avait": c["statut"], "a": cible})
            self.actualiser()
        except sqlite3.Error as e:
            messagebox.showerror("Erreur", str(e))

    def _bloquer(self):   self._action_statut("bloque",   "BLOCAGE",   "Bloquer")
    def _debloquer(self): self._action_statut("actif",    "DEBLOCAGE", "Débloquer")
    def _suspendre(self): self._action_statut("suspendu", "SUSPENSION","Suspendre")
    def _reactiver(self): self._action_statut("actif",    "REACTIVATION","Réactiver")

    def detail(self):
        c = self._sel()
        if not c:
            return
        m = self.db.un("SELECT * FROM membre WHERE id=?", (c["membre_id"],))
        dlg = tk.Toplevel(self)
        dlg.title(f"Compte #{c['id']} — {m['nom']} {m.get('prenom') or ''}")
        dlg.geometry("600x420")
        dlg.grab_set()
        nb = ttk.Notebook(dlg)
        nb.pack(fill="both", expand=True, padx=8, pady=8)

        finfos = ttk.Frame(nb, padding=14)
        nb.add(finfos, text="  Informations  ")
        solde = Finance.solde_compte(self.db, c["membre_id"], c["type_compte"],
                                     c["devise"] or DEVISE_DEFAUT)
        lignes = [
            ("Membre",        f"{m['nom']} {m.get('prenom') or ''}".strip()),
            ("Type de compte", _libelle_compte(c["type_compte"])),
            ("Devise",         c["devise"] or DEVISE_DEFAUT),
            ("Solde",          f"{solde:,.0f} {c['devise'] or DEVISE_DEFAUT}"),
            ("Statut",         _libelle_statut_compte(c["statut"])),
            ("Description",    c["description"] or "—"),
            ("Créé le",        c["cree_le"]),
        ]
        for r, (lbl, val) in enumerate(lignes):
            ttk.Label(finfos, text=f"{lbl} :", font=(FONT, 10, "bold")).grid(
                row=r, column=0, sticky="e", padx=(0, 12), pady=3)
            ttk.Label(finfos, text=val).grid(row=r, column=1, sticky="w", pady=3)

        fev = ttk.Frame(nb)
        nb.add(fev, text="  Événements  ")
        tv_e, f_e = treeview(fev, ("Date", "Événement", "Note", "Par"), [140, 110, 260, 90])
        f_e.pack(fill="both", expand=True, padx=4, pady=4)
        evts = self.db.tous("""
            SELECT ce.cree_le, ce.type_evenement, ce.note, u.nom
            FROM compte_evenement ce LEFT JOIN utilisateur u ON ce.cree_par=u.id
            WHERE ce.compte_id=? ORDER BY ce.id DESC""", (c["id"],))
        for i, ev in enumerate(evts):
            tv_e.insert("", "end", tags=("p" if i % 2 == 0 else "i",), values=(
                ev["cree_le"], ev["type_evenement"], ev["note"] or "",
                ev["nom"] or "—"))

        fm = ttk.Frame(nb)
        nb.add(fm, text="  Mouvements (courant / bloqué)  ")
        tv_m, f_m = treeview(fm, ("Date", "Type", "Montant", "Note"), [140, 90, 110, 260])
        f_m.pack(fill="both", expand=True, padx=4, pady=4)
        if c["type_compte"] in ("courant", "bloque"):
            mvts = self.db.tous("""
                SELECT cm.cree_le, cm.type_mouvement, cm.montant, cm.note
                FROM compte_mouvement cm WHERE cm.compte_id=? ORDER BY cm.id DESC
            """, (c["id"],))
            for i, mv in enumerate(mvts):
                tv_m.insert("", "end", tags=("p" if i % 2 == 0 else "i",), values=(
                    mv["cree_le"], mv["type_mouvement"],
                    f"{mv['montant']:,.0f} {c['devise']}", mv["note"] or ""))
        btn(dlg, "Fermer", dlg.destroy).pack(pady=10)


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
        for txt, cmd, st, perm in [
            ("+ Nouvelle session", self.ajouter,   "Vert.TButton",   "sessions.create"),
            ("Clôturer session",   self.cloturer,  "Rouge.TButton",  "sessions.close"),
            ("Actualiser",         self.actualiser, "TButton",       "sessions.view"),
        ]:
            if not self.auth.permis(perm):
                continue
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
        try:
            self.auth.exiger("sessions.create", contexte="création session")
        except PermissionError as e:
            messagebox.showerror("Erreur", str(e))
            return
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
        try:
            self.auth.exiger("sessions.close", contexte="clôture session")
        except PermissionError as e:
            messagebox.showerror("Erreur", str(e))
            return
        s = self.tv.focus()
        if not s:
            messagebox.showwarning("Sélection", "Sélectionnez une session."); return
        session = self.db.un("SELECT statut FROM session WHERE id=?", (int(s),))
        if not session:
            messagebox.showerror("Erreur", "Session introuvable."); return
        if session["statut"] != "ouverte":
            messagebox.showwarning("Clôture", "Cette session est déjà fermée."); return
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
            ("Bilan financier",           self._bilan,       "Bleu.TButton",  "reports.view"),
            ("Membres → CSV",             self._exp_membres, "Bleu.TButton",  "reports.export"),
            ("Épargnes → CSV",            self._exp_ep,      "Bleu.TButton",  "reports.export"),
            ("Crédits → CSV",             self._exp_cr,      "Bleu.TButton",  "reports.export"),
            ("Crédits en retard → CSV",   self._exp_retards, "Rouge.TButton", "reports.export"),
            ("Journal d'audit → CSV",     self._exp_audit,   "TButton",       "audit.view"),
            ("Rapport complet → HTML",    self._rapport_html, "Vert.TButton", "reports.generate"),
            ("Sauvegarde base de données",self._sauver,      "Vert.TButton",  "backup.create"),
        ]
        for i, (lbl, cmd, st, perm) in enumerate(actions):
            if not self.auth.permis(perm):
                continue
            r, c = divmod(i, 3)
            btn(grille, lbl, cmd, st, l=22).grid(row=r, column=c, padx=8, pady=8, sticky="ew")

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=14, pady=8)
        ttk.Label(self, text="Aperçu du bilan :", style="Sub.TLabel").pack(anchor="w", padx=16)
        self.txt = tk.Text(self, height=18, font=("Courier New", 10),
                           bg="#F8F9FA", fg=C["texte"], relief="flat", state="disabled")
        self.txt.pack(fill="both", expand=True, padx=16, pady=6)
        self._bilan()

    # ── Stats ─────────────────────────────────────────────────────
    def _somme_par_devise(self, sql, *args):
        """{devise: total} — agrégat SQL GROUP BY devise sur une ligne."""
        return {r["devise"] or DEVISE_DEFAUT: r["t"]
                for r in self.db.tous(sql, *args)}

    def _get_stats(self):
        db, aid = self.db, self.avec_id
        Finance.maj_statuts(db)
        membres   = db.valeur("SELECT COUNT(*) FROM membre WHERE statut='actif' AND avec_id=?", (aid,)) or 0
        ep        = self._somme_par_devise(
            "SELECT e.devise AS devise, SUM(e.montant) AS t FROM epargne e"
            " JOIN membre m ON e.membre_id=m.id"
            " WHERE m.avec_id=? AND e.annule=0 GROUP BY e.devise", (aid,))
        cr_p      = self._somme_par_devise(
            "SELECT c.devise AS devise, SUM(c.principal) AS t FROM credit c"
            " JOIN membre m ON c.membre_id=m.id"
            " WHERE m.avec_id=? GROUP BY c.devise", (aid,))
        cr_i      = self._somme_par_devise(
            "SELECT c.devise AS devise, SUM(c.montant_interet) AS t FROM credit c"
            " JOIN membre m ON c.membre_id=m.id"
            " WHERE m.avec_id=? GROUP BY c.devise", (aid,))
        pf_actif  = self._somme_par_devise(
            "SELECT c.devise AS devise, SUM(c.montant_total-c.rembourse) AS t FROM credit c"
            " JOIN membre m ON c.membre_id=m.id"
            " WHERE m.avec_id=? AND c.statut IN ('actif','en_retard') GROUP BY c.devise",
            (aid,))
        rembs     = self._somme_par_devise(
            "SELECT r.devise AS devise, SUM(r.montant_total) AS t FROM remboursement r"
            " JOIN membre m ON r.membre_id=m.id"
            " WHERE m.avec_id=? AND r.annule=0 GROUP BY r.devise", (aid,))
        retards   = db.valeur("SELECT COUNT(*) FROM credit c JOIN membre m ON c.membre_id=m.id WHERE m.avec_id=? AND c.statut='en_retard'", (aid,)) or 0
        cr_actifs = db.valeur("SELECT COUNT(*) FROM credit c JOIN membre m ON c.membre_id=m.id WHERE m.avec_id=? AND c.statut='actif'", (aid,)) or 0
        cr_soldes = db.valeur("SELECT COUNT(*) FROM credit c JOIN membre m ON c.membre_id=m.id WHERE m.avec_id=? AND c.statut='solde'", (aid,)) or 0
        sessions  = db.valeur("SELECT COUNT(*) FROM session WHERE avec_id=?", (aid,)) or 0
        return dict(membres=membres, ep=ep, cr_p=cr_p, cr_i=cr_i,
                    pf_actif=pf_actif, rembs=rembs, retards=retards,
                    cr_actifs=cr_actifs, cr_soldes=cr_soldes,
                    sessions=sessions)

    @staticmethod
    def _fmt_d(pat, d, prefixe="", suffixe=""):
        """Patte de mise en forme par devise d'un dict {devise: montant}."""
        if not d:
            return f"{pat.format(valeur=0, devise=DEVISE_DEFAUT)}"
        return "\n".join(
            f"{prefixe}{pat.format(valeur=v, devise=k)}{suffixe}"
            for k, v in sorted(d.items()))

    def _bilan(self):
        s = self._get_stats()
        epam = sum(s["ep"].values()); pfam = sum(s["pf_actif"].values())
        solde = epam - pfam
        def la(d, v):
            return "  ·  ".join(f"{vv:>12,.0f} {kk}" for kk, vv in sorted(d.items())) \
                if d else f"{v:>12,.0f} {DEVISE_DEFAUT}"
        texte = f"""
{"═"*66}
      BILAN FINANCIER — {APP_NOM} v{APP_VERSION}
      Généré le : {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}
{"═"*66}

 MEMBRES
   Membres actifs                : {s['membres']:>10}

 ÉPARGNES
   Total collecté                : {la(s['ep'], 0)}

 CRÉDITS
   Total principal octroyé       : {la(s['cr_p'], 0)}
   Total intérêts prévus         : {la(s['cr_i'], 0)}
   Portefeuille actif (solde)    : {la(s['pf_actif'], 0)}
   Nombre crédits en retard      : {s['retards']:>10}

 REMBOURSEMENTS
   Total encaissé                : {la(s['rembs'], 0)}

 SESSIONS
   Total sessions tenues         : {s['sessions']:>10}

 SOLDE NET ESTIMÉ
   Épargnes — Portefeuille actif : {solde:>14,.0f} (toutes devises confondues)

{"═"*66}
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
        self.auth.exiger("reports.export", contexte="export membres CSV")
        rows = self.db.tous("""
            SELECT m.id, m.numero, m.nom, m.prenom, m.telephone, m.adresse,
                   m.nb_parts, m.statut, m.date_adhesion
            FROM membre m WHERE m.avec_id=? ORDER BY m.nom
        """, (self.avec_id,))
        ep, cr = _soldes_membres(self.db, self.avec_id)
        lignes = []
        for r in rows:
            mes_ep = {d: v for (mid, d), v in ep.items() if mid == r["id"]}
            mes_cr = {d: v for (mid, d), v in cr.items() if mid == r["id"]}
            lab_ep = " | ".join(f"{v:,.0f} {d}" for d, v in sorted(mes_ep.items()))
            lab_cr = " | ".join(f"{v:,.0f} {d}" for d, v in sorted(mes_cr.items()))
            lignes.append([r["id"], r["numero"], r["nom"], r["prenom"], r["telephone"],
                           r["adresse"], r["nb_parts"], r["statut"], r["date_adhesion"],
                           lab_ep or "0", lab_cr or "0"])
        self._csv("membres.csv",
                  ["ID","N° Membre","Nom","Prénom","Téléphone","Adresse",
                   "Nb Parts","Statut","Adhésion","Épargnes (par devise)",
                   "Crédit actif (par devise)"],
                  lignes)

    def _exp_ep(self):
        self.auth.exiger("reports.export", contexte="export épargnes CSV")
        rows = self.db.tous("""
            SELECT e.id, e.date_op, m.nom, m.prenom, e.type, e.montant,
                   e.devise, e.description, e.annule
            FROM epargne e JOIN membre m ON e.membre_id=m.id
            WHERE m.avec_id=? ORDER BY e.date_op DESC
        """, (self.avec_id,))
        self._csv("epargnes.csv",
                  ["ID","Date","Nom","Prénom","Type","Montant","Devise",
                   "Description","Annulé"],
                  [[r["id"],r["date_op"],r["nom"],r["prenom"],r["type"],
                    r["montant"],r["devise"] or DEVISE_DEFAUT, r["description"],
                    "Oui" if r["annule"] else "Non"]
                   for r in rows])

    def _exp_cr(self):
        self.auth.exiger("reports.export", contexte="export crédits CSV")
        rows = self.db.tous("""
            SELECT c.id, c.date_octroi, m.nom, m.prenom, c.principal,
                   c.taux, c.duree_mois, c.montant_interet, c.montant_total,
                   c.rembourse, c.date_echeance, c.statut, c.devise, c.type_credit
            FROM credit c JOIN membre m ON c.membre_id=m.id
            WHERE m.avec_id=? ORDER BY c.date_octroi DESC
        """, (self.avec_id,))
        self._csv("credits.csv",
                  ["ID","Date octroi","Nom","Prénom","Type","Principal","Taux","Durée",
                   "Intérêt","Total","Remboursé","Solde","Devise","Échéance","Statut"],
                  [[r["id"],r["date_octroi"],r["nom"],r["prenom"],
                    _le_libelle_type_credit(r["type_credit"]),r["principal"],
                    f"{r['taux']*100:.1f}%",f"{r['duree_mois']} mois",
                    r["montant_interet"],r["montant_total"],r["rembourse"],
                    r["montant_total"]-r["rembourse"],r["devise"] or DEVISE_DEFAUT,
                    r["date_echeance"],r["statut"]]
                   for r in rows])

    def _exp_retards(self):
        self.auth.exiger("reports.export", contexte="export retards CSV")
        rows = self.db.tous("""
            SELECT c.id, m.nom, m.prenom, m.telephone, c.montant_total,
                   c.rembourse, c.date_echeance, c.devise
            FROM credit c JOIN membre m ON c.membre_id=m.id
            WHERE m.avec_id=? AND c.statut='en_retard' ORDER BY c.date_echeance
        """, (self.avec_id,))
        self._csv("credits_en_retard.csv",
                  ["Crédit#","Nom","Prénom","Téléphone","Total","Remboursé",
                   "Solde","Devise","Échéance","Jours retard"],
                  [[r["id"],r["nom"],r["prenom"],r["telephone"],r["montant_total"],
                    r["rembourse"],r["montant_total"]-r["rembourse"],
                    r["devise"] or DEVISE_DEFAUT,
                    r["date_echeance"],Finance.jours_retard(r["date_echeance"])]
                   for r in rows])

    def _exp_audit(self):
        self.auth.exiger("audit.view", contexte="export journal CSV")
        rows = self.db.tous(
            "SELECT ts,login,action,tbl,rid,details FROM audit_log ORDER BY id DESC")
        self._csv("audit.csv",
                  ["Horodatage","Utilisateur","Action","Table","ID","Détails"],
                  [[r["ts"],r["login"],r["action"],r["tbl"],r["rid"],r["details"]]
                   for r in rows])

    def _rapport_html(self):
        self.auth.exiger("reports.generate", contexte="rapport HTML")
        s   = self._get_stats()
        solde = sum(s["ep"].values()) - sum(s["pf_actif"].values())
        devises = sorted(set(list(s["ep"]) + list(s["pf_actif"]) + list(s["rembs"]))
                         or [DEVISE_DEFAUT])
        membres = self.db.tous("""
            SELECT m.id, m.nom, m.prenom, m.telephone, m.statut
            FROM membre m WHERE m.avec_id=? ORDER BY m.nom
        """, (self.avec_id,))
        ep_m, cr_m = _soldes_membres(self.db, self.avec_id)
        retards = self.db.tous("""
            SELECT m.nom, m.prenom, m.telephone, c.montant_total,
                   c.rembourse, c.date_echeance, c.devise
            FROM credit c JOIN membre m ON c.membre_id=m.id
            WHERE m.avec_id=? AND c.statut='en_retard' ORDER BY c.date_echeance
        """, (self.avec_id,))

        def tr_m(m):
            nom = html.escape(f"{m['nom']} {m['prenom'] or ''}".strip())
            tel = html.escape(m['telephone'] or '')
            statut = html.escape(m['statut'])
            mes_ep = {d: v for (mid, d), v in ep_m.items() if mid == m["id"]}
            lab = " / ".join(f"{v:,.0f} {d}" for d, v in sorted(mes_ep.items())) or "0"
            return (f"<tr><td>{nom}</td>"
                    f"<td>{tel}</td><td>{statut}</td>"
                    f"<td>{lab}</td></tr>")
        def tr_r(r):
            solde_cr = r["montant_total"] - r["rembourse"]
            jr = Finance.jours_retard(r["date_echeance"])
            nom = html.escape(f"{r['nom']} {r['prenom'] or ''}".strip())
            tel = html.escape(r['telephone'] or '')
            ech = html.escape(str(r['date_echeance']))
            return (f"<tr class='alerte'><td>{nom}</td>"
                    f"<td>{tel}</td>"
                    f"<td>{solde_cr:,.0f} {r['devise'] or DEVISE_DEFAUT}</td>"
                    f"<td>{ech}</td>"
                    f"<td>{jr}j</td></tr>")

        def carte(valeur, lib, fond="#1A5276"):
            return (f"<div class='k' style='background:{fond}'>"
                    f"<div class='v'>{valeur}</div><div class='l'>{lib}</div></div>")

        cartes = [carte(s['membres'], "Membres actifs")]
        for d in devises:
            cartes.append(carte(f"{s['ep'].get(d,0):,.0f}", f"Épargnes {d}"))
        for d in devises:
            cartes.append(carte(f"{s['pf_actif'].get(d,0):,.0f}", f"Portefeuille crédit {d}"))
        for d in devises:
            cartes.append(carte(f"{s['rembs'].get(d,0):,.0f}", f"Remboursements {d}"))
        cartes.append(carte(s['retards'], "Crédits en retard",
                            "#C0392B" if s['retards']>0 else "#1E8449"))
        cartes.append(carte(f"{solde:,.0f}", "Solde net (toutes devises)",
                            "#1E8449" if solde>=0 else "#C0392B"))
        kpi = "\n  ".join(cartes)

        series = []
        for d in devises:
            series.append((f"Épargnes {d}", s["ep"].get(d, 0), "#1E8449"))
        for d in devises:
            series.append((f"Crédit {d}", s["pf_actif"].get(d, 0), "#7D6608"))
        for d in devises:
            series.append((f"Remboursé {d}", s["rembs"].get(d, 0), "#6C3483"))
        series.append(("Solde net", max(solde, 0), "#2980B9"))
        svg_bar = ChartEngine.svg_bar(series)
        svg_pie = ChartEngine.svg_pie([
            ("Actifs", s.get("cr_actifs", 0), "#2980B9"),
            ("Retard", s["retards"], "#C0392B"),
            ("Soldés", s.get("cr_soldes", 0), "#1E8449"),
        ])

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
  .charts{{display:flex;gap:20px;margin:20px 0;flex-wrap:wrap}}
  .chart-box{{flex:1;min-width:320px;background:#fff;border:1px solid #D5D8DC;border-radius:8px;padding:16px;text-align:center}}
  .chart-box h3{{margin:0 0 8px 0;color:#1A5276;font-size:1em}}
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
  {kpi}
</div>
<div class="charts">
  <div class="chart-box"><h3>Vue financière</h3>{svg_bar}</div>
  <div class="chart-box"><h3>Statut des crédits</h3>{svg_pie}</div>
</div>
<h2>Liste des membres</h2>
<table><tr><th>Nom complet</th><th>Téléphone</th><th>Statut</th><th>Épargnes (par devise)</th></tr>
{''.join(tr_m(m) for m in membres)}</table>
{'<h2>Crédits en retard</h2><table><tr><th>Nom</th><th>Téléphone</th><th>Solde</th><th>Échéance</th><th>Retard</th></tr>' + ''.join(tr_r(r) for r in retards) + '</table>' if retards else ''}
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
            self.auth.exiger("backup.create", contexte="sauvegarde manuelle")
            dest = self.bkp.sauvegarder()
            self.db.audit(self.auth.uid, self.auth.ulogin, "SAUVEGARDE",
                          details={"dest": dest})
            messagebox.showinfo("Sauvegarde réussie",
                f"Base de données sauvegardée :\n{dest}")
        except Exception as e:
            messagebox.showerror("Erreur sauvegarde", str(e))


# ════════════════════════════════════════════════════════════════
#  ADMINISTRATION — UTILISATEURS, RÔLES, JOURNAL D'ACTIVITÉ
# ════════════════════════════════════════════════════════════════

class OngletAdmin(ttk.Frame):
    """Gestion multi-utilisateurs + permissions granulaires + audit."""

    def __init__(self, parent, db, auth, avec_id=1):
        super().__init__(parent)
        self.db = db; self.auth = auth; self.avec_id = avec_id
        self.columnconfigure(0, weight=1); self.rowconfigure(0, weight=1)
        self._ui()

    def _ui(self):
        nb = ttk.Notebook(self)
        nb.grid(row=0, column=0, sticky="nsew", padx=10, pady=8)
        self._tab_utilisateurs(nb)
        self._tab_journal(nb)
        self.actualiser()

    def _tab_utilisateurs(self, nb):
        tab = ttk.Frame(nb)
        nb.add(tab, text="Utilisateurs")
        tab.columnconfigure(0, weight=1); tab.rowconfigure(1, weight=1)

        bar = ttk.Frame(tab)
        bar.grid(row=0, column=0, sticky="ew", padx=12, pady=8)
        ttk.Label(bar, text="Comptes utilisateurs", style="Titre.TLabel").pack(side="left")
        for txt, cmd, st, perm in [
            ("+ Nouvel utilisateur", self.ajouter,     "Vert.TButton",  "users.create"),
            ("Modifier",             self.modifier,    "Bleu.TButton",  "users.edit"),
            ("Permissions",          self.permissions, "Bleu.TButton",  "users.permissions"),
            ("Rôles",                self.roles,       "Bleu.TButton",  "users.permissions"),
            ("Activer/Désactiver",   self.bascule,     "Rouge.TButton", "users.disable"),
            ("Réinitialiser mdp",    self.reinit,      "TButton",       "users.edit"),
            ("Actualiser",           self.actualiser,  "TButton",       "users.view"),
        ]:
            if not self.auth.permis(perm):
                continue
            btn(bar, txt, cmd, st).pack(side="right", padx=3)

        cols = ("ID","Nom","Login","Rôle","Statut","AVEC","Dernière connexion","Créé le")
        lrg  = [40, 160, 120, 130, 80, 120, 170, 140]
        self.tv, f = treeview(tab, cols, lrg)
        f.grid(row=1, column=0, sticky="nsew", padx=12, pady=4)
        self.tv.bind("<Double-1>", lambda e: self.permissions())
        self.v_res = tk.StringVar()
        ttk.Label(tab, textvariable=self.v_res,
                  font=(FONT, 10, "bold")).grid(row=2, column=0, pady=6)

    def _tab_journal(self, nb):
        tab = ttk.Frame(nb)
        nb.add(tab, text="Journal d'activité")
        tab.columnconfigure(0, weight=1); tab.rowconfigure(1, weight=1)

        bar = ttk.Frame(tab)
        bar.grid(row=0, column=0, sticky="ew", padx=12, pady=8)
        ttk.Label(bar, text="Journal d'activité (audit)").pack(side="left")
        ttk.Label(bar, text="Utilisateur :").pack(side="left", padx=(16, 4))
        self.v_filtre = tk.StringVar()
        self.cb_f = ttk.Combobox(bar, textvariable=self.v_filtre, state="readonly",
                                 width=16)
        self.cb_f.pack(side="left")
        self.v_filtre.trace("w", lambda *a: self.actualiser_journal())
        btn(bar, "Actualiser", self.actualiser_journal).pack(side="right", padx=3)
        if self.auth.permis("audit.view"):
            btn(bar, "Exporter CSV", self._exp_audit).pack(side="right", padx=3)

        cols = ("Date","Utilisateur","Action","Table","ID","Détails")
        lrg  = [160, 110, 180, 100, 60, 480]
        self.tv_j, f = treeview(tab, cols, lrg)
        f.grid(row=1, column=0, sticky="nsew", padx=12, pady=4)
        self.actualiser_journal()

    def actualiser(self):
        for it in self.tv.get_children():
            self.tv.delete(it)
        users = self.db.tous("""
            SELECT u.*, a.nom as avec_nom FROM utilisateur u
            LEFT JOIN avec a ON u.avec_id=a.id ORDER BY u.id
        """)
        for i, u in enumerate(users):
            tag = ("rouge" if not u["actif"] else ("p" if i % 2 == 0 else "i"))
            self.tv.insert("", "end", iid=str(u["id"]), tags=(tag,), values=(
                u["id"], u["nom"], u["login"], u["role"],
                "Actif" if u["actif"] else "Désactivé",
                (u["avec_nom"] if not u["avec_id"] or u["avec_id"] == self.avec_id
                 else u["avec_nom"] or "—"),
                u["derniere_connexion"] or "—", u["cree_le"] or "—"))
        self.v_res.set(f"{len(users)} utilisateur(s)")
        logins = sorted({r["login"] for r in users})
        self.cb_f["values"] = ["Tous"] + [l for l in logins][:200]
        if not self.v_filtre.get():
            self.v_filtre.set("Tous")

    def actualiser_journal(self):
        for it in self.tv_j.get_children():
            self.tv_j.delete(it)
        filtre = self.v_filtre.get() if hasattr(self, "v_filtre") else "Tous"
        if filtre in (None, "", "Tous"):
            rows = self.db.tous(
                "SELECT ts,login,action,tbl,rid,details FROM audit_log"
                " ORDER BY id DESC LIMIT 400")
        else:
            rows = self.db.tous(
                "SELECT ts,login,action,tbl,rid,details FROM audit_log"
                " WHERE login=? ORDER BY id DESC LIMIT 400", (filtre,))
        for i, r in enumerate(rows):
            self.tv_j.insert("", "end", tags=("p" if i % 2 == 0 else "i",), values=(
                r["ts"] or "", r["login"] or "", r["action"], r["tbl"] or "",
                r["rid"] if r["rid"] is not None else "", r["details"] or ""))

    def _exp_audit(self):
        self.auth.exiger("audit.view", contexte="export journal CSV")
        p = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="audit.csv",
                                         filetypes=[("CSV", "*.csv")])
        if not p:
            return
        rows = self.db.tous(
            "SELECT ts,login,action,tbl,rid,details FROM audit_log ORDER BY id DESC")
        with open(p, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["Horodatage", "Utilisateur", "Action", "Table", "ID", "Détails"])
            w.writerows([[r["ts"], r["login"], r["action"], r["tbl"],
                          r["rid"], r["details"]] for r in rows])
        self.db.audit(self.auth.uid, self.auth.ulogin, "EXPORT_CSV",
                      details={"fichier": p, "lignes": len(rows)})
        messagebox.showinfo("Export réussi", f"Fichier exporté :\n{p}")

    def _sel(self):
        s = self.tv.focus()
        if not s:
            messagebox.showwarning("Sélection", "Sélectionnez un utilisateur.")
            return None
        return int(s)

    def ajouter(self):
        DlgUtilisateur(self, self.db, self.auth, self.avec_id,
                       callback=self.actualiser)

    def modifier(self):
        uid = self._sel()
        if uid:
            u = self.db.un("SELECT * FROM utilisateur WHERE id=?", (uid,))
            DlgUtilisateur(self, self.db, self.auth, self.avec_id, utilisateur=u,
                           callback=self.actualiser)

    def permissions(self):
        uid = self._sel()
        if uid:
            u = self.db.un("SELECT * FROM utilisateur WHERE id=?", (uid,))
            DlgPermissions(self, self.db, self.auth, u, callback=self.actualiser)

    def roles(self):
        DlgRoles(self, self.db, self.auth)

    def bascule(self):
        uid = self._sel()
        if not uid:
            return
        u = self.db.un("SELECT * FROM utilisateur WHERE id=?", (uid,))
        if u["id"] == self.auth.uid:
            messagebox.showwarning("Impossible",
                                   "Vous ne pouvez pas désactiver votre propre compte.")
            return
        try:
            self.auth.exiger("users.disable", contexte="activation/désactivation")
        except PermissionError as e:
            messagebox.showerror("Erreur", str(e)); return
        nouvel_etat = 0 if u["actif"] else 1
        if not messagebox.askyesno(
                "Confirmer",
                "Désactiver ce compte ? Il ne pourra plus se connecter." if nouvel_etat == 0
                else "Réactiver ce compte ?", parent=self):
            return
        self.db.exec("UPDATE utilisateur SET actif=? WHERE id=?", (nouvel_etat, uid))
        self.db.commit()
        action = "DESACTIVER_UTILISATEUR" if nouvel_etat == 0 else "REACTIVER_UTILISATEUR"
        self.db.audit(self.auth.uid, self.auth.ulogin, action, "utilisateur", uid,
                      {"login": u["login"]})
        self.actualiser()

    def reinit(self):
        uid = self._sel()
        if not uid:
            return
        u = self.db.un("SELECT * FROM utilisateur WHERE id=?", (uid,))
        try:
            self.auth.exiger("users.edit", contexte="réinitialisation mot de passe")
        except PermissionError as e:
            messagebox.showerror("Erreur", str(e)); return
        nouveau = simpledialog.askstring(
            "Réinitialiser le mot de passe",
            f"Nouveau mot de passe pour « {u['nom']} » :\n(minimum 4 caractères)",
            parent=self)
        if nouveau is None:
            return
        if len(nouveau) < 4:
            messagebox.showerror("Erreur", "Minimum 4 caractères."); return
        if nouveau == MDP_DEFAUT:
            messagebox.showerror("Erreur",
                "Le mot de passe usine est interdit.\nChoisissez-en un autre.")
            return
        sel = secrets.token_hex(16)
        ph = hashlib.pbkdf2_hmac('sha256', f"{nouveau}{sel}".encode(),
                                 sel.encode(), 100000).hex()
        self.db.exec("UPDATE utilisateur SET pwd_hash=?,sel=? WHERE id=?",
                     (ph, sel, uid))
        self.db.commit()
        self.db.audit(self.auth.uid, self.auth.ulogin, "REINITIALISER_MDP",
                      "utilisateur", uid, {"login": u["login"]})
        messagebox.showinfo("Succès", "Mot de passe réinitialisé.")


class DlgUtilisateur(tk.Toplevel):
    """Création / modification d'un compte local (jamais supprimé physique)."""

    def __init__(self, parent, db, auth, avec_id, utilisateur=None, callback=None):
        super().__init__(parent)
        self.db = db; self.auth = auth; self.avec_id = avec_id
        self.u = utilisateur; self.cb = callback
        self.title("Modifier l'utilisateur" if utilisateur else "Nouvel utilisateur")
        self.resizable(False, False); self.grab_set()
        centrer(self, 460, 400)
        self._ui()

    def _ui(self):
        u = self.u or {}
        frm = ttk.Frame(self, padding=20)
        frm.pack(fill="both", expand=True)
        frm.columnconfigure(1, weight=1)
        ttk.Label(frm, text="Compte utilisateur local", style="Sub.TLabel").grid(
            row=0, column=0, columnspan=2, pady=(0, 14))

        self.v_nom, _  = champ(frm, "Nom complet *", 1, u.get("nom", ""))
        self.v_log, _  = champ(frm, "Identifiant *", 2, u.get("login", ""))
        if not self.u:
            self.v_mdp, _ = champ(frm, "Mot de passe *", 3, secret=True)
        positions = [("Rôle", 4), ("AVEC", 5)]

        ttk.Label(frm, text="Rôle").grid(row=4, column=0, sticky="e", padx=(0, 8), pady=5)
        self.v_role = tk.StringVar(value=u.get("role", "agent"))
        roles = [r["nom"] for r in self.db.tous("SELECT nom FROM role ORDER BY nom")]
        if u.get("role") not in roles:
            roles.insert(0, u.get("role"))
        ttk.Combobox(frm, textvariable=self.v_role, values=roles,
                     state="readonly", width=26).grid(row=4, column=1, sticky="ew", pady=5)

        ttk.Label(frm, text="AVEC").grid(row=5, column=0, sticky="e", padx=(0, 8), pady=5)
        avecs = self.db.tous("SELECT id,nom FROM avec ORDER BY id")
        self.amap = {a["nom"]: a["id"] for a in avecs}
        self.v_avec = tk.StringVar(value=u.get("avec_id", self.avec_id) or self.avec_id)
        nom_avec = next((n for n, i in self.amap.items()
                         if i == (u.get("avec_id") or self.avec_id)), None) or ""
        self.v_avec = tk.StringVar(value=nom_avec)
        ttk.Combobox(frm, textvariable=self.v_avec, values=list(self.amap.keys()),
                     state="readonly", width=26).grid(row=5, column=1, sticky="ew", pady=5)

        self.v_actif = tk.BooleanVar(value=bool(u.get("actif", 1)))
        ttk.Checkbutton(frm, text="Compte actif", variable=self.v_actif).grid(
            row=6, column=1, sticky="w", pady=5)

        bf = ttk.Frame(frm)
        bf.grid(row=7, column=0, columnspan=2, pady=16)
        btn(bf, "Enregistrer", self._sauver, "Vert.TButton").pack(side="left", padx=8)
        btn(bf, "Annuler", self.destroy).pack(side="left", padx=8)

        for var in (self.v_nom, self.v_log):
            var.trace("w", lambda *a: self.v_role.set(self.v_role.get()))

    def _sauver(self):
        try:
            if self.u:
                self.auth.exiger("users.edit", contexte="modification utilisateur")
            else:
                self.auth.exiger("users.create", contexte="création utilisateur")
            nom  = self.v_nom.get().strip()
            login = self.v_log.get().strip()
            if not nom or not login:
                raise ValueError("Le nom et l'identifiant sont obligatoires.")
            if not re.match(r"^[A-Za-z0-9._\-]+$", login):
                raise ValueError("Identifiant invalide (lettres, chiffres, . _ - uniquement).")
            avec_id = self.amap.get(self.v_avec.get(), self.avec_id)
            role = self.v_role.get() or "agent"
            actif = 1 if self.v_actif.get() else 0
            if self.u:
                self.db.exec("""
                    UPDATE utilisateur SET nom=?, role=?, actif=?, avec_id=?
                    WHERE id=?""", (nom, role, actif, avec_id, self.u["id"]))
                self.db.commit()
                self.db.audit(self.auth.uid, self.auth.ulogin, "MODIFIER_UTILISATEUR",
                              "utilisateur", self.u["id"],
                              {"login": login, "role": role, "actif": actif})
            else:
                mdp = self.v_mdp.get()
                if len(mdp) < 4:
                    raise ValueError("Le mot de passe doit contenir au moins 4 caractères.")
                if mdp == MDP_DEFAUT:
                    raise ValueError("Le mot de passe usine est interdit pour les nouveaux comptes.")
                sel = secrets.token_hex(16)
                ph  = hashlib.pbkdf2_hmac('sha256', f"{mdp}{sel}".encode(),
                                          sel.encode(), 100000).hex()
                cur = self.db.exec(
                    "INSERT INTO utilisateur(nom,login,pwd_hash,sel,role,actif,avec_id)"
                    " VALUES(?,?,?,?,?,?,?)",
                    (nom, login, ph, sel, role, actif, avec_id))
                self.db.commit()
                self.db.audit(self.auth.uid, self.auth.ulogin, "CREER_UTILISATEUR",
                              "utilisateur", cur.lastrowid,
                              {"login": login, "role": role, "actif": actif})
            if self.cb: self.cb()
            self.destroy()
        except (PermissionError, ValueError, sqlite3.Error) as e:
            messagebox.showerror("Erreur", str(e), parent=self)


class DlgPermissions(tk.Toplevel):
    """Éditeur de permissions granulaires pour un utilisateur."""

    def __init__(self, parent, db, auth, utilisateur, callback=None):
        super().__init__(parent)
        self.db = db; self.auth = auth; self.u = utilisateur; self.cb = callback
        self.title(f"Permissions — {utilisateur['nom']}")
        self.geometry("620x560")
        self.grab_set()
        centrer(self, 620, 560)
        self.vars = {}
        self._ui()

    def _ui(self):
        u = self.u
        frm = ttk.Frame(self, padding=14)
        frm.pack(fill="both", expand=True)
        frm.columnconfigure(0, weight=1); frm.rowconfigure(1, weight=1)

        ttk.Label(frm, text=f"Permissions de « {u['nom']} » — {u['login']}",
                  style="Sub.TLabel").grid(row=0, column=0, sticky="w")
        if u["role"] == "admin":
            ttk.Label(frm, text="L'administrateur dispose automatiquement de TOUTES les permissions.",
                      foreground=C["or"]).grid(row=0, column=0, sticky="e")

        # Frame scrollable
        canevas = tk.Canvas(frm, highlightthickness=0)
        barre = ttk.Scrollbar(frm, orient="vertical", command=canevas.yview)
        contenant = ttk.Frame(canevas)
        contenant.bind("<Configure>",
                       lambda e: canevas.configure(scrollregion=canevas.bbox("all")))
        canevas.create_window((0, 0), window=contenant, anchor="nw")
        canevas.configure(yscrollcommand=barre.set)
        canevas.grid(row=1, column=0, sticky="nsew")
        barre.grid(row=1, column=1, sticky="ns")
        frm.columnconfigure(0, weight=1)

        deja = {p["code"] for p in self.db.tous(
            "SELECT code FROM user_permission WHERE utilisateur_id=?",
            (self.u["id"],))}
        groupes = {}
        for code, lib, grp in PERMISSIONS:
            groupes.setdefault(grp, []).append((code, lib))

        rang = 0
        for grp, items in groupes.items():
            ttk.Label(contenant, text=grp, style="Sub.TLabel").grid(
                row=rang, column=0, sticky="w", pady=(8, 0)); rang += 1
            for code, lib in items:
                var = tk.BooleanVar(value=code in deja)
                self.vars[code] = var
                ttk.Checkbutton(contenant, text=lib, variable=var).grid(
                    row=rang, column=0, sticky="w", padx=(18, 0)); rang += 1

        bande = ttk.Frame(frm)
        bande.grid(row=2, column=0, sticky="ew", pady=10)
        def tout(etat):
            for v in self.vars.values():
                v.set(etat)
        btn(bande, "Tout sélectionner", lambda: tout(True)).pack(side="left", padx=4)
        btn(bande, "Tout désélectionner", lambda: tout(False)).pack(side="left", padx=4)
        btn(bande, "Enregistrer", self._sauver, "Vert.TButton").pack(side="right", padx=4)
        btn(bande, "Annuler", self.destroy).pack(side="right", padx=4)

    def _sauver(self):
        try:
            self.auth.exiger("users.permissions",
                             contexte=f"permissions de {self.u['login']}")
        except PermissionError as e:
            messagebox.showerror("Erreur", str(e), parent=self); return
        if not messagebox.askyesno("Confirmer",
                "Appliquer ces permissions à l'utilisateur ?\nLes permissions "
                "actuelles seront remplacées.", parent=self):
            return
        self.db.exec("DELETE FROM user_permission WHERE utilisateur_id=?",
                     (self.u["id"],))
        for code, var in self.vars.items():
            if var.get():
                self.db.exec("INSERT OR IGNORE INTO user_permission"
                             "(utilisateur_id,code) VALUES(?,?)",
                             (self.u["id"], code))
        self.db.commit()
        self.db.audit(self.auth.uid, self.auth.ulogin, "DEFINIR_PERMISSIONS",
                      "utilisateur", self.u["id"],
                      {"login": self.u["login"],
                       "nb": sum(1 for v in self.vars.values() if v.get())})
        if self.u["id"] == self.auth.uid:
            self.auth._charger_permissions()
        if self.cb: self.cb()
        self.destroy()


class DlgRoles(tk.Toplevel):
    """Gestion des rôles (ensembles de permissions) et des permissions du rôle."""

    def __init__(self, parent, db, auth):
        super().__init__(parent)
        self.db = db; self.auth = auth
        self.title("Rôles et permissions")
        self.resizable(False, False); self.grab_set()
        centrer(self, 720, 480)
        self._ui()
        self.actualiser()

    def _ui(self):
        frm = ttk.Frame(self, padding=16)
        frm.pack(fill="both", expand=True)
        frm.columnconfigure(0, weight=1); frm.rowconfigure(1, weight=1)

        bar = ttk.Frame(frm)
        bar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(bar, text="Rôles", style="Titre.TLabel").pack(side="left")
        btn(bar, "+ Nouveau rôle", self.ajouter, "Vert.TButton").pack(side="right", padx=3)
        btn(bar, "Modifier", self.modifier, "Bleu.TButton").pack(side="right", padx=3)
        btn(bar, "Permissions", self.permissions, "Bleu.TButton").pack(side="right", padx=3)
        btn(bar, "Supprimer", self.supprimer, "Rouge.TButton").pack(side="right", padx=3)

        cols = ("Nom", "Description", "Type")
        lrg  = [170, 420, 90]
        self.tv, f = treeview(frm, cols, lrg)
        f.grid(row=1, column=0, sticky="nsew")

    def actualiser(self):
        for it in self.tv.get_children():
            self.tv.delete(it)
        roles = self.db.tous("SELECT * FROM role ORDER BY nom")
        for i, r in enumerate(roles):
            self.tv.insert("", "end", iid=str(r["id"]), tags=("p" if i % 2 == 0 else "i",),
                           values=(r["nom"], r["description"] or "",
                                   "Prédéfini" if r["systeme"] else "Personnalisé"))
        self.roles = roles

    def _sel(self):
        s = self.tv.focus()
        if not s:
            messagebox.showwarning("Sélection", "Sélectionnez un rôle.")
            return None
        return int(s)

    def ajouter(self):
        try:
            self.auth.exiger("users.permissions", contexte="créer un rôle")
        except PermissionError as e:
            messagebox.showerror("Erreur", str(e)); return
        nom = simpledialog.askstring("Nouveau rôle", "Nom du rôle :", parent=self)
        if not nom or not nom.strip():
            return
        nom = nom.strip()
        if self.db.un("SELECT id FROM role WHERE nom=?", (nom,)):
            messagebox.showerror("Erreur", "Ce rôle existe déjà."); return
        self.db.exec("INSERT INTO role(nom,description,systeme) VALUES(?,?,0)",
                     (nom, "Rôle personnalisé"))
        self.db.commit()
        self.db.audit(self.auth.uid, self.auth.ulogin, "AJOUTER_ROLE",
                      "role", details={"nom": nom})
        self.actualiser()

    def modifier(self):
        rid = self._sel()
        if not rid: return
        r = self.db.un("SELECT * FROM role WHERE id=?", (rid,))
        nouveau = simpledialog.askstring("Modifier le rôle",
            "Description du rôle :", parent=self, initialvalue=r["description"] or "")
        if nouveau is None:
            return
        try:
            self.auth.exiger("users.permissions", contexte="modifier un rôle")
        except PermissionError as e:
            messagebox.showerror("Erreur", str(e)); return
        self.db.exec("UPDATE role SET description=? WHERE id=?", (nouveau.strip() or None, rid))
        self.db.commit()
        self.db.audit(self.auth.uid, self.auth.ulogin, "MODIFIER_ROLE",
                      "role", rid, {"nom": r["nom"]})
        self.actualiser()

    def permissions(self):
        rid = self._sel()
        if not rid: return
        r = self.db.un("SELECT * FROM role WHERE id=?", (rid,))
        DlgRolePermissions(self, self.db, self.auth, r, callback=self.actualiser)

    def supprimer(self):
        rid = self._sel()
        if not rid: return
        r = self.db.un("SELECT * FROM role WHERE id=?", (rid,))
        if r["systeme"]:
            messagebox.showwarning("Rôle système",
                                   "Les rôles prédéfinis ne peuvent pas être supprimés.")
            return
        if not messagebox.askyesno("Confirmer",
                f"Supprimer le rôle « {r['nom']} » ?", parent=self):
            return
        try:
            self.auth.exiger("users.permissions", contexte="supprimer un rôle")
        except PermissionError as e:
            messagebox.showerror("Erreur", str(e)); return
        self.db.exec("DELETE FROM role WHERE id=?", (rid,))
        self.db.commit()
        self.db.audit(self.auth.uid, self.auth.ulogin, "SUPPRIMER_ROLE",
                      "role", rid, {"nom": r["nom"]})
        self.actualiser()


class DlgRolePermissions(DlgPermissions):
    """Réutilise l'éditeur de permissions pour un rôle (toujours refusé)."""

    def __init__(self, parent, db, auth, role, callback=None):
        self.role = role
        self.vars = {}
        self._cibles = []
        super().__init__(parent, db, auth, {"nom": role["nom"], "login": role["nom"],
                                            "id": role["id"], "role": "role"},
                         callback=callback)

    def _ui(self):
        u = {"nom": self.role["nom"], "login": self.role["nom"]}
        frm = ttk.Frame(self, padding=14)
        frm.pack(fill="both", expand=True)
        frm.columnconfigure(0, weight=1); frm.rowconfigure(1, weight=1)
        ttk.Label(frm, text=f"Permissions du rôle « {self.role['nom']} »",
                  style="Sub.TLabel").grid(row=0, column=0, sticky="w")

        canevas = tk.Canvas(frm, highlightthickness=0)
        barre = ttk.Scrollbar(frm, orient="vertical", command=canevas.yview)
        contenant = ttk.Frame(canevas)
        contenant.bind("<Configure>",
                       lambda e: canevas.configure(scrollregion=canevas.bbox("all")))
        canevas.create_window((0, 0), window=contenant, anchor="nw")
        canevas.configure(yscrollcommand=barre.set)
        canevas.grid(row=1, column=0, sticky="nsew")
        barre.grid(row=1, column=1, sticky="ns")

        deja = {p["code"] for p in self.db.tous(
            "SELECT code FROM role_permission WHERE role_id=?", (self.role["id"],))}
        groupes = {}
        for code, lib, grp in PERMISSIONS:
            groupes.setdefault(grp, []).append((code, lib))
        rang = 0
        for grp, items in groupes.items():
            ttk.Label(contenant, text=grp, style="Sub.TLabel").grid(
                row=rang, column=0, sticky="w", pady=(8, 0)); rang += 1
            for code, lib in items:
                var = tk.BooleanVar(value=code in deja)
                self.vars[code] = var
                ttk.Checkbutton(contenant, text=lib, variable=var).grid(
                    row=rang, column=0, sticky="w", padx=(18, 0)); rang += 1

        bande = ttk.Frame(frm)
        bande.grid(row=2, column=0, sticky="ew", pady=10)
        def tout(etat):
            for v in self.vars.values():
                v.set(etat)
        btn(bande, "Tout sélectionner", lambda: tout(True)).pack(side="left", padx=4)
        btn(bande, "Tout désélectionner", lambda: tout(False)).pack(side="left", padx=4)
        btn(bande, "Enregistrer", self._sauver, "Vert.TButton").pack(side="right", padx=4)
        btn(bande, "Annuler", self.destroy).pack(side="right", padx=4)

    def _sauver(self):
        try:
            self.auth.exiger("users.permissions",
                             contexte=f"permissions du rôle {self.role['nom']}")
        except PermissionError as e:
            messagebox.showerror("Erreur", str(e), parent=self); return
        if not messagebox.askyesno("Confirmer",
                f"Appliquer ces permissions au rôle « {self.role['nom']} » ?",
                parent=self):
            return
        self.db.exec("DELETE FROM role_permission WHERE role_id=?", (self.role["id"],))
        for code, var in self.vars.items():
            if var.get():
                self.db.exec("INSERT OR IGNORE INTO role_permission"
                             "(role_id,code) VALUES(?,?)", (self.role["id"], code))
        self.db.commit()
        self.db.audit(self.auth.uid, self.auth.ulogin, "DEFINIR_PERMISSIONS",
                      "role", self.role["id"], {"nom": self.role["nom"]})
        if self.cb: self.cb()
        self.destroy()


# ════════════════════════════════════════════════════════════════
#  DOCUMENTS — MODÈLES, REÇUS, DOCUMENTS GÉNÉRÉS
# ════════════════════════════════════════════════════════════════

class OngletDocuments(ttk.Frame):
    """Modèles par AVEC, historique des reçus, documents générés."""

    def __init__(self, parent, db, auth, avec_id=1):
        super().__init__(parent)
        self.db = db; self.auth = auth; self.avec_id = avec_id
        self.columnconfigure(0, weight=1); self.rowconfigure(0, weight=1)
        Modeles._creer_dossiers()
        self._ui()

    def _ui(self):
        nb = ttk.Notebook(self)
        nb.grid(row=0, column=0, sticky="nsew", padx=10, pady=8)
        self._tab_modeles(nb)
        self._tab_recus(nb)
        self._tab_generes(nb)

    def _tab_modeles(self, nb):
        tab = ttk.Frame(nb)
        nb.add(tab, text="Modèles")
        tab.columnconfigure(0, weight=1); tab.rowconfigure(1, weight=1)
        bar = ttk.Frame(tab)
        bar.grid(row=0, column=0, sticky="ew", padx=12, pady=8)
        ttk.Label(bar, text="Modèles de documents (par AVEC)",
                  style="Titre.TLabel").pack(side="left")
        for txt, cmd, st, perm in [
            ("+ Ajouter un modèle", self.ajouter_modele, "Vert.TButton", "documents.add_template"),
            ("Modifier",            self.modifier_modele, "Bleu.TButton", "documents.edit_template"),
            ("Supprimer",           self.supprimer_modele, "Rouge.TButton", "documents.delete_template"),
            ("Par défaut",          self.defaut_modele,  "Bleu.TButton", "documents.edit_template"),
            ("Générer document",    self.generer,        "Vert.TButton", "documents.generate"),
            ("Actualiser",          self.actualiser_modeles, "TButton", "documents.view"),
        ]:
            if not self.auth.permis(perm):
                continue
            btn(bar, txt, cmd, st).pack(side="right", padx=3)

        cols = ("ID","Nom","Type","Format","AVEC","Par défaut","Créé le","Modifié le")
        lrg  = [40, 200, 140, 70, 130, 90, 140, 140]
        self.tv_m, f = treeview(tab, cols, lrg)
        f.grid(row=1, column=0, sticky="nsew", padx=12, pady=4)
        self.tv_m.bind("<Double-1>", lambda e: self.modifier_modele())
        self.v_aide = tk.StringVar()
        ttk.Label(tab, textvariable=self.v_aide, font=(FONT, 9),
                  foreground=C["texte_mute"]).grid(row=2, column=0, sticky="w", padx=16)
        self.v_aide.set("Formats : DOCX, ODT, HTML, TXT — champs {{VARIABLE}} remplacés "
                        "à la génération. Variables : " + " ".join(
                            "{{" + v + "}}" for v in list(Modeles.NAUT)))
        self.actualiser_modeles()

    def actualiser_modeles(self):
        for it in self.tv_m.get_children():
            self.tv_m.delete(it)
        rows = self.db.tous("""
            SELECT t.*, a.nom as avec_nom FROM document_template t
            JOIN avec a ON t.avec_id=a.id ORDER BY t.avec_id, t.nom
        """)
        for i, r in enumerate(rows):
            tag = ("vert" if r["par_defaut"] else ("p" if i % 2 == 0 else "i"))
            self.tv_m.insert("", "end", iid=str(r["id"]), tags=(tag,), values=(
                r["id"], r["nom"], r["type"], r["format"], r["avec_nom"],
                "✓" if r["par_defaut"] else "", r["cree_le"] or "", r["modifie_le"] or ""))

    def _sel_modele(self):
        s = self.tv_m.focus()
        if not s:
            messagebox.showwarning("Sélection", "Sélectionnez un modèle.")
            return None
        return int(s)

    def ajouter_modele(self):
        try:
            self.auth.exiger("documents.add_template", contexte="ajout modèle")
        except PermissionError as e:
            messagebox.showerror("Erreur", str(e)); return
        chemin = filedialog.askopenfilename(
            title="Choisir un modèle (DOCX / ODT / HTML / TXT)",
            filetypes=[("Modèles", "*.docx *.odt *.html *.htm *.txt"),
                       ("Tous", "*.*")])
        if not chemin:
            return
        ext = Path(chemin).suffix.lower().lstrip(".")
        if ext not in FORMATS_MODELES:
            messagebox.showerror("Format non supporté",
                f"Supportés : DOCX, ODT, HTML, TXT.\nReçu : .{ext}")
            return
        nom = simpledialog.askstring("Nom du modèle", "Nom du modèle :", parent=self)
        if not nom:
            return
        type_ = simpledialog.askstring("Type de document",
            "Type (Reçu, Attestation, Rapport financier, Relevé membre, Bilan,\n"
            "Procès-verbal, …) :", parent=self, initialvalue="Reçu")
        if not type_:
            return
        deja = self.db.un(
            "SELECT id FROM document_template WHERE avec_id=? AND par_defaut=1 AND type=?",
            (self.avec_id, type_))
        par_defaut = (not deja) and messagebox.askyesno(
            "Modèle par défaut",
            f"Définir ce modèle comme modèle par défaut pour « {type_} » ?")
        try:
            Modeles.importer(self.db, chemin, self.avec_id, nom, type_,
                             self.auth.uid, par_defaut=1 if par_defaut else 0)
            self.actualiser_modeles()
        except ValueError as e:
            messagebox.showerror("Erreur", str(e))

    def modifier_modele(self):
        mid = self._sel_modele()
        if not mid: return
        ml = self.db.un("SELECT * FROM document_template WHERE id=?", (mid,))
        try:
            self.auth.exiger("documents.edit_template", contexte="modification modèle")
        except PermissionError as e:
            messagebox.showerror("Erreur", str(e)); return
        nom = simpledialog.askstring("Modifier le modèle", "Nom du modèle :",
                                     parent=self, initialvalue=ml["nom"])
        if not nom:
            return
        self.db.exec("UPDATE document_template SET nom=?, modifie_le=datetime('now','localtime')"
                     " WHERE id=?", (nom.strip(), mid))
        self.db.commit()
        self.db.audit(self.auth.uid, self.auth.ulogin, "MODIFIER_MODELE",
                      "document_template", mid, {"nom": nom.strip()})
        self.actualiser_modeles()

    def supprimer_modele(self):
        mid = self._sel_modele()
        if not mid: return
        ml = self.db.un("SELECT * FROM document_template WHERE id=?", (mid,))
        if not messagebox.askyesno(
                "Confirmer suppression",
                f"Supprimer le modèle « {ml['nom']} » ?\n"
                "Le fichier sera déplacé dans documents/archives.", parent=self):
            return
        try:
            self.auth.exiger("documents.delete_template", contexte="suppression modèle")
        except PermissionError as e:
            messagebox.showerror("Erreur", str(e)); return
        fichier = ml.get("fichier")
        if fichier and Path(fichier).is_file():
            try:
                shutil.move(fichier, str(DOC_ARC / Path(fichier).name))
            except OSError:
                pass
        self.db.exec("DELETE FROM document_template WHERE id=?", (mid,))
        self.db.commit()
        self.db.audit(self.auth.uid, self.auth.ulogin, "SUPPRIMER_MODELE",
                      "document_template", mid, {"nom": ml["nom"]})
        self.actualiser_modeles()

    def defaut_modele(self):
        mid = self._sel_modele()
        if not mid: return
        ml = self.db.un("SELECT * FROM document_template WHERE id=?", (mid,))
        try:
            self.auth.exiger("documents.edit_template",
                             contexte=f"défaut {ml['type']}")
        except PermissionError as e:
            messagebox.showerror("Erreur", str(e)); return
        self.db.exec("UPDATE document_template SET par_defaut=0 WHERE avec_id=? AND type=?",
                     (self.avec_id, ml["type"]))
        self.db.exec("UPDATE document_template SET par_defaut=1, "
                     "modifie_le=datetime('now','localtime') WHERE id=?", (mid,))
        self.db.commit()
        self.db.audit(self.auth.uid, self.auth.ulogin, "MODELE_PAR_DEFAUT",
                      "document_template", mid, {"type": ml["type"]})
        self.actualiser_modeles()

    def generer(self):
        DlgGenererDocument(self, self.db, self.auth, self.avec_id,
                           callback=self.actualiser_generes)

    def _tab_recus(self, nb):
        tab = ttk.Frame(nb)
        nb.add(tab, text="Reçus")
        tab.columnconfigure(0, weight=1); tab.rowconfigure(1, weight=1)
        bar = ttk.Frame(tab)
        bar.grid(row=0, column=0, sticky="ew", padx=12, pady=8)
        ttk.Label(bar, text="Historique des reçus", style="Titre.TLabel").pack(side="left")
        ttk.Label(bar, text="Recherche :").pack(side="left", padx=(16, 4))
        self.v_rech_r = tk.StringVar()
        self.v_rech_r.trace("w", lambda *a: self.actualiser_recus())
        ttk.Entry(bar, textvariable=self.v_rech_r, width=18).pack(side="left")
        for txt, cmd, st, perm in [
            ("Voir le reçu",    self.voir_recu,   "Bleu.TButton", "receipts.view"),
            ("Réimprimer",      self.reimprimer,  "Vert.TButton", "receipts.reprint"),
            ("Enregistrer PDF", self.recu_pdf,    "TButton",      "receipts.view"),
            ("Actualiser",      self.actualiser_recus, "TButton", "receipts.view"),
        ]:
            if not self.auth.permis(perm):
                continue
            btn(bar, txt, cmd, st).pack(side="right", padx=3)

        cols = ("N° Reçu","Date","Type","Membre","Montant","Devise","Utilisateur")
        lrg  = [130, 145, 170, 180, 110, 60, 100]
        self.tv_r, f = treeview(tab, cols, lrg)
        f.grid(row=1, column=0, sticky="nsew", padx=12, pady=4)
        self.tv_r.bind("<Double-1>", lambda e: self.voir_recu())
        self.actualiser_recus()

    def actualiser_recus(self):
        for it in self.tv_r.get_children():
            self.tv_r.delete(it)
        terme = self.v_rech_r.get().strip().lower() if hasattr(self, "v_rech_r") else ""
        rows = self.db.tous("""
            SELECT r.*, m.nom, m.prenom, m.numero, u.nom as unom
            FROM receipt r LEFT JOIN membre m ON r.membre_id=m.id
            LEFT JOIN utilisateur u ON r.cree_par=u.id
            WHERE r.avec_id=? ORDER BY r.id DESC LIMIT 600
        """, (self.avec_id,))
        for i, r in enumerate(rows):
            nc = f"{r['nom'] or ''} {r['prenom'] or ''}".strip() or "—"
            if terme and terme not in (r["recu_no"] + " " + nc).lower():
                continue
            self.tv_r.insert("", "end", iid=str(r["id"]),
                             tags=("p" if i % 2 == 0 else "i"), values=(
                r["recu_no"], r["cree_le"] or "", Recep.ligne(r["type"]), nc,
                f"{r['montant'] or 0:,.0f}", r["devise"] or DEVISE_DEFAUT,
                r["unom"] or "—"))

    def _sel_recu(self):
        s = self.tv_r.focus()
        if not s:
            messagebox.showwarning("Sélection", "Sélectionnez un reçu.")
            return None
        return int(s)

    def _recu_complet(self, rid):
        r = self.db.un("SELECT * FROM receipt WHERE id=?", (rid,))
        if not r: return None
        membre = self.db.un("SELECT * FROM membre WHERE id=?", (r["membre_id"],)) or {}
        avec = self.db.un("SELECT * FROM avec WHERE id=?", (r["avec_id"],)) or {}
        details = {}
        try:
            details = json.loads(r["details"] or "{}")
        except ValueError:
            details = {}
        return r, avec, membre, details

    def voir_recu(self):
        rid = self._sel_recu()
        if not rid: return
        try:
            self.auth.exiger("receipts.view", contexte="consulter reçu")
        except PermissionError as e:
            messagebox.showerror("Erreur", str(e)); return
        r, avec, membre, details = self._recu_complet(rid)
        texte = Recep.texte(r, avec, membre, details)
        dlg = tk.Toplevel(self); dlg.title(f"Reçu {r['recu_no']}")
        dlg.resizable(False, False)
        centrer(dlg, 600, 520)
        from tkinter import scrolledtext
        st = scrolledtext.ScrolledText(dlg, width=66, height=24, font=("Courier", 9))
        st.pack(fill="both", expand=True, padx=10, pady=10)
        st.insert("1.0", texte); st.config(state="disabled")

    def reimprimer(self):
        rid = self._sel_recu()
        if not rid: return
        try:
            self.auth.exiger("receipts.reprint", contexte="réimpression reçu")
        except PermissionError as e:
            messagebox.showerror("Erreur", str(e)); return
        r, avec, membre, details = self._recu_complet(rid)
        imprimer_recu(self, self.auth, r, avec, membre, details or None,
                      (self.auth.user or {}).get("nom", ""),
                      (self.auth.user or {}).get("role", ""), reimprime=True)

    def recu_pdf(self):
        rid = self._sel_recu()
        if not rid: return
        try:
            self.auth.exiger("receipts.view", contexte="export PDF reçu")
        except PermissionError as e:
            messagebox.showerror("Erreur", str(e)); return
        r, avec, membre, details = self._recu_complet(rid)
        texte = Recep.texte(r, avec, membre, details)
        pdf_path = str(DOC_REC / (r["recu_no"] + ".pdf"))
        PDFGen.generer(texte.split("\n"), pdf_path)
        self.db.audit(self.auth.uid, self.auth.ulogin, "RECU_EXPORT_PDF",
                      "receipt", rid, {"recu_no": r["recu_no"]})
        messagebox.showinfo("Export PDF", f"Reçu enregistré :\n{pdf_path}")

    def _tab_generes(self, nb):
        tab = ttk.Frame(nb)
        nb.add(tab, text="Documents générés")
        tab.columnconfigure(0, weight=1); tab.rowconfigure(1, weight=1)
        bar = ttk.Frame(tab)
        bar.grid(row=0, column=0, sticky="ew", padx=12, pady=8)
        ttk.Label(bar, text="Documents générés depuis les modèles",
                  style="Titre.TLabel").pack(side="left")
        btn(bar, "Ouvrir le dossier", self.ouvrir_dossier).pack(side="right", padx=3)
        btn(bar, "Actualiser", self.actualiser_generes).pack(side="right", padx=3)

        cols = ("ID","Date","Type","Nom du fichier","Utilisateur")
        lrg  = [40, 150, 150, 420, 110]
        self.tv_g, f = treeview(tab, cols, lrg)
        f.grid(row=1, column=0, sticky="nsew", padx=12, pady=4)
        self.actualiser_generes()

    def actualiser_generes(self):
        for it in self.tv_g.get_children():
            self.tv_g.delete(it)
        rows = self.db.tous("""
            SELECT d.*, u.nom as unom FROM document_genere d
            LEFT JOIN utilisateur u ON d.cree_par=u.id
            WHERE d.avec_id=? ORDER BY d.id DESC LIMIT 400
        """, (self.avec_id,))
        for i, r in enumerate(rows):
            self.tv_g.insert("", "end", iid=str(r["id"]),
                             tags=("p" if i % 2 == 0 else "i"), values=(
                r["id"], r["cree_le"] or "", r["type"] or "",
                r["nom_fichier"] or "", r["unom"] or "—"))

    def ouvrir_dossier(self):
        try:
            Imprimeur.ouvrir(str(DOC_GEN))
        except Exception:
            messagebox.showinfo("Documents", f"Dossier :\n{DOC_GEN}")


class DlgGenererDocument(tk.Toplevel):
    """Génère un document depuis un modèle avec les variables {{...}}."""

    def __init__(self, parent, db, auth, avec_id, callback=None):
        super().__init__(parent)
        self.db = db; self.auth = auth; self.avec_id = avec_id; self.cb = callback
        self.title("Générer un document")
        self.geometry("760x600")
        self.grab_set()
        Modeles._creer_dossiers()
        self._ui()
        self._maj_contexte()

    def _ui(self):
        frm = ttk.Frame(self, padding=14)
        frm.pack(fill="both", expand=True)
        frm.columnconfigure(1, weight=1); frm.rowconfigure(4, weight=1)

        self.modeles = self.db.tous("""
            SELECT * FROM document_template WHERE avec_id=? ORDER BY par_defaut DESC, nom
        """, (self.avec_id,))
        if not self.modeles:
            ttk.Label(frm, text="Aucun modèle disponible pour cette AVEC.\n"
                                "Ajoutez d'abord un modèle (onglet Modèles).",
                      foreground=C["rouge"]).grid(row=0, column=0, columnspan=3, pady=20)
            return

        ttk.Label(frm, text="Modèle *").grid(row=0, column=0, sticky="e", padx=(0, 8), pady=5)
        self.v_ml = tk.StringVar()
        cbm = ttk.Combobox(frm, textvariable=self.v_ml,
                           values=[f"{m['nom']} ({m['type']})" for m in self.modeles],
                           state="readonly", width=34)
        cbm.grid(row=0, column=1, sticky="ew", pady=5)
        cbm.bind("<<ComboboxSelected>>", lambda e: self._apercu())

        ttk.Label(frm, text="Membre").grid(row=1, column=0, sticky="e", padx=(0, 8), pady=5)
        membres = self.db.tous("SELECT id,nom,prenom,numero,nb_parts,telephone,adresse,statut "
                               "FROM membre WHERE avec_id=? ORDER BY nom",
                               (self.avec_id,))
        self.mmap = {f"{m['nom']} {m['prenom'] or ''}".strip(): m for m in membres}
        self.v_mm = tk.StringVar()
        cbm2 = ttk.Combobox(frm, textvariable=self.v_mm, values=list(self.mmap.keys()),
                            state="readonly", width=34)
        cbm2.grid(row=1, column=1, sticky="ew", pady=5)
        cbm2.bind("<<ComboboxSelected>>", lambda e: self._maj_contexte())

        ttk.Label(frm, text="Crédit").grid(row=2, column=0, sticky="e", padx=(0, 8), pady=5)
        self.v_cr = tk.StringVar()
        self.crmap = {}
        self.cb_cr = ttk.Combobox(frm, textvariable=self.v_cr, state="readonly", width=34)
        self.cb_cr.grid(row=2, column=1, sticky="ew", pady=5)
        self.cb_cr.bind("<<ComboboxSelected>>", lambda e: self._maj_contexte())

        ttk.Label(frm, text="Champs supplémentaires").grid(
            row=3, column=0, sticky="ne", padx=(0, 8), pady=5)
        self.txt_vars = tk.Text(frm, width=38, height=5, font=(FONT, 9))
        self.txt_vars.grid(row=3, column=1, columnspan=2, sticky="ew", pady=5)
        ttk.Label(frm, text="Une variable par ligne :  NOM=valeur", foreground=C["texte_mute"],
                  font=(FONT, 8)).grid(row=3, column=2, sticky="w", padx=(6, 0))

        apercu_f = ttk.LabelFrame(frm, text="Prévisualisation (données réelles)")
        apercu_f.grid(row=4, column=0, columnspan=3, sticky="nsew", pady=6)
        apercu_f.columnconfigure(0, weight=1); apercu_f.rowconfigure(0, weight=1)
        self.txt_ap = tk.Text(apercu_f, width=80, height=12, font=("Courier", 9))
        self.txt_ap.grid(row=0, column=0, sticky="nsew")
        barre = ttk.Scrollbar(apercu_f, command=self.txt_ap.yview)
        barre.grid(row=0, column=1, sticky="ns")
        self.txt_ap.config(yscrollcommand=barre.set)

        bande = ttk.Frame(frm)
        bande.grid(row=5, column=0, columnspan=3, pady=10)
        btn(bande, "Prévisualiser", self._apercu).pack(side="left", padx=4)
        btn(bande, "Générer", self._generer, "Vert.TButton").pack(side="left", padx=4)
        btn(bande, "Imprimer", self._imprimer, "Bleu.TButton").pack(side="left", padx=4)
        btn(bande, "Exporter PDF", self._pdf).pack(side="left", padx=4)
        btn(bande, "Fermer", self.destroy).pack(side="right", padx=4)
        self._apercu()

    def _ml(self):
        lbl = self.v_ml.get()
        for m in self.modeles:
            if f"{m['nom']} ({m['type']})" == lbl:
                return m
        return None

    def _maj_contexte(self, ev=None):
        if not hasattr(self, "v_mm"):
            return
        # Crédits du membre sélectionné
        nom = self.v_mm.get()
        m = self.mmap.get(nom)
        if m:
            creds = self.db.tous("""
                SELECT * FROM credit WHERE membre_id=? AND statut IN ('actif','en_retard')
            """, (m["id"],))
            self.crmap = {f"Crédit #{c['id']} — Solde {Finance.solde_credit(c):,.0f} "
                          f"{c['devise'] or DEVISE_DEFAUT}":
                          c for c in creds}
            self.cb_cr["values"] = list(self.crmap.keys())
            self.v_cr.set(list(self.crmap.keys())[0] if self.crmap else "")
        else:
            self.crmap = {}
            self.cb_cr["values"] = []
            self.v_cr.set("")
        self._apercu()

    def _valeurs(self):
        avec = self.db.un("SELECT * FROM avec WHERE id=?", (self.avec_id,))
        nom = self.v_mm.get()
        m = self.mmap.get(nom)
        cr = None
        lblc = self.v_cr.get() if hasattr(self, "v_cr") else ""
        if self.crmap and lblc in self.crmap:
            cr = self.crmap[lblc]
        contexte = {}
        for ligne in self.txt_vars.get("1.0", "end").splitlines():
            if "=" in ligne:
                k, v = ligne.split("=", 1)
                if k.strip():
                    contexte[k.strip().upper()] = v
        if "SESSION_NUMERO" not in contexte or "DATE_REUNION" not in contexte:
            sess = self.db.un(
                "SELECT id, numero, date_reunion FROM session WHERE avec_id=? "
                "ORDER BY id DESC LIMIT 1", (self.avec_id,))
            if sess:
                contexte.setdefault("SESSION_NUMERO",
                                    str(sess["numero"] or sess["id"]))
                contexte.setdefault("DATE_REUNION", sess["date_reunion"] or "")
        return Modeles.valeurs_standard(
            avec, membre=m, credit=cr, contexte=contexte, auth=self.auth)

    def _contenu_substitue(self):
        ml = self._ml()
        if not ml:
            return "", None
        contenu = Modeles.lire_contenu(ml["fichier"]) if ml["fichier"] else ml.get("contenu") or ""
        return Modeles.substituer(contenu, self._valeurs()), ml

    def _apercu(self):
        contenu, ml = self._contenu_substitue()
        self.txt_ap.config(state="normal")
        self.txt_ap.delete("1.0", "end")
        if not ml:
            self.txt_ap.insert("1.0", "Sélectionnez un modèle.")
        else:
            self.txt_ap.insert("1.0",
                Modeles.texte_apercu(contenu, ml["format"])[:12000])
        self.txt_ap.config(state="disabled")

    def _sortie(self, ml):
        hor = datetime.now().strftime("%Y%m%d_%H%M%S")
        nom = re.sub(r"[^A-Za-z0-9_\-]", "_", ml["nom"])
        return str(DOC_GEN / f"{hor}_{nom}.{ml['format']}")

    def _generer(self, ouvrir_apres=False):
        try:
            self.auth.exiger("documents.generate", contexte="génération document")
            ml = self._ml()
            if not ml:
                raise ValueError("Sélectionnez un modèle.")
            sortie = self._sortie(ml)
            Modeles.generer(ml, self._valeurs(), sortie)
            self.db.exec("INSERT INTO document_genere"
                         "(avec_id,template_id,type,nom_fichier,variables,cree_par)"
                         " VALUES(?,?,?,?,?,?)",
                         (self.avec_id, ml["id"], ml["type"], Path(sortie).name,
                          json.dumps(self._valeurs(), ensure_ascii=False),
                          self.auth.uid))
            self.db.commit()
            self.db.audit(self.auth.uid, self.auth.ulogin, "GENERER_DOCUMENT",
                          "document_template", ml["id"],
                          {"fichier": Path(sortie).name, "type": ml["type"]})
            messagebox.showinfo("Document généré",
                                f"Fichier créé :\n{sortie}", parent=self)
            if self.cb: self.cb()
            if ouvrir_apres:
                return sortie
            return sortie
        except (PermissionError, ValueError, sqlite3.Error, OSError) as e:
            messagebox.showerror("Erreur", str(e), parent=self)

    def _imprimer(self):
        try:
            self.auth.exiger("documents.print", contexte="impression document")
        except PermissionError as e:
            messagebox.showerror("Erreur", str(e), parent=self); return
        sortie = self._generer()
        if not sortie:
            return
        if Imprimeur.imprimer(sortie):
            self.db.audit(self.auth.uid, self.auth.ulogin, "DOCUMENT_IMPRIME",
                          details={"fichier": Path(sortie).name})
            messagebox.showinfo("Impression", "Document envoyé à l'imprimante.",
                                parent=self)
        else:
            messagebox.showwarning(
                "Impression indisponible",
                "Aucune imprimante détectée.\nLe document a été généré dans :\n%s"
                % sortie, parent=self)

    def _pdf(self):
        try:
            self.auth.exiger("documents.export", contexte="export PDF document")
        except PermissionError as e:
            messagebox.showerror("Erreur", str(e), parent=self); return
        ml = self._ml()
        if not ml:
            messagebox.showwarning("Modèle", "Sélectionnez un modèle."); return
        try:
            contenu = Modeles.texte_apercu(self._contenu_substitue()[0], ml["format"])
        except (ValueError, OSError) as e:
            messagebox.showerror("Erreur", str(e), parent=self)
            return
        pdf = str(DOC_GEN / Path(self._sortie(ml)).stem + ".pdf")
        try:
            PDFGen.generer(contenu.split("\n"), pdf)
        except (OSError, ValueError) as e:
            messagebox.showerror("Erreur", str(e), parent=self)
            return
        self.db.audit(self.auth.uid, self.auth.ulogin, "DOCUMENT_EXPORT_PDF",
                      details={"fichier": Path(pdf).name})
        messagebox.showinfo("Export PDF",
                            f"Document PDF généré :\n{pdf}", parent=self)


# ════════════════════════════════════════════════════════════════
#  PARAMÈTRES — INFORMATIONS AVEC + IMPRESSION + SAUVEGARDES
# ════════════════════════════════════════════════════════════════

class OngletParametres(ttk.Frame):
    """Informations de l'AVEC, paramètres financiers, sauvegardes."""

    def __init__(self, parent, db, auth, avec_id=1):
        super().__init__(parent)
        self.db = db; self.auth = auth; self.avec_id = avec_id
        self.bkp = Backup()
        self.columnconfigure(0, weight=1)
        self._ui()

    def _ui(self):
        a = self.db.un("SELECT * FROM avec WHERE id=?", (self.avec_id,)) or {}

        # ── Informations générales ──────────────────────────────
        frm = ttk.LabelFrame(self, text="Informations de l'AVEC", padding=16)
        frm.pack(fill="x", padx=16, pady=(14, 8))
        frm.columnconfigure(1, weight=1)

        champs = [
            ("nom", "Nom de l'AVEC *", a.get("nom", "")),
            ("adresse", "Adresse", a.get("adresse") or ""),
            ("telephone", "Téléphone", a.get("telephone") or ""),
            ("email", "E-mail", a.get("email") or ""),
            ("devise", "Devise principale", a.get("devise") or DEVISE_DEFAUT),
            ("description", "Description", a.get("description") or ""),
            ("montant_part", "Montant de la part", str(a.get("montant_part") or "")),
        ]
        self.vs = {}
        for i, (cle, lib, val) in enumerate(champs):
            self.vs[cle], _ = champ(frm, lib, i, val)
        self.v_auto = tk.BooleanVar(value=bool(int(a.get("impression_auto") or 0)))
        ttk.Checkbutton(frm, text="Imprimer automatiquement les reçus après une opération",
                        variable=self.v_auto).grid(row=len(champs), column=0,
                                                   columnspan=2, sticky="w", pady=8)

        bf = ttk.Frame(frm)
        bf.grid(row=len(champs) + 1, column=0, columnspan=2, pady=8)
        btn(bf, "Enregistrer les paramètres", self._enregistrer,
            "Vert.TButton").pack(side="left", padx=8)
        if not self.auth.permis("settings.edit"):
            for w in frm.winfo_children():
                if isinstance(w, ttk.Entry):
                    w.configure(state="disabled")

        # ── Paramètres financiers ───────────────────────────────
        fin = ttk.LabelFrame(self, text="Paramètres financiers", padding=16)
        fin.pack(fill="x", padx=16, pady=8)
        fin.columnconfigure(1, weight=1)

        self.vf = {}
        champs_fin = [
            ("taux_interet", "Taux d'intérêt annuel — standard (ex : 0.10 = 10 %)",
             str(a.get("taux_interet") or TAUX_INTERET_DEFAUT)),
            ("taux_interet_urgence", "Taux d'intérêt annuel — urgence (ex : 0.15)",
             str(a.get("taux_interet_urgence") or 0.15)),
            ("taux_interet_investissement", "Taux d'intérêt annuel — investissement (ex : 0.10)",
             str(a.get("taux_interet_investissement") or 0.10)),
            ("taux_penalite", "Taux de pénalité de retard mensuel (ex : 0.02 = 2 %/mois)",
             str(a.get("taux_penalite") or TAUX_PENALITE_DEFAUT)),
        ]
        for i, (cle, lib, val) in enumerate(champs_fin):
            self.vf[cle], _ = champ(fin, lib, i, val)

        self.dev_bv = {d: tk.BooleanVar(value=d in _devises_autorisees(a))
                       for d in DEVISES}
        ttk.Label(fin, text="Devises autorisées :").grid(
            row=len(champs_fin), column=0, sticky="nw", padx=(0, 8), pady=6)
        devf = ttk.Frame(fin)
        devf.grid(row=len(champs_fin), column=1, sticky="w", pady=4)
        for d in DEVISES:
            ttk.Checkbutton(devf, text=d, variable=self.dev_bv[d]).pack(
                side="left", padx=8)

        self.typ_bv = {t: tk.BooleanVar(value=t in _types_credit_avec(a))
                       for t in TYPES_CREDIT}
        ttk.Label(fin, text="Types de crédit autorisés :").grid(
            row=len(champs_fin) + 1, column=0, sticky="nw", padx=(0, 8), pady=6)
        tyf = ttk.Frame(fin)
        tyf.grid(row=len(champs_fin) + 1, column=1, sticky="w", pady=4)
        for t in TYPES_CREDIT:
            ttk.Checkbutton(tyf, text=_le_libelle_type_credit(t),
                            variable=self.typ_bv[t]).pack(side="left", padx=8)

        bff = ttk.Frame(fin)
        bff.grid(row=len(champs_fin) + 2, column=0, columnspan=2, pady=10)
        btn(bff, "Enregistrer les paramètres financiers", self._enregistrer_fin,
            "Vert.TButton").pack(side="left", padx=8)
        ttk.Label(fin, text="Ces taux sont figés (clichés) sur chaque crédit à "
                            "l'octroi ; les crédits existants ne changent pas.",
                  font=(FONT, 9, "italic"), foreground=C["texte_mute"]).grid(
            row=len(champs_fin) + 3, column=0, columnspan=2, sticky="w", pady=(0, 4))
        if not self.auth.permis("settings.financial.edit"):
            for w in fin.winfo_children():
                if isinstance(w, ttk.Entry):
                    w.configure(state="disabled")
            for d in DEVISES:
                self.dev_bv[d].set(False)
            for t in TYPES_CREDIT:
                self.typ_bv[t].set(False)

        # Zone sauvegardes
        bk = ttk.LabelFrame(self, text="Sauvegardes de la base de données", padding=16)
        bk.pack(fill="x", padx=16, pady=8)
        last = Backup.derniere_sauvegarde()
        ttk.Label(bk, text="Dernière sauvegarde : %s"
                           % (last or "aucune encore")).pack(anchor="w")
        bb = ttk.Frame(bk)
        bb.pack(anchor="w", pady=8)
        if self.auth.permis("backup.create"):
            btn(bb, "Sauvegarder maintenant", self._sauver, "Vert.TButton").pack(
                side="left", padx=4)
        if self.auth.permis("backup.restore"):
            btn(bb, "Restaurer la dernière sauvegarde", self._restaurer,
                "Rouge.TButton").pack(side="left", padx=4)

    def _enregistrer(self):
        try:
            self.auth.exiger("settings.edit", contexte="modification paramètres AVEC")
            nom = self.vs["nom"].get().strip()
            if not nom:
                raise ValueError("Le nom de l'AVEC est obligatoire.")
            try:
                mp = float(self.vs["montant_part"].get() or 0)
            except ValueError:
                raise ValueError("Montant de la part invalide.")
            if mp <= 0:
                raise ValueError("Vérifiez : montant de la part > 0.")
            dev = self.vs["devise"].get().strip().upper()
            if dev not in DEVISES:
                dev = DEVISE_DEFAUT
            self.db.exec("""
                UPDATE avec SET nom=?,adresse=?,telephone=?,email=?,devise=?,
                description=?,montant_part=?,impression_auto=? WHERE id=?
            """, (nom, self.vs["adresse"].get().strip() or None,
                  self.vs["telephone"].get().strip() or None,
                  self.vs["email"].get().strip() or None,
                  dev,
                  self.vs["description"].get().strip() or None,
                  mp, 1 if self.v_auto.get() else 0, self.avec_id))
            self.db.commit()
            self.db.audit(self.auth.uid, self.auth.ulogin, "MODIFIER_AVEC",
                          "avec", self.avec_id, {"nom": nom, "devise": dev})
            messagebox.showinfo("Paramètres", "Paramètres de l'AVEC enregistrés.")
        except (PermissionError, ValueError, sqlite3.Error) as e:
            messagebox.showerror("Erreur", str(e))

    def _enregistrer_fin(self):
        try:
            self.auth.exiger("settings.financial.edit",
                             contexte="modification paramètres financiers")
            a = self.db.un("SELECT * FROM avec WHERE id=?", (self.avec_id,)) or {}
            try:
                vals = {cle: float(self.vf[cle].get() or 0)
                        for cle in ("taux_interet", "taux_interet_urgence",
                                    "taux_interet_investissement", "taux_penalite")}
            except ValueError:
                raise ValueError("Taux invalides.")
            for lib, v in vals.items():
                if not (0 < v <= 1):
                    raise ValueError(
                        f"Taux « {lib} » invalide : il doit être entre 0 et 1.")
            devises = [d for d in DEVISES if self.dev_bv[d].get()]
            types = [t for t in TYPES_CREDIT if self.typ_bv[t].get()]
            if not devises:
                raise ValueError("Sélectionnez au moins une devise autorisée.")
            if not types:
                raise ValueError("Sélectionnez au moins un type de crédit.")
            old = {k: (a.get(k)) for k in vals}
            self.db.exec("""
                UPDATE avec SET taux_interet=?,taux_interet_urgence=?,
                taux_interet_investissement=?,taux_penalite=?,
                devises_autorisees=?,types_credit=? WHERE id=?
            """, (vals["taux_interet"], vals["taux_interet_urgence"],
                  vals["taux_interet_investissement"], vals["taux_penalite"],
                  json.dumps(devises), json.dumps(types), self.avec_id))
            self.db.commit()
            old["devises_autorisees"] = a.get("devises_autorisees")
            old["types_credit"] = a.get("types_credit")
            self.db.audit(self.auth.uid, self.auth.ulogin,
                          "MODIFIER_PARAMS_FINANCIERS", "avec", self.avec_id,
                          {"avant": old,
                           "après": {"taux_interet": vals["taux_interet"],
                                     "taux_interet_urgence": vals["taux_interet_urgence"],
                                     "taux_interet_investissement": vals["taux_interet_investissement"],
                                     "taux_penalite": vals["taux_penalite"],
                                     "devises_autorisees": devises,
                                     "types_credit": types}})
            messagebox.showinfo(
                "Paramètres financiers",
                "Paramètres financiers enregistrés.\n"
                "Les crédits déjà octroyés conservent leurs taux.\n"
                "Les nouveaux crédits utilisent ces paramètres.")
        except (PermissionError, ValueError, sqlite3.Error) as e:
            messagebox.showerror("Erreur", str(e))

    def _sauver(self):
        try:
            self.auth.exiger("backup.create", contexte="sauvegarde manuelle")
        except PermissionError as e:
            messagebox.showerror("Erreur", str(e)); return
        try:
            dest = self.bkp.sauvegarder()
            self.db.audit(self.auth.uid, self.auth.ulogin, "SAUVEGARDE",
                          details={"dest": dest, "source": "parametres"})
            messagebox.showinfo("Sauvegarde réussie",
                                f"Base de données sauvegardée :\n{dest}")
        except Exception as e:
            messagebox.showerror("Erreur sauvegarde", str(e))

    def _restaurer(self):
        try:
            self.auth.exiger("backup.restore", contexte="restauration sauvegarde")
        except PermissionError as e:
            messagebox.showerror("Erreur", str(e)); return
        dernier = Backup.derniere_sauvegarde()
        if not dernier:
            messagebox.showwarning("Aucune sauvegarde",
                                   "Aucune sauvegarde disponible dans :\n%s" % BACKUP_DIR)
            return
        if not messagebox.askyesno(
                "Restaurer la sauvegarde",
                "Restaurer la dernière sauvegarde ?\n\n"
                f"Fichier : {dernier}\n\n"
                "ATTENTION : la base actuelle sera remplacée.\n"
                "Il est conseillé de sauvegarder d'abord la base courante.",
                parent=self):
            return
        try:
            self.bkp.sauvegarder()   # filet de sécurité
        except Exception:
            pass
        Backup.restaurer()
        messagebox.showinfo("Restauration",
                            "Sauvegarde restaurée.\nReconnectez-vous pour continuer.",
                            parent=self)


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
        self.db = self._ouvrir_base_securisee()
        if self.db is None:
            self.destroy()
            return
        self.auth = Auth(self.db)
        self.bkp  = Backup()
        self._backup_after_id = None

        self.protocol("WM_DELETE_WINDOW", self._quitter)
        self._lancer_connexion()

    def _ouvrir_base_securisee(self):
        """Ouvre la base ; en cas de corruption, propose une restauration propre.

        Retourne une instance DB fonctionnelle, ou None (application fermée).
        Ne détruit jamais les données sans accord explicite de l'utilisateur.
        """
        try:
            return DB()
        except sqlite3.DatabaseError:
            dernier = Backup.derniere_sauvegarde()
            if dernier:
                date_bkp = datetime.fromtimestamp(
                    os.path.getmtime(dernier)).strftime("%d/%m/%Y à %H:%M")
                reponse = messagebox.askyesno(
                    "Base de données endommagée",
                    "Le fichier akibacore.db est illisible ou corrompu.\n\n"
                    f"Une sauvegarde du {date_bkp} est disponible.\n"
                    "Voulez-vous la restaurer maintenant ?\n\n"
                    "(La base actuelle sera remplacée par cette sauvegarde.)")
            else:
                reponse = False
            if reponse:
                try:
                    Backup.restaurer()
                    return DB()
                except Exception:
                    pass
            messagebox.showerror(
                "AkibaCore — Impossible de démarrer",
                "La base de données est corrompue et aucune restauration "
                "n'a été effectuée.\n\n"
                "Pour récupérer vos données manuellement :\n"
                "1. Fermez cette fenêtre.\n"
                "2. Ouvrez le dossier 'sauvegardes'.\n"
                "3. Copiez la sauvegarde la plus récente et renommez-la "
                "'akibacore.db' dans le dossier de l'application.")
            return None

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
                 font=(FONT, 12, "bold")).pack(side="left", pady=7)
        u = self.auth.user
        tk.Label(top,
                 text=f"{u['nom']}  |  {u['role'].upper()}  |  {date.today().strftime('%d/%m/%Y')}   ",
                 fg="#AED6F1", bg=C["bleu"], font=(FONT, 9)).pack(side="right", pady=10)

        # ─ Barre latérale + zone de contenu ─
        self.avec_id = 1
        onglets = [
            ("Tableau de Bord", "\u2302",  Dashboard, None),
            ("Membres",         "\u263A",  OngletMembres, "members"),
            ("Épargnes",        "\u25C7",  OngletEpargnes, "savings"),
            ("Crédits",         "\u25B6",  OngletCredits, "loans"),
            ("Remboursements",  "\u25C0",  OngletRemboursements, "repayments"),
            ("Comptes",         "\u25A3",  OngletComptes, "accounts"),
            ("Sessions",        "\u25A0",  OngletSessions, "sessions"),
            ("Rapports",        "\u25CF",  OngletRapports, "reports"),
            ("Administration",  "\u2699",  OngletAdmin, ("users", "audit")),
            ("Documents",       "\u2756",  OngletDocuments, "documents"),
            ("Paramètres",      "\u25CE",  OngletParametres, "settings"),
        ]
        # Chaque page n'apparaît que si l'utilisateur possède au moins une
        # permission correspondante (ou est admin, qui a toutes les permissions).
        def _page_autorisee(prefixes):
            if prefixes is None:        # Tableau de Bord : toujours visible
                return True
            if self.auth.est_admin:
                return True
            if isinstance(prefixes, str):
                prefixes = [prefixes]
            return any(
                self.auth.permis(code)
                for code, _lib, _grp in PERMISSIONS
                for pref in prefixes
                if code.startswith(pref + ".")
            )
        self._onglets_defs = [
            (nom, ic, Cls) for nom, ic, Cls, prefixes in onglets
            if _page_autorisee(prefixes)
        ]
        if not self._onglets_defs:
            self._onglets_defs = [("Tableau de Bord", "\u2302", Dashboard)]
        mid = tk.Frame(self, bg=C["gris"])
        mid.pack(fill="both", expand=True)

        items_nav = [(n, ic) for n, ic, _ in self._onglets_defs]
        # Conteneur créé AVANT la sidebar : selectionner(0) appelle
        # immédiatement _naviguer() qui en a besoin.
        self._conteneur = tk.Frame(mid, bg=C["gris"])
        self._sidebar = Sidebar(mid, items_nav, self._naviguer)
        self._sidebar.pack(side="left", fill="y")
        self._conteneur.pack(side="left", fill="both", expand=True)
        self._sidebar.selectionner(0)

        # ─ Barre inférieure ─
        bas = tk.Frame(self, bg=C["gris_f"], height=26)
        bas.pack(fill="x", side="bottom")
        bas.pack_propagate(False)
        self.v_statut = tk.StringVar(value="Prêt.")
        tk.Label(bas, textvariable=self.v_statut,
                 bg=C["gris_f"], font=(FONT, 9)).pack(side="left", padx=10, pady=4)
        for lbl, cmd in [("Changer mot de passe", self._changer_mdp),
                          ("Se déconnecter",       self._deconnecter)]:
            tk.Button(bas, text=lbl, command=cmd, relief="flat",
                      bg=C["gris_f"], font=(FONT, 9),
                       cursor="hand2").pack(side="right", padx=10, pady=4)

    def _naviguer(self, index):
        """Charge l'onglet correspondant dans la zone de contenu.

        Une erreur pendant la construction d'une page ne doit JAMAIS laisser
        une fenêtre vide (page blanche) : elle est journalisée et un message
        clair est affiché avec une référence traçable.
        """
        for w in self._conteneur.winfo_children():
            w.destroy()
        try:
            _, _, Cls = self._onglets_defs[index]
            page = Cls(self._conteneur, self.db, self.auth, self.avec_id)
            page.pack(fill="both", expand=True)
        except Exception as exc:
            ref = "AKB-" + str(int(datetime.now().timestamp() * 1000) % 1000000)
            import traceback
            try:
                journal = REPERTOIRE_DONNEES / "erreur_demarrage.log"
                with open(journal, "a", encoding="utf-8") as f:
                    f.write("\n" + "=" * 60 + "\n")
                    f.write(f"[{ref}] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                            f" — échec affichage page (index {index})\n")
                    traceback.print_exc(file=f)
            except Exception:
                pass
            # Reconstruit un contenu minimal pour éviter la page blanche.
            try:
                cadre = tk.Frame(self._conteneur, bg=C["gris"])
                cadre.pack(fill="both", expand=True)
                ttk.Label(
                    cadre,
                    text="Une erreur est survenue lors de l'affichage de cette page.\n\n"
                         "Veuillez réessayer ou contacter l'administrateur.",
                    style="Titre.TLabel",
                ).pack(pady=40)
                ttk.Label(
                    cadre,
                    text=f"Référence : {ref}",
                    font=(FONT, 10),
                ).pack()
            except Exception:
                pass
            try:
                messagebox.showerror(
                    "AkibaCore — Erreur",
                    "Une erreur est survenue.\n"
                    "Veuillez contacter l'administrateur.\n\n"
                    f"Référence : {ref}",
                    parent=self,
                )
            except Exception:
                pass

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
    try:
        app = AkibaCore()
        app.mainloop()
    except SystemExit:
        raise
    except BaseException as exc:
        # Un échec au démarrage ne doit JAMAIS être silencieux :
        # trace écrite dans erreur_demarrage.log + boîte de dialogue.
        import traceback
        try:
            journal = REPERTOIRE_DONNEES / "erreur_demarrage.log"
            with open(journal, "a", encoding="utf-8") as f:
                f.write("\n" + "=" * 60 + "\n")
                f.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n")
                traceback.print_exc(file=f)
        except Exception:
            journal = None
        try:
            r = tkinter.Tk()
            r.withdraw()
            msg = (
                "AkibaCore n'a pas pu démarrer.\n\n"
                f"Erreur : {type(exc).__name__}: {exc}\n\n"
                "Vérifiez :\n"
                "  • que le dossier du programme est accessible en écriture ;\n"
                "  • qu'aucune autre instance n'est déjà ouverte.\n"
            )
            if journal is not None:
                msg += f"\nDétails techniques enregistrés dans :\n{journal}"
            tkinter.messagebox.showerror("AkibaCore — Erreur de démarrage", msg)
            r.destroy()
        except Exception:
            pass
        raise
