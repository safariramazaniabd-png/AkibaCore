#!/usr/bin/env python3
"""Tests des reçus financiers AkibaCore v2.1.
Couvre : numérotation unique jamais réutilisée, enregistrement + audit,
contenu du ticket, génération PDF hors ligne.
Aucune dépendance externe (unittest uniquement).
"""
import unittest
import sys
import os
import tempfile
import shutil
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from main import (
    DB, Auth, Recep, PDFGen, Imprimeur, APP_NOM,
)


class TestRecepBase(unittest.TestCase):
    def setUp(self):
        self.db = DB(":memory:")
        self.auth = Auth(self.db)
        self.assertTrue(self.auth.connecter("admin", "admin123"))
        self.db.exec("INSERT INTO membre(nom,prenom,numero,avec_id)"
                     " VALUES('KABILA','Jean','M-001',1)")
        self.db.commit()
        self.membre = self.db.un("SELECT * FROM membre WHERE numero='M-001'")
        self.avec = self.db.un("SELECT * FROM avec WHERE id=1")

    def test_numero_premier(self):
        no = Recep.numero_suivant(self.db)
        self.assertEqual(no, f"REC-{date.today().year}-000001")

    def test_numero_sequentiels(self):
        u = self.auth.uid
        r1 = Recep.enregistrer(self.db, u, "admin", "EPARGNE", "epargne", 1,
                               self.membre["id"], 5000, avec_id=1)
        r2 = Recep.enregistrer(self.db, u, "admin", "EPARGNE", "epargne", 2,
                               self.membre["id"], 3000, avec_id=1)
        self.assertEqual(r1["recu_no"], f"REC-{date.today().year}-000001")
        self.assertEqual(r2["recu_no"], f"REC-{date.today().year}-000002")

    def test_numero_jamais_reutilise_apres_suppression(self):
        u = self.auth.uid
        r1 = Recep.enregistrer(self.db, u, "admin", "EPARGNE", "epargne", 1,
                               self.membre["id"], 5000, avec_id=1)
        r2 = Recep.enregistrer(self.db, u, "admin", "EPARGNE", "epargne", 2,
                               self.membre["id"], 3000, avec_id=1)
        self.db.exec("DELETE FROM receipt WHERE id=?", (r2["id"],))
        self.db.commit()
        # MAX() ne régresse pas : le numéro 000003 est attribué, jamais 000002.
        r3 = Recep.enregistrer(self.db, u, "admin", "EPARGNE", "epargne", 3,
                               self.membre["id"], 1000, avec_id=1)
        self.assertEqual(r3["recu_no"], f"REC-{date.today().year}-000003")

    def test_sequences_par_annee(self):
        # Un reçu de 2025 ne doit pas perturber la séquence 2026.
        self.db.exec("INSERT INTO receipt(recu_no,type,operation,membre_id,avec_id,montant)"
                     " VALUES('REC-2025-000042','EPARGNE','epargne',?,1,500)",
                     (self.membre["id"],))
        self.db.commit()
        self.assertEqual(self.db.valeur(
            "SELECT recu_no FROM receipt WHERE recu_no LIKE 'REC-2025-%'"),
            "REC-2025-000042")
        self.assertEqual(Recep.numero_suivant(self.db),
                         f"REC-{date.today().year}-000001")

    def test_enregistrer_audit_et_details_json(self):
        details = {"penalite": 0, "interet": 100, "principal": 900,
                   "solde": 2000, "credit_id": 7}
        r = Recep.enregistrer(self.db, self.auth.uid, "admin", "REMBOURSEMENT",
                              "remboursement", 12, self.membre["id"], 1000,
                              details, avec_id=1)
        self.assertIn("penalite", r["details"])
        import json
        self.assertDictEqual(json.loads(r["details"]), details)
        audit = self.db.tous("SELECT action, uid FROM audit_log WHERE action='CREER_RECU'")
        self.assertEqual(len(audit), 1)
        self.assertEqual(audit[0]["uid"], self.auth.uid)

    def test_ligne_libelles(self):
        self.assertEqual(Recep.ligne("EPARGNE"), "DÉPÔT D'ÉPARGNE")
        self.assertEqual(Recep.ligne("REMBOURSEMENT"), "REMBOURSEMENT DE CRÉDIT")
        self.assertEqual(Recep.ligne("CREDIT"), "OCTROI DE CRÉDIT")
        self.assertEqual(Recep.ligne("INCONNU"), "INCONNU")

    def test_texte_ticket_complet(self):
        r = Recep.enregistrer(self.db, self.auth.uid, "admin", "EPARGNE",
                              "epargne", 1, self.membre["id"], 5000, avec_id=1)
        txt = Recep.texte(r, self.avec, self.membre,
                          utilisateur_nom="Administrateur", utilisateur_role="admin")
        self.assertIn(APP_NOM, txt)
        self.assertIn("AVEC Bukavu", txt)
        self.assertIn(r["recu_no"], txt)
        self.assertIn("M-001", txt)
        self.assertIn("KABILA Jean", txt)
        self.assertIn("DÉPÔT D'ÉPARGNE", txt)
        self.assertIn("5,000 CDF", txt)
        self.assertIn("Administrateur", txt)
        self.assertIn("(admin)", txt)

    def test_texte_remboursement_details(self):
        details = {"montant_impute": 1000, "penalite": 50, "interet": 100,
                   "principal": 850, "solde": 4000, "credit_id": 7}
        r = Recep.enregistrer(self.db, self.auth.uid, "admin", "REMBOURSEMENT",
                              "remboursement", 12, self.membre["id"], 1000,
                              details, avec_id=1)
        txt = Recep.texte(r, self.avec, self.membre)
        self.assertIn("1,000 CDF", txt)
        self.assertIn("Pénalité : 50 CDF", txt)
        self.assertIn("Intérêt : 100 CDF", txt)
        self.assertIn("Principal : 850 CDF", txt)
        self.assertIn("Solde restant : 4,000 CDF", txt)
        self.assertIn("Crédit : CR-0007", txt)

    def test_creation_reçu_fk_membre(self):
        with self.assertRaises(Exception):
            Recep.enregistrer(self.db, self.auth.uid, "admin", "EPARGNE",
                              "epargne", 1, 99999, 5000, avec_id=1)


class TestPDFGen(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _chemin(self, nom="out.pdf"):
        return os.path.join(self.tmp, nom)

    def test_pdf_structure_base(self):
        chemin = self._chemin()
        PDFGen.generer(["Ligne 1", ("Ligne en gras", True)], chemin)
        data = open(chemin, "rb").read()
        self.assertTrue(data.startswith(b"%PDF-1.4"))
        self.assertTrue(data.rstrip().endswith(b"%%EOF"))
        self.assertIn(b"/Type /Catalog", data)
        self.assertIn(b"/Type /Page", data)
        self.assertIn(b"/Courier", data)
        self.assertIn(b"xref", data)
        # 4 objets de base + 1 page + 1 contenu = 6
        self.assertEqual(data.count(b" 0 obj"), 6)

    def test_pdf_accents_cp1252(self):
        chemin = self._chemin()
        PDFGen.generer(["Épargne — reçu n° REC-2026-000001 (é à ç û)"], chemin)
        data = open(chemin, "rb").read()
        self.assertTrue(data.startswith(b"%PDF-1.4"))
        self.assertIn("Épargne".encode("cp1252"), data)

    def test_pdf_longue_ligne_multipage_pas_de_pb(self):
        chemin = self._chemin()
        for i in range(200):
            PDFGen.generer(["x" * 300, ("y" * 200, True)], chemin)
        data = open(chemin, "rb").read()
        self.assertTrue(data.startswith(b"%PDF-1.4"))
        self.assertTrue(data.rstrip().endswith(b"%%EOF"))

    def test_pdf_texte_vide(self):
        chemin = self._chemin()
        PDFGen.generer([], chemin)
        data = open(chemin, "rb").read()
        # Une page vide au minimum, PDF toujours valide
        self.assertTrue(data.startswith(b"%PDF-1.4"))
        self.assertTrue(data.rstrip().endswith(b"%%EOF"))

    def test_pdf_reelu_recu(self):
        db = DB(":memory:")
        auth = Auth(db)
        auth.connecter("admin", "admin123")
        db.exec("INSERT INTO membre(nom,prenom,numero,avec_id) VALUES('A','B','M-9',1)")
        db.commit()
        m = db.un("SELECT * FROM membre WHERE numero='M-9'")
        a = db.un("SELECT * FROM avec WHERE id=1")
        r = Recep.enregistrer(db, auth.uid, "admin", "EPARGNE", "epargne", 1,
                              m["id"], 7500, avec_id=1)
        texte = Recep.texte(r, a, m, utilisateur_nom="Admin", utilisateur_role="admin")
        chemin = self._chemin("recu.pdf")
        PDFGen.generer(texte.split("\n"), chemin)
        data = open(chemin, "rb").read()
        self.assertTrue(data.startswith(b"%PDF-1.4"))
        self.assertIn(b"%PDF", data)
        self.assertIn("7,500 CDF".encode("cp1252"), data)


class TestImprimeur(unittest.TestCase):
    def test_aucune_imprimante_retourne_faux_sans_planter(self):
        # Sur machines sans 'lp'/'lpr', aucune levee d'exception : False.
        self.assertIsInstance(Imprimeur.imprimer("/tmp/opencode/inexistant.pdf"), bool)


if __name__ == "__main__":
    unittest.main()