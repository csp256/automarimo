automarimo
=========================================

With `automarimo`, you can double-click a `.py` file and have it automatically opened as a marimo notebook when appropriate.

It is also capable of automatically converting `.ipynb` Jupyter nobteooks to marimo notebooks.

Finally, you can double click an empty `.py` to get a default marimo notebook.

## Installation (Windows)

1. Move this folder somewhere permanent. Do NOT leave it in Downloads. 
    For example:
    * `C:\Users\<yourname>\automarimo\`
2. If you are going to rename the folder, do it now.
3. Right-click any `.py` file. (There are some in this directory!)
4. Choose:
    * Open with -> Choose another app
5. Click: 
    - More apps -> Look for another app on this PC
6. Browse to where you put automarimo: 
    - `C:\Users\<yourname>\automarimo\`
7. Select: 
    - `automarimo.cmd`
8. Check: 
    - Always use this app to open `.py` files
9. Repeat steps 3 through 8 with any `.ipynb` file. (There is one in this directory!)

## Installation (macOS)

1. Download `automarimo.app` somewhere stable, such as your `Applications` folder.
2. Double-click `automarimo.app` once to make sure macOS will launch it.
3. If macOS warns that the app was downloaded from the internet, allow it in **System Settings → Privacy & Security**.
4. In Finder, select any `.py` file. (There are some in this directory!)
5. Press **Command-I** to open **Get Info**.
6. Expand **Open with**.
7. Choose **automarimo.app** from the app list.
8. Click **Change All...**.

Repeat steps 5 through 8 with any `.ipynb` file.

- On Mac, automarimo stores its user config under `~/.config/automarimo/`.
- If `~/.config/` is owned by `root` instead of your user, Automarimo may fail to create its config directory. Fix the ownership before using it: `sudo chown -R "$USER":staff ~/.config`
- If you move `automarimo.app` after setting it as the default opener, you may need to repeat the **Open with → Change All...** step.

# First-run editor picker

The first time you open a normal Python file, automarimo will try to detect common
editor installs such as VS Code, Cursor, and VSCodium. It will then allow you to select between:

- Any of the automatically detected editors.
- Browse to an editor executable manually.
- Use the current Windows default app for ordinary `.py` files.

<!-- How it decides whether a file is a marimo notebook
--------------------------------------------------
The detector is conservative. It requires all of these:
- a real import of `marimo`
- an assignment from `*.App(...)`
- at least one `@app.cell` decorator

That avoids misclassifying ordinary Python files that merely mention marimo. -->

## Configuration

You may edit `config.json` in this same folder. This can allow you to change the editor later, or alter other behaviors.

Note, the `converted_ipynb_filename_template` field must include `{stem}`, and must produce a `.py` filename.

If you delete `config.json` then it will be recreated from defaults the next time automarimo runs.

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
