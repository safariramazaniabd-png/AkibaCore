#!/usr/bin/env python3
"""Tests des modèles de documents personnalisables AkibaCore v2.1.
Couvre : import DOCX/ODT/TXT, prévisualisation, substitution des {{VAR}},
échappement XML/HTML, génération de fichiers réels, valeurs standard,
dossier des modèles. Aucune dépendance externe (unittest uniquement).
"""
import unittest
import sys
import os
import io
import zipfile
import shutil
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
import main
from main import (
    DB, Auth, Modeles, FORMATS_MODELES, Finance,
)
from datetime import date


def _docx(modele_dir, xml_document="<w:document>{{AVEC_NOM}}</w:document>"):
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w") as z:
        z.writestr("word/document.xml", xml_document)
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("_rels/.rels", "<Relationships/>")
    chemin = Path(modele_dir) / "modele.docx"
    chemin.write_bytes(bio.getvalue())
    return str(chemin)


def _odt(modele_dir, xml_content="<office:document><text:p>{{AVEC_NOM}}</text:p></office:document>"):
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w") as z:
        z.writestr("content.xml", xml_content)
        z.writestr("mimetype", "application/vnd.oasis.opendocument.text")
    chemin = Path(modele_dir) / "modele.odt"
    chemin.write_bytes(bio.getvalue())
    return str(chemin)


class TestModeles(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.avant = (main.DOC_IN, main.DOC_REC, main.DOC_RAP,
                      main.DOC_ARC, main.DOC_GEN)
        main.DOC_IN  = Path(self.tmp) / "modeles"
        main.DOC_REC = Path(self.tmp) / "recus"
        main.DOC_RAP = Path(self.tmp) / "rapports"
        main.DOC_ARC = Path(self.tmp) / "archives"
        main.DOC_GEN = Path(self.tmp) / "generes"
        for d in (main.DOC_IN, main.DOC_REC, main.DOC_RAP,
                  main.DOC_ARC, main.DOC_GEN):
            d.mkdir(parents=True, exist_ok=True)
        self.db = DB(":memory:")
        self.auth = Auth(self.db)
        self.assertTrue(self.auth.connecter("admin", "admin123"))

    def tearDown(self):
        (main.DOC_IN, main.DOC_REC, main.DOC_RAP,
         main.DOC_ARC, main.DOC_GEN) = self.avant
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_formats_supportes(self):
        self.assertEqual(FORMATS_MODELES,
                         {"docx", "odt", "html", "htm", "txt"})

    def test_import_format_non_supporte(self):
        p = os.path.join(self.tmp, "m.pdf")
        Path(p).write_text("x")
        with self.assertRaises(ValueError):
            Modeles.importer(self.db, p, 1, "M", "Reçu", self.auth.uid)

    def test_import_fichier_inexistant(self):
        with self.assertRaises(ValueError):
            Modeles.importer(self.db, os.path.join(self.tmp, "absent.docx"),
                             1, "M", "Reçu", self.auth.uid)

    def test_import_txt(self):
        src = os.path.join(self.tmp, "attestation.txt")
        Path(src).write_text("Attestation pour {{MEMBRE_NOM}}", encoding="utf-8")
        mid = Modeles.importer(self.db, src, 1, "Attestation", "Attestation",
                               self.auth.uid, par_defaut=1)
        ml = self.db.un("SELECT * FROM document_template WHERE id=?", (mid,))
        self.assertEqual(ml["format"], "txt")
        self.assertEqual(ml["par_defaut"], 1)
        self.assertTrue(os.path.isfile(ml["fichier"]))
        self.assertIn("{{MEMBRE_NOM}}", ml["contenu"])
        audit = self.db.tous("SELECT action FROM audit_log WHERE action='AJOUTER_MODELE'")
        self.assertEqual(len(audit), 1)

    def test_import_docx_et_par_defaut_unique(self):
        d1 = _docx(self.tmp)
        m1 = Modeles.importer(self.db, d1, 1, "Recu A", "Reçu",
                              self.auth.uid, par_defaut=1)
        d2 = _docx(self.tmp, "<w:document>B</w:document>")
        m2 = Modeles.importer(self.db, d2, 1, "Recu B", "Reçu",
                              self.auth.uid, par_defaut=1)
        # Seul le dernier importé reste « par défaut » pour le type Reçu.
        self.assertEqual(self.db.valeur(
            "SELECT COUNT(*) FROM document_template WHERE type='Reçu' AND par_defaut=1"), 1)
        self.assertEqual(self.db.valeur(
            "SELECT par_defaut FROM document_template WHERE id=?", (m2,)), 1)
        self.assertEqual(self.db.valeur(
            "SELECT par_defaut FROM document_template WHERE id=?", (m1,)), 0)

    def test_lire_contenu_docx(self):
        d = _docx(self.tmp, "<w:document>CONTENU DOCX</w:document>")
        self.assertIn("CONTENU DOCX", Modeles.lire_contenu(d))

    def test_lire_contenu_odt(self):
        d = _odt(self.tmp, "<office:document>CONTENU ODT</office:document>")
        self.assertIn("CONTENU ODT", Modeles.lire_contenu(d))

    def test_substitution_et_echappement_html(self):
        val = {"AVEC_NOM": "AVEC Bukavu & Fils <Bridge>"}
        contenu = "<doc>{{AVEC_NOM}} et {{INCONNUE}}</doc>"
        out = Modeles.substituer(contenu, val)
        self.assertIn("AVEC Bukavu &amp; Fils &lt;Bridge&gt;", out)
        # variable inconnue conservée telle quelle
        self.assertIn("{{INCONNUE}}", out)

    def test_generer_txt(self):
        src = os.path.join(self.tmp, "m.txt")
        Path(src).write_text("Reçu {{RECU_NUMERO}} pour {{MEMBRE_NOM}}", encoding="utf-8")
        mid = Modeles.importer(self.db, src, 1, "Reçu txt", "Reçu",
                               self.auth.uid)
        ml = self.db.un("SELECT * FROM document_template WHERE id=?", (mid,))
        sortie = os.path.join(self.tmp, "genere.txt")
        vals = {"RECU_NUMERO": "REC-2026-000001", "MEMBRE_NOM": "KABILA"}
        Modeles.generer(ml, vals, sortie)
        contenu = Path(sortie).read_text(encoding="utf-8")
        self.assertIn("REC-2026-000001", contenu)
        self.assertIn("KABILA", contenu)
        self.assertNotIn("{{", contenu)

    def test_generer_docx_modifie_xml_en_place(self):
        xml = "<w:document><w:p>{{AVEC_NOM}}</w:p></w:document>"
        d = _docx(self.tmp, xml)
        mid = Modeles.importer(self.db, d, 1, "Reçu docx", "Reçu",
                               self.auth.uid, par_defaut=1)
        ml = self.db.un("SELECT * FROM document_template WHERE id=?", (mid,))
        sortie = os.path.join(self.tmp, "genere.docx")
        Modeles.generer(ml, {"AVEC_NOM": "AVEC Kivu"}, sortie)
        with zipfile.ZipFile(sortie) as z:
            contenu = z.read("word/document.xml").decode("utf-8")
        self.assertIn("AVEC Kivu", contenu)
        self.assertNotIn("{{AVEC_NOM}}", contenu)
        # Les autres membres de l'archive sont conservés
        with zipfile.ZipFile(sortie) as z:
            self.assertIn("[Content_Types].xml", z.namelist())

    def test_generer_odt(self):
        d = _odt(self.tmp, "<office:document><text:p>{{AVEC_NOM}}</text:p></office:document>")
        mid = Modeles.importer(self.db, d, 1, "Attestation odt", "Attestation",
                               self.auth.uid)
        ml = self.db.un("SELECT * FROM document_template WHERE id=?", (mid,))
        sortie = os.path.join(self.tmp, "att.odt")
        Modeles.generer(ml, {"AVEC_NOM": "Bukavu 2026"}, sortie)
        with zipfile.ZipFile(sortie) as z:
            contenu = z.read("content.xml").decode("utf-8")
        self.assertIn("Bukavu 2026", contenu)
        self.assertNotIn("{{AVEC_NOM}}", contenu)

    def test_valeurs_standard_completes(self):
        avec = self.db.un("SELECT * FROM avec WHERE id=1")
        db_m = self.db
        db_m.exec("INSERT INTO membre(nom,prenom,numero,nb_parts,telephone,adresse,avec_id)"
                  " VALUES('KABILA','Jean','M-001',3,'+243','Goma',1)")
        db_m.commit()
        membre = db_m.un("SELECT * FROM membre WHERE numero='M-001'")
        credit = {"id": 5, "montant_total": 150000.0, "montant_interet": 10000.0,
                  "principal": 140000.0, "rembourse": 50000.0}
        recu = {"recu_no": "REC-2026-000001", "type": "EPARGNE", "montant": 5000.0}
        v = Modeles.valeurs_standard(avec, membre=membre, recu=recu,
                                     credit=credit, auth=self.auth)
        self.assertEqual(v["AVEC_NOM"], "AVEC Bukavu")
        self.assertEqual(v["AVEC_DEVISE"], "CDF")
        self.assertEqual(v["MEMBRE_NOM"], "KABILA")
        self.assertEqual(v["MEMBRE_PARTS"], "3")
        self.assertEqual(v["RECU_NUMERO"], "REC-2026-000001")
        self.assertEqual(v["CREDIT_NUMERO"], "5")
        self.assertEqual(v["SOLDE"], "100,000")
        self.assertEqual(v["UTILISATEUR"], "admin")
        self.assertEqual(v["DATE"], date.today().strftime("%d/%m/%Y"))

    def test_valeurs_standard_minimales(self):
        avec = self.db.un("SELECT * FROM avec WHERE id=1")
        v = Modeles.valeurs_standard(avec)
        self.assertEqual(v["AVEC_NOM"], "AVEC Bukavu")
        self.assertTrue(v["DATE"])
        for cle in ("MEMBRE_NOM", "RECU_NUMERO", "CREDIT_NUMERO"):
            self.assertNotIn(cle, v)

    def test_texte_apercu_html(self):
        html = "<html><p>Hello <b>Monde</b></p><script>var x=1;</script></html>"
        txt = Modeles.texte_apercu(html, "html")
        self.assertIn("Hello Monde", txt)
        self.assertNotIn("<", txt.split("var x")[0])

    def test_texte_apercu_docx_retours_ligne(self):
        xml = "<w:p>A</w:p><w:p>B</w:p>"
        txt = Modeles.texte_apercu(xml, "docx")
        self.assertIn("\n", txt)

    def test_creer_dossiers(self):
        Modeles._creer_dossiers()
        for d in (main.DOC_IN, main.DOC_REC, main.DOC_RAP, main.DOC_ARC, main.DOC_GEN):
            self.assertTrue(d.is_dir())


if __name__ == "__main__":
    unittest.main()