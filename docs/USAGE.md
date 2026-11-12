# User guide

This app turns a public EasyEDA component link into files for Fusion 360 and KiCad.
Below is the full path: from searching the EasyEDA library to a ready component in
your Fusion library.

---

## What you need

- Windows 10/11 (64-bit).
- Internet access — the component is downloaded from EasyEDA.
- The unpacked `EasyEDA2KiCad` folder with `EasyEDA2KiCad.exe`.

No Python, no KiCad and no EasyEDA account are required.

---

## Step 1. Find the component in the EasyEDA library

1. Open EasyEDA and sign in to the editor.
2. Open the component library (the **Library** panel).
3. Search for the part by name, package or LCSC number.
4. Click the component to open its card and press the **Info** / **i** button.

The component page opens in your browser — the page with the symbol, footprint and
3D preview.

> Community components without an LCSC number work too. The only requirement is
> that the component page is public.

---

## Step 2. Copy the link

Copy the page URL from the browser address bar. It looks like this:

```
https://easyeda.com/component/0123456789abcdef0123456789abcdef
```

It must be the component page URL. LCSC or JLCPCB links (`.../C12345.html`) are not
supported — the app needs the EasyEDA UUID.

If you copy the link and then launch the app, it will pre-fill the field from the
clipboard automatically.

---

## Step 3. Convert

1. Run `EasyEDA2KiCad.exe`.
2. Paste the link into **Component link** (or press **Paste**).
3. Choose an output folder in **Save to**.
4. Check the boxes:
   - **Symbol** — `.kicad_sym`;
   - **Footprint** — `.kicad_mod`;
   - **3D model** — `.step` and `.wrl`, when the component has one.
5. Click **Convert**.

The log shows what was found, what was created and any warnings. The
**Open folder** button opens the result in Explorer.

### Output folder

```
<name>_<uuid8>/
├── <name>.kicad_sym                 ← symbol
├── <name>.pretty/
│   └── <name>.kicad_mod             ← footprint
└── <name>.3dshapes/
    ├── <model>.step                 ← 3D for Fusion
    └── <model>.wrl                  ← 3D for KiCad
```

If the component has no 3D model, no `.3dshapes` folder is created and the log
contains a warning.

---

## Step 4. Import into Fusion 360

This is the important step. The import order matters: **footprint first, symbol
second**. That way Fusion links them to each other.

1. Open Fusion 360.
2. Open **Library Manager** and create a new library or open an existing one.
3. Click **Import**.
4. Select the **`.kicad_mod`** file (footprint) from the `.pretty` folder.
5. Click **Import** again and select the **`.kicad_sym`** file (symbol).
6. Fusion matches the symbol with the footprint using the `Footprint` field — the
   library now contains a component (Device) with its footprint attached.

If the symbol and footprint are not linked:

- make sure both files were imported into the **same library**;
- delete both items and repeat the import in the right order: `.kicad_mod`, then
  `.kicad_sym`;
- as a last resort, create a Device manually: **Devices** tab → **Create New
  Device** → add the symbol, the footprint and (if available) the 3D package.

After that the component can be placed on a schematic and a board like any other.

---

## Step 5. Add the 3D model in Fusion (optional)

Fusion does not attach STEP to a footprint automatically — that is a Fusion
limitation. If the `.step` file exists, add it manually (four clicks):

1. **Data Panel** → **Upload** → upload the `.step` file to the project.
2. In the library open the **Footprints** tab.
3. Right-click the footprint → **Create New 3D Model**.
4. In the new window: **Data Panel** → right-click the STEP file →
   **Insert into current design**.
5. Align the model with the footprint, click **Finish** and save the library.

The `.wrl` file is only for the KiCad 3D viewer and is not needed in Fusion.

---

## If you use KiCad

KiCad keeps the symbol and the footprint in separate libraries; the link between
them is the `Footprint` field in the symbol. The app already fills it in.

1. `Preferences → Manage Symbol Libraries` → add the `.kicad_sym` file.
2. `Preferences → Manage Footprint Libraries` → add the `.pretty` folder.
   **Keep the library nickname equal to the folder name**, otherwise the reference
   inside the symbol will not resolve.
3. Place the symbol in the schematic.
4. `Tools → Update PCB from Schematic` (**F8**) — the footprint appears on the board.

The footprint never appears in the schematic itself — it always lives on the PCB.
If F8 says “Footprint not found”, open the symbol in Symbol Editor, check the
`Footprint` field, and either rename the library to match it or assign the
footprint again via `Tools → Assign Footprints`.

---

## Updating a component

To regenerate a part, simply convert it again into the same folder: the files are
overwritten. If the part is already in a Fusion library, import the new files over
the old ones or delete the old library items first.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| “No component UUID found in the link” | The link is not a component card | Open the component card in EasyEDA and copy the browser URL |
| “Component not found (404)” | The component is private or deleted | Make sure the page opens in a browser without signing in |
| “This component has no 3D model” | The author did not attach a model | Take a STEP from the part manufacturer or draw a placeholder body |
| “This component has no symbol — footprint only” | In EasyEDA it is a standalone footprint, not a device | Expected: no symbol is created for it |
| Fusion imports a symbol without a footprint | The symbol was imported first | Delete both items, import `.kicad_mod`, then `.kicad_sym` |
| Fusion shows an “empty” component | The files went into different libraries | Import both files into the same library |
| KiCad: “Footprint not found” | The library nickname does not match | Rename the library or assign the footprint again |
| SmartScreen: “Windows protected your PC” | The executable is not code-signed | **More info → Run anyway** |
| Antivirus complains | False positive on a packed `.exe` | Add the folder to exclusions or build from source |
| The 3D download takes a while | STEP models can be several megabytes | Wait; the log shows progress |

---

## Where settings are stored

The last link, output folder and checkboxes are saved in:

```
%LOCALAPPDATA%\EasyEDA2KiCad\config.json
```

Delete this file to reset the settings.
