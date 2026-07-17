"""
Alro Bin Finder — data refresh
Usage:  python update_bins.py BINS.xlsx alro-bin-finder.html
Reads the latest bin spreadsheet and swaps the data inside the app file in place.
Expects columns (in order): PART NUMBER, LESSO, PRODUCT LINE, DESCRIPTION, Whse 2 Primary Bin
Requires: pip install pandas openpyxl
"""
import sys, json, re, datetime
import pandas as pd

def clean(v):
    if pd.isna(v):
        return ''
    return re.sub(r'\s+', ' ', str(v).strip())

def main():
    if len(sys.argv) != 3:
        print(__doc__); sys.exit(1)
    xlsx, html_path = sys.argv[1], sys.argv[2]

    df = pd.read_excel(xlsx)
    if df.shape[1] < 5:
        sys.exit(f"ERROR: expected 5 columns, found {df.shape[1]}. Wrong file?")
    df = df.iloc[:, :5]
    df.columns = ['part', 'lesso', 'line', 'desc', 'bin']

    rows = []
    for _, r in df.iterrows():
        part = clean(r['part'])
        if not part:
            continue
        rows.append([part, clean(r['lesso']), clean(r['line']),
                     clean(r['desc']), clean(r['bin']).upper()])
    if len(rows) < 100:
        sys.exit(f"ERROR: only {len(rows)} parts found — refusing to overwrite. Check the spreadsheet.")

    data = json.dumps(rows, separators=(',', ':'), ensure_ascii=True)
    built = datetime.date.today().strftime('%b %d, %Y')

    html = open(html_path, encoding='utf-8').read()
    # lambda replacement: backslashes in the JSON must be inserted literally, not parsed as regex templates
    new_html, n1 = re.subn(r'const DATA = \[\[.*?\]\];', lambda _: 'const DATA = ' + data + ';', html, count=1, flags=re.S)
    new_html, n2 = re.subn(r'const BUILT = ".*?";', lambda _: f'const BUILT = "{built}";', new_html, count=1)
    if n1 != 1:
        sys.exit("ERROR: could not find DATA block in HTML — file may be corrupted.")

    open(html_path, 'w', encoding='utf-8').write(new_html)
    unbinned = sum(1 for r in rows if not r[4])
    print(f"OK: {len(rows):,} parts written ({unbinned:,} with no bin). Data date set to {built}.")
    print("Re-deploy the HTML file and you're done.")

if __name__ == '__main__':
    main()
