# -*- coding: utf-8 -*-
"""배포판 만들기 (PyInstaller). **크로스 빌드는 안 된다** - 윈도우 exe 는 윈도우에서,
맥 .app 은 맥에서 돌린다. 릴리스는 GitHub Actions(.github/workflows/release.yml)가 한다.

    pip install -r client/requirements.txt pyinstaller
    python tools/build.py --server https://myuni.example.com

결과: dist/MyUNi-<버전>-windows.zip  또는  dist/MyUNi-<버전>-mac.zip
"""
import argparse
import os
import plistlib
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "client"))

from common.version import VERSION  # noqa: E402
from myuni import sprites           # noqa: E402

NAME = "MyUNi"


def make_icon(work):
    """캐릭터 얼굴로 앱 아이콘을 만든다 (.ico / .icns)."""
    big = sprites.icon(512)
    if sys.platform == "win32":
        path = os.path.join(work, "icon.ico")
        big.save(path, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    elif sys.platform == "darwin":
        path = os.path.join(work, "icon.icns")
        big.save(path)
    else:
        path = None
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", default=os.environ.get("MYUNI_SERVER_URL", ""),
                    help="배포판이 붙을 서버 주소 (https://...)")
    args = ap.parse_args()
    if not args.server:
        print("!! --server 가 없어서 개발용 주소(127.0.0.1:8787)로 붙는 판이 만들어집니다.")

    work = tempfile.mkdtemp(prefix="myuni-build-")
    with open(os.path.join(work, "server_url.txt"), "w", encoding="utf-8") as f:
        f.write(args.server.strip())
    sep = ";" if sys.platform == "win32" else ":"

    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed",
           "--name", NAME,
           "--paths", ROOT, "--paths", os.path.join(ROOT, "client"),
           "--add-data", os.path.join(work, "server_url.txt") + sep + ".",
           "--distpath", os.path.join(ROOT, "dist"), "--workpath", os.path.join(work, "build"),
           "--specpath", work]
    icon = make_icon(work)
    if icon:
        cmd += ["--icon", icon]
    if sys.platform == "win32":
        cmd += ["--hidden-import", "pystray._win32"]
    if sys.platform == "darwin":
        cmd += ["--osx-bundle-identifier", "com.myuni.desktop"]
    cmd.append(os.path.join(ROOT, "client", "run.pyw"))
    print(" ".join(cmd))
    subprocess.check_call(cmd)

    dist = os.path.join(ROOT, "dist")
    if sys.platform == "darwin":
        app = os.path.join(dist, NAME + ".app")
        plist_path = os.path.join(app, "Contents", "Info.plist")
        with open(plist_path, "rb") as f:
            plist = plistlib.load(f)
        # 독에 안 뜨는 앱 (메뉴 막대 아이콘만). 코드에서도 숨기지만, 켜지는 순간 한 번 튀는 것까지 막는다.
        plist["LSUIElement"] = True
        plist["CFBundleShortVersionString"] = VERSION
        plist["CFBundleVersion"] = VERSION
        with open(plist_path, "wb") as f:
            plistlib.dump(plist, f)
        target, label = app, "mac"
    else:
        target, label = os.path.join(dist, NAME), "windows" if sys.platform == "win32" else "linux"

    archive = os.path.join(dist, "%s-%s-%s" % (NAME, VERSION, label))
    shutil.make_archive(archive, "zip", os.path.dirname(target), os.path.basename(target))
    print("만듦:", archive + ".zip")


if __name__ == "__main__":
    main()
