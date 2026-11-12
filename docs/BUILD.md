# Building from source

## Requirements

- Windows 10/11 x64.
- Python 3.11+ (tested on 3.12). Download: https://www.python.org/downloads/
  Enable **Add Python to PATH** during installation.
- Internet access — to install dependencies.

## Run from source

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

`easyeda2kicad` is the only runtime dependency. The GUI uses Tkinter, which ships
with the official Windows Python build.

## Build the .exe

Install PyInstaller and build the portable folder:

```powershell
pip install -r requirements-dev.txt

$icon = (Resolve-Path "icon.ico").Path
python -m PyInstaller --noconfirm --clean --onedir --windowed `
  --icon $icon --add-data "$icon;." `
  --name EasyEDA2KiCad `
  --distpath dist --workpath build --specpath build app.py
```

Result: `dist\EasyEDA2KiCad\EasyEDA2KiCad.exe` together with the `_internal` folder.

### Single file instead of a folder

```powershell
python -m PyInstaller --noconfirm --clean --onefile --windowed `
  --icon $icon --add-data "$icon;." `
  --name EasyEDA2KiCad `
  --distpath dist --workpath build --specpath build app.py
```

Result: `dist\EasyEDA2KiCad.exe`. A one-file build extracts itself to a temporary
folder on every launch: it starts a few seconds slower and triggers antivirus
false positives more often. For releases, `--onedir` is recommended.

> `--add-data` must point to an **absolute** path to `icon.ico`; with
> `--specpath build` PyInstaller otherwise looks for the icon inside `build`.

## Build the release archive

Use the script:

```powershell
.\build.ps1
```

It creates `dist\EasyEDA2KiCad\` and packs it into `EasyEDA2KiCad-portable.zip`,
adding `README.md`, `LICENSE`, `THIRD_PARTY_NOTICES.md` and the `docs` folder.

Use `-OneFile` to build a single executable:

```powershell
.\build.ps1 -OneFile
```

## Verify the build

1. Unpack the archive into a clean folder (not the project folder).
2. Run `EasyEDA2KiCad.exe` — the window should open.
3. Paste a test link, for example:
   `https://easyeda.com/component/c2754a5dac404cb1b757213b56759c67` (RP2040).
4. Check that `.kicad_sym`, `.kicad_mod` and `.step` were created.

## Common build issues

| Problem | Fix |
|---|---|
| `Python was not found` | Reinstall Python with **Add Python to PATH** enabled |
| `No module named tkinter` | Use the official python.org build, not a minimal distribution |
| `Unable to find icon.ico` | Pass an absolute path to `--icon` and `--add-data` |
| Antivirus deletes the `.exe` | Build with `--onedir` or add the folder to exclusions |
| `ModuleNotFoundError: easyeda2kicad` | Activate `.venv` and run `pip install -r requirements.txt` |
