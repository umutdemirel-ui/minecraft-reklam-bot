# Build on Windows with: pyinstaller --clean --noconfirm MinecraftAutoAdvertiser.spec
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('config/settings.json', 'config'), ('assets/icon.ico', 'assets'),
           ('assets/icon.png', 'assets')] + collect_data_files('customtkinter'),
    hiddenimports=['pyautogui', 'pygetwindow', 'keyboard'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'numpy', 'pandas', 'scipy', 'PySide6', 'PyQt5', 'IPython'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
          name='MinecraftAutoAdvertiser', debug=False, bootloader_ignore_signals=False,
          strip=False, upx=False, console=False, disable_windowed_traceback=False,
          icon='assets/icon.ico', version='installer/version_info.txt')
