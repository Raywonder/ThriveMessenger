#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

APP_NAME="Thrive Messenger"
DIST_NAME="thrive_messenger"
OUT_DIR="${ROOT_DIR}/dist-macos"
# Standing rule: every Mac app ships as universal2 (Apple silicon arm64 + Intel x86_64), signed and notarised.
# The universal2 python.org framework Python builds it; wxPython only ships single-arch Mac wheels, so the
# x86_64 and arm64 wheels are merged into one universal2 wheel with delocate-merge.
ARCH_LABEL="${1:-x86_64}"
TARGET_ARCH="${THRIVE_TARGET_ARCH:-universal2}"
VENV_DIR="${ROOT_DIR}/.venv-build"
UNIVERSAL_PY="/Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13"
if [[ "${TARGET_ARCH}" == "universal2" ]]; then
  PYTHON_BIN="${THRIVE_PYTHON_BIN:-${UNIVERSAL_PY}}"
  [[ -x "${PYTHON_BIN}" ]] || { echo "universal2 build needs the python.org universal2 Python at ${UNIVERSAL_PY}" >&2; exit 1; }
else
  PYTHON_BIN="${THRIVE_PYTHON_BIN:-python3}"
fi
WX_VERSION="${THRIVE_WX_VERSION:-4.2.4}"
APP_VERSION="${THRIVE_APP_VERSION:-15.21.0}"

${PYTHON_BIN} -m venv "${VENV_DIR}"
source "${VENV_DIR}/bin/activate"

python -m pip install --upgrade pip
REQS=("pyinstaller>=6.18.0" "keyring>=25.7.0" "plyer>=2.1.0" "sounddevice>=0.5.1" "pyobjc-core" "pyobjc-framework-Cocoa"
      "pyobjc-framework-ServiceManagement")
if [[ "${TARGET_ARCH}" == "universal2" ]]; then
  # Download every dependency for both architectures, merge each single-arch pair into a universal2 wheel
  # (wxPython, cffi and the like only publish separate x86_64 and arm64 Mac wheels), then install only those.
  WHEELS="${ROOT_DIR}/.wheels"
  rm -rf "${WHEELS}"; mkdir -p "${WHEELS}/x86_64" "${WHEELS}/arm64" "${WHEELS}/universal2"
  python -m pip install "delocate>=0.12"
  PYV="$(python -c 'import sys;print(f"{sys.version_info[0]}.{sys.version_info[1]}")')"
  for arch in x86_64 arm64; do
    python -m pip download --only-binary=:all: --python-version "${PYV}" --platform "macosx_11_0_${arch}" \
      -d "${WHEELS}/${arch}" "wxPython==${WX_VERSION}" "${REQS[@]}"
  done
  python - "${WHEELS}" <<'PY'
import os, subprocess, sys
root = sys.argv[1]
def key(name):  # distribution name and version, e.g. ("cffi", "2.0.0")
    parts = name.split("-")
    return parts[0].lower().replace("_", "-"), parts[1]
arm = {key(f): f for f in os.listdir(os.path.join(root, "arm64")) if f.endswith(".whl")}
for f in sorted(os.listdir(os.path.join(root, "x86_64"))):
    if not f.endswith(".whl"):
        continue
    src = os.path.join(root, "x86_64", f)
    if "-none-any" in f or "universal2" in f:
        subprocess.check_call(["cp", src, os.path.join(root, "universal2", f)])
        continue
    other = arm.get(key(f))
    if not other:
        sys.exit(f"no arm64 wheel matching {f}")
    subprocess.check_call(["delocate-merge", src, os.path.join(root, "arm64", other), "-w", os.path.join(root, "universal2")])
    print("merged", f, "+", other)
PY
  python -m pip install --no-index --find-links "${WHEELS}/universal2" "wxPython==${WX_VERSION}" "${REQS[@]}"
else
  python -m pip install "wxPython>=4.2.5,<4.3" "${REQS[@]}"
fi

rm -rf build dist "${OUT_DIR}"
mkdir -p "${OUT_DIR}"

pyinstaller \
  --clean \
  --noconfirm \
  --windowed \
  --name "${APP_NAME}" \
  --osx-bundle-identifier "fm.tappedin.thrivemessenger" \
  --add-data "client.conf:." \
  --add-data "assets/help:assets/help" \
  --add-data "assets/videos:assets/videos" \
  --add-data "sounds:sounds" \
  --add-data "README.md:." \
  --add-data "F1_HELP.md:." \
  --hidden-import AppKit \
  --hidden-import Foundation \
  --hidden-import ServiceManagement \
  --target-arch "${TARGET_ARCH}" \
  --osx-entitlements-file "packaging/macos-thrive.entitlements" \
  main.py

APP_PATH="dist/${APP_NAME}.app"
[[ "${TARGET_ARCH}" == "universal2" ]] && ARCH_LABEL="universal2"
ZIP_PATH="${OUT_DIR}/${DIST_NAME}-macos-${ARCH_LABEL}.zip"

if [[ ! -d "${APP_PATH}" ]]; then
  echo "Build failed: ${APP_PATH} was not created" >&2
  exit 1
fi

/usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString ${APP_VERSION}" "${APP_PATH}/Contents/Info.plist"
# Voice messages and voicemail record from the microphone; macOS requires a reason string or it refuses access.
MIC_REASON="Thrive Messenger records voice messages and voicemail from your microphone only when you press Command R."
/usr/libexec/PlistBuddy -c "Set :NSMicrophoneUsageDescription ${MIC_REASON}" "${APP_PATH}/Contents/Info.plist" 2>/dev/null \
  || /usr/libexec/PlistBuddy -c "Add :NSMicrophoneUsageDescription string ${MIC_REASON}" "${APP_PATH}/Contents/Info.plist"
if ! /usr/libexec/PlistBuddy -c "Set :CFBundleVersion ${APP_VERSION}" "${APP_PATH}/Contents/Info.plist"; then
  /usr/libexec/PlistBuddy -c "Add :CFBundleVersion string ${APP_VERSION}" "${APP_PATH}/Contents/Info.plist"
fi

if [[ "${TARGET_ARCH}" == "universal2" ]]; then
  # Every Mach-O file in the bundle must carry both architectures, or the build fails.
  bad=0; checked=0
  while IFS= read -r -d '' f; do
    if file -b "$f" | grep -q "Mach-O"; then
      checked=$((checked + 1))
      archs="$(lipo -archs "$f" 2>/dev/null || true)"
      if [[ "$archs" != *x86_64* || "$archs" != *arm64* ]]; then
        echo "NOT UNIVERSAL: ${f#${APP_PATH}/} (${archs:-unknown})" >&2; bad=$((bad + 1))
      fi
    fi
  done < <(find "${APP_PATH}" -type f -print0)
  echo "lipo check: ${checked} Mach-O files, ${bad} not universal2"
  [[ $bad -eq 0 ]] || exit 1
fi

if [[ -n "${THRIVE_CODESIGN_IDENTITY:-}" ]]; then
  codesign --force --deep --options runtime --timestamp --entitlements packaging/macos-thrive.entitlements \
    --sign "${THRIVE_CODESIGN_IDENTITY}" "${APP_PATH}"
else
  codesign --force --deep --sign - "${APP_PATH}"
fi
codesign --verify --deep --strict "${APP_PATH}"

ditto -c -k --sequesterRsrc --keepParent "${APP_PATH}" "${ZIP_PATH}"
echo "Created ${ZIP_PATH}"
