import unittest

from http_content_negotiation import (
    match_accept,
    match_accept_encoding,
    match_accept_language,
)


class TestAccept(unittest.TestCase):
    def test_picks_first_when_equal(self):
        self.assertEqual(match_accept("text/html, application/json", ["application/json", "text/html"]), "text/html")

    def test_specific_beats_wildcard(self):
        self.assertEqual(match_accept("text/*, text/html", ["text/html"]), "text/html")

    def test_wildcard_fallback(self):
        self.assertEqual(match_accept("text/*", ["text/html"]), "text/html")

    def test_global_wildcard(self):
        self.assertEqual(match_accept("*/*", ["application/json"]), "application/json")

    def test_quality_prefers_higher(self):
        self.assertEqual(match_accept("application/json;q=0.5, text/html;q=0.9", ["application/json", "text/html"]), "text/html")

    def test_quality_zero_drops(self):
        self.assertEqual(match_accept("text/html;q=0, application/json;q=1", ["text/html", "application/json"]), "application/json")

    def test_no_match_returns_none(self):
        self.assertIsNone(match_accept("text/html", ["application/json"]))

    def test_empty_header_no_match(self):
        self.assertIsNone(match_accept("", ["application/json"]))

    def test_malformed_q_drops_item(self):
        self.assertEqual(match_accept("application/json;q=abc, text/html", ["application/json", "text/html"]), "text/html")

    def test_quality_tie_break_specificity(self):
        self.assertEqual(match_accept("text/*;q=0.5, text/html;q=0.5", ["text/html"]), "text/html")

    def test_trailing_params_ok(self):
        self.assertEqual(match_accept("text/html;level=1", ["text/html"]), "text/html")

    def test_case_insensitive_media(self):
        self.assertEqual(match_accept("TEXT/HTML", ["text/html"]), "text/html")

    def test_server_wildcard_offered_ignored(self):
        self.assertIsNone(match_accept("text/html", ["*/*", "text/*"]))


class TestEncoding(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(match_accept_encoding("gzip, br", ["br", "gzip"]), "gzip")

    def test_quality_prefers_higher(self):
        self.assertEqual(match_accept_encoding("gzip;q=0.5, br;q=0.9", ["gzip", "br"]), "br")

    def test_wildcard_matches_any(self):
        self.assertEqual(match_accept_encoding("*", ["br"]), "br")

    def test_wildcard_lower_than_specific_with_same_q(self):
        self.assertEqual(match_accept_encoding("*, br", ["br"]), "br")

    def test_quality_zero_drops(self):
        self.assertEqual(match_accept_encoding("gzip;q=0, br", ["gzip", "br"]), "br")

    def test_no_match_returns_none(self):
        self.assertIsNone(match_accept_encoding("gzip", ["br"]))

    def test_empty_header_no_match(self):
        self.assertIsNone(match_accept_encoding("", ["br"]))

    def test_identity_keyword(self):
        self.assertEqual(match_accept_encoding("identity;q=0.5, br;q=0.9", ["identity", "br"]), "br")

    def test_server_wildcard_offered_ignored(self):
        self.assertIsNone(match_accept_encoding("br", ["*"]))

    def test_case_insensitive_encoding(self):
        self.assertEqual(match_accept_encoding("GZIP", ["gzip"]), "gzip")

    def test_malformed_q_drops_item(self):
        self.assertEqual(match_accept_encoding("gzip;q=foo, br", ["gzip", "br"]), "br")

    def test_quality_tie_break_specificity(self):
        self.assertEqual(match_accept_encoding("*;q=0.5, br;q=0.5", ["br"]), "br")


class TestLanguage(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(match_accept_language("en-US, fr-FR", ["fr-FR", "en-US"]), "en-US")

    def test_quality_prefers_higher(self):
        self.assertEqual(match_accept_language("en-US;q=0.5, fr-FR;q=0.9", ["en-US", "fr-FR"]), "fr-FR")

    def test_wildcard_matches_any(self):
        self.assertEqual(match_accept_language("*", ["fr-FR"]), "fr-FR")

    def test_wildcard_lower_than_specific_with_same_q(self):
        self.assertEqual(match_accept_language("*, fr-FR", ["fr-FR"]), "fr-FR")

    def test_quality_zero_drops(self):
        self.assertEqual(match_accept_language("en-US;q=0, fr-FR", ["en-US", "fr-FR"]), "fr-FR")

    def test_no_match_returns_none(self):
        self.assertIsNone(match_accept_language("en-US", ["fr-FR"]))

    def test_empty_header_no_match(self):
        self.assertIsNone(match_accept_language("", ["fr-FR"]))

    def test_no_prefix_matching(self):
        self.assertIsNone(match_accept_language("en", ["en-US"]))

    def test_server_wildcard_offered_ignored(self):
        self.assertIsNone(match_accept_language("en-US", ["*"]))

    def test_case_insensitive_language(self):
        self.assertEqual(match_accept_language("en-us", ["en-US"]), "en-US")

    def test_malformed_q_drops_item(self):
        self.assertEqual(match_accept_language("en-US;q=xyz, fr-FR", ["en-US", "fr-FR"]), "fr-FR")

    def test_quality_tie_break_specificity(self):
        self.assertEqual(match_accept_language("*;q=0.5, fr-FR;q=0.5", ["fr-FR"]), "fr-FR")


if __name__ == "__main__":
    unittest.main()
