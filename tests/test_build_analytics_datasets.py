import unittest

import pandas as pd

from src.build_analytics_datasets import assign_price_levels, count_options


class AnalyticsDatasetTests(unittest.TestCase):
    def test_count_options(self):
        values = pd.Series(["Oat; Almond; Soy", "Whole", None, ""])
        self.assertEqual(count_options(values).tolist(), [3, 1, 0, 0])

    def test_price_levels_preserve_missing(self):
        prices = pd.Series([5.0, 7.0, 9.0, None])
        levels, lower, upper = assign_price_levels(prices)
        self.assertEqual(levels.iloc[:3].tolist(), ["Low", "Medium", "High"])
        self.assertTrue(pd.isna(levels.iloc[3]))
        self.assertLess(lower, upper)


if __name__ == "__main__":
    unittest.main()
