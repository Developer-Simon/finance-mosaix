# Branding

Source for the Finance mosaix logo ("Mosaik-M": two legs of tiles with a wedge, wordmark `finance**mosaix**` in Sora).

`build_logo.py` generates every logo file in the repository, so edit the mark or the colours there and rerun it:

```bash
python branding/build_logo.py
```

It needs `fontTools` (installed with the dashboard dependencies) and ImageMagick (`magick`) with SVG support for the PNG and ICO files.

| Output | Used by |
|---|---|
| `src/finance_mosaix/dashboard/assets/logo-{light,dark,mark}.svg` | Streamlit sidebar logo and page icon |
| `electron/assets/logo.svg` | Electron title bar (wordmark in `currentColor`) |
| `electron/assets/icon.svg`, `icon.png`, `icons/*.png` | App icons for electron-builder |
| `docs/img/favicon.{svg,ico}`, `docs/img/logo.svg` | Docs favicon and sidebar avatar |

Colours: tiles `#4F46E5`, `#6366F1`, `#818CF8`; wedge `#EC4899`.

`fonts/` holds Sora under the SIL Open Font License (`fonts/OFL.txt`).
