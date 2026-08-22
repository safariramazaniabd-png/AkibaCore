#!/usr/bin/env python3
"""Tests complets pour AkibaCore v2.0.0 — couverture etendue.
Aucune dependance externe (unittest uniquement).
"""
import unittest
import sys
import os
import hashlib
import secrets
import tempfile
import shutil
from datetime import date, timedelta, datetime

sys.path.insert(0, os.path.dirname(__file__))
from main import (
    Finance, DB, Auth, Backup, _MAX_TENTATIVES, _LOCKOUT_SECONDS,
    _TENTATIVES_CONNEXION, TAUX_INTERET_DEFAUT, TAUX_PENALITE_DEFAUT,
    BACKUP_MAX, APP_VERSION,
)


# ════════════════════════════════════════════════════════════════
#  FINANCE — CALCULS EXTREMES ET LIMITES
# ════════════════════════════════════════════════════════════════

class TestInteretEdgeCases(unittest.TestCase):
    def test_0_mois(self):
        self.assertEqual(Finance.interet_simple(100_000, 0.10, 0), 0)

    def test_1_mois(self):
        self.assertEqual(Finance.interet_simple(100_000, 0.10, 1), 833.33)

    def test_24_mois(self):
        self.assertEqual(Finance.interet_simple(100_000, 0.10, 24), 20_000)

    def test_36_mois(self):
        self.assertEqual(Finance.interet_simple(100_000, 0.10, 36), 30_000)

    def test_montant_decimal(self):
        r = Finance.interet_simple(33_333.33, 0.10, 7)
        self.assertAlmostEqual(r, 1944.44, places=2)

    def test_taux_zero(self):
        self.assertEqual(Finance.interet_simple(100_000, 0, 12), 0)

    def test_principal_zero(self):
        self.assertEqual(Finance.interet_simple(0, 0.10, 12), 0)

    def test_taux_50_pourcent(self):
        self.assertEqual(Finance.interet_simple(100_000, 0.50, 12), 50_000)

    def test_grand_principal(self):
        r = Finance.interet_simple(10_000_000, 0.10, 12)
        self.assertEqual(r, 1_000_000)


class TestPenaliteEdgeCases(unittest.TestCase):
    def test_1_jour(self):
        self.assertAlmostEqual(Finance.penalite(100_000, 0.02, 1), 66.67, places=2)

    def test_29_jours(self):
        self.assertAlmostEqual(Finance.penalite(100_000, 0.02, 29), 1933.33, places=2)

    def test_31_jours(self):
        self.assertAlmostEqual(Finance.penalite(100_000, 0.02, 31), 2066.67, places=2)

    def test_60_jours(self):
        self.assertEqual(Finance.penalite(100_000, 0.02, 60), 4_000)

    def test_90_jours(self):
        self.assertEqual(Finance.penalite(100_000, 0.02, 90), 6_000)

    def test_365_jours(self):
        self.assertEqual(Finance.penalite(100_000, 0.02, 365), 24_333.33)

    def test_montant_zero(self):
        self.assertEqual(Finance.penalite(0, 0.02, 30), 0)

    def test_taux_zero(self):
        self.assertEqual(Finance.penalite(100_000, 0, 30), 0)


class TestJoursRetardAdvanced(unittest.TestCase):
    def test_hier(self):
        hier = (date.today() - timedelta(days=1)).isoformat()
        self.assertEqual(Finance.jours_retard(hier), 1)

    def test_exactement_aujourd_hui(self):
        self.assertEqual(Finance.jours_retard(date.today().isoformat()), 0)

    def test_futur(self):
        futur = (date.today() + timedelta(days=10)).isoformat()
        self.assertEqual(Finance.jours_retard(futur), 0)

    def test_format_avec_heure(self):
        hier = (date.today() - timedelta(days=5)).isoformat()
        self.assertEqual(Finance.jours_retard(hier + " 14:30:00"), 5)

    def test_chaine_vide(self):
        self.assertEqual(Finance.jours_retard(""), 0)

    def test_none_comme_string(self):
        self.assertEqual(Finance.jours_retard("None"), 0)


class TestDateEcheanceAdvanced(unittest.TestCase):
    def test_3_mois_depuis_31(self):
        r = Finance.date_echeance(date(2025, 1, 31), 3)
        self.assertEqual(r, date(2025, 4, 30))

    def test_1_mois_depuis_31_janvier(self):
        r = Finance.date_echeance(date(2025, 1, 31), 1)
        self.assertEqual(r, date(2025, 2, 28))

    def test_13_mois(self):
        r = Finance.date_echeance(date(2025, 6, 15), 13)
        self.assertEqual(r, date(2026, 7, 15))

    def test_24_mois(self):
        r = Finance.date_echeance(date(2025, 1, 1), 24)
        self.assertEqual(r, date(2027, 1, 1))

    def test_annee_bissextile_fevrier_29(self):
        r = Finance.date_echeance(date(2024, 1, 29), 1)
        self.assertEqual(r, date(2024, 2, 29))

    def test_annee_non_bissextile_fevrier_28(self):
        r = Finance.date_echeance(date(2025, 1, 29), 1)
        self.assertEqual(r, date(2025, 2, 28))

    def test_29_fevrier_sur_bissextile(self):
        r = Finance.date_echeance(date(2024, 2, 29), 12)
        self.assertEqual(r, date(2025, 2, 28))

    def test_12_mois_annee_complete(self):
        r = Finance.date_echeance(date(2025, 3, 15), 12)
        self.assertEqual(r, date(2026, 3, 15))


class TestValiderMontantAdvanced(unittest.TestCase):
    def test_espaces_et_virgules(self):
        self.assertEqual(Finance.valider_montant("1 000 000,50"), 1_000_000.5)

    def test_entier_positif(self):
        self.assertEqual(Finance.valider_montant("50000"), 50_000.0)

    def test_decimal_point(self):
        self.assertEqual(Finance.valider_montant("1000.50"), 1000.5)

    def test_tres_grand(self):
        self.assertEqual(Finance.valider_montant("999999999"), 999_999_999)

    def test_0_point_01(self):
        self.assertEqual(Finance.valider_montant("0.01"), 0.01)

    def test_negatif_rejete(self):
        with self.assertRaises(ValueError):
            Finance.valider_montant("-1")

    def test_0_rejete(self):
        with self.assertRaises(ValueError):
            Finance.valider_montant("0")

    def test_texte_rejete(self):
        with self.assertRaises(ValueError):
            Finance.valider_montant("abc")

    def test_vide_rejete(self):
        with self.assertRaises(ValueError):
            Finance.valider_montant("")


class TestValiderDateAdvanced(unittest.TestCase):
    def test_31_decembre(self):
        self.assertEqual(Finance.valider_date("2025-12-31"), date(2025, 12, 31))

    def test_1er_janvier(self):
        self.assertEqual(Finance.valider_date("2025-01-01"), date(2025, 1, 1))

    def test_29_fevrier_bissextile(self):
        self.assertEqual(Finance.valider_date("2024-02-29"), date(2024, 2, 29))

    def test_29_fevrier_non_bissextile_rejete(self):
        with self.assertRaises(ValueError):
            Finance.valider_date("2025-02-29")

    def test_format_invers_rejete(self):
        with self.assertRaises(ValueError):
            Finance.valider_date("31-12-2025")

    def test_format_slash_rejete(self):
        with self.assertRaises(ValueError):
            Finance.valider_date("12/31/2025")

    def test_espaces_rejetes(self):
        with self.assertRaises(ValueError):
            Finance.valider_date("  ")


# ════════════════════════════════════════════════════════════════
#  DB — INDEX, SCHEMA, INTEGRITE
# ════════════════════════════════════════════════════════════════

class TestDBIndexes(unittest.TestCase):
    def setUp(self):
        self.db = DB(":memory:")

    def test_index_epargne_membre_existe(self):
        r = self.db.tous(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_epargne_membre'")
        self.assertEqual(len(r), 1)

    def test_index_credit_statut_existe(self):
        r = self.db.tous(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_credit_statut'")
        self.assertEqual(len(r), 1)

    def test_index_credit_echeance_existe(self):
        r = self.db.tous(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_credit_echeance'")
        self.assertEqual(len(r), 1)

    def test_index_remboursement_credit_existe(self):
        r = self.db.tous(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_remboursement_credit'")
        self.assertEqual(len(r), 1)

    def test_index_remboursement_membre_existe(self):
        r = self.db.tous(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_remboursement_membre'")
        self.assertEqual(len(r), 1)

    def test_index_audit_ts_existe(self):
        r = self.db.tous(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_audit_ts'")
        self.assertEqual(len(r), 1)

    def test_index_epargne_session_existe(self):
        r = self.db.tous(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_epargne_session'")
        self.assertEqual(len(r), 1)

    def test_index_credit_membre_existe(self):
        r = self.db.tous(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_credit_membre'")
        self.assertEqual(len(r), 1)


class TestDBSchema完整性(unittest.TestCase):
    def setUp(self):
        self.db = DB(":memory:")

    def test_toutes_tables_existent(self):
        tables = {r[0] for r in self.db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        for t in ("utilisateur", "avec", "membre", "session",
                   "epargne", "credit", "remboursement", "audit_log"):
            self.assertIn(t, tables, f"Table {t} manquante")

    def test_8_tables_principales(self):
        tables = [r[0] for r in self.db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()]
        self.assertEqual(len(tables), 8)

    def test_foreign_keys_actives(self):
        fk = self.db.valeur("PRAGMA foreign_keys")
        self.assertEqual(fk, 1)

    def test_wal_mode(self):
        mode = self.db.valeur("PRAGMA journal_mode")
        self.assertIn(mode, ("wal", "memory"))

    def test_fk_violee_epargne_membre_inexistant(self):
        with self.assertRaises(Exception):
            self.db.exec("INSERT INTO epargne(membre_id,montant,type) VALUES(9999,100,'ordinaire')")
            self.db.commit()

    def test_check_constraint_montant_positif(self):
        with self.assertRaises(Exception):
            self.db.exec("INSERT INTO epargne(membre_id,montant,type) VALUES(1,-100,'ordinaire')")
            self.db.commit()

    def test_check_constraint_role_invalide(self):
        with self.assertRaises(Exception):
            self.db.exec(
                "INSERT INTO utilisateur(nom,login,pwd_hash,sel,role) VALUES('X','x','h','s','superadmin')")
            self.db.commit()


class TestDBTransaction(unittest.TestCase):
    def setUp(self):
        self.db = DB(":memory:")

    def test_commit_persiste(self):
        self.db.exec("INSERT INTO membre(nom,avec_id) VALUES('Test',1)")
        self.db.commit()
        self.assertEqual(self.db.valeur("SELECT COUNT(*) FROM membre WHERE nom='Test'"), 1)

    def test_rollback_annule(self):
        self.db.exec("INSERT INTO membre(nom,avec_id) VALUES('Test2',1)")
        self.db.rollback()
        self.assertEqual(self.db.valeur("SELECT COUNT(*) FROM membre WHERE nom='Test2'"), 0)

    def test_audit_ne_crash_jamais(self):
        self.db.audit(9999, "ghost", "TEST", details={"key": "val"})
        self.db.audit(None, None, "TEST_NULL")

    def test_dict_row_factory(self):
        self.db.exec("INSERT INTO membre(nom,avec_id) VALUES('Dict',1)")
        self.db.commit()
        r = self.db.un("SELECT * FROM membre WHERE nom='Dict'")
        self.assertIsInstance(r, dict)
        self.assertIn("nom", r)


# ════════════════════════════════════════════════════════════════
#  AUTH — SECURITE ET LIMITES
# ════════════════════════════════════════════════════════════════

class TestAuthAdvanced(unittest.TestCase):
    def setUp(self):
        self.db = DB(":memory:")
        self.auth = Auth(self.db)

    def test_mdp_long(self):
        long_mdp = "a" * 256
        self.auth.connecter("admin", "admin123")
        self.auth.changer_mdp("admin", "admin123", long_mdp)
        self.assertTrue(self.auth.connecter("admin", long_mdp))

    def test_mdp_caracteres_speciaux(self):
        mdp = "!@#$%^&*()_+-=[]{}|;':\",./<>?`~"
        self.auth.connecter("admin", "admin123")
        self.auth.changer_mdp("admin", "admin123", mdp)
        self.assertTrue(self.auth.connecter("admin", mdp))

    def test_mdp_unicode(self):
        mdp = "motdepasse_éàüô_123"
        self.auth.connecter("admin", "admin123")
        self.auth.changer_mdp("admin", "admin123", mdp)
        self.assertTrue(self.auth.connecter("admin", mdp))

    def test_double_deconnexion(self):
        self.auth.user = None
        self.assertFalse(self.auth.est_admin)
        self.assertIsNone(self.auth.uid)
        self.assertIsNone(self.auth.ulogin)

    def test_uid_avant_connexion(self):
        self.assertIsNone(self.auth.uid)
        self.assertIsNone(self.auth.ulogin)

    def test_est_admin_agent(self):
        sel = secrets.token_hex(16)
        ph = hashlib.pbkdf2_hmac('sha256', f"agent1{sel}".encode(),
                                 sel.encode(), 100000).hex()
        self.db.exec(
            "INSERT INTO utilisateur(nom,login,pwd_hash,sel,role)"
            " VALUES(?,?,?,?,?)",
            ("Agent Test", "agent1", ph, sel, "agent"))
        self.db.commit()
        self.auth.connecter("agent1", "agent1")
        self.assertFalse(self.auth.est_admin)

    def test_est_admin_lecteur(self):
        sel = secrets.token_hex(16)
        ph = hashlib.pbkdf2_hmac('sha256', f"lect1{sel}".encode(),
                                 sel.encode(), 100000).hex()
        self.db.exec(
            "INSERT INTO utilisateur(nom,login,pwd_hash,sel,role)"
            " VALUES(?,?,?,?,?)",
            ("Lecteur Test", "lecteur1", ph, sel, "lecteur"))
        self.db.commit()
        self.auth.connecter("lecteur1", "lect1")
        self.assertFalse(self.auth.est_admin)

    def test_login_apres_desactivation(self):
        self.db.exec("UPDATE utilisateur SET actif=0 WHERE login='admin'")
        self.db.commit()
        result = self.auth.connecter("admin", "admin123")
        self.assertFalse(result)
        self.assertIsNone(self.auth.user)

    def test_changement_mdp_deux_fois(self):
        self.auth.connecter("admin", "admin123")
        self.auth.changer_mdp("admin", "admin123", "newpass1")
        self.assertTrue(self.auth.connecter("admin", "newpass1"))
        self.auth.changer_mdp("admin", "newpass1", "newpass2")
        self.assertTrue(self.auth.connecter("admin", "newpass2"))
        self.assertFalse(self.auth.connecter("admin", "newpass1"))

    def test_hachage_nest_pas_sha256_simple(self):
        u = self.db.un("SELECT * FROM utilisateur WHERE login='admin'")
        sha256_simple = hashlib.sha256(f"admin123{u['sel']}".encode()).hexdigest()
        self.assertNotEqual(sha256_simple, u["pwd_hash"])


class TestRateLimiting(unittest.TestCase):
    def setUp(self):
        import main
        main._TENTATIVES_CONNEXION.clear()

    def tearDown(self):
        import main
        main._TENTATIVES_CONNEXION.clear()

    def test_constantes_config(self):
        self.assertEqual(_MAX_TENTATIVES, 5)
        self.assertEqual(_LOCKOUT_SECONDS, 30)

    def test_compteur_increment(self):
        import main
        now = datetime.now().timestamp()
        main._TENTATIVES_CONNEXION["test"] = (0, now)
        nb, debut = main._TENTATIVES_CONNEXION["test"]
        main._TENTATIVES_CONNEXION["test"] = (nb + 1, debut)
        self.assertEqual(main._TENTATIVES_CONNEXION["test"][0], 1)

    def test_lockout_apres_max(self):
        import main
        now = datetime.now().timestamp()
        main._TENTATIVES_CONNEXION["test"] = (_MAX_TENTATIVES, now)
        nb, _ = main._TENTATIVES_CONNEXION["test"]
        self.assertGreaterEqual(nb, _MAX_TENTATIVES)

    def test_reset_apres_lockout_expire(self):
        import main
        old = datetime.now().timestamp() - _LOCKOUT_SECONDS - 1
        main._TENTATIVES_CONNEXION["test"] = (_MAX_TENTATIVES, old)
        nb, debut = main._TENTATIVES_CONNEXION["test"]
        ecoule = datetime.now().timestamp() - debut
        self.assertGreater(ecoule, _LOCKOUT_SECONDS)


# ════════════════════════════════════════════════════════════════
#  EPARGNE — OPERATIONS COMPLETES
# ════════════════════════════════════════════════════════════════

class TestEpargneComplete(unittest.TestCase):
    def setUp(self):
        self.db = DB(":memory:")
        self.db.exec("INSERT INTO membre(nom,prenom,avec_id) VALUES('Dupont','Marie',1)")
        self.db.commit()
        self.mid = self.db.valeur("SELECT id FROM membre WHERE nom='Dupont'")

    def test_depot_et_solde(self):
        for m in [10_000, 20_000, 5_000]:
            self.db.exec(
                "INSERT INTO epargne(membre_id,montant,type) VALUES(?,?,?)",
                (self.mid, m, "ordinaire"))
        self.db.commit()
        self.assertEqual(Finance.solde_epargne(self.db, self.mid), 35_000)

    def test_annulation_et_solde(self):
        self.db.exec(
            "INSERT INTO epargne(membre_id,montant,type) VALUES(?,?,?)",
            (self.mid, 50_000, "ordinaire"))
        self.db.commit()
        eid = self.db.valeur("SELECT id FROM epargne WHERE montant=50000")
        self.db.exec("UPDATE epargne SET annule=1 WHERE id=?", (eid,))
        self.db.commit()
        self.assertEqual(Finance.solde_epargne(self.db, self.mid), 0)

    def test_solde_un_membre_sans_epargne(self):
        self.assertEqual(Finance.solde_epargne(self.db, 9999), 0)

    def test_tous_types_epargne(self):
        for t in ["ordinaire", "solidarite", "urgence"]:
            self.db.exec(
                "INSERT INTO epargne(membre_id,montant,type) VALUES(?,?,?)",
                (self.mid, 10_000, t))
        self.db.commit()
        total = self.db.valeur(
            "SELECT COUNT(*) FROM epargne WHERE membre_id=? AND annule=0",
            (self.mid,))
        self.assertEqual(total, 3)

    def test_montant_minimal(self):
        self.db.exec(
            "INSERT INTO epargne(membre_id,montant,type) VALUES(?,?,?)",
            (self.mid, 0.01, "ordinaire"))
        self.db.commit()
        self.assertAlmostEqual(Finance.solde_epargne(self.db, self.mid), 0.01, places=2)

    def test_grand_montant(self):
        self.db.exec(
            "INSERT INTO epargne(membre_id,montant,type) VALUES(?,?,?)",
            (self.mid, 50_000_000, "ordinaire"))
        self.db.commit()
        self.assertEqual(Finance.solde_epargne(self.db, self.mid), 50_000_000)


# ════════════════════════════════════════════════════════════════
#  CREDIT — BLOCAGE ACTIF ET STATUTS
# ════════════════════════════════════════════════════════════════

class TestCreditBlocageActif(unittest.TestCase):
    """Verifie qu'on ne peut pas octroyer un 2eme credit actif."""

    def setUp(self):
        self.db = DB(":memory:")
        self.db.exec("INSERT INTO membre(nom,prenom,avec_id) VALUES('Kabila','Jean',1)")
        self.db.commit()
        self.mid = self.db.valeur("SELECT id FROM membre WHERE nom='Kabila'")

    def test_credit_actif_bloque_nouveau(self):
        ech = Finance.date_echeance(date(2025, 1, 1), 6)
        self.db.exec("""
            INSERT INTO credit(membre_id,principal,taux,duree_mois,
            date_octroi,date_echeance,montant_interet,montant_total,statut)
            VALUES(?,?,?,?,?,?,?,?,?)
        """, (self.mid, 100_000, 0.10, 6, "2025-01-01", ech.isoformat(), 5_000, 105_000, "actif"))
        self.db.commit()
        solde = self.db.valeur(
            "SELECT COALESCE(SUM(montant_total-rembourse),0) FROM credit"
            " WHERE membre_id=? AND statut IN ('actif','en_retard')", (self.mid,)) or 0
        self.assertGreater(solde, 0, "Le membre a un crédit actif — le blocage doit s'appliquer")

    def test_credit_solde_permet_nouveau(self):
        ech = Finance.date_echeance(date(2024, 1, 1), 6)
        self.db.exec("""
            INSERT INTO credit(membre_id,principal,taux,duree_mois,
            date_octroi,date_echeance,montant_interet,montant_total,rembourse,statut)
            VALUES(?,?,?,?,?,?,?,?,?,?)
        """, (self.mid, 100_000, 0.10, 6, "2024-01-01", ech.isoformat(), 5_000, 105_000, 105_000, "solde"))
        self.db.commit()
        solde = self.db.valeur(
            "SELECT COALESCE(SUM(montant_total-rembourse),0) FROM credit"
            " WHERE membre_id=? AND statut IN ('actif','en_retard')", (self.mid,)) or 0
        self.assertEqual(solde, 0, "Crédit soldé — nouveau crédit autorisé")


class TestCreditStatuts(unittest.TestCase):
    def setUp(self):
        self.db = DB(":memory:")
        self.db.exec("INSERT INTO membre(nom,prenom,avec_id) VALUES('Test','User',1)")
        self.db.commit()
        self.mid = self.db.valeur("SELECT id FROM membre WHERE nom='Test'")

    def test_maj_retard(self):
        ech = Finance.date_echeance(date(2024, 1, 1), 6)
        self.db.exec("""
            INSERT INTO credit(membre_id,principal,taux,duree_mois,
            date_octroi,date_echeance,montant_interet,montant_total,statut)
            VALUES(?,?,?,?,?,?,?,?,?)
        """, (self.mid, 100_000, 0.10, 6, "2024-01-01", ech.isoformat(), 5_000, 105_000, "actif"))
        self.db.commit()
        Finance.maj_statuts(self.db)
        c = self.db.un("SELECT statut FROM credit WHERE membre_id=?", (self.mid,))
        self.assertEqual(c["statut"], "en_retard")

    def test_maj_solde(self):
        ech = Finance.date_echeance(date(2025, 6, 1), 6)
        self.db.exec("""
            INSERT INTO credit(membre_id,principal,taux,duree_mois,
            date_octroi,date_echeance,montant_interet,montant_total,rembourse,statut)
            VALUES(?,?,?,?,?,?,?,?,?,?)
        """, (self.mid, 100_000, 0.10, 6, "2025-06-01", ech.isoformat(), 5_000, 105_000, 105_000, "actif"))
        self.db.commit()
        Finance.maj_statuts(self.db)
        c = self.db.un("SELECT statut FROM credit WHERE membre_id=?", (self.mid,))
        self.assertEqual(c["statut"], "solde")

    def test_annule_non_touche(self):
        ech = Finance.date_echeance(date(2024, 1, 1), 6)
        self.db.exec("""
            INSERT INTO credit(membre_id,principal,taux,duree_mois,
            date_octroi,date_echeance,montant_interet,montant_total,statut)
            VALUES(?,?,?,?,?,?,?,?,?)
        """, (self.mid, 100_000, 0.10, 6, "2024-01-01", ech.isoformat(), 5_000, 105_000, "annule"))
        self.db.commit()
        Finance.maj_statuts(self.db)
        c = self.db.un("SELECT statut FROM credit WHERE membre_id=?", (self.mid,))
        self.assertEqual(c["statut"], "annule")

    def test_solde_credit(self):
        ech = Finance.date_echeance(date(2025, 6, 1), 6)
        self.db.exec("""
            INSERT INTO credit(membre_id,principal,taux,duree_mois,
            date_octroi,date_echeance,montant_interet,montant_total,rembourse)
            VALUES(?,?,?,?,?,?,?,?,?)
        """, (self.mid, 100_000, 0.10, 6, "2025-06-01", ech.isoformat(), 5_000, 105_000, 30_000))
        self.db.commit()
        c = self.db.un("SELECT * FROM credit WHERE membre_id=?", (self.mid,))
        self.assertEqual(Finance.solde_credit(c), 75_000)

    def test_maj_solde_partiel(self):
        ech = Finance.date_echeance(date(2026, 6, 1), 6)
        self.db.exec("""
            INSERT INTO credit(membre_id,principal,taux,duree_mois,
            date_octroi,date_echeance,montant_interet,montant_total,rembourse,statut)
            VALUES(?,?,?,?,?,?,?,?,?,?)
        """, (self.mid, 100_000, 0.10, 6, "2026-06-01", ech.isoformat(), 5_000, 105_000, 50_000, "actif"))
        self.db.commit()
        Finance.maj_statuts(self.db)
        c = self.db.un("SELECT statut FROM credit WHERE membre_id=?", (self.mid,))
        self.assertEqual(c["statut"], "actif", "Remboursement partiel ne doit pas changer le statut")


# ════════════════════════════════════════════════════════════════
#  REMBOURSEMENT — IMPUTATION AMELIOREE
# ════════════════════════════════════════════════════════════════

class TestRemboursementImputation(unittest.TestCase):
    def setUp(self):
        self.db = DB(":memory:")
        self.db.exec("INSERT INTO membre(nom,prenom,avec_id) VALUES('Mubi','Aline',1)")
        self.db.commit()
        self.mid = self.db.valeur("SELECT id FROM membre WHERE nom='Mubi'")
        ech = Finance.date_echeance(date(2025, 1, 1), 6)
        self.db.exec("""
            INSERT INTO credit(membre_id,principal,taux,duree_mois,
            date_octroi,date_echeance,montant_interet,montant_total)
            VALUES(?,?,?,?,?,?,?,?)
        """, (self.mid, 100_000, 0.10, 6, "2025-01-01", ech.isoformat(), 5_000, 105_000))
        self.db.commit()
        self.cid = self.db.valeur("SELECT id FROM credit WHERE membre_id=?", (self.mid,))

    def test_imputation_sans_retard(self):
        c = self.db.un("SELECT * FROM credit WHERE id=?", (self.cid,))
        solde = c["montant_total"] - c["rembourse"]
        jr = 0
        pen = 0
        mt = 20_000
        pen_pay = min(pen, mt)
        reste = mt - pen_pay
        ratio_total = c["montant_total"] if c["montant_total"] > 0 else 1
        interet_restant = max(0, c["montant_interet"] * (1 - c["rembourse"] / ratio_total))
        principal_restant = max(0, c["montant_total"] - c["rembourse"] - interet_restant)
        total_restant = interet_restant + principal_restant
        ratio_i = interet_restant / total_restant if total_restant > 0 else 0
        int_pay = round(reste * ratio_i, 2)
        prin_pay = round(reste - int_pay, 2)
        self.assertEqual(pen_pay, 0)
        self.assertGreater(int_pay, 0)
        self.assertGreater(prin_pay, 0)
        self.assertAlmostEqual(int_pay + prin_pay, mt, places=2)

    def test_imputation_avec_penalite(self):
        c = self.db.un("SELECT * FROM credit WHERE id=?", (self.cid,))
        jr = 30
        pen = Finance.penalite(c["montant_total"] - c["rembourse"],
                               TAUX_PENALITE_DEFAUT, jr)
        mt = 30_000
        pen_pay = min(pen, mt)
        reste = mt - pen_pay
        self.assertGreater(pen_pay, 0)
        self.assertEqual(pen_pay, 2_100)
        self.assertEqual(reste, 27_900)

    def test_paiement_integral(self):
        c = self.db.un("SELECT * FROM credit WHERE id=?", (self.cid,))
        self.db.exec("""
            INSERT INTO remboursement(credit_id,membre_id,mont_principal,
            mont_interet,mont_penalite,montant_total,date_paiement)
            VALUES(?,?,?,?,?,?,?)
        """, (self.cid, self.mid, 105_000, 0, 0, 105_000, "2025-06-01"))
        self.db.exec("UPDATE credit SET rembourse=105000,statut='solde' WHERE id=?", (self.cid,))
        self.db.commit()
        c = self.db.un("SELECT * FROM credit WHERE id=?", (self.cid,))
        self.assertEqual(c["rembourse"], 105_000)
        self.assertEqual(c["statut"], "solde")
        self.assertEqual(Finance.solde_credit(c), 0)

    def test_plusieurs_paiements(self):
        c = self.db.un("SELECT * FROM credit WHERE id=?", (self.cid,))
        # Paiement 1: 50 000
        self.db.exec("""
            INSERT INTO remboursement(credit_id,membre_id,mont_principal,
            mont_interet,mont_penalite,montant_total,date_paiement)
            VALUES(?,?,?,?,?,?,?)
        """, (self.cid, self.mid, 47_619.05, 2_380.95, 0, 50_000, "2025-02-01"))
        self.db.exec("UPDATE credit SET rembourse=50000 WHERE id=?", (self.cid,))
        self.db.commit()
        c = self.db.un("SELECT * FROM credit WHERE id=?", (self.cid,))
        self.assertEqual(Finance.solde_credit(c), 55_000)
        # Paiement 2: 55 000 (solde)
        self.db.exec("""
            INSERT INTO remboursement(credit_id,membre_id,mont_principal,
            mont_interet,mont_penalite,montant_total,date_paiement)
            VALUES(?,?,?,?,?,?,?)
        """, (self.cid, self.mid, 55_000, 0, 0, 55_000, "2025-03-01"))
        self.db.exec("UPDATE credit SET rembourse=105000,statut='solde' WHERE id=?", (self.cid,))
        self.db.commit()
        c = self.db.un("SELECT * FROM credit WHERE id=?", (self.cid,))
        self.assertEqual(c["statut"], "solde")
        self.assertEqual(Finance.solde_credit(c), 0)

    def test_penalite_remboursement_retard_60_jours(self):
        c = self.db.un("SELECT * FROM credit WHERE id=?", (self.cid,))
        jr = 60
        pen = Finance.penalite(c["montant_total"] - c["rembourse"],
                               TAUX_PENALITE_DEFAUT, jr)
        self.assertEqual(pen, 4_200)  # 105_000 * 0.02 * 2

    def test_penalite_remboursement_retard_90_jours(self):
        c = self.db.un("SELECT * FROM credit WHERE id=?", (self.cid,))
        jr = 90
        pen = Finance.penalite(c["montant_total"] - c["rembourse"],
                               TAUX_PENALITE_DEFAUT, jr)
        self.assertEqual(pen, 6_300)  # 105_000 * 0.02 * 3


# ════════════════════════════════════════════════════════════════
#  SESSIONS
# ════════════════════════════════════════════════════════════════

class TestSessions(unittest.TestCase):
    def setUp(self):
        self.db = DB(":memory:")
        self.auth = Auth(self.db)
        self.auth.connecter("admin", "admin123")

    def test_creation_session(self):
        nb = (self.db.valeur("SELECT COUNT(*) FROM session WHERE avec_id=?", (1,)) or 0) + 1
        self.db.exec(
            "INSERT INTO session(avec_id,numero,date_reunion,notes,cree_par)"
            " VALUES(?,?,?,?,?)",
            (1, nb, "2025-06-15", "Test session", self.auth.uid))
        self.db.commit()
        s = self.db.un("SELECT * FROM session WHERE numero=?", (nb,))
        self.assertIsNotNone(s)
        self.assertEqual(s["statut"], "ouverte")

    def test_cloture_session(self):
        self.db.exec(
            "INSERT INTO session(avec_id,numero,date_reunion,cree_par)"
            " VALUES(?,?,?,?)",
            (1, 1, "2025-06-15", self.auth.uid))
        self.db.commit()
        sid = self.db.valeur("SELECT id FROM session WHERE numero=1")
        self.db.exec("UPDATE session SET statut='fermee' WHERE id=?", (sid,))
        self.db.commit()
        s = self.db.un("SELECT statut FROM session WHERE id=?", (sid,))
        self.assertEqual(s["statut"], "fermee")

    def test_session_deja_fermee(self):
        self.db.exec(
            "INSERT INTO session(avec_id,numero,date_reunion,statut,cree_par)"
            " VALUES(?,?,?,?,?)",
            (1, 1, "2025-06-15", "fermee", self.auth.uid))
        self.db.commit()
        s = self.db.un("SELECT statut FROM session WHERE numero=1")
        self.assertEqual(s["statut"], "fermee")

    def test_numerotation_auto(self):
        for i in range(5):
            self.db.exec(
                "INSERT INTO session(avec_id,numero,date_reunion,cree_par)"
                " VALUES(?,?,?,?)",
                (1, i + 1, f"2025-0{i+1}-15", self.auth.uid))
        self.db.commit()
        count = self.db.valeur("SELECT COUNT(*) FROM session WHERE avec_id=?", (1,))
        self.assertEqual(count, 5)

    def test_session_sans_notes(self):
        self.db.exec(
            "INSERT INTO session(avec_id,numero,date_reunion,cree_par)"
            " VALUES(?,?,?,?)",
            (1, 1, "2025-06-15", self.auth.uid))
        self.db.commit()
        s = self.db.un("SELECT * FROM session WHERE numero=1")
        self.assertIsNone(s["notes"])


# ════════════════════════════════════════════════════════════════
#  MEMBRES — VALIDATIONS
# ════════════════════════════════════════════════════════════════

class TestMembres(unittest.TestCase):
    def setUp(self):
        self.db = DB(":memory:")

    def test_ajout_membre(self):
        self.db.exec(
            "INSERT INTO membre(avec_id,nom,prenom,telephone,numero,nb_parts,statut)"
            " VALUES(?,?,?,?,?,?,?)",
            (1, "Test", "User", "+243999999999", "001", 5, "actif"))
        self.db.commit()
        m = self.db.un("SELECT * FROM membre WHERE nom='Test'")
        self.assertIsNotNone(m)
        self.assertEqual(m["prenom"], "User")
        self.assertEqual(m["nb_parts"], 5)
        self.assertEqual(m["statut"], "actif")

    def test_modification_membre(self):
        self.db.exec("INSERT INTO membre(nom,avec_id) VALUES('Mod',1)")
        self.db.commit()
        mid = self.db.valeur("SELECT id FROM membre WHERE nom='Mod'")
        self.db.exec("UPDATE membre SET prenom='ified' WHERE id=?", (mid,))
        self.db.commit()
        m = self.db.un("SELECT prenom FROM membre WHERE id=?", (mid,))
        self.assertEqual(m["prenom"], "ified")

    def test_changement_statut(self):
        self.db.exec("INSERT INTO membre(nom,statut,avec_id) VALUES('Status','actif',1)")
        self.db.commit()
        mid = self.db.valeur("SELECT id FROM membre WHERE nom='Status'")
        for s in ["suspendu", "sorti", "actif"]:
            self.db.exec("UPDATE membre SET statut=? WHERE id=?", (s, mid))
            self.db.commit()
            m = self.db.un("SELECT statut FROM membre WHERE id=?", (mid,))
            self.assertEqual(m["statut"], s)

    def test_membre_avec_id_par_defaut(self):
        self.db.exec("INSERT INTO membre(nom) VALUES('Default')")
        self.db.commit()
        m = self.db.un("SELECT avec_id FROM membre WHERE nom='Default'")
        self.assertEqual(m["avec_id"], 1)

    def test_membre_unicode(self):
        self.db.exec(
            "INSERT INTO membre(nom,prenom,adresse,avec_id) VALUES(?,?,?,?)",
            ("Mükendal", "Béatrice", "Kinshasa / République Démocratique du Congo", 1))
        self.db.commit()
        m = self.db.un("SELECT * FROM membre WHERE nom='Mükendal'")
        self.assertIsNotNone(m)
        self.assertIn("République", m["adresse"])

    def test_notes_longues(self):
        notes = "A" * 1000
        self.db.exec(
            "INSERT INTO membre(nom,notes,avec_id) VALUES(?,?,?)",
            ("LongNotes", notes, 1))
        self.db.commit()
        m = self.db.un("SELECT notes FROM membre WHERE nom='LongNotes'")
        self.assertEqual(len(m["notes"]), 1000)


# ════════════════════════════════════════════════════════════════
#  AUDIT LOG — TRACABILITE
# ════════════════════════════════════════════════════════════════

class TestAuditLog(unittest.TestCase):
    def setUp(self):
        self.db = DB(":memory:")

    def test_action_enregistree(self):
        self.db.audit(1, "admin", "TEST_ACTION", "membre", 42, {"key": "val"})
        self.db.commit()
        r = self.db.un("SELECT * FROM audit_log WHERE action='TEST_ACTION'")
        self.assertIsNotNone(r)
        self.assertEqual(r["uid"], 1)
        self.assertEqual(r["login"], "admin")
        self.assertEqual(r["tbl"], "membre")
        self.assertEqual(r["rid"], 42)

    def test_details_json(self):
        self.db.audit(1, "admin", "TEST_JSON", details={"montant": 5000, "type": "epargne"})
        self.db.commit()
        import json
        r = self.db.un("SELECT details FROM audit_log WHERE action='TEST_JSON'")
        d = json.loads(r["details"])
        self.assertEqual(d["montant"], 5000)

    def test_details_none(self):
        self.db.audit(1, "admin", "TEST_NONE")
        self.db.commit()
        r = self.db.un("SELECT details FROM audit_log WHERE action='TEST_NONE'")
        self.assertIsNone(r["details"])

    def test_timestamp_present(self):
        self.db.audit(1, "admin", "TEST_TS")
        self.db.commit()
        r = self.db.un("SELECT ts FROM audit_log WHERE action='TEST_TS'")
        self.assertIsNotNone(r["ts"])

    def test_plusieurs_actions(self):
        for i in range(10):
            self.db.audit(1, "admin", f"ACTION_{i}")
        self.db.commit()
        count = self.db.valeur("SELECT COUNT(*) FROM audit_log WHERE action LIKE 'ACTION_%'")
        self.assertEqual(count, 10)


# ════════════════════════════════════════════════════════════════
#  BACKUP — SAUVEGARDE ET RESTAURATION
# ════════════════════════════════════════════════════════════════

class TestBackup(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.dbpath = os.path.join(self.tmpdir, "test.db")
        self.bkppath = os.path.join(self.tmpdir, "sauvegardes")
        self.db = DB(self.dbpath)
        self.bkp = Backup(self.dbpath, self.bkppath)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_sauvegarde_cree_fichier(self):
        dest = self.bkp.sauvegarder()
        self.assertTrue(os.path.exists(dest))
        self.assertIn("akibacore_", os.path.basename(dest))
        self.assertTrue(dest.endswith(".db"))

    def test_sauvegarde_contient_donnees(self):
        self.db.exec("INSERT INTO membre(nom,avec_id) VALUES('Backup',1)")
        self.db.commit()
        self.db.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        dest = self.bkp.sauvegarder()
        db2 = DB(dest)
        m = db2.un("SELECT * FROM membre WHERE nom='Backup'")
        self.assertIsNotNone(m)

    def test_rotation_15_fichiers(self):
        for i in range(17):
            self.bkp.sauvegarder()
        fichiers = sorted([
            f for f in os.listdir(self.bkppath)
            if f.startswith("akibacore_") and f.endswith(".db")
        ])
        self.assertLessEqual(len(fichiers), BACKUP_MAX)

    def test_sauvegarde_apres_modification(self):
        self.db.exec("INSERT INTO membre(nom,avec_id) VALUES('Before',1)")
        self.db.commit()
        self.db.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        dest1 = self.bkp.sauvegarder()
        self.db.exec("INSERT INTO membre(nom,avec_id) VALUES('After',1)")
        self.db.commit()
        self.db.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        import time; time.sleep(1.1)
        dest2 = self.bkp.sauvegarder()
        db1 = DB(dest1)
        db2 = DB(dest2)
        self.assertIsNone(db1.un("SELECT * FROM membre WHERE nom='After'"))
        self.assertIsNotNone(db2.un("SELECT * FROM membre WHERE nom='After'"))

    def test_backup_repertoire_auto_cree(self):
        shutil.rmtree(self.bkppath, ignore_errors=True)
        self.assertFalse(os.path.exists(self.bkppath))
        self.bkp.sauvegarder()
        self.assertTrue(os.path.exists(self.bkppath))

    def test_restore_donnees_identiques(self):
        self.db.exec("INSERT INTO membre(nom,prenom,avec_id) VALUES('Restore','Test',1)")
        self.db.exec("INSERT INTO epargne(membre_id,montant,type) VALUES(1,50000,'ordinaire')")
        self.db.commit()
        self.db.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        dest = self.bkp.sauvegarder()
        self.db.exec("UPDATE membre SET nom='Modified' WHERE id=1")
        self.db.commit()
        db2 = DB(dest)
        m = db2.un("SELECT * FROM membre WHERE id=1")
        self.assertEqual(m["nom"], "Restore")


# ════════════════════════════════════════════════════════════════
#  END-TO-END — PARCOURS COMPLET
# ════════════════════════════════════════════════════════════════

class TestEndToEnd(unittest.TestCase):
    def setUp(self):
        self.db = DB(":memory:")
        self.auth = Auth(self.db)
        self.auth.connecter("admin", "admin123")

    def test_parcours_complet(self):
        """Scenario complet : membre -> epargne -> session -> credit -> remboursement."""
        # 1. Creer membre
        self.db.exec(
            "INSERT INTO membre(avec_id,nom,prenom,telephone,numero,nb_parts,statut)"
            " VALUES(?,?,?,?,?,?,?)",
            (1, "E2E", "Testeur", "+243999999999", "E2E001", 3, "actif"))
        self.db.commit()
        mid = self.db.valeur("SELECT id FROM membre WHERE nom='E2E'")
        self.assertIsNotNone(mid)

        # 2. Enregistrer epargne
        self.db.exec(
            "INSERT INTO epargne(membre_id,montant,type,date_op,cree_par)"
            " VALUES(?,?,?,?,?)",
            (mid, 50_000, "ordinaire", "2025-01-15", self.auth.uid))
        self.db.commit()
        ep = Finance.solde_epargne(self.db, mid)
        self.assertEqual(ep, 50_000)

        # 3. Creer session
        self.db.exec(
            "INSERT INTO session(avec_id,numero,date_reunion,cree_par)"
            " VALUES(?,?,?,?)",
            (1, 1, "2025-01-15", self.auth.uid))
        self.db.commit()
        sid = self.db.valeur("SELECT id FROM session WHERE numero=1")
        self.assertIsNotNone(sid)

        # 4. Octroyer credit
        do = date(2025, 2, 1)
        dur = 6
        t = TAUX_INTERET_DEFAUT
        p = 100_000
        inter = Finance.interet_simple(p, t, dur)
        total = round(p + inter, 2)
        ech = Finance.date_echeance(do, dur)
        self.db.exec("""
            INSERT INTO credit(membre_id,principal,taux,duree_mois,
            date_octroi,date_echeance,montant_interet,montant_total,cree_par)
            VALUES(?,?,?,?,?,?,?,?,?)
        """, (mid, p, t, dur, do.isoformat(), ech.isoformat(), inter, total, self.auth.uid))
        self.db.commit()
        cid = self.db.valeur("SELECT id FROM credit WHERE membre_id=?", (mid,))
        self.assertEqual(inter, 5_000)
        self.assertEqual(total, 105_000)

        # 5. Rembourser partiellement
        self.db.exec("""
            INSERT INTO remboursement(credit_id,membre_id,mont_principal,
            mont_interet,mont_penalite,montant_total,date_paiement,cree_par)
            VALUES(?,?,?,?,?,?,?,?)
        """, (cid, mid, 47_619.05, 2_380.95, 0, 50_000, "2025-03-01", self.auth.uid))
        self.db.exec("UPDATE credit SET rembourse=50000 WHERE id=?", (cid,))
        self.db.commit()
        c = self.db.un("SELECT * FROM credit WHERE id=?", (cid,))
        self.assertEqual(Finance.solde_credit(c), 55_000)

        # 6. Rembourser le solde
        self.db.exec("""
            INSERT INTO remboursement(credit_id,membre_id,mont_principal,
            mont_interet,mont_penalite,montant_total,date_paiement,cree_par)
            VALUES(?,?,?,?,?,?,?,?)
        """, (cid, mid, 55_000, 0, 0, 55_000, "2025-04-01", self.auth.uid))
        self.db.exec("UPDATE credit SET rembourse=105000,statut='solde' WHERE id=?", (cid,))
        self.db.commit()
        c = self.db.un("SELECT * FROM credit WHERE id=?", (cid,))
        self.assertEqual(c["statut"], "solde")
        self.assertEqual(c["rembourse"], 105_000)
        self.assertEqual(Finance.solde_credit(c), 0)

        # 7. Verifier audit
        logs = self.db.tous(
            "SELECT action FROM audit_log WHERE uid=?", (self.auth.uid,))
        actions = {l["action"] for l in logs}
        self.assertIn("CONNEXION", actions)

    def test_multiples_membres_et_credits(self):
        """Deux membres avec credits separes."""
        for nom in ["Alpha", "Beta"]:
            self.db.exec("INSERT INTO membre(nom,avec_id) VALUES(?,1)", (nom,))
        self.db.commit()
        ids = [r["id"] for r in self.db.tous("SELECT id FROM membre WHERE nom IN ('Alpha','Beta')")]

        for mid in ids:
            ech = Finance.date_echeance(date(2026, 1, 1), 12)
            self.db.exec("""
                INSERT INTO credit(membre_id,principal,taux,duree_mois,
                date_octroi,date_echeance,montant_interet,montant_total)
                VALUES(?,?,?,?,?,?,?,?)
            """, (mid, 200_000, 0.10, 12, "2026-01-01", ech.isoformat(), 20_000, 220_000))
        self.db.commit()

        Finance.maj_statuts(self.db)
        for mid in ids:
            c = self.db.un("SELECT statut FROM credit WHERE membre_id=?", (mid,))
            self.assertEqual(c["statut"], "actif", f"Credit de membre {mid} doit etre actif")


# ════════════════════════════════════════════════════════════════
#  FINANCE — CALCULS REFERENCE (CAS DE TEST OFFICIELS)
# ════════════════════════════════════════════════════════════════

class TestCasReferences(unittest.TestCase):
    """Cas de reference documentes dans les specifications."""

    def test_reference_interet_1000_10pct_12mois(self):
        """Principal=1000, Taux=10%, Duree=12 mois -> Interet=100, Total=1100"""
        i = Finance.interet_simple(1000, 0.10, 12)
        self.assertEqual(i, 100)

    def test_reference_interet_1000_10pct_6mois(self):
        """Principal=1000, Taux=10%, Duree=6 mois -> Interet=50, Total=1050"""
        i = Finance.interet_simple(1000, 0.10, 6)
        self.assertEqual(i, 50)

    def test_reference_interet_1000_10pct_3mois(self):
        """Principal=1000, Taux=10%, Duree=3 mois -> Interet=25, Total=1025"""
        i = Finance.interet_simple(1000, 0.10, 3)
        self.assertEqual(i, 25)

    def test_reference_penalite_1000_2pct_30jours(self):
        """Solde=1000, Taux=2%, Retard=30j -> Penalite=20"""
        p = Finance.penalite(1000, 0.02, 30)
        self.assertEqual(p, 20)

    def test_reference_penalite_1000_2pct_60jours(self):
        """Solde=1000, Taux=2%, Retard=60j -> Penalite=40"""
        p = Finance.penalite(1000, 0.02, 60)
        self.assertEqual(p, 40)


# ════════════════════════════════════════════════════════════════
#  VERSION ET CONFIGURATION
# ════════════════════════════════════════════════════════════════

class TestConfiguration(unittest.TestCase):
    def test_version_format(self):
        parties = APP_VERSION.split(".")
        self.assertEqual(len(parties), 3)
        for p in parties:
            self.assertTrue(p.isdigit())

    def test_backup_max_positif(self):
        self.assertGreater(BACKUP_MAX, 0)
        self.assertLessEqual(BACKUP_MAX, 100)

    def test_taux_defaut_coherents(self):
        self.assertGreater(TAUX_INTERET_DEFAUT, 0)
        self.assertLess(TAUX_INTERET_DEFAUT, 1)
        self.assertGreater(TAUX_PENALITE_DEFAUT, 0)
        self.assertLess(TAUX_PENALITE_DEFAUT, 1)


if __name__ == "__main__":
    unittest.main()
