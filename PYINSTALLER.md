# Creating Shithead Executables with pyinstaller

Generate an executable which can be run on a machine with the same operating system (Linux or Windows) without installing Python and any additional libraries.

## Linux

**IMPORTANT** Do not install masters-of-shithead locally (with *python -m pip install -e .*) before calling pyinstaller, it would result in extremly large executables.

If not already created (venv directory), create a virtual environment:
```
$ cd ~/my-user/my-path/masters-of-shithead
$ python3 -m venv venv --prompt="shithead"
```
Activate the virtual environment:
```
$ cd ~/my-path/masters-of-shithead
$ source venv/bin/activate
(shithead) $
```
In case of a new virtual environment, install the arcade, numpy and the pyinstaller packages first:
```
(shithead) $ pip install arcade
(shithead) $ pip install numpy
(shithead) $ pip install pyinstaller
```
**NOTE**: At the time of writing I wasn't able to install the arcade library on Python 3.11 or later. Use pyenv to install Python 3.10.1  and make it the default version with **'pyenv global 3.10.1'**.  

Create the entry-point script:
```
(shithead) $ cd src
(shithead) $ gvim shithead_start.py

from shithead.__main__ import main

if __name__ == '__main__':
    main()
```
In order to get a preliminary spec-file for a single file executable, we call *pyinstaller* with this entry-point script and the *'--onefile'* option:
```
(shithead) $ pyinstaller shithead_start.py --name shithead --onefile
```
This creates the *shithead.spec* file and the new directories *build* and *dist*. But the *shithead* executable in *dist* is not usable yet, because some additional non-code files are missing. To fix this, we have to enter these files into the *datas=[]* list in *shithead.spec*:
```
# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(
    ['shithead_start.py'],
    pathex=[],
    binaries=[],
	datas=[('./shithead/title.json','shithead'),\
	       ('./shithead/rules.py','shithead'),\
		   ('./shithead/face_up_table.json', 'shithead'),\
		   ('./shithead/rules_eng.json', 'shithead'),\
		   ('./shithead/rules_ger.json', 'shithead')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='shithead',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
```
Now we call *pyinstaller* again with the modified spec-file:
```
(shithead) $ pyinstaller shithead.spec
```
This should create a single file executable, which can be started with:
```
(shithead) $ ./dist/shithead
```

To create a desktop shortcut with the icon *'src/shithead4.ico'*, we need a desktop file:
```
(shithead) $ gvim shithead.desktop

[Desktop Entry]
Version=1.0.2
Name=Shithead
GenericName=Card Game
Comment=Play Shithead against 1-5 AI Players
Exec=/home/my-user/my-path/masters-of-shithead/src/dist/shithead
Path=
Icon=/home/my-user/my-path/masters-of-shithead/src/shithead4.ico
Type=Application
Categories=Application
```
Copy *'shithead.desktop'* to the desktop:
```
(shithead) $ cp shithead.desktop ~/Desktop/.
```
and make sure it is executable:
```
(shithead) $ chmod ugo+x ~/Desktop/shithead.desktop
```
Now you should see the 'Shithead' icon on the desktop:
```
[right mouse click] on the icon
Select 'Allow Launching'
```
Now you should be able to start the shithead game with a double click on the icon. Note, that this comes with the disadvantage, of not having a console to show errors and log messages.

## Windows

Open a windows command-line shell:
```
[Windows-Key] + X
[Run] cmd.exe [OK]
```
Get the path to the Python executable:
```
C:\Users\my-user\> where.exe python
C:\Users\my-user\AppData\Local\Programs\Python\Python310\python.exe
```
Create a virtual environment for the 'masters-of-shithead' project:
```
C:\Users\my-user\> D:
D:\> cd Projects\masters-of-shithead
D:\Projects\masters-of-shithead\> C:\Users\my-user\AppData\Local\Programs\Python\Python310\python -m venv venv --prompt="shithead"
D:\Projects\masters-of-shithead\> venv\Scripts\activate
(shithead) D:\Projects\masters-of-shithead\>
```
In case of a new virtual environment, install the arcade, numpy, and the pyinstaller packages first:
```
(shithead) D:\Projects\masters-of-shithead\> pip install arcade
(shithead) D:\Projects\masters-of-shithead\> pip install numpy
(shithead) D:\Projects\masters-of-shithead\> pip install pyinstaller
```
**NOTE**: At the time of writing I wasn't able to install the arcade library on Python 3.11 or later. Use pyenv-win to install Python 3.10.1  and make it the default version with **'pyenv global 3.10.1'**.  

Create the entry-point script *shithead_start.py* in 'D:\Projects\masters-of-shithead\src' with an editor:
```
from shithead.__main__ import main

if __name__ == '__main__':
    main()
```

In order to get a preliminary spec-file for a single file executable, we call *pyinstaller* with this entry-point script and the *'--onefile'* option:
```
(shithead) D:\Projects\masters-of-shithead\> cd src
(shithead) D:\Projects\masters-of-shithead\src\> pyinstaller shithead_start.py --name shithead --onefile
```
This creates the *shithead.spec* file and the new directories *build* and *dist*. But the *shithead* executable in *dist* is not usable yet, because some additional non-code files are missing. To fix this, we have to enter these files into the *datas=[]* list in *shithead.spec*:

```
# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(
    ['shithead_start.py'],
    pathex=[],
    binaries=[],
    datas=[('./shithead/title.json','shithead'), ('./shithead/rules.py', 'shithead'), ('./shithead/face_up_table.json', 'shithead'), ('./shithead/ms_rules_eng.json','shithead'), ('./shithead/ms_rules_ger.json', 'shithead')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='shithead',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="./shithead4.ico",
)
```
Note, that we also entered the path to the icon with *'icon='*.

Now we call *pyinstaller* again with the modified spec-file:
```
(shithead) D:\Projects\masters-of-shithead\src\> pyinstaller shithead.spec
```
This should create a single file executable, which can be started with:
```
(shithead) D:\Projects\masters-of-shithead\src\> .\dist\shithead.exe
```
To create a desktop shortcut with the icon *'shithead4.ico'*:
```
[right mouse click] on desktop
[New] -> [Shortcut]
Location of the item: D:\Projects\masters-of-shithead\src\dist\shithead.exe -> [Next]
Type a name for this shortcut: Shithead -> [Finish]
```
Now the icon should appear on the desktop (it's already included in shithead.exe) and the game can be started with a double click.
This opens a console, where errors and log messages are displayed.  
**Note**: The default font of the console cannot display all of the used unicode characters (♢, ♡ ,↻, ↺).  
=> change it to another font, e.g. 'Nsimsun'.
