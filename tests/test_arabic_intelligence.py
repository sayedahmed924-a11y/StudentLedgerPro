import unittest

from arabic_intelligence import (
    find_possible_duplicate_names,
    normalize_arabic_text,
    similarity_score,
)


class ArabicIntelligenceTests(unittest.TestCase):
    def test_normalizes_tashkeel_tatweel_and_alef(self):
        self.assertEqual(normalize_arabic_text("أَحْمَـد"), "احمد")

    def test_normalizes_spacing_and_separators(self):
        self.assertEqual(normalize_arabic_text("  رقم-القومي  "), "رقم القومي")

    def test_keeps_digits(self):
        self.assertEqual(normalize_arabic_text("رقم 12345"), "رقم 12345")

    def test_similarity_is_high_for_typographic_variants(self):
        self.assertGreaterEqual(similarity_score("أحمد محمد", "احمد محمد"), 99)

    def test_duplicate_detection_is_suggestion_only(self):
        result = find_possible_duplicate_names(["محمد أحمد", "محمـد احمد", "سارة علي"])
        self.assertEqual(len(result), 1)
        self.assertGreaterEqual(result[0]["score"], 90)
        self.assertIn("left_index", result[0])


if __name__ == "__main__":
    unittest.main()
