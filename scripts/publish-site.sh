#!/bin/zsh
# Publish SITE_DIR to the gh-pages branch as a single orphan commit.
# Env overrides: PUBLISH_REMOTE (default: origin URL of the repo at $PWD), HASH_FILE,
# FORCE=1 (push even if the stored hash matches).
set -eu

site="${1:?usage: publish-site.sh SITE_DIR}"
hash_file="${HASH_FILE:-$HOME/Library/Application Support/retro-pixoo/site-hash}"

if [[ ! -d "$site" ]] || [[ -z "$(find "$site" -type f -print -quit)" ]]; then
  echo "publish-site: no site at $site, nothing to publish"
  exit 0
fi

# manifest.json holds a timestamp, so leave it out: only changed images/pages count.
new_hash="$(cd "$site" && find . -type f ! -name manifest.json -print0 | sort -z | xargs -0 shasum | shasum | cut -d' ' -f1)"
if [[ -z "${FORCE:-}" && -f "$hash_file" && "$(<"$hash_file")" == "$new_hash" ]]; then
  echo "publish-site: unchanged, skipping push"
  exit 0
fi

remote="${PUBLISH_REMOTE:-$(git remote get-url origin)}"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

cp -R "$site/." "$tmp/"
git -C "$tmp" init -q
git -C "$tmp" add -A
git -C "$tmp" -c commit.gpgsign=false -c user.name=retro-pixoo -c user.email=retro-pixoo@localhost commit -q -m "site: update gallery"
git -C "$tmp" push -q --force "$remote" HEAD:gh-pages

mkdir -p "$(dirname "$hash_file")"
print -r -- "$new_hash" > "$hash_file"
echo "publish-site: pushed gh-pages"
