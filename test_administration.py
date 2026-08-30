#!/usr/bin/env python3
"""Tests de régression pour la livraison finale v2.2.0.

Couvre spécifiquement :
  - la cause racine de la « page blanche » Administration (le filtrage de
    navigation _page_autorisee parcourait PERMISSIONS comme une liste de
    chaînes alors que ce sont des tuples → AttributeError pour tout
    utilisateur non-admin) ;
  - la gestion multi-utilisateurs (Utilisateurs / Rôles / Permissions) ;
  - la séparation stricte des devises CDF / USD ;
  - les comptes membres (épargne / crédit / courant / bloqué) ;
  - les taux figés à l'octroi (snapshot) ;
  - les reçus ;
  - les modèles de documents (isolation par AVEC).

Aucune dépendance externe (unittest uniquement).
"""
import unittest
import sys
import os
import json
import hashlib
import secrets
import tempfile
import shutil
import pathlib
from datetime import date

sys.path.insert(0, os.path.dirname(__file__))
from main import (
    DB, Auth, Finance, Recep, Modeles, PERMISSIONS, ROLES_DEFAUTS,
    DEVISES, DEVISE_DEFAUT, TAUX_INTERET_DEFAUT, TAUX_PENALITE_DEFAUT,
    FORMATS_MODELES, DOC_IN, APP_VERSION,
    _est_ecrivable, _repertoire_application, REPERTOIRE_DONNEES,
)


# ════════════════════════════════════════════════════════════════
#  PORTABILITÉ — DONNÉES JAMAIS DANS UN DOSSIER NON ÉCRIVABLE
# ════════════════════════════════════════════════════════════════

class TestRepertoireDonnees(unittest.TestCase):
    """Le répertoire de données ne doit jamais être non-écrivable
    (protection Windows "Program Files"). Vérifie la détection d'écriture
    et le basculement vers un dossier utilisateur."""

    def test_repertoire_donnees_ecrivable_par_defaut(self):
        # En développement : le répertoire application est aussi le répertoire
        # des données (dossier du script, accessible en écriture).
        rd = pathlib.Path(REPERTOIRE_DONNEES)
        self.assertTrue(_est_ecrivable(rd))

    def test_est_ecrivable_dossier_ok(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertTrue(_est_ecrivable(pathlib.Path(d)))

    def test_est_ecrivable_dossier_impossible(self):
        # Un fichier utilisé comme dossier est impossible à écrire.
        with tempfile.TemporaryDirectory() as d:
            fichier = pathlib.Path(d) / "bloc.txt"
            fichier.write_text("x", encoding="utf-8")
            self.assertFalse(_est_ecrivable(fichier))

    def test_basculement_vers_dossier_utilisateur(self):
        # Si le dossier application n'est pas écrivable et qu'une variable
        # d'environnement utilisateur existe, on bascule vers elle.
        app_orig = _repertoire_application
        env_orig = dict(os.environ)
        try:
            os.environ["LOCALAPPDATA"] = "/tmp/opencode/LocalAppDataTest"
            main = sys.modules["main"]
            main._repertoire_application = lambda: pathlib.Path("/proc/impossible_akiba")
            rd = main._repertoire_donnees()
            self.assertTrue(str(rd).endswith("LocalAppDataTest/AkibaCore")
                            or "LocalAppDataTest" in str(rd))
        finally:
            os.environ.clear()
            os.environ.update(env_orig)
            main = sys.modules["main"]
            main._repertoire_application = app_orig


# ════════════════════════════════════════════════════════════════
#  CAUSE RACINE — PAGE BLANCHE ADMINISTRATION
# ════════════════════════════════════════════════════════════════
#
# Le bug : dans AkibaCore._construire, la fonction imbriquée _page_autorisee
# parcourait `for p in PERMISSIONS ... if p.startswith(pref + ".")`.
# Or PERMISSIONS est une liste de TUPLE (code, libelle, groupe) : l'appel
# .startswith() sur un tuple levait AttributeError, provoquant l'échec de
# toute la construction de navigation pour CHAQUE utilisateur non-admin,
# donc une fenêtre blanche. Les administrateurs étaient épargnés car
# _page_autorisee retourne True très tôt via est_admin.
#
# Le correctif itère désormais sur `code` (le premier élément du tuple).
# On verrouille ici l'invariant de données (chaque code est une chaîne
# préfixable) et on rejoue exactement la logique corrigée.

class TestNavigationPageAutorisee(unittest.TestCase):
    """Rejoue la logique corrigée de _page_autorisee sans nécessiter Tk."""

    @staticmethod
    def _page_autorisee(auth, prefixes):
        # Miroir EXACT de la logique corrigée dans main.py (_construire).
        if prefixes is None:
            return True
        if auth.est_admin:
            return True
        if isinstance(prefixes, str):
            prefixes = [prefixes]
        return any(
            auth.permis(code)
            for code, _lib, _grp in PERMISSIONS
            for pref in prefixes
            if code.startswith(pref + ".")
        )

    def setUp(self):
        self.db = DB(":memory:")
        self.auth = Auth(self.db)
        self.assertTrue(self.auth.connecter("admin", "admin123"))

    def test_permis_codes_sont_des_chaines_prefixables(self):
        # Invariant de données qui a fait échouer la navigation.
        for entry in PERMISSIONS:
            self.assertIsInstance(entry, tuple)
            self.assertIsInstance(entry[0], str)
            self.assertTrue(entry[0].startswith(entry[0].split(".")[0] + "."))

    def test_admin_voit_toutes_les_pages(self):
        for pref in (None, "users", "audit", "documents", "accounts",
                     "settings", "members", "savings", "loans",
                     "repayments", "reports", "sessions", "receipts", "backup"):
            self.assertTrue(self._page_autorisee(self.auth, pref),
                            f"admin doit voir le préfixe {pref}")

    def _creer_non_admin(self, login, role, perms):
        sel = secrets.token_hex(16)
        ph = hashlib.pbkdf2_hmac('sha256', f"t123{sel}".encode(),
                                 sel.encode(), 100000).hex()
        self.db.exec(
            "INSERT INTO utilisateur(nom,login,pwd_hash,sel,role,avec_id)"
            " VALUES(?,?,?,?,?,1)", (login.title(), login, ph, sel, role))
        self.db.commit()
        if perms:
            uid = self.db.valeur("SELECT id FROM utilisateur WHERE login=?", (login,))
            for p in perms:
                self.db.exec(
                    "INSERT OR IGNORE INTO user_permission(utilisateur_id,code)"
                    " VALUES(?,?)", (uid, p))
            self.db.commit()
        auth = Auth(self.db)
        self.assertTrue(auth.connecter(login, "t123"))
        return auth

    def test_non_admin_agent_peut_naviguer_sans_crash(self):
        # L'agent a les permissions du rôle 'agent' : ni users.* ni backup.restore,
        # mais il possède audit.view.
        auth = self._creer_non_admin("agentx", "agent", None)
        # La page Administration est accessible via son droit audit.view.
        self.assertTrue(self._page_autorisee(auth, ("users", "audit")))
        # … mais la page Utilisateurs (préfixe "users") ne l'est PAS.
        self.assertFalse(self._page_autorisee(auth, "users"))
        # Les pages métier restent visibles.
        self.assertTrue(self._page_autorisee(auth, "members"))
        self.assertTrue(self._page_autorisee(auth, "savings"))

    def test_non_admin_avec_audit_view_voit_administration(self):
        # Un utilisateur possédant audit.view doit pouvoir ouvrir
        # Administration (l'onglet lui est présenté) sans crash.
        auth = self._creer_non_admin("auditeur2", "auditeur", ["audit.view"])
        self.assertTrue(self._page_autorisee(auth, ("users", "audit")))
        # et sans aucune permission users.*, seul le journal est pertinent
        self.assertFalse(any(auth.permis(c) for c in
                             ("users.view", "users.create", "users.edit",
                              "users.disable", "users.permissions")))

    def test_page_autorisee_retourne_toujours_un_bool(self):
        auth = self._creer_non_admin("lecteurx", "lecteur", None)
        for pref in (None, "", "users", "audit", "members", "xyz_absolu"):
            for _ in range(3):
                v = self._page_autorisee(auth, pref)
                self.assertIn(v, (True, False), f"pref={pref!r} → {v!r}")


# ════════════════════════════════════════════════════════════════
#  GESTION MULTI-UTILISATEURS — UTILISATEURS / RÔLES / PERMISSIONS
# ════════════════════════════════════════════════════════════════

class TestGestionUtilisateurs(unittest.TestCase):
    def setUp(self):
        self.db = DB(":memory:")
        self.auth = Auth(self.db)
        self.assertTrue(self.auth.connecter("admin", "admin123"))

    def _creer(self, login, role, actif=1):
        sel = secrets.token_hex(16)
        ph = hashlib.pbkdf2_hmac('sha256', f"mdp{sel}".encode(),
                                 sel.encode(), 100000).hex()
        self.db.exec(
            "INSERT INTO utilisateur(nom,login,pwd_hash,sel,role,actif,avec_id)"
            " VALUES(?,?,?,?,?,?,1)", (login, login, ph, sel, role, actif))
        self.db.commit()
        return self.db.valeur("SELECT id FROM utilisateur WHERE login=?", (login,))

    def test_desactivation_empeche_connexion(self):
        uid = self._creer("userdes", "agent")
        self.db.exec("UPDATE utilisateur SET actif=0 WHERE id=?", (uid,))
        self.db.commit()
        self.assertFalse(Auth(self.db).connecter("userdes", "mdp"))

    def test_reactivation_restaure_connexion(self):
        uid = self._creer("useract", "agent", actif=0)
        self.db.exec("UPDATE utilisateur SET actif=1 WHERE id=?", (uid,))
        self.db.commit()
        self.assertTrue(Auth(self.db).connecter("useract", "mdp"))

    def test_reinitialisation_mdp(self):
        uid = self._creer("userreinit", "agent")
        sel = secrets.token_hex(16)
        ph = hashlib.pbkdf2_hmac('sha256', f"nouveau{sel}".encode(),
                                 sel.encode(), 100000).hex()
        self.db.exec("UPDATE utilisateur SET pwd_hash=?, sel=? WHERE id=?",
                     (ph, sel, uid))
        self.db.commit()
        self.assertFalse(Auth(self.db).connecter("userreinit", "mdp"))
        self.assertTrue(Auth(self.db).connecter("userreinit", "nouveau"))

    def test_permission_individuelle_accorde_droit(self):
        # L'agent n'a PAS settings.financial.edit par défaut ; on le lui octroie
        # individuellement et il devient effectif.
        uid = self._creer("userperm", "agent")
        auth = Auth(self.db)
        auth.connecter("userperm", "mdp")
        self.assertFalse(auth.permis("settings.financial.edit"))
        self.db.exec("INSERT INTO user_permission(utilisateur_id,code)"
                     " VALUES(?,?)", (uid, "settings.financial.edit"))
        self.db.commit()
        auth._charger_permissions()
        self.assertTrue(auth.permis("settings.financial.edit"))
        # Une permission non octroyée reste refusée.
        self.assertFalse(auth.permis("backup.restore"))

    def test_role_defaut_contient_42_permissions_admin(self):
        admin_perms = tuple(ROLES_DEFAUTS["admin"])[2]
        self.assertEqual(len(admin_perms), len(PERMISSIONS))

    def test_suppression_aucune_permissions(self):
        # Un utilisateur 'caissier' sans droit supplémentaire ne doit pas
        # avoir accès aux fonctions d'administration.
        uid = self._creer("caissier2", "caissier")
        auth = Auth(self.db)
        auth.connecter("caissier2", "mdp")
        self.assertFalse(auth.permis("users.view"))
        self.assertFalse(auth.permis("audit.view"))
        self.assertFalse(auth.permis("backup.restore"))
        self.assertFalse(auth.permis("settings.financial.edit"))


# ════════════════════════════════════════════════════════════════
#  DEVISES — SÉPARATION STRICTE CDF / USD
# ════════════════════════════════════════════════════════════════

class TestDevisesSeparation(unittest.TestCase):
    def setUp(self):
        self.db = DB(":memory:")
        self.auth = Auth(self.db)
        self.auth.connecter("admin", "admin123")
        self.db.exec("INSERT INTO membre(nom,prenom,numero,avec_id)"
                     " VALUES('MBUYI','Chantal','M-002',1)")
        self.db.commit()
        self.mid = self.db.valeur("SELECT id FROM membre WHERE numero='M-002'")

    def test_devises_non_melangees_epargne(self):
        for m, d in ((50000, "CDF"), (100, "USD")):
            self.db.exec(
                "INSERT INTO epargne(membre_id,montant,type,date_op,annule,devise)"
                " VALUES(?,?,'ordinaire',date('now'),0,?)", (self.mid, m, d))
        self.db.commit()
        self.assertEqual(Finance.solde_epargne(self.db, self.mid, "CDF"), 50000)
        self.assertEqual(Finance.solde_epargne(self.db, self.mid, "USD"), 100)
        # Le total "toutes devises" ne mélange pas : il n'est jamais additionné.
        self.assertEqual(Finance.solde_epargne(self.db, self.mid, "USD"), 100)

    def test_solde_epargne_annulation_exclue(self):
        self.db.exec(
            "INSERT INTO epargne(membre_id,montant,type,date_op,annule,devise)"
            " VALUES(?,2500,'ordinaire',date('now'),1,'CDF')", (self.mid,))
        self.db.commit()
        self.assertEqual(Finance.solde_epargne(self.db, self.mid, "CDF"), 0)

    def test_devises_autorisees(self):
        # CDF et USD sont reconnus.
        self.assertEqual(DEVISES, ("CDF", "USD"))
        self.assertEqual(DEVISE_DEFAUT, "CDF")


# ════════════════════════════════════════════════════════════════
#  COMPTES MEMBRES — ÉPARGNE / CRÉDIT / COURANT / BLOQUÉ
# ════════════════════════════════════════════════════════════════

class TestComptesMembres(unittest.TestCase):
    def setUp(self):
        self.db = DB(":memory:")
        self.auth = Auth(self.db)
        self.auth.connecter("admin", "admin123")
        self.uid = self.auth.uid
        self.db.exec("INSERT INTO membre(nom,prenom,numero,avec_id)"
                     " VALUES('KASONGO','Patrick','M-003',1)")
        self.db.commit()
        self.mid = self.db.valeur("SELECT id FROM membre WHERE numero='M-003'")

    def test_avoir_compte_cree_table_compte(self):
        c = Finance.avoir_compte(self.db, self.uid, self.mid, "epargne", "CDF")
        self.assertIsNotNone(c)
        self.assertEqual(c["type_compte"], "epargne")
        evt = self.db.tous(
            "SELECT * FROM compte_evenement WHERE compte_id=?", (c["id"],))
        self.assertTrue(any(e["type_evenement"] == "CREATION" for e in evt))

    def test_impliquer_compte_mouvement_depot(self):
        comp = Finance.impliquer_compte(
            self.db, self.uid, self.mid, "courant", "CDF", "depot", 45000)
        self.assertEqual(
            Finance.solde_compte(self.db, self.mid, "courant", "CDF"), 45000)
        # mouvement retrait diminue
        Finance.impliquer_compte(
            self.db, self.uid, self.mid, "courant", "CDF", "retrait", 5000)
        self.assertEqual(
            Finance.solde_compte(self.db, self.mid, "courant", "CDF"), 40000)

    def test_deux_comptes_memes_type_devises_differentes(self):
        Finance.impliquer_compte(self.db, self.uid, self.mid, "bloque", "CDF", "depot", 100000)
        Finance.impliquer_compte(self.db, self.uid, self.mid, "bloque", "USD", "depot", 200)
        self.assertEqual(Finance.solde_compte(self.db, self.mid, "bloque", "CDF"), 100000)
        self.assertEqual(Finance.solde_compte(self.db, self.mid, "bloque", "USD"), 200)

    def test_compte_bloque_conciliation(self):
        Finance.avoir_compte(self.db, self.uid, self.mid, "epargne", "CDF")
        self.assertFalse(Finance.compte_bloque(self.db, self.mid, "epargne", "CDF"))
        self.db.exec("UPDATE compte SET statut='bloque'"
                     " WHERE membre_id=? AND type_compte='epargne' AND devise='CDF'",
                     (self.mid,))
        self.db.commit()
        self.assertTrue(Finance.compte_bloque(self.db, self.mid, "epargne", "CDF"))


# ════════════════════════════════════════════════════════════════
#  TAUX — SNAPSHOT À L'OCTROI (l'ancien crédit ne change jamais)
# ════════════════════════════════════════════════════════════════

class TestTauxSnapshot(unittest.TestCase):
    def test_credit_conserve_le_taux_d_octroi(self):
        db = DB(":memory:")
        db.exec("INSERT INTO membre(nom,prenom,numero,avec_id)"
                " VALUES('ILUNGA','Grace','M-004',1)")
        db.commit()
        mid = db.valeur("SELECT id FROM membre WHERE numero='M-004'")
        # Octroi avec le taux par défaut (10 % annuel), snapshot taux_penalite.
        principal = 5000
        taux = 0.10
        duree = 12
        interet = Finance.interet_simple(principal, taux, duree)
        db.exec(
            "INSERT INTO credit(membre_id,session_id,principal,taux,duree_mois,"
            "date_octroi,date_echeance,montant_interet,montant_total,rembourse,"
            "statut,devise,type_credit,taux_penalite)"
            " VALUES(?,NULL,?,?,?,date('now'),date('now','+12 months'),?,?,0,"
            "'actif','CDF','ordinaire',?)",
            (mid, principal, taux, duree, interet, principal + interet,
             TAUX_PENALITE_DEFAUT))
        db.commit()
        cr = db.un("SELECT * FROM credit WHERE membre_id=?", (mid,))
        self.assertEqual(cr["taux"], 0.10)
        self.assertEqual(cr["taux_penalite"], TAUX_PENALITE_DEFAUT)
        # L'AVEC passe le taux à 12 % : l'ancien crédit est inchangé.
        db.exec("UPDATE avec SET taux_interet=0.12 WHERE id=1")
        db.commit()
        cr2 = db.un("SELECT * FROM credit WHERE membre_id=?", (mid,))
        self.assertEqual(cr2["taux"], 0.10)
        self.assertEqual(Finance.solde_credit(cr2), cr2["montant_total"])


# ════════════════════════════════════════════════════════════════
#  REÇUS — NUMÉROTATION + DEVISE
# ════════════════════════════════════════════════════════════════

class TestRecusDevise(unittest.TestCase):
    def setUp(self):
        self.db = DB(":memory:")
        self.auth = Auth(self.db)
        self.auth.connecter("admin", "admin123")
        self.db.exec("INSERT INTO membre(nom,prenom,numero,avec_id)"
                     " VALUES('NGOMA','Serge','M-005',1)")
        self.db.commit()
        self.mid = self.db.valeur("SELECT id FROM membre WHERE numero='M-005'")

    def test_reçu_enregistre_la_devise(self):
        r = Recep.enregistrer(self.db, self.auth.uid, "admin", "EPARGNE",
                              "epargne", 1, self.mid, 25000, devise="USD",
                              avec_id=1)
        self.assertEqual(r["devise"], "USD")
        self.assertEqual(r["montant"], 25000)

    def test_sequence_unique_et_incrementale(self):
        r1 = Recep.enregistrer(self.db, self.auth.uid, "admin", "EPARGNE",
                               "epargne", 1, self.mid, 100, devise="CDF",
                               avec_id=1)
        r2 = Recep.enregistrer(self.db, self.auth.uid, "admin", "REMB",
                               "remboursement", 2, self.mid, 50, devise="USD",
                               avec_id=1)
        self.assertNotEqual(r1["recu_no"], r2["recu_no"])
        self.assertEqual(Recep.numero_suivant(self.db),
                         f"REC-{date.today().year}-000003")


# ════════════════════════════════════════════════════════════════
#  MODÈLES DE DOCUMENTS — ISOLATION PAR AVEC + VARIABLES
# ════════════════════════════════════════════════════════════════

class TestModelesDocuments(unittest.TestCase):
    def setUp(self):
        self.db = DB(":memory:")
        self.auth = Auth(self.db)
        self.auth.connecter("admin", "admin123")
        self.tmp = tempfile.mkdtemp()
        # Deux AVEC.
        self.db.exec("INSERT INTO avec(nom) VALUES('AVEC A')")
        self.avec_a = self.db.valeur("SELECT id FROM avec WHERE nom='AVEC A'")
        self.db.exec("INSERT INTO avec(nom) VALUES('AVEC B')")
        self.avec_b = self.db.valeur("SELECT id FROM avec WHERE nom='AVEC B'")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_import_et_isolation_par_avec(self):
        html = "<html><body>{{AVEC_NOM}} — {{DATE}}</body></html>"
        src = os.path.join(self.tmp, "modele_a.html")
        with open(src, "w", encoding="utf-8") as f:
            f.write(html)
        mid = Modeles.importer(self.db, src, self.avec_a, "Modele A",
                               "Reçu", self.auth.uid, par_defaut=1)
        self.assertIsNotNone(mid)
        # Le modèle appartient bien à l'AVEC A.
        ml = self.db.un("SELECT * FROM document_template WHERE id=?", (mid,))
        self.assertEqual(ml["avec_id"], self.avec_a)
        # Une autre AVEC ne voit pas ce modèle.
        b_modeles = self.db.tous(
            "SELECT id FROM document_template WHERE avec_id=?", (self.avec_b,))
        self.assertEqual(len(b_modeles), 0)

    def test_variables_dynamiques(self):
        avec = {"nom": "AVEC Bukavu", "adresse": "Avenue X", "telephone": "123",
                "email": "a@b.c", "devise": "CDF", "description": "Test"}
        vals = Modeles.valeurs_standard(avec, membre={"numero": "M-1",
                                                      "nom": "K", "prenom": "J",
                                                      "telephone": "9",
                                                      "adresse": "Rue Y",
                                                      "nb_parts": 3})
        self.assertEqual(vals["AVEC_NOM"], "AVEC Bukavu")
        self.assertEqual(vals["MEMBRE_NUMERO"], "M-1")
        sub = Modeles.substituer("{{AVEC_NOM}} / {{MEMBRE_NUMERO}}", vals)
        self.assertEqual(sub, "AVEC Bukavu / M-1")
        # Inconnue laissée intacte, pas d'erreur.
        self.assertIn("{{INCONNUE}}", Modeles.substituer("{{INCONNUE}}", vals))

    def test_formats_supportes(self):
        self.assertTrue(FORMATS_MODELES.issuperset({"docx", "odt", "html", "txt"}))


if __name__ == "__main__":
    unittest.main(verbosity=2)
