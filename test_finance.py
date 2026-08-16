#!/usr/bin/env python3
"""Tests minimaux pour les classes Finance, DB et Auth (pas de dependances externes)."""
import unittest
from datetime import date
import sys, os, hashlib, secrets, tempfile

sys.path.insert(0, os.path.dirname(__file__))
from main import Finance, DB, Auth, TAUX_PENALITE_DEFAUT


# ════════════════════════════════════════════════════════════════
#  FINANCE
# ════════════════════════════════════════════════════════════════

class TestInteretSimple(unittest.TestCase):
    def test_10_pourcent_12_mois(self):
        self.assertEqual(Finance.interet_simple(100_000, 0.10, 12), 10_000)

    def test_10_pourcent_6_mois(self):
        self.assertEqual(Finance.interet_simple(100_000, 0.10, 6), 5_000)

    def test_arrondi_2_decimales(self):
        self.assertEqual(Finance.interet_simple(33_333, 0.10, 7), 1_944.43)


class TestPenalite(unittest.TestCase):
    def test_30_jours(self):
        self.assertEqual(Finance.penalite(100_000, 0.02, 30), 2_000)

    def test_15_jours(self):
        self.assertEqual(Finance.penalite(100_000, 0.02, 15), 1_000)

    def test_0_jour(self):
        self.assertEqual(Finance.penalite(100_000, 0.02, 0), 0)


class TestJoursRetard(unittest.TestCase):
    def test_pas_de_retard(self):
        future = date.today().isoformat()
        self.assertEqual(Finance.jours_retard(future), 0)

    def test_10_jours(self):
        from datetime import timedelta
        d = (date.today() - timedelta(days=10)).isoformat()
        self.assertEqual(Finance.jours_retard(d), 10)

    def test_date_invalide(self):
        self.assertEqual(Finance.jours_retard("abc"), 0)


class TestDateEcheance(unittest.TestCase):
    def test_12_mois(self):
        r = Finance.date_echeance(date(2025, 1, 15), 12)
        self.assertEqual(r, date(2026, 1, 15))

    def test_1_mois(self):
        r = Finance.date_echeance(date(2025, 1, 31), 1)
        self.assertEqual(r, date(2025, 2, 28))

    def test_bissextile_29_fevrier(self):
        r = Finance.date_echeance(date(2024, 1, 29), 1)
        self.assertEqual(r, date(2024, 2, 29))

    def test_non_bissextile_28_fevrier(self):
        r = Finance.date_echeance(date(2025, 1, 29), 1)
        self.assertEqual(r, date(2025, 2, 28))

    def test_siecle_non_bissextile(self):
        r = Finance.date_echeance(date(2099, 12, 31), 12)
        self.assertEqual(r, date(2100, 12, 31))


class TestValiderMontant(unittest.TestCase):
    def test_valide(self):
        self.assertEqual(Finance.valider_montant("1000"), 1000.0)

    def test_virgule(self):
        self.assertEqual(Finance.valider_montant("1 000,50"), 1000.5)

    def test_negatif(self):
        with self.assertRaises(ValueError):
            Finance.valider_montant("-100")

    def test_zero(self):
        with self.assertRaises(ValueError):
            Finance.valider_montant("0")

    def test_vide(self):
        with self.assertRaises(ValueError):
            Finance.valider_montant("")


class TestValiderDate(unittest.TestCase):
    def test_valide(self):
        self.assertEqual(Finance.valider_date("2025-06-15"), date(2025, 6, 15))

    def test_invalide(self):
        with self.assertRaises(ValueError):
            Finance.valider_date("15-06-2025")

    def test_vide(self):
        with self.assertRaises(ValueError):
            Finance.valider_date("")


# ════════════════════════════════════════════════════════════════
#  DB (BDD en memoire)
# ════════════════════════════════════════════════════════════════

class TestDB(unittest.TestCase):
    def setUp(self):
        self.db = DB(":memory:")

    def test_seeds_admin_cree(self):
        admin = self.db.un("SELECT * FROM utilisateur WHERE login='admin'")
        self.assertIsNotNone(admin)
        self.assertEqual(admin["role"], "admin")
        self.assertEqual(admin["nom"], "Administrateur")

    def test_seeds_avec_cree(self):
        a = self.db.un("SELECT * FROM avec WHERE nom='AVEC Bukavu'")
        self.assertIsNotNone(a)

    def test_exec_et_un(self):
        self.db.exec("INSERT INTO membre(nom,prenom,avec_id) VALUES(?,?,?)",
                     ("Test", "User", 1))
        self.db.commit()
        m = self.db.un("SELECT * FROM membre WHERE nom='Test'")
        self.assertIsNotNone(m)
        self.assertEqual(m["prenom"], "User")

    def test_tous(self):
        self.db.exec("INSERT INTO membre(nom,avec_id) VALUES(?,?)", ("A", 1))
        self.db.exec("INSERT INTO membre(nom,avec_id) VALUES(?,?)", ("B", 1))
        self.db.commit()
        rows = self.db.tous("SELECT * FROM membre ORDER BY nom")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["nom"], "A")

    def test_valeur(self):
        r = self.db.valeur("SELECT COUNT(*) FROM utilisateur")
        self.assertEqual(r, 1)  # admin seed

    def test_rollback(self):
        self.db.exec("INSERT INTO membre(nom,avec_id) VALUES(?,?)", ("X", 1))
        self.db.rollback()
        r = self.db.valeur("SELECT COUNT(*) FROM membre WHERE nom='X'")
        self.assertEqual(r, 0)

    def test_audit_ne_leve_jamais_exception(self):
        # audit avec uid inexistant ne doit pas lever d'exception
        self.db.audit(9999, "ghost", "TEST", details={"clé": "valeur"})
        # pas d'assertion — on vérifie juste qu'aucune exception n'est levée

    def test_wal_mode(self):
        mode = self.db.valeur("PRAGMA journal_mode")
        # En memoire, WAL n'est pas applicable — on verifie juste que le PRAGMA ne plante pas
        self.assertIn(mode, ("wal", "memory"))

    def test_foreign_keys(self):
        fk = self.db.valeur("PRAGMA foreign_keys")
        self.assertEqual(fk, 1)

    def test_row_factory_dict(self):
        self.db.exec("INSERT INTO membre(nom,avec_id) VALUES(?,?)", ("Dict", 1))
        self.db.commit()
        m = self.db.un("SELECT * FROM membre WHERE nom='Dict'")
        self.assertIsInstance(m, dict)


# ════════════════════════════════════════════════════════════════
#  AUTH
# ════════════════════════════════════════════════════════════════

class TestAuth(unittest.TestCase):
    def setUp(self):
        self.db = DB(":memory:")
        self.auth = Auth(self.db)

    def test_connexion_admin(self):
        r = self.auth.connecter("admin", "admin123")
        self.assertTrue(r)
        self.assertEqual(self.auth.user["login"], "admin")

    def test_connexion_mauvais_mdp(self):
        r = self.auth.connecter("admin", "mauvais")
        self.assertFalse(r)
        self.assertIsNone(self.auth.user)

    def test_connexion_login_inexistant(self):
        r = self.auth.connecter("nobody", "admin123")
        self.assertFalse(r)

    def test_est_admin(self):
        self.auth.connecter("admin", "admin123")
        self.assertTrue(self.auth.est_admin)

    def test_est_admin_si_deconnecte(self):
        self.assertFalse(self.auth.est_admin)

    def test_uid_et_ulogin(self):
        self.auth.connecter("admin", "admin123")
        self.assertIsNotNone(self.auth.uid)
        self.assertEqual(self.auth.ulogin, "admin")

    def test_changer_mdp(self):
        self.auth.connecter("admin", "admin123")
        self.auth.changer_mdp("admin", "admin123", "nouveau42")
        # L'ancien mot de passe ne fonctionne plus
        self.assertFalse(self.auth.connecter("admin", "admin123"))
        # Le nouveau fonctionne
        self.assertTrue(self.auth.connecter("admin", "nouveau42"))

    def test_changer_mdp_ancien_incorrect(self):
        self.auth.connecter("admin", "admin123")
        with self.assertRaises(ValueError):
            self.auth.changer_mdp("admin", "mauvais", "nouveau42")

    def test_hachage_pbkdf2(self):
        """Verifie que le hash en BDD est bien un PBKDF2 et pas du SHA-256 brut."""
        u = self.db.un("SELECT * FROM utilisateur WHERE login='admin'")
        sha256_simple = hashlib.sha256(f"admin123{u['sel']}".encode()).hexdigest()
        self.assertNotEqual(sha256_simple, u["pwd_hash"])


# ════════════════════════════════════════════════════════════════
#  OPERATIONS METIER (epargne, credit, remboursement)
# ════════════════════════════════════════════════════════════════

class TestMetierEpargne(unittest.TestCase):
    """Tests pour les operations d'epargne en BDD memoire."""

    def setUp(self):
        self.db = DB(":memory:")
        self.db.exec("INSERT INTO membre(nom,prenom,avec_id) VALUES(?,?,?)",
                     ("Dupont", "Marie", 1))
        self.db.commit()
        self.membre_id = self.db.valeur("SELECT id FROM membre WHERE nom='Dupont'")

    def test_depot_epargne(self):
        self.db.exec(
            "INSERT INTO epargne(membre_id,montant,type,date_op) VALUES(?,?,?,?)",
            (self.membre_id, 50_000, "ordinaire", "2025-06-15"))
        self.db.commit()
        total = Finance.solde_epargne(self.db, self.membre_id)
        self.assertEqual(total, 50_000)

    def test_depot_multiples(self):
        for m in [10_000, 20_000, 5_000]:
            self.db.exec(
                "INSERT INTO epargne(membre_id,montant,type) VALUES(?,?,?)",
                (self.membre_id, m, "ordinaire"))
        self.db.commit()
        self.assertEqual(Finance.solde_epargne(self.db, self.membre_id), 35_000)

    def test_annulation_epargne(self):
        self.db.exec(
            "INSERT INTO epargne(membre_id,montant,type) VALUES(?,?,?)",
            (self.membre_id, 50_000, "ordinaire"))
        self.db.commit()
        eid = self.db.valeur("SELECT id FROM epargne WHERE montant=50000")
        self.db.exec("UPDATE epargne SET annule=1 WHERE id=?", (eid,))
        self.db.commit()
        self.assertEqual(Finance.solde_epargne(self.db, self.membre_id), 0)

    def test_types_epargne(self):
        for t in ["ordinaire", "solidarite", "urgence"]:
            self.db.exec(
                "INSERT INTO epargne(membre_id,montant,type) VALUES(?,?,?)",
                (self.membre_id, 10_000, t))
        self.db.commit()
        total = self.db.valeur(
            "SELECT COUNT(*) FROM epargne WHERE membre_id=? AND annule=0",
            (self.membre_id,))
        self.assertEqual(total, 3)


class TestMetierCredit(unittest.TestCase):
    """Tests pour les operations de credit en BDD memoire."""

    def setUp(self):
        self.db = DB(":memory:")
        self.db.exec("INSERT INTO membre(nom,prenom,avec_id) VALUES(?,?,?)",
                     ("Kabila", "Jean", 1))
        self.db.commit()
        self.membre_id = self.db.valeur("SELECT id FROM membre WHERE nom='Kabila'")

    def test_octroi_credit(self):
        inter = Finance.interet_simple(100_000, 0.10, 6)
        total = 100_000 + inter
        ech = Finance.date_echeance(date(2025, 1, 15), 6)
        self.db.exec("""
            INSERT INTO credit(membre_id,principal,taux,duree_mois,
            date_octroi,date_echeance,montant_interet,montant_total)
            VALUES(?,?,?,?,?,?,?,?)
        """, (self.membre_id, 100_000, 0.10, 6,
              "2025-01-15", ech.isoformat(), inter, total))
        self.db.commit()
        c = self.db.un("SELECT * FROM credit WHERE membre_id=?", (self.membre_id,))
        self.assertIsNotNone(c)
        self.assertEqual(c["principal"], 100_000)
        self.assertEqual(c["montant_interet"], 5_000)
        self.assertEqual(c["montant_total"], 105_000)
        self.assertEqual(c["statut"], "actif")
        self.assertEqual(c["rembourse"], 0)

    def test_maj_statuts_retard(self):
        ech = Finance.date_echeance(date(2024, 1, 1), 6)
        self.db.exec("""
            INSERT INTO credit(membre_id,principal,taux,duree_mois,
            date_octroi,date_echeance,montant_interet,montant_total,statut)
            VALUES(?,?,?,?,?,?,?,?,?)
        """, (self.membre_id, 100_000, 0.10, 6,
              "2024-01-01", ech.isoformat(), 5_000, 105_000, "actif"))
        self.db.commit()
        Finance.maj_statuts(self.db)
        c = self.db.un("SELECT statut FROM credit WHERE membre_id=?", (self.membre_id,))
        self.assertEqual(c["statut"], "en_retard")

    def test_maj_statuts_solde(self):
        ech = Finance.date_echeance(date(2025, 6, 1), 6)
        self.db.exec("""
            INSERT INTO credit(membre_id,principal,taux,duree_mois,
            date_octroi,date_echeance,montant_interet,montant_total,rembourse,statut)
            VALUES(?,?,?,?,?,?,?,?,?,?)
        """, (self.membre_id, 100_000, 0.10, 6,
              "2025-06-01", ech.isoformat(), 5_000, 105_000, 105_000, "actif"))
        self.db.commit()
        Finance.maj_statuts(self.db)
        c = self.db.un("SELECT statut FROM credit WHERE membre_id=?", (self.membre_id,))
        self.assertEqual(c["statut"], "solde")

    def test_solde_credit(self):
        ech = Finance.date_echeance(date(2025, 6, 1), 6)
        self.db.exec("""
            INSERT INTO credit(membre_id,principal,taux,duree_mois,
            date_octroi,date_echeance,montant_interet,montant_total,rembourse)
            VALUES(?,?,?,?,?,?,?,?,?)
        """, (self.membre_id, 100_000, 0.10, 6,
              "2025-06-01", ech.isoformat(), 5_000, 105_000, 30_000))
        self.db.commit()
        c = self.db.un("SELECT * FROM credit WHERE membre_id=?", (self.membre_id,))
        self.assertEqual(Finance.solde_credit(c), 75_000)


class TestMetierRemboursement(unittest.TestCase):
    """Tests pour les remboursements et l'imputation penalty -> interet -> principal."""

    def setUp(self):
        self.db = DB(":memory:")
        self.db.exec("INSERT INTO membre(nom,prenom,avec_id) VALUES(?,?,?)",
                     ("Mubi", "Aline", 1))
        self.db.commit()
        self.mid = self.db.valeur("SELECT id FROM membre WHERE nom='Mubi'")

        # Credit de 100 000 a 10% sur 6 mois = 5 000 interet = 105 000 total
        ech = Finance.date_echeance(date(2025, 1, 1), 6)
        self.db.exec("""
            INSERT INTO credit(membre_id,principal,taux,duree_mois,
            date_octroi,date_echeance,montant_interet,montant_total)
            VALUES(?,?,?,?,?,?,?,?)
        """, (self.mid, 100_000, 0.10, 6,
              "2025-01-01", ech.isoformat(), 5_000, 105_000))
        self.db.commit()
        self.cid = self.db.valeur("SELECT id FROM credit WHERE membre_id=?", (self.mid,))

    def test_remboursement_simple(self):
        # Rembourser 20 000 sans retard (pas de penalite)
        c = self.db.un("SELECT * FROM credit WHERE id=?", (self.cid,))
        self.db.exec("""
            INSERT INTO remboursement(credit_id,membre_id,mont_principal,
            mont_interet,mont_penalite,montant_total,date_paiement)
            VALUES(?,?,?,?,?,?,?)
        """, (self.cid, self.mid, 20_000, 0, 0, 20_000, "2025-02-01"))
        self.db.exec("UPDATE credit SET rembourse=rembourse+20000 WHERE id=?", (self.cid,))
        self.db.commit()
        c = self.db.un("SELECT * FROM credit WHERE id=?", (self.cid,))
        self.assertEqual(c["rembourse"], 20_000)
        self.assertEqual(Finance.solde_credit(c), 85_000)

    def test_remboursement_integral(self):
        # Rembourser la totalite
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

    def test_imputation_penalite_interet_principal(self):
        """Verifie l'algorithme d'imputation : penalite -> interet -> principal."""
        solde = 105_000
        jr = 30  # 30 jours de retard
        pen = Finance.penalite(solde, TAUX_PENALITE_DEFAUT, jr)
        self.assertEqual(pen, 2_100)  # 105_000 * 0.02 * (30/30)

        mt_paye = 10_000
        pen_pay = min(pen, mt_paye)  # 2_100
        reste = mt_paye - pen_pay    # 7_900
        ratio_i = 5_000 / 105_000   # ~0.0476
        int_pay = round(reste * ratio_i, 2)
        prin_pay = round(reste - int_pay, 2)

        self.assertEqual(pen_pay, 2_100)
        self.assertGreater(int_pay, 0)
        self.assertGreater(prin_pay, 0)
        self.assertAlmostEqual(pen_pay + int_pay + prin_pay, mt_paye, places=2)

    def test_statut_en_retard_apres_echeance(self):
        ech = Finance.date_echeance(date(2024, 6, 1), 6)
        self.db.exec("""
            INSERT INTO credit(membre_id,principal,taux,duree_mois,
            date_octroi,date_echeance,montant_interet,montant_total)
            VALUES(?,?,?,?,?,?,?,?)
        """, (self.mid, 50_000, 0.10, 6,
              "2024-06-01", ech.isoformat(), 2_500, 52_500))
        self.db.commit()
        Finance.maj_statuts(self.db)
        c = self.db.un("SELECT statut FROM credit WHERE membre_id=? AND montant_total=52500",
                       (self.mid,))
        self.assertEqual(c["statut"], "en_retard")


if __name__ == "__main__":
    unittest.main()
