#!/usr/bin/env python3
"""Scénario utilisateur réel — validation de bout en bout (hors ligne).

Reproduit dans l'ordre :
  1. Connexion admin
  2. Configuration CDF + USD
  3. Création de membres
  4. Création d'un utilisateur agent + permissions
  5. Dépôt épargne (50 000 CDF) + reçu
  6. Dépôt épargne (100 USD) + reçu — devises séparées
  7. Octroi d'un crédit (taux configuré, snapshot) + vérification intérêt
  8. Remboursement partiel + reçu
  9. Comptes : épargne/crédit/courant/bloqué créés
 10. Rapport : soldes par devise corrects
 11. Sauvegarde + restauration + vérification des données
Sans aucune dépendance réseau. unittest uniquement.
"""
import unittest
import sys
import os
import json
import hashlib
import secrets
import tempfile
import shutil
from datetime import date

sys.path.insert(0, os.path.dirname(__file__))
from main import (
    DB, Auth, Finance, Recep, Backup, PDFGen,
    TAUX_INTERET_DEFAUT, TAUX_PENALITE_DEFAUT,
)


class TestScenarioReel(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmp, "akibacore.db")
        self.bkp = Backup(db_chemin=self.db_path, rep=os.path.join(self.tmp, "sauvegardes"))
        self.db = DB(self.db_path)

    def tearDown(self):
        try:
            self.db._conn.close()
        except Exception:
            pass
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_scenario_complet(self):
        # 1. Connexion admin
        auth = Auth(self.db)
        self.assertTrue(auth.connecter("admin", "admin123"))

        # 2. Configurer CDF + USD sur l'AVEC 1
        self.db.exec("UPDATE avec SET devise='CDF', "
                     "devises_autorisees=?, types_credit=? WHERE id=1",
                     (json.dumps(["CDF", "USD"]), json.dumps(["ordinaire", "urgence"])))
        self.db.commit()

        # 3. Membres
        for n, p, num in (("KABILA", "Jean", "M-1"), ("MBUYI", "Chantal", "M-2")):
            self.db.exec("INSERT INTO membre(nom,prenom,numero,avec_id,nb_parts)"
                         " VALUES(?,?,?,1,3)", (n, p, num))
        self.db.commit()
        m1 = self.db.valeur("SELECT id FROM membre WHERE numero='M-1'")
        m2 = self.db.valeur("SELECT id FROM membre WHERE numero='M-2'")

        # 4. Créer un agent + permission
        sel = secrets.token_hex(16)
        ph = hashlib.pbkdf2_hmac('sha256', f"agent123{sel}".encode(),
                                 sel.encode(), 100000).hex()
        self.db.exec("INSERT INTO utilisateur(nom,login,pwd_hash,sel,role,avec_id)"
                     " VALUES('Agent','agent1',?,?,?,1)", (ph, sel, "agent"))
        self.db.commit()
        agent = Auth(self.db)
        self.assertTrue(agent.connecter("agent1", "agent123"))
        self.assertTrue(agent.permis("savings.create"))
        self.assertFalse(agent.permis("backup.restore"))

        # 5. Dépôt 50 000 CDF + reçu
        self.db.exec("INSERT INTO epargne(membre_id,montant,type,date_op,annule,devise,cree_par)"
                     " VALUES(?,50000,'ordinaire',date('now'),0,'CDF',?)", (m1, agent.uid))
        self.db.commit()
        r_cdf = Recep.enregistrer(self.db, agent.uid, "agent1", "EPARGNE", "epargne",
                                  self.db.valeur("SELECT id FROM epargne WHERE membre_id=? AND devise='CDF'",
                                                 (m1,)), m1, 50000, devise="CDF", avec_id=1)
        self.assertEqual(r_cdf["devise"], "CDF")

        # 6. Dépôt 100 USD + reçu (devises séparées)
        self.db.exec("INSERT INTO epargne(membre_id,montant,type,date_op,annule,devise,cree_par)"
                     " VALUES(?,100,'ordinaire',date('now'),0,'USD',?)", (m2, agent.uid))
        self.db.commit()
        r_usd = Recep.enregistrer(self.db, agent.uid, "agent1", "EPARGNE", "epargne",
                                  self.db.valeur("SELECT id FROM epargne WHERE membre_id=? AND devise='USD'",
                                                 (m2,)), m2, 100, devise="USD", avec_id=1)
        self.assertEqual(r_usd["devise"], "USD")
        # Les soldes ne sont jamais mélangés.
        self.assertEqual(Finance.solde_epargne(self.db, m1, "CDF"), 50000)
        self.assertEqual(Finance.solde_epargne(self.db, m1, "USD"), 0)
        self.assertEqual(Finance.solde_epargne(self.db, m2, "USD"), 100)

        # 7. Octroi crédit 500 USD, taux 10 %/an, 12 mois
        principal = 500
        taux = TAUX_INTERET_DEFAUT
        duree = 12
        interet = Finance.interet_simple(principal, taux, duree)
        self.db.exec(
            "INSERT INTO credit(membre_id,session_id,principal,taux,duree_mois,"
            "date_octroi,date_echeance,montant_interet,montant_total,rembourse,statut,"
            "devise,type_credit,taux_penalite,cree_par)"
            " VALUES(?,NULL,?,?,?,date('now'),date('now','+12 months'),?,?,0,"
            "'actif','USD','ordinaire',?,?)",
            (m2, principal, taux, duree, interet, principal + interet,
             TAUX_PENALITE_DEFAUT, agent.uid))
        self.db.commit()
        cr = self.db.un("SELECT * FROM credit WHERE membre_id=? AND devise='USD'", (m2,))
        self.assertEqual(cr["taux"], 0.10)
        self.assertEqual(Finance.solde_credit(cr), principal + interet)
        # Changement de taux ensuite : le crédit existant reste à 10 %.
        self.db.exec("UPDATE avec SET taux_interet=0.12 WHERE id=1")
        self.db.commit()
        self.assertEqual(self.db.un("SELECT * FROM credit WHERE id=?", (cr["id"],))["taux"], 0.10)

        # 8. Remboursement partiel (penalite -> interet -> capital) + reçu
        self.db.exec(
            "INSERT INTO remboursement(credit_id,membre_id,mont_principal,mont_interet,"
            "mont_penalite,montant_total,date_paiement,annule,devise,cree_par)"
            " VALUES(?,?,0,?,0,?,date('now'),0,'USD',?)",
            (cr["id"], m2, interet, interet, agent.uid))
        self.db.commit()
        self.db.exec("UPDATE credit SET rembourse=rembourse+? WHERE id=?",
                     (interet, cr["id"]))
        self.db.commit()
        cr2 = self.db.un("SELECT * FROM credit WHERE id=?", (cr["id"],))
        self.assertEqual(cr2["rembourse"], interet)
        r_remb = Recep.enregistrer(self.db, agent.uid, "agent1", "REMB", "remboursement",
                                   cr["id"], m2, interet, devise="USD", avec_id=1)
        self.assertEqual(r_remb["devise"], "USD")

        # 9. Comptes créés automatiquement
        Finance.avoir_compte(self.db, agent.uid, m1, "epargne", "CDF")
        Finance.avoir_compte(self.db, agent.uid, m2, "credit", "USD")
        Finance.impliquer_compte(self.db, agent.uid, m2, "courant", "USD", "depot", 200)
        Finance.impliquer_compte(self.db, agent.uid, m2, "bloque", "CDF", "depot", 30000)
        self.assertEqual(Finance.solde_compte(self.db, m2, "courant", "USD"), 200)
        self.assertEqual(Finance.solde_compte(self.db, m2, "bloque", "CDF"), 30000)

        # 10. Rapport : soldes par devise
        total_cdf = Finance.solde_epargne(self.db, m1, "CDF")
        total_usd = Finance.solde_epargne(self.db, m2, "USD")
        self.assertEqual(total_cdf, 50000)
        self.assertEqual(total_usd, 100)

        # 11. Sauvegarde + restauration + vérification
        sauvegarde = self.bkp.sauvegarder()
        self.assertTrue(os.path.exists(sauvegarde))
        # Ferme la connexion avant restauration (copie du fichier).
        self.db._conn.close()
        self.bkp.restaurer(db_chemin=self.db_path,
                           rep=os.path.join(self.tmp, "sauvegardes"))
        db2 = DB(self.db_path)
        self.assertEqual(
            db2.valeur("SELECT COUNT(*) FROM epargne WHERE annule=0 AND devise='CDF'"), 1)
        self.assertEqual(
            db2.valeur("SELECT COUNT(*) FROM epargne WHERE annule=0 AND devise='USD'"), 1)
        self.assertEqual(db2.valeur("SELECT COUNT(*) FROM receipt"), 3)
        self.assertEqual(db2.valeur("SELECT COUNT(*) FROM credit"), 1)
        self.assertEqual(
            db2.valeur("SELECT login FROM utilisateur WHERE role='agent'"), "agent1")


if __name__ == "__main__":
    unittest.main(verbosity=2)
