# Publish the gallery to pixoo.kelsin.net

The hourly job writes the gallery to `~/Library/Application Support/retro-pixoo/site` and `scripts/publish-site.sh` force-pushes it to the `gh-pages` branch of `kelsin/pixoo` (one orphan commit, only when an image changed). GitHub Pages serves that branch.

## 1. Run the job once

```bash
make reload PIXOO_IP=<your ip>
make run
make logs        # wait for "publish-site: pushed gh-pages", then Ctrl-C
git ls-remote origin gh-pages    # prints a commit SHA when the branch exists
```

`reload` rewrites the plist, so pass your usual `RA_USER`, `LB_USER`, `BGG_USER` too if they differ from the Makefile defaults. `SITE_CNAME` defaults to `pixoo.kelsin.net` in the Makefile, so the job writes a `CNAME` file into every push; override it with `SITE_CNAME=other.host`, or `SITE_CNAME=` to disable.

## 2. GitHub Pages settings

Repo `kelsin/pixoo` → Settings → Pages:

- Source: **Deploy from a branch**
- Branch: **gh-pages**, folder **/ (root)** → Save

## 3. Custom domain

On the same page, set **Custom domain** to `pixoo.kelsin.net` and Save. The job's `CNAME` file already holds this value, so each force-push keeps the setting.

## 4. DNS

At the kelsin.net DNS provider add:

| Type | Name | Value |
| --- | --- | --- |
| `CNAME` | `pixoo` | `kelsin.github.io` |

The value is your GitHub user host only: no path, no repo name, no trailing slash. Back in Settings → Pages wait for the DNS check to pass, then tick **Enforce HTTPS** once it becomes available. The certificate can take up to about an hour.

## 5. Verify

```bash
dig pixoo.kelsin.net +short     # kelsin.github.io. then GitHub IPs
curl -sI https://pixoo.kelsin.net | head -1    # HTTP/2 200
```

Open https://pixoo.kelsin.net: the slideshow should load.

## Troubleshooting

- **404**: Pages is on the wrong branch or folder (needs `gh-pages` and `/ (root)`), or the first push has not happened yet (step 1).
- **Custom domain resets after a publish**: the `CNAME` file is missing from the push. Check `SITE_CNAME` is in the plist (`grep SITE_CNAME ~/Library/LaunchAgents/com.retro-pixoo.hourly.plist`); if empty, rerun `make reload` without overriding `SITE_CNAME`.
- **Enforce HTTPS greyed out**: DNS has not propagated or the certificate is still being issued. Check `dig`, then wait and refresh.
- **Cadence and logs**: the job runs hourly, but pushes only when an image changed (the hash is in `~/Library/Application Support/retro-pixoo/site-hash`; delete it, or run `make publish FORCE=1`, to push anyway; plain `make publish` applies the same hash check). Output goes to `~/Library/Logs/retro-pixoo.log`.
- **Hourly publish fails while 1Password is locked or unanswered**: the push goes over origin's SSH URL through the 1Password SSH agent. Check `~/Library/Logs/retro-pixoo.log`, unlock 1Password, then `make run`.
