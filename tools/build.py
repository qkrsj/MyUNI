# -*- coding: utf-8 -*-
"""배포판 만들기 (PyInstaller). **크로스 빌드는 안 된다** - 윈도우 exe 는 윈도우에서,
맥 .app 은 맥에서 돌린다. 릴리스는 GitHub Actions(.github/workflows/release.yml)가 한다.

    pip install -r client/requirements.txt pyinstaller
    python tools/build.py --server https://myuni.example.com

결과 (이름에 버전을 안 넣는다 - 다운로드 페이지가 releases/latest/download/<이름> 으로 바로 건다):
    윈도우  dist/MyUNi-Setup.exe   설치 파일 (Inno Setup 필요, tools/installer.iss)
    맥      dist/MyUNi.dmg         .app 을 응용 프로그램 폴더로 끌어 넣는 디스크 이미지
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
        out = package_mac(dist, work)
    elif sys.platform == "win32":
        out = package_windows(dist, icon)
    else:
        out = shutil.make_archive(os.path.join(dist, NAME + "-linux"), "zip", dist, NAME)
    print("만듦:", out)


def package_mac(dist, work):
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

    # 디스크 이미지 안에 앱과 '응용 프로그램' 바로 가기를 나란히 둔다 (끌어다 놓으면 설치)
    stage = os.path.join(work, "dmg")
    os.makedirs(stage)
    shutil.copytree(app, os.path.join(stage, NAME + ".app"), symlinks=True)
    os.symlink("/Applications", os.path.join(stage, "Applications"))
    out = os.path.join(dist, NAME + ".dmg")
    subprocess.check_call(["hdiutil", "create", "-volname", NAME, "-srcfolder", stage,
                           "-ov", "-format", "UDZO", out])
    return out


def find_iscc():
    found = shutil.which("iscc")
    if found:
        return found
    for base in (os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramFiles"),
                 os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs")):
        if base:
            p = os.path.join(base, "Inno Setup 6", "ISCC.exe")
            if os.path.exists(p):
                return p
    return None


def package_windows(dist, icon):
    iscc = find_iscc()
    if not iscc:
        raise SystemExit("Inno Setup 6 이 없습니다. https://jrsoftware.org/isdl.php 에서 깔거나 "
                         "'choco install innosetup' 을 돌리세요.")
    subprocess.check_call([iscc, "/Q",
                           "/DAppVersion=" + VERSION,
                           "/DSourceDir=" + os.path.join(dist, NAME),
                           "/DOutputDir=" + dist,
                           "/DIconFile=" + icon,
                           os.path.join(ROOT, "tools", "installer.iss")])
    return os.path.join(dist, NAME + "-Setup.exe")


if __name__ == "__main__":
    main()
