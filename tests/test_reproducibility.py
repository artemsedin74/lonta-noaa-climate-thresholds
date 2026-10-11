"""Offline source-integrity and method-boundary checks; Python standard library."""
import calendar
import csv
import hashlib
import json
import shutil
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from analysis import analyze, month_days

ROOT = Path(__file__).resolve().parents[1]


class ReproducibilityTests(unittest.TestCase):
    def test_preserved_sources_and_selection(self):
        rows, report = analyze(ROOT / 'data')
        self.assertEqual(len(rows), 288)
        self.assertEqual(report['rawHashesMatched'], 24)
        self.assertEqual(report['variableValues'], 864)
        self.assertEqual(report['roundedNonzeroValues'], 13)
        self.assertEqual(report['bothPublishedDirectionsPositive'], 221)
        self.assertEqual(report['bothDirectionsAtLeast10FDays'], 109)

    def test_decimal_units_against_published_focal_examples(self):
        _, report = analyze(ROOT / 'data')
        expected = [(64.9, 104.8, 101.7, 3.1, 0),
                    (64.8, 105.3, 99.2, 6, 0),
                    (66.3, 77.2, 116.1, 0, 39),
                    (65.1, 85, 88.1, 0, 3)]
        columns = ['temperature_F', 'heating_F_days', 'cooling_F_days',
                   'proxy_heating_F_days', 'proxy_cooling_F_days']
        self.assertEqual([tuple(row[c] for c in columns)
                          for row in report['focalExamples']], expected)

    def test_february_preserves_eight_leap_days(self):
        # Decimal division by 30 repeats; compare the mean with an independent
        # calendar count, rather than requiring multiplication to be exact.
        total = sum(calendar.monthrange(year, 2)[1] for year in range(1991, 2021))
        self.assertEqual(total, 848)
        self.assertEqual(month_days(2), Decimal(total) / Decimal(30))

    def test_invented_daily_example_is_not_threshold_of_average(self):
        # Independent mathematical illustration, not reconstructed NOAA weather.
        values = [Decimal(50), Decimal(80)]
        mean = sum(values) / len(values)
        daily_heating = sum(max(65-v, Decimal(0)) for v in values)
        daily_cooling = sum(max(v-65, Decimal(0)) for v in values)
        self.assertEqual((mean, daily_heating, daily_cooling), (65, 15, 15))
        self.assertEqual(max(65-mean, 0) * len(values), 0)
        self.assertEqual(max(mean-65, 0) * len(values), 0)

    def test_modified_source_bytes_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder) / 'data'
            shutil.copytree(ROOT / 'data', data)
            raw = data / 'raw/USW00012842.csv'
            raw.write_bytes(raw.read_bytes() + b'\n')
            with self.assertRaises(AssertionError):
                analyze(data)

    def test_duplicate_month_rejected_even_with_updated_manifest_hash(self):
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder) / 'data'
            shutil.copytree(ROOT / 'data', data)
            raw = data / 'raw/USW00012842.csv'
            with raw.open(newline='') as stream:
                reader = csv.DictReader(stream)
                fields = reader.fieldnames
                rows = list(reader)
            rows[1]['DATE'] = rows[0]['DATE']
            with raw.open('w', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
            selected = json.loads((data / 'selected.json').read_text())
            target = next(c for c in selected['cities'] if c['station'] == 'USW00012842')
            target['sourceSha256'] = hashlib.sha256(raw.read_bytes()).hexdigest()
            (data / 'selected.json').write_text(json.dumps(selected))
            with self.assertRaises(AssertionError):
                analyze(data)


if __name__ == '__main__':
    unittest.main()
