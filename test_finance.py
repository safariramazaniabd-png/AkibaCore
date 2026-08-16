#!/usr/bin/env python3
"""Tests minimaux pour la classe Finance (pas de dependances externes)."""
import unittest
from datetime import date
import sys, os

sys.path.insert(0, os.path.dirname(__file__))
from main import Finance


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


if __name__ == "__main__":
    unittest.main()
