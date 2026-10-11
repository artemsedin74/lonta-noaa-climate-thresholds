"""Audit NOAA normals and contrast them with a monthly-mean threshold proxy.

Python 3.10+; the analysis uses the standard library, plotting uses matplotlib.
python3 analysis.py [--data /path/to/noaa-monthly-1991-2020] [--no-chart]
No network requests, temperature forecasts, or contractor demand estimation.
"""
import argparse
import calendar
from collections import Counter
import csv
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
DEFAULT_DATA = (HERE / 'data' if (HERE / 'data/selected.json').exists()
                else HERE.parents[3] / 'web/data/noaa-monthly-1991-2020')
VARIABLES = {'temperature': 'MLY-TAVG-NORMAL', 'heating': 'MLY-HTDD-NORMAL',
             'cooling': 'MLY-CLDD-NORMAL'}
# Examples illustrate cool-side, warm-side and nearly neutral means. They are
# deliberately selected examples, not the top four or a random national sample.
FOCAL_KEYS = [('USW00012842', 12), ('USW00003017', 9),
              ('USW00094846', 9), ('USW00023183', 11)]


def month_days(month):
    # NOAA includes February 29. Eight leap years occur during 1991–2020.
    return Decimal(sum(calendar.monthrange(year, month)[1] for year in range(1991, 2021))) / Decimal(30)


def mean_proxy(temperature, month):
    base = Decimal(65)
    days = month_days(month)
    return max(base - temperature, Decimal(0)) * days, max(temperature - base, Decimal(0)) * days


def analyze(data=DEFAULT_DATA):
    assert sum(calendar.isleap(year) for year in range(1991, 2021)) == 8
    assert (month_days(2) * 30).quantize(Decimal('1')) == 848
    selected = json.loads((data / 'selected.json').read_text())
    assert selected['period'] == '1991–2020' or selected['period'] == '1991-2020'
    assert selected['baseF'] == 65
    cities = selected['cities']
    assert len(cities) == 24 and len({c['station'] for c in cities}) == 24
    results, hashes, flags, years = [], [], Counter(), Counter()
    for city in cities:
        raw_path = data / 'raw' / (city['station'] + '.csv')
        digest = hashlib.sha256(raw_path.read_bytes()).hexdigest()
        assert digest == city['sourceSha256'], city['station']
        hashes.append({'station': city['station'], 'sourceUrl': city['sourceUrl'], 'sha256': digest})
        with raw_path.open(newline='') as stream:
            raw = list(csv.DictReader(stream))
        assert [int(row['DATE']) for row in raw] == list(range(1, 13))
        for row, previous in zip(raw, city['months']):
            month = int(row['DATE'])
            assert row['STATION'].strip() == city['station']
            assert row['NAME'].strip() == city['stationName']
            assert previous['month'] == month
            record = {'city': city['city'], 'station': city['station'],
                      'station_name': city['stationName'], 'month': month,
                      'normal_period': '1991-2020', 'base_F': 65}
            values, year_counts = {}, []
            for label, variable in VARIABLES.items():
                value = Decimal(row[variable].strip())
                assert value.is_finite() and value != Decimal(-9999), (city['station'], month, variable)
                assert -150 <= value <= 150 if label == 'temperature' else value >= 0
                measure = row['meas_flag_' + variable].strip()
                completeness = row['comp_flag_' + variable].strip()
                n = int(row['years_' + variable])
                assert measure in {'', 'X'} and completeness in {'S', 'R'} and 10 <= n <= 30
                if measure == 'X':
                    assert value == 0  # Retain the rounded-nonzero flag, never assert a true zero.
                values[label] = value
                year_counts.append(n)
                unit = 'F' if label == 'temperature' else 'F_days'
                record[label + '_' + unit] = float(value)
                record[label + '_measurement_flag'] = measure
                record[label + '_completeness_flag'] = completeness
                record[label + '_years'] = n
                flags[(label, completeness, measure)] += 1
                years[n] += 1
                if label != 'temperature':
                    assert value == Decimal(str(previous[label]['value']))
                    assert (measure or None) == previous[label]['measurementFlag']
                    assert completeness == previous[label]['completenessFlag']
                    assert n == previous[label]['years']
            h, c = mean_proxy(values['temperature'], month)
            record.update(proxy_heating_F_days=float(h), proxy_cooling_F_days=float(c),
                          proxy_month_days=float(month_days(month)), source_url=city['sourceUrl'],
                          source_sha256=digest, year_counts_match=len(set(year_counts)) == 1)
            results.append(record)
    assert len(results) == 288 and len({(r['station'], r['month']) for r in results}) == 288
    focal = [next(r for r in results if (r['station'], r['month']) == key) for key in FOCAL_KEYS]
    # Direct transcription fixtures; protect decimal units against a /10 error.
    expected = [(64.9, 104.8, 101.7, 3.1, 0), (64.8, 105.3, 99.2, 6, 0),
                (66.3, 77.2, 116.1, 0, 39), (65.1, 85, 88.1, 0, 3)]
    fields = ['temperature_F', 'heating_F_days', 'cooling_F_days',
              'proxy_heating_F_days', 'proxy_cooling_F_days']
    assert [tuple(r[k] for k in fields) for r in focal] == expected
    both = sum(r['heating_F_days'] > 0 and r['cooling_F_days'] > 0 for r in results)
    meaningful_both = sum(r['heating_F_days'] >= 10 and r['cooling_F_days'] >= 10 for r in results)
    report = {'executedAtUtc': datetime.now(timezone.utc).isoformat(),
              'python': sys.version.split()[0], 'status': 'checks_passed',
              'rawHashesMatched': len(hashes), 'stationMonths': len(results),
              'variableValues': 864, 'duplicateStationMonths': 0, 'missingValues': 0,
              'sourceUnits': 'Decimal degrees Fahrenheit and Fahrenheit degree-days; no /10 scaling',
              'bothPublishedDirectionsPositive': both,
              'bothDirectionsAtLeast10FDays': meaningful_both,
              'roundedNonzeroValues': sum(n for (_, _, m), n in flags.items() if m == 'X'),
              'contributingYearRange': [min(years), max(years)],
              'stationMonthsWithMatchingYearCounts': sum(r['year_counts_match'] for r in results),
              'flags': [{'metric': k[0], 'completeness': k[1], 'measurement': k[2], 'count': n}
                        for k, n in sorted(flags.items())],
              'focalExamples': focal, 'rawSourceFiles': hashes,
              'scope': 'Purposive 24-airport selection, twelve repeated months each; not a national random sample.',
              'interpretation': 'Method contrast, not a percentage error estimate for HVAC jobs or a reconstruction of daily history.',
              'proxy': 'days * max(65 - monthly mean, 0) and days * max(monthly mean - 65, 0). February uses 28 + 8/30 days.',
              'limits': [
                  'NOAA normals include adjusted temperatures and missing-year estimation; matching counts do not prove identical underlying daily records.',
                  'The monthly-mean proxy is deliberately information-losing; it is not an alternative NOAA degree-day method.',
                  'Both directions in a monthly normal do not establish their simultaneous occurrence on any day, year or building.',
                  'Degree-days measure temperature exposure, not energy, leads, revenue, equipment failures or budget requirements.'
              ]}
    return results, report


def chart(focal, output=HERE / 'figure.png'):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    colors = {'heating': '#b75a22', 'cooling': '#23799b'}
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11})
    fig, axes = plt.subplots(1, 2, figsize=(13, 7.5), sharey=True)
    fig.patch.set_facecolor('#faf9f5')
    y = np.arange(len(focal))
    labels = [f"{r['city']} · {calendar.month_abbr[r['month']]}\n{r['temperature_F']:.1f}°F monthly mean" for r in focal]
    for ax, metric in zip(axes, ['heating', 'cooling']):
        published = [r[metric + '_F_days'] for r in focal]
        proxy = [r['proxy_' + metric + '_F_days'] for r in focal]
        ax.set_facecolor('#faf9f5')
        ax.barh(y - .18, published, height=.28, color=colors[metric], label='Published degree-day normal')
        ax.barh(y + .18, proxy, height=.28, color='#959b9d', label='Monthly-mean shortcut')
        for idx, (p, q) in enumerate(zip(published, proxy)):
            ax.text(p + 2, idx - .18, f'{p:.1f}', va='center', fontsize=11, fontweight='bold', color=colors[metric])
            ax.text(q + 2, idx + .18, f'{q:.1f}', va='center', fontsize=11, color='#555d61')
        ax.set_title(metric.capitalize() + ' degree-days', loc='left', pad=20, fontsize=14, fontweight='bold')
        ax.set_xlim(0, 135)
        ax.set_xticks([0, 30, 60, 90, 120])
        ax.set_xlabel('°F-days · 65°F base', labelpad=10)
        ax.set_axisbelow(True)
        ax.grid(axis='x', alpha=.15)
        ax.set_yticks(y, labels)
        ax.tick_params(axis='both', length=0)
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.legend(loc='lower left', bbox_to_anchor=(0, 1.21), frameon=False, fontsize=10)
    axes[0].invert_yaxis()
    fig.text(.04, .94, 'A month near 65°F can carry both heating and cooling exposure',
             fontsize=19, weight='bold', color='#202d33')
    fig.text(.04, .887, 'Four illustrative airport station-months · NOAA 1991–2020 climate normals', fontsize=12, color='#48545a')
    fig.subplots_adjust(left=.21, right=.965, top=.69, bottom=.21, wspace=.13)
    fig.text(.04, .115, 'Shortcut: days × positive temperature difference from 65°F, applied after averaging.', fontsize=10, color='#48545a')
    fig.text(.04, .078, 'Source: NOAA NCEI station CSVs; calculation: Lonta Research. Selected examples, not a national sample.', fontsize=10, color='#48545a')
    fig.text(.04, .042, 'Climate exposure is not a forecast of equipment use, leads or revenue.', fontsize=10, color='#48545a')
    fig.savefig(output, dpi=160, facecolor=fig.get_facecolor())
    fig.savefig(output.with_suffix('.svg'), facecolor=fig.get_facecolor())
    svg_path = output.with_suffix('.svg')
    svg_path.write_text('\n'.join(line.rstrip() for line in svg_path.read_text().splitlines()) + '\n')
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=DEFAULT_DATA)
    parser.add_argument('--no-chart', action='store_true')
    args = parser.parse_args()
    rows, report = analyze(args.data)
    with (HERE / 'station-months.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    (HERE / 'analysis.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    if not args.no_chart:
        chart(report['focalExamples'])
    print(json.dumps({k: report[k] for k in ['status', 'rawHashesMatched', 'stationMonths', 'variableValues',
                     'bothPublishedDirectionsPositive', 'bothDirectionsAtLeast10FDays', 'roundedNonzeroValues',
                     'stationMonthsWithMatchingYearCounts']}, indent=2))


if __name__ == '__main__':
    main()
