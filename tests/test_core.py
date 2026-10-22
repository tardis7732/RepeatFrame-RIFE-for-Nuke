import unittest
from repeatframe_core import find_runs, fraction


def detect(sequence, first=1):
    return find_runs(first, first + len(sequence) - 1,
                     {first+i: abs(sequence[i]-sequence[i-1]) for i in range(1, len(sequence))})


class RepeatTests(unittest.TestCase):
    def test_one_duplicate(self):
        runs, trailing = detect([1, 2, 3, 4, 4, 5, 6, 7, 8, 9])
        self.assertEqual(runs, [dict(left=4, right=6, start=5, end=5)])
        self.assertEqual(fraction(5, runs[0]), .5)
        self.assertEqual(trailing, [])

    def test_two_duplicates(self):
        runs, _ = detect([1, 2, 3, 4, 4, 4, 5, 6, 7, 8, 9])
        self.assertAlmostEqual(fraction(5, runs[0]), 1/3)
        self.assertAlmostEqual(fraction(6, runs[0]), 2/3)

    def test_missing_without_repeat_is_untouched(self):
        self.assertEqual(detect([1, 2, 3, 4, 6, 7, 8, 9]), ([], []))

    def test_edges_and_multiple_runs(self):
        self.assertEqual(detect([1]), ([], []))
        self.assertEqual(detect([1, 1, 1]), ([], [2, 3]))
        runs, trailing = detect([1, 1, 2, 2, 3, 3], first=-10)
        self.assertEqual([(r['left'], r['right']) for r in runs], [(-10, -8), (-8, -6)])
        self.assertEqual(trailing, [-5])

    def test_tolerance_and_invalid_samples(self):
        self.assertEqual(len(find_runs(1, 3, {2: .00001, 3: 1}, .001)[0]), 1)
        with self.assertRaises(ValueError):
            find_runs(1, 2, {2: float('nan')})


if __name__ == '__main__':
    unittest.main()
