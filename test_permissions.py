#!/usr/bin/env python3
"""Tests des permissions et des rôles AkibaCore v2.1.
Couvre : catalogue des permissions, rôles prédéfinis, permis()/exiger(),
audit REFUS_ACTION, permissions individuelles, migration base v2.0.0 -> v2.1.0.
Aucune dépendance externe (unittest uniquement).
"""
import unittest
import sys
import os
import hashlib
import secrets
import sqlite3
import tempfile

sys.path.insert(0, os.path.dirname(__file__))
from main import (
    DB, Auth, PERMISSIONS, ROLES_DEFAUTS,
)


def _creer_utilisateur(db, nom, login, mdp, role, avec_id=1):
    sel = secrets.token_hex(16)
    ph = hashlib.pbkdf2_hmac('sha256', f"{mdp}{sel}".encode(),
                             sel.encode(), 100000).hex()
    db.exec(
        "INSERT INTO utilisateur(nom,login,pwd_hash,sel,role,avec_id) VALUES(?,?,?,?,?,?)",
        (nom, login, ph, sel, role, avec_id))
    db.commit()
    return login


def _creer_base_v0(chemin):
    """Reconstruit une base au schéma v2.0.0 (8 tables, CHECK sur le rôle,
    pas de colonnes annexes sur avec, user_version=0)."""
    conn = sqlite3.connect(chemin)
    conn.executescript("""
        CREATE TABLE utilisateur (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            nom     TEXT NOT NULL,
            login   TEXT UNIQUE NOT NULL,
            pwd_hash TEXT NOT NULL,
            sel     TEXT NOT NULL,
            role    TEXT NOT NULL CHECK (role IN ('admin','agent','lecteur')),
            actif   INTEGER DEFAULT 1,
            cree_le TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE avec (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            nom           TEXT NOT NULL,
            description   TEXT,
            montant_part  REAL DEFAULT 5000,
            taux_interet  REAL DEFAULT 0.1,
            taux_penalite REAL DEFAULT 0.02,
            actif         INTEGER DEFAULT 1,
            cree_le       TEXT DEFAULT CURRENT_DATE
        );
    """)
    sel = secrets.token_hex(16)
    ph = hashlib.pbkdf2_hmac('sha256', f"admin123{sel}".encode(),
                             sel.encode(), 100000).hex()
    sel2 = secrets.token_hex(16)
    ph2 = hashlib.pbkdf2_hmac('sha256', f"agent123{sel2}".encode(),
                              sel2.encode(), 100000).hex()
    conn.execute("INSERT INTO avec(nom,description) VALUES('AVEC Bukavu','Test')")
    conn.execute(
        "INSERT INTO utilisateur(nom,login,pwd_hash,sel,role) VALUES(?,?,?,?,?)",
        ("Ancien Admin", "admin", ph, sel, "admin"))
    conn.execute(
        "INSERT INTO utilisateur(nom,login,pwd_hash,sel,role) VALUES(?,?,?,?,?)",
        ("Ancien Agent", "agent", ph2, sel2, "agent"))
    conn.execute("PRAGMA user_version = 0")
    conn.commit()
    conn.close()


class TestCataloguePermissions(unittest.TestCase):
    def test_codes_uniques_et_complets(self):
        codes = [p[0] for p in PERMISSIONS]
        self.assertEqual(len(codes), len(set(codes)))
        self.assertEqual(len(codes), 42)

    def test_avec_les_cles_attendues(self):
        codes = {p[0] for p in PERMISSIONS}
        for attendu in ("members.create", "savings.create", "loans.cancel",
                        "repayments.create", "sessions.close", "reports.export",
                        "receipts.print", "receipts.reprint",
                        "documents.add_template", "documents.export",
                        "users.permissions", "backup.restore", "audit.view",
                        "settings.edit", "settings.financial.edit",
                        "accounts.view", "accounts.block"):
            self.assertIn(attendu, codes)

    def test_roles_predefinis_non_vides(self):
        self.assertIn("admin", ROLES_DEFAUTS)
        for code, (lib, desc, perms) in ROLES_DEFAUTS.items():
            self.assertTrue(lib and desc)
            self.assertTrue(perms)
            for p in perms:
                self.assertIn(p, [x[0] for x in PERMISSIONS],
                              f"Role {code}: permission inconnue {p}")

    def test_admin_contient_toutes_les_permissions(self):
        admin_codes = set(ROLES_DEFAUTS["admin"][2])
        self.assertEqual(admin_codes, {p[0] for p in PERMISSIONS})


class TestAuthPermissions(unittest.TestCase):
    def setUp(self):
        self.db = DB(":memory:")
        self.auth = Auth(self.db)
        self.assertTrue(self.auth.connecter("admin", "admin123"))

    def test_admin_toutes_permissions(self):
        for code, _, _ in PERMISSIONS:
            self.assertTrue(self.auth.permis(code), code)

    def test_lecteur_consultation_seule(self):
        _creer_utilisateur(self.db, "Lecteur", "lect", "lecteur123", "lecteur")
        self.auth.connecter("lect", "lecteur123")
        for code in ("members.view", "savings.view", "loans.view",
                     "repayments.view", "sessions.view", "reports.view",
                     "receipts.view", "documents.view"):
            self.assertTrue(self.auth.permis(code), code)
        for code in ("members.create", "savings.create", "loans.create",
                     "repayments.create", "users.permissions", "settings.edit",
                     "backup.create", "documents.add_template"):
            self.assertFalse(self.auth.permis(code), code)

    def test_agent_operations_sans_administration(self):
        _creer_utilisateur(self.db, "Agent", "agt", "agent123", "agent")
        self.auth.connecter("agt", "agent123")
        for code in ("members.create", "savings.create", "loans.create",
                     "repayments.create", "sessions.create", "receipts.print",
                     "documents.generate"):
            self.assertTrue(self.auth.permis(code), code)
        for code in ("users.permissions", "users.create", "settings.edit"):
            self.assertFalse(self.auth.permis(code), code)

    def test_exiger_refuse_et_audite(self):
        _creer_utilisateur(self.db, "Lecteur", "lect", "lecteur123", "lecteur")
        self.auth.connecter("lect", "lecteur123")
        with self.assertRaises(PermissionError):
            self.auth.exiger("backup.create", contexte="test")
        lignes = self.db.tous(
            "SELECT action, details FROM audit_log WHERE action='REFUS_ACTION'")
        self.assertEqual(len(lignes), 1)
        self.assertIn("backup.create", lignes[0]["details"])

    def test_exiger_admin_toujours_accepte(self):
        self.assertIsNone(self.auth.exiger("users.permissions", contexte="test"))

    def test_sans_connexion_aucune_permission(self):
        self.auth = Auth(self.db)
        self.assertFalse(self.auth.permis("members.view"))
        with self.assertRaises(PermissionError):
            self.auth.exiger("members.view", auditer=False)

    def test_permission_individuelle_ajoutee(self):
        _creer_utilisateur(self.db, "Agent", "agt", "agent123", "agent")
        uid = self.db.valeur("SELECT id FROM utilisateur WHERE login='agt'")
        self.db.exec("INSERT INTO user_permission(utilisateur_id,code) VALUES(?,?)",
                     (uid, "users.create"))
        self.db.commit()
        self.auth.connecter("agt", "agent123")
        self.assertTrue(self.auth.permis("users.create"))
        self.assertFalse(self.auth.permis("users.permissions"))

    def test_permission_individuelle_retiree(self):
        _creer_utilisateur(self.db, "Agent", "agt", "agent123", "agent")
        uid = self.db.valeur("SELECT id FROM utilisateur WHERE login='agt'")
        self.db.exec("INSERT INTO user_permission(utilisateur_id,code) VALUES(?,?)",
                     (uid, "users.permissions"))
        self.db.commit()
        self.auth.connecter("agt", "agent123")
        self.assertTrue(self.auth.permis("users.permissions"))
        self.db.exec("DELETE FROM user_permission WHERE utilisateur_id=? AND code=?",
                     (uid, "users.permissions"))
        self.db.commit()
        self.auth.connecter("agt", "agent123")
        self.assertFalse(self.auth.permis("users.permissions"))

    def test_permissions_effectives_methode(self):
        n = len(self.auth.permissions_effectives())
        self.assertEqual(n, len(PERMISSIONS))

    def test_desactivation_bloque_connexion(self):
        uid = self.db.valeur("SELECT id FROM utilisateur WHERE login='admin'")
        self.db.exec("UPDATE utilisateur SET actif=0 WHERE id=?", (uid,))
        self.db.commit()
        self.assertFalse(self.auth.connecter("admin", "admin123"))

    def test_changement_role_met_a_jour_permissions(self):
        uid = self.db.valeur("SELECT id FROM utilisateur WHERE login='admin'")
        self.db.exec("UPDATE utilisateur SET role='lecteur' WHERE id=?", (uid,))
        self.db.commit()
        self.auth.connecter("admin", "admin123")
        self.assertFalse(self.auth.est_admin)
        self.assertFalse(self.auth.permis("users.permissions"))
        self.assertTrue(self.auth.permis("members.view"))

    def test_roles_seedes_en_base(self):
        # Sur base neuve les 7 rôles prédéfinis doivent exister.
        self.assertEqual(self.db.valeur("SELECT COUNT(*) FROM role"), len(ROLES_DEFAUTS))
        mots = {"admin", "agent", "lecteur", "caissier", "gestionnaire_credit",
                "secretaire", "auditeur"}
        reels = {r["nom"] for r in self.db.tous("SELECT nom FROM role")}
        self.assertEqual(mots, reels)


class TestMigrationV0(unittest.TestCase):
    def test_migration_preserve_donnees_et_schema(self):
        tmp = tempfile.mktemp(suffix=".db")
        _creer_base_v0(tmp)
        try:
            db = DB(tmp)
            self.assertEqual(db.valeur("PRAGMA user_version"), 3)
            tables = {r[0] for r in db.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%'")}
            self.assertEqual(len(tables), 19)
            cols_avec = {r[1] for r in db.conn.execute("PRAGMA table_info(avec)")}
            for col in ("adresse", "telephone", "email", "devise", "logo",
                        "impression_auto", "taux_interet_urgence",
                        "taux_interet_investissement", "devises_autorisees",
                        "types_credit"):
                self.assertIn(col, cols_avec)
            cols_user = {r[1] for r in db.conn.execute("PRAGMA table_info(utilisateur)")}
            self.assertIn("avec_id", cols_user)
            self.assertIn("derniere_connexion", cols_user)
            cols_membre = {r[1] for r in db.conn.execute("PRAGMA table_info(membre)")}
            self.assertIn("type_compte", cols_membre)
            for tbl, col in (("epargne", "devise"), ("credit", "devise"),
                             ("credit", "type_credit"), ("credit", "taux_penalite"),
                             ("remboursement", "devise"), ("receipt", "devise")):
                self.assertIn(col, {r[1] for r in db.conn.execute(
                    f"PRAGMA table_info({tbl})")})
            for tbl in ("compte", "compte_evenement", "compte_mouvement"):
                self.assertIn(tbl, tables)
            # Données préservées à l'identique
            self.assertEqual(db.valeur("SELECT COUNT(*) FROM utilisateur"), 2)
            self.assertEqual(db.valeur("SELECT role FROM utilisateur WHERE login='admin'"), "admin")
            self.assertEqual(db.valeur("SELECT avec_id FROM utilisateur WHERE login='agent'"), 1)
            self.assertEqual(db.valeur("SELECT nom FROM avec WHERE id=1"), "AVEC Bukavu")
            # Marque de devise historique migrée FC -> CDF
            self.assertEqual(db.valeur("SELECT devise FROM avec WHERE id=1"), "CDF")
            self.assertEqual(db.valeur("PRAGMA integrity_check"), "ok")
            self.assertFalse(db.conn.execute("PRAGMA foreign_key_check").fetchall(),
                             "violations de clés étrangères après migration")
            # Seeds permissions présents
            self.assertEqual(db.valeur("SELECT COUNT(*) FROM permission"), len(PERMISSIONS))
            # Les anciens comptes restent fonctionnels (à leur niveau de rôle).
            a = Auth(db)
            self.assertTrue(a.connecter("admin", "admin123"))
            self.assertTrue(a.permis("users.permissions"))
            self.assertTrue(a.permis("backup.restore"))
            self.assertTrue(a.connecter("agent", "agent123"))
            # L'agent n'a pas accès à l'administration ni aux taux.
            self.assertFalse(a.permis("users.permissions"))
            self.assertFalse(a.permis("settings.financial.edit"))
        finally:
            for suffixe in ("", "-wal", "-shm"):
                try:
                    os.remove(tmp + suffixe)
                except OSError:
                    pass

    def test_migration_est_idempotente(self):
        tmp = tempfile.mktemp(suffix=".db")
        _creer_base_v0(tmp)
        try:
            DB(tmp)               # première migration
            db = DB(tmp)          # réouverture : ne doit pas casser ni dupliquer
            self.assertEqual(db.valeur("PRAGMA user_version"), 3)
            self.assertEqual(db.valeur("SELECT COUNT(*) FROM utilisateur"), 2)
            self.assertEqual(db.valeur("SELECT COUNT(*) FROM role"), len(ROLES_DEFAUTS))
            self.assertFalse(db.conn.execute("PRAGMA foreign_key_check").fetchall())
            self.assertIn("type_compte",
                          {r[1] for r in db.conn.execute("PRAGMA table_info(membre)")})
        finally:
            for suffixe in ("", "-wal", "-shm"):
                try:
                    os.remove(tmp + suffixe)
                except OSError:
                    pass

    def test_parametres_financiers_reserves_a_l_admin(self):
        db = DB(":memory:")
        _creer_utilisateur(db, "Agent", "agt", "agent123", "agent")
        a = Auth(db)
        self.assertTrue(a.connecter("agt", "agent123"))
        self.assertFalse(a.permis("settings.financial.edit"), "agent ne doit pas éditer les taux")
        with self.assertRaises(PermissionError):
            a.exiger("settings.financial.edit", contexte="changement taux")
        admin = Auth(db)
        self.assertTrue(admin.connecter("admin", "admin123"))
        self.assertTrue(admin.permis("settings.financial.edit"))
        self.assertIsNone(admin.exiger("settings.financial.edit", contexte="test"))


if __name__ == "__main__":
    unittest.main()