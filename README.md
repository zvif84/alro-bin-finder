# Alro Bin Finder — Warehouse 2

Live site: see the About section of this repo (or Settings → Pages).

## How to update the bin data (for Zvi)

1. Export the latest bin spreadsheet from your system. It must have these 5 columns in this order:
   **PART NUMBER, LESSO, PRODUCT LINE, DESCRIPTION, Whse 2 Primary Bin**
2. Name the file exactly `BINS.xlsx`
3. On this GitHub page, click **Add file → Upload files**
4. Drag `BINS.xlsx` in (it replaces the old one), then click **Commit changes**
5. Wait about 1 minute. The site rebuilds itself automatically. Done.

You can watch the rebuild under the **Actions** tab. Green check = live.

If the upload has the wrong columns or looks broken, the rebuild will fail safely
and the old data stays live. Nothing to break.

## What's in this repo

- `index.html` — the app itself (data is baked in at deploy time)
- `BINS.xlsx` — the current bin data (this is the only file Zvi ever touches)
- `update_bins.py` — script the robot runs to inject the spreadsheet into the app
- `.github/workflows/deploy.yml` — the robot
