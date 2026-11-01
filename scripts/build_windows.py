"""Run on Windows. Produces a portable ZIP and, with --installer, a per-user setup EXE."""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(command):
    import urllib.parse
    print("+", subprocess.list2cmdline([str(part) for part in command]), flush=True)
    try:
        result = subprocess.run([str(part) for part in command], cwd=ROOT, text=True,
                                encoding="utf-8", errors="replace",
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output = result.stdout
        print(output, flush=True)
    except Exception as exc:
        output = f"{type(exc).__name__}: {exc}"
        print(output, flush=True)
        if os.environ.get("GITHUB_ACTIONS"):
            print("::error title=Windows build::" + urllib.parse.quote(output, safe=""), flush=True)
        raise SystemExit(1) from exc
    if result.returncode:
        if os.environ.get("GITHUB_ACTIONS"):
            tail = output[-5500:]
            print("::error title=Windows build::" + urllib.parse.quote(tail, safe=""), flush=True)
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--installer", action="store_true")
    parser.add_argument("--skip-tests", action="store_true")
    args = parser.parse_args()
    if os.name != "nt" or sys.version_info < (3, 12):
        raise SystemExit("Windows ve Python 3.12+ gerekir. Linux'ta Windows EXE üretilmez.")
    os.chdir(ROOT)
    if not args.skip_tests:
        run([sys.executable, "-m", "pytest", "-q"])
    run([sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm", "MinecraftAutoAdvertiser.spec"])
    exe = ROOT / "dist" / "MinecraftAutoAdvertiser.exe"
    if not exe.is_file():
        raise SystemExit("PyInstaller EXE üretmedi.")
    portable = ROOT / "dist" / "portable"
    portable.mkdir(parents=True, exist_ok=True)
    shutil.copy2(exe, portable / exe.name)
    (portable / "portable.txt").write_text("Bu dosya verileri EXE yanındaki data klasöründe tutar.\n", encoding="utf-8")
    shutil.copy2(ROOT / "README.md", portable / "README.md")
    archive = ROOT / "dist" / "MinecraftAutoAdvertiser-Portable-1.0.0.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        for path in portable.iterdir():
            bundle.write(path, path.name)
    print(f"Portable: {archive}")
    if args.installer:
        iscc = shutil.which("iscc") or r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
        if not Path(iscc).is_file():
            raise SystemExit("Inno Setup 6 bulunamadı: https://jrsoftware.org/isinfo.php")
        run([iscc, ROOT / "installer" / "setup.iss"])
    artifacts = [archive]
    if args.installer:
        artifacts.append(ROOT / "dist" / "MinecraftAutoAdvertiser-Setup-1.0.0.exe")
    checksums = []
    for artifact in artifacts:
        digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
        checksums.append(f"{digest}  {artifact.name}")
        print(f"SHA256 {artifact.name}: {digest}")
    (ROOT / "dist" / "SHA256SUMS.txt").write_text("\n".join(checksums) + "\n", encoding="utf-8")
    print("Build tamamlandı. Gerçek Minecraft/sunucu kabul testi ayrıca yapılmalıdır.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        import urllib.parse
        detail = traceback.format_exc()
        print(detail, flush=True)
        if os.environ.get("GITHUB_ACTIONS"):
            print("::error title=Windows build exception::" + urllib.parse.quote(detail[-5500:], safe=""), flush=True)
        raise SystemExit(1)
