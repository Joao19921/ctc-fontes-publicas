import unittest
from unittest.mock import patch

from integracoes.fontes_publicas.client import (
    SourceError, _json, parse_pncp_control, pncp_search_publications,
)


class PublicSourcesTests(unittest.TestCase):
    def test_parse_numeric_control(self):
        self.assertEqual(parse_pncp_control("07954480000179-1-026867/2026"),
                         ("07954480000179", 2026, 26867))

    def test_parse_alphanumeric_cnpj(self):
        self.assertEqual(parse_pncp_control("12ABC4560001XY-1-000001/2026"),
                         ("12ABC4560001XY", 2026, 1))

    def test_invalid_control(self):
        with self.assertRaises(ValueError):
            parse_pncp_control("123-2026")

    def test_modality_required(self):
        with self.assertRaises(TypeError):
            pncp_search_publications("20260101", "20260131")

    def test_invalid_date_and_page_size(self):
        with self.assertRaises(ValueError):
            pncp_search_publications("2026-01-01", "20260131", modalidade=6)
        with self.assertRaises(ValueError):
            pncp_search_publications("20260101", "20260131", modalidade=6,
                                    tamanho_pagina=501)

    @patch("integracoes.fontes_publicas.client._request",
           return_value=(b'{"data": []}', "application/json"))
    def test_json_response(self, _request):
        self.assertEqual(_json("https://example.invalid"), {"data": []})

    @patch("integracoes.fontes_publicas.client._request",
           return_value=(b"not-json", "text/plain"))
    def test_invalid_json(self, _request):
        with self.assertRaises(SourceError):
            _json("https://example.invalid")


if __name__ == "__main__":
    unittest.main()
