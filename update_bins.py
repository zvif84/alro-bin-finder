"""
Alro Bin Finder — data refresh (v3, dual warehouse)
Usage:
  python update_bins.py <datafile.csv|datafile.xlsx> index.html
  python update_bins.py auto index.html        (picks newest of BINS.csv / BINS.xlsx)

Columns are matched by HEADER NAME, not position. Recognized (case-insensitive):
  part:   contains product/part (not line)          REQUIRED
  keyword: contains keyword                          optional
  line:   contains line                              REQUIRED
  desc:   contains desc                              REQUIRED
  bin WH02: contains bin, not 5                      REQUIRED
  bin WH05: contains bin and 5                       optional
  min / max: contains min / max                      optional
  shelf WH02: contains shelf (not 5)                 optional
  shelf WH05: contains 5 and (hand or shelf)         optional

Requires: pip install pandas openpyxl
"""
import sys, os, json, re, datetime
try:
    from zoneinfo import ZoneInfo
    ET = ZoneInfo('America/New_York')
except Exception:
    ET = None
import pandas as pd


def clean(v):
    if pd.isna(v):
        return ''
    return re.sub(r'\s+', ' ', str(v).strip())


def clean_num(v):
    if pd.isna(v):
        return ''
    s = str(v).strip().replace(',', '')
    try:
        return str(int(float(s)))
    except (ValueError, OverflowError):
        return ''


def pick_auto():
    candidates = [f for f in ('BINS.csv', 'BINS.CSV', 'BINS.xlsx') if os.path.exists(f)]
    if not candidates:
        sys.exit('ERROR: auto mode found no BINS.csv or BINS.xlsx in this folder.')
    return max(candidates, key=os.path.getmtime)


def main():
    if len(sys.argv) != 3:
        print(__doc__); sys.exit(1)
    datafile, html_path = sys.argv[1], sys.argv[2]
    if datafile == 'auto':
        datafile = pick_auto()
    print(f'Reading data from: {datafile}')

    if datafile.lower().endswith('.csv'):
        df = pd.read_csv(datafile, dtype=str)
    else:
        df = pd.read_excel(datafile, dtype=str)

    cols = list(df.columns)
    low = {c: c.lower() for c in cols}

    def find(pred):
        for c in cols:
            if pred(low[c]):
                return c
        return None

    c_part  = find(lambda l: ('product' in l or 'part' in l) and 'line' not in l)
    c_kw    = find(lambda l: 'keyword' in l)
    c_line  = find(lambda l: 'line' in l)
    c_desc  = find(lambda l: 'desc' in l)
    c_bin2  = find(lambda l: 'bin' in l and '5' not in l)
    c_bin5  = find(lambda l: 'bin' in l and '5' in l)
    c_min   = find(lambda l: 'min' in l)
    c_max   = find(lambda l: 'max' in l)
    c_shelf2 = find(lambda l: 'shelf' in l and '5' not in l)
    c_shelf5 = find(lambda l: '5' in l and ('hand' in l or 'shelf' in l))

    missing = [n for n, c in [('part', c_part), ('product line', c_line),
                              ('description', c_desc), ('WH02 bin', c_bin2)] if c is None]
    if missing:
        sys.exit(f'ERROR: could not find required column(s): {missing}. Headers were: {cols}')
    print(f'Column map: part={c_part!r} kw={c_kw!r} line={c_line!r} desc={c_desc!r}\n'
          f'  bin2={c_bin2!r} bin5={c_bin5!r} min={c_min!r} max={c_max!r} '
          f'shelf2={c_shelf2!r} shelf5={c_shelf5!r}')

    rows = []
    for _, r in df.iterrows():
        part = clean(r[c_part])
        if not part:
            continue
        rows.append([
            part,
            clean(r[c_kw]) if c_kw else '',
            clean(r[c_line]),
            clean(r[c_desc]),
            clean(r[c_bin2]).upper(),
            clean_num(r[c_min]) if c_min else '',
            clean_num(r[c_max]) if c_max else '',
            clean_num(r[c_shelf2]) if c_shelf2 else '',
            clean(r[c_bin5]).upper() if c_bin5 else '',
            clean_num(r[c_shelf5]) if c_shelf5 else '',
        ])
    if len(rows) < 100:
        sys.exit(f'ERROR: only {len(rows)} parts found — refusing to overwrite. Check the file.')

    data = json.dumps(rows, separators=(',', ':'), ensure_ascii=True)
    now = datetime.datetime.now(ET) if ET else datetime.datetime.now()
    built = now.strftime('%b %d, %I:%M %p') + (' ET' if ET else '')

    html = open(html_path, encoding='utf-8').read()
    new_html, n1 = re.subn(r'const DATA = (?:/\*__DATA__\*/|\[\[.*?\]\]);',
                           lambda _: 'const DATA = ' + data + ';', html, count=1, flags=re.S)
    new_html, n2 = re.subn(r'const BUILT = (?:/\*__BUILT__\*/|".*?");',
                           lambda _: f'const BUILT = "{built}";', new_html, count=1)
    if n1 != 1:
        sys.exit('ERROR: could not find DATA block in HTML — file may be corrupted.')

    open(html_path, 'w', encoding='utf-8').write(new_html)
    wh5 = sum(1 for r in rows if r[8])
    print(f'OK: {len(rows):,} parts written ({wh5:,} with a WH05 bin). Stamp: {built}.')


if __name__ == '__main__':
    main()
