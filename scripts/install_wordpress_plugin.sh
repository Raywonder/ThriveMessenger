#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLUGIN_SRC="${ROOT_DIR}/wordpress/thrive-server-sync"
PLUGIN_SLUG="thrive-server-sync"

if [[ ! -f "${PLUGIN_SRC}/${PLUGIN_SLUG}.php" ]]; then
  echo "Plugin source was not found: ${PLUGIN_SRC}" >&2
  exit 1
fi

if [[ -n "${WP_ROOTS:-}" ]]; then
  IFS=':' read -r -a roots <<< "${WP_ROOTS}"
else
  mapfile -t roots < <(
    find /home -maxdepth 3 -type f -path "*/wp-config.php" -printf '%h\n' 2>/dev/null | sort -u
  )
fi

if [[ "${#roots[@]}" -eq 0 ]]; then
  echo "No WordPress roots detected. Set WP_ROOTS=/path/to/site:/path/to/other-site to install explicitly." >&2
  exit 2
fi

for root in "${roots[@]}"; do
  [[ -f "${root}/wp-config.php" ]] || {
    echo "Skipping ${root}: wp-config.php not found" >&2
    continue
  }
  plugins_dir="${root}/wp-content/plugins"
  [[ -d "${plugins_dir}" ]] || {
    echo "Skipping ${root}: wp-content/plugins not found" >&2
    continue
  }

  target="${plugins_dir}/${PLUGIN_SLUG}"
  mkdir -p "${target}"
  rsync -a --delete "${PLUGIN_SRC}/" "${target}/"
  echo "Installed ${PLUGIN_SLUG} into ${target}"

  if command -v wp >/dev/null 2>&1; then
    wp --path="${root}" plugin activate "${PLUGIN_SLUG}" --quiet || {
      echo "Installed ${PLUGIN_SLUG} for ${root}, but WP-CLI activation failed" >&2
      continue
    }
    echo "Activated ${PLUGIN_SLUG} for ${root}"
  else
    echo "WP-CLI not found; plugin copied for ${root} but not activated" >&2
  fi
done
