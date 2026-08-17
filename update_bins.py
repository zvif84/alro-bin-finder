"""
Alro Bin Finder — data refresh (v2)
Usage:
  python update_bins.py <datafile.csv|datafile.xlsx> index.html
  python update_bins.py auto index.html        (picks newest of BINS.csv / BINS.xlsx)

Reads the bin spreadsheet and swaps the data inside the app file in place.
Columns are matched by HEADER NAME, not position, so column order never matters.

Recognized headers (case-insensitive, fuzzy):
  part:  "Product (15)" or "PART NUMBER" or anything containing product/part
  line:  anything containing "line"
  desc:  anything containing "desc"
  bin:   anything containing "bin"
  min:   anything containing "min"      (optional)
  max:   anything containing "max"      (optional)
  shelf: anything containing "shelf"    (optional)

Requires: pip install pandas openpyxl
"""
import sys, os, json, re, datetime
import pandas as pd


def clean(v):
    if pd.isna(v):
        return ''
    return re.sub(r'\s+', ' ', str(v).strip())


def clean_num(v):
    """Return a clean integer string, or '' for blank/junk values."""
    if pd.isna(v):
        return ''
    s = str(v).strip().replace(',', '')
    try:
        return str(int(float(s)))
    except (ValueError, OverflowError):
        return ''


def find_col(cols, *needles, exclude=()):
    for c in cols:
        lc = c.lower()
        if any(n in lc for n in needles) and not any(x in lc for x in exclude):
            return c
    return None


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
    c_part = find_col(cols, 'product', 'part', exclude=('line',))
    c_line = find_col(cols, 'line')
    c_desc = find_col(cols, 'desc')
    c_bin = find_col(cols, 'bin')
    c_min = find_col(cols, 'min')
    c_max = find_col(cols, 'max')
    c_shelf = find_col(cols, 'shelf', 'on hand')

    missing = [name for name, c in
               [('part', c_part), ('product line', c_line), ('description', c_desc), ('bin', c_bin)]
               if c is None]
    if missing:
        sys.exit(f'ERROR: could not find required column(s): {missing}. Headers were: {cols}')
    print(f'Column map: part={c_part!r} line={c_line!r} desc={c_desc!r} bin={c_bin!r} '
          f'min={c_min!r} max={c_max!r} shelf={c_shelf!r}')

    rows = []
    for _, r in df.iterrows():
        part = clean(r[c_part])
        if not part:
            continue
        rows.append([
            part,
            clean(r[c_line]),
            clean(r[c_desc]),
            clean(r[c_bin]).upper(),
            clean_num(r[c_min]) if c_min else '',
            clean_num(r[c_max]) if c_max else '',
            clean_num(r[c_shelf]) if c_shelf else '',
        ])
    if len(rows) < 100:
        sys.exit(f'ERROR: only {len(rows)} parts found — refusing to overwrite. Check the file.')

    data = json.dumps(rows, separators=(',', ':'), ensure_ascii=True)
    built = datetime.date.today().strftime('%b %d, %Y')

    html = open(html_path, encoding='utf-8').read()
    # lambda replacement: backslashes in the JSON must be inserted literally, not parsed as regex templates
    new_html, n1 = re.subn(r'const DATA = (?:/\*__DATA__\*/|\[\[.*?\]\]);',
                           lambda _: 'const DATA = ' + data + ';', html, count=1, flags=re.S)
    new_html, n2 = re.subn(r'const BUILT = (?:/\*__BUILT__\*/|".*?");',
                           lambda _: f'const BUILT = "{built}";', new_html, count=1)
    if n1 != 1:
        sys.exit('ERROR: could not find DATA block in HTML — file may be corrupted.')

    open(html_path, 'w', encoding='utf-8').write(new_html)
    unbinned = sum(1 for r in rows if not r[3])
    no_stock = sum(1 for r in rows if r[6] == '')
    print(f'OK: {len(rows):,} parts written ({unbinned:,} with no bin, {no_stock:,} with no stock count). '
          f'Data date set to {built}.')


if __name__ == '__main__':
    main()
