automarimo
=========================================

With `automarimo`, you can double-click a `.py` file and have it automatically opened as a marimo notebook when appropriate.

It is also capable of automatically converting `.ipynb` Jupyter nobteooks to marimo notebooks.

Finally, you can double click an empty `.py` to get a default marimo notebook.

# Installation (Windows)

1. Move this folder somewhere stable. Do NOT leave it in Downloads.
   Good example:
     `C:\Users\<yourname>\Tools\automarimo\`

2. Right-click any `.py` file. (There are some in this directory!)

3. Choose:
     Open with -> Choose another app

4. Click:
     More apps -> Look for another app on this PC

5. Browse to:
     `...\automarimo\automarimo.cmd`

6. Check:
     Always use this app to open `.py` files

7. Do not move or rename this directory.

# First-run editor picker

The first time you open a normal Python file, automarimo will try to detect common
editor installs such as VS Code, Cursor, and VSCodium. It will then allow you to select between:

- Any of the automatically detected editors.
- Browse to an editor executable manually.
- Use the current Windows default app for ordinary `.py` files.

Your choice is saved into config.json in this same folder.

<!-- How it decides whether a file is a marimo notebook
--------------------------------------------------
The detector is conservative. It requires all of these:
- a real import of `marimo`
- an assignment from `*.App(...)`
- at least one `@app.cell` decorator

That avoids misclassifying ordinary Python files that merely mention marimo. -->

## Configuration

Edit config.json in this same folder if you want to change the editor later.

Typical Windows VS Code configuration:

```
{
  "editor_command": [
    "C:\\Users\\YOURNAME\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe",
    "--reuse-window"
  ],
  "marimo_args": [
    "run",
    "--with",
    "marimo",
    "marimo",
    "edit",
    "--sandbox",
    "--watch"
  ],
  "auto_install_uv": true,
  "uv_install_dir": ".\\vendor\\uv",
  "debug": false
}
```

## Automatic `uv` Installation

If uv is not found, automarimo will try to install it into:
    `.\vendor\uv`
inside this folder.

It uses the official Windows PowerShell installer for `uv` and sets the install target explicitly.
No PATH changes are required.

## Behavior Notes

- For marimo notebooks, automarimo keeps a console window open on purpose.
  That window is the marimo backend. Do not close it while using the notebook.

- For ordinary Python files, automarimo launches the editor and exits.

Troubleshooting
---------------
1. Ordinary .py files do not open in the expected editor
   - Open a normal, non-marimo `.py` file once through automarimo and complete the picker.
   - Or edit `config.json` directly.
   - To access the picker again, simply set `"editor_command": null,` inside `config.json`, then open another non-marimo `.py` file.

2. marimo notebooks fail to open
   - Check `automarimo.log`
   - Run:
       `py -3 .\automarimo.py --debug .\your_notebook.py`

3. uv installation fails
   - Your machine may block PowerShell downloads or script execution.
   - In that case, install uv manually and then update `config.json` if needed.

4. You moved the folder after associating .py files with automarimo.cmd
   - Ideally, move it back. Otherwise, rename `automarimo.cmd` to, say, `automarimo2.cmd`
   - Re-do the one-time Open with / Always use this app step, but select `automarimo2.cmd`.
