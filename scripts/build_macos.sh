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
APP_VERSION="${THRIVE_APP_VERSION:-15.17.0}"

${PYTHON_BIN} -m venv "${VENV_DIR}"
source "${VENV_DIR}/bin/activate"

python -m pip install --upgrade pip
if [[ "${TARGET_ARCH}" == "universal2" ]]; then
  WHEELS="${ROOT_DIR}/.wheels"
  rm -rf "${WHEELS}"; mkdir -p "${WHEELS}/x86_64" "${WHEELS}/arm64" "${WHEELS}/universal2"
  python -m pip install "delocate>=0.12"
  PYV="$(python -c 'import sys;print(f"{sys.version_info[0]}.{sys.version_info[1]}")')"
  python -m pip download --only-binary=:all: --no-deps --python-version "${PYV}" --platform macosx_10_13_x86_64 -d "${WHEELS}/x86_64" "wxPython==${WX_VERSION}"
  python -m pip download --only-binary=:all: --no-deps --python-version "${PYV}" --platform macosx_11_0_arm64 -d "${WHEELS}/arm64" "wxPython==${WX_VERSION}"
  delocate-merge "${WHEELS}"/x86_64/*.whl "${WHEELS}"/arm64/*.whl -w "${WHEELS}/universal2"
  python -m pip install "${WHEELS}"/universal2/*.whl
  WX_REQ="wxPython==${WX_VERSION}"
else
  WX_REQ="wxPython>=4.2.5,<4.3"
fi
python -m pip install \
  "pyinstaller>=6.18.0" \
  "keyring>=25.7.0" \
  "plyer>=2.1.0" \
  "${WX_REQ}" \
  "sounddevice>=0.5.1" \
  "pyobjc-core" \
  "pyobjc-framework-Cocoa" \
  "pyobjc-framework-ServiceManagement"

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
