# Deploying

Target: **Streamlit Community Cloud**, which deploys straight from this GitHub
repository.

## Why this host

| Target | Can it run this app? |
|---|---|
| **Streamlit Community Cloud** | Yes. Deploys from the GitHub repo, real Python, free, secrets UI. Sleeps after inactivity and cold-starts slowly. |
| Hugging Face Spaces | Yes, equivalent capability, but needs a second git remote to keep in sync. |
| Google Earth Engine Apps | No. GEE Apps run JavaScript in the Code Editor only. No Python, no pandas, no per-class carbon accounting, no CSV export. Maps only. |
| GitHub Pages | No. Static hosting. Every number would have to be precomputed to JSON, and "calculations running in the background" would be a fiction. |
| Voila | Technically yes, but its cold start shows a blank "Executing N of N" spinner for tens of seconds. |

## Steps

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with
   GitHub.
2. **New app** → **Deploy a public app from a repo**:
   - Repository: `moosarazauaf/pakistan-lulc-carbon`
   - Branch: `main`
   - Main file path: `app.py`
3. Click **Deploy**. It installs `requirements.txt` and starts the app.

The app will come up working immediately, because every number is served from
the committed `cache/*.json`. The Map tab will show a notice that Earth Engine
is unavailable until you complete step 4.

## 4. Add the Earth Engine key (you have to do this yourself)

The service-account key is a private credential, so it is gitignored and never
committed. Add it through Streamlit's own secrets interface:

**App menu → Settings → Secrets**. Either form works.

**Single-line base64 (recommended).** No quoting or newline hazards, so it
cannot be mangled by the secrets editor. Generate it and copy it to the
clipboard without it ever appearing on screen:

```bash
.venv/Scripts/python.exe -c "import base64,pathlib;print(base64.b64encode(pathlib.Path('service_account.json').read_bytes()).decode())" | clip
```

Then paste as the value:

```toml
GEE_SERVICE_ACCOUNT = "eyJ0eXBlIjogInNlcnZpY2VfYWNjb3VudCIsIC4uLg=="
```

**Multi-line JSON.** The triple quotes preserve the JSON's own quotes and the
newlines inside `private_key`:

```toml
GEE_SERVICE_ACCOUNT = '''
{ ...entire contents of service_account.json... }
'''
```

The value between the triple quotes must start with `{` and end with `}`. The
common failures are saving the block with nothing between the quotes, and
pasting the key name a second time inside the value.

Save, and the app restarts with the Map tab live. If it does not, open the
**"Why is Earth Engine unavailable?"** expander on the app: it names which of
those shapes the secret matched, without printing any of it.

`src/gee.py` reads this from `st.secrets` first and falls back to the
`GEE_SERVICE_ACCOUNT` environment variable, so the same repo also runs on
Hugging Face Spaces or any container host without modification.

Confirm the service account is registered for Earth Engine and its Cloud project
has the Earth Engine API enabled, otherwise the Map tab stays in numbers-only
mode.

## What must never be committed

`service_account.json`. It is in `.gitignore`. Before any push:

```bash
git status --porcelain | grep service_account && echo "STOP" || echo "clean"
```

## The cache is committed on purpose

`cache/areas.json`, `cache/transitions.json` and `cache/meta.json` are about
5.6 MB and **should** be in the repo. They are the result set: they make the app
start instantly, make every number reproducible without an Earth Engine account,
and let the app degrade gracefully to numbers-only mode. Only `cache/*.tmp` and
`cache/*.log` are ignored.

Rebuilding them takes roughly an hour of Earth Engine time
(`python scripts/build_cache.py`, resumable).

## After deploying, check these

- No "Cache is still building" warning. If it appears, the cache did not commit.
- National area reconciles to roughly 865,000 km², which confirms Azad Kashmir
  and Gilgit-Baltistan are included.
- The default comparison reads **2000 to 2023 (maps 2000-2022), seam-free**.
- The Method and limits tab renders. That is where the caveats live, and a
  deployment that drops it is misleading.
- Map tab renders tiles once the secret is set.

## Keeping it awake

Streamlit Community Cloud hibernates any app with **no traffic for 12 hours**,
and the free tier has no setting to turn that off. A visitor arriving at a
sleeping app waits 30 to 60 seconds on a "this app has gone to sleep" page. The
window used to be 7 days, then 72 hours; it is now 12.

Two scheduled workflows handle this.

`.github/workflows/keep-awake.yml` visits the app every 4 hours. That is six
visits a day against a 12-hour budget, so it survives GitHub delaying or
dropping two consecutive runs, which scheduled workflows do under load.

It drives a headless browser rather than curling the URL, for two reasons. What
resets the timer is the websocket session the front end opens, not the initial
HTTP GET. And against an already-sleeping app a GET just fetches the hibernation
page without waking anything — the browser clicks the wake button.

Every check walks `page.frames`, because on `*.streamlit.app` the app is served
inside a cross-origin iframe and the top-level `document.body.innerText` is
empty whether the app is healthy, asleep or broken. The first version of this
script checked the top frame and failed for exactly that reason.

The script exits non-zero if the app never renders, so it doubles as an uptime
check: a failed scheduled run is a real alert, not a silent no-op.

`.github/workflows/keep-schedule-alive.yml` pushes one empty commit a month.
GitHub disables scheduled workflows in a public repository after 60 days with no
repository activity, a disabled workflow cannot re-enable itself, and the
auto-disable hits every scheduled workflow at once — so without this the
keep-awake schedule would quietly die during any quiet stretch.

To check on them:

```bash
gh run list --workflow=keep-awake.yml --limit 5
gh workflow run keep-awake.yml          # force a visit now
```

If the app ever needs to be truly always-on with no cold start at all, the
options are a paid host with one instance kept warm (Fly.io, Cloud Run), or
rebuilding as a static site — every number already comes from the committed
cache, so only the live Earth Engine map depends on a running server.

## Cost and quota

The free tier is enough; the app does no heavy computation at request time.
Earth Engine tile requests count against the service account's quota, so real
traffic generates real tile load. If that becomes a problem the map can move to
precomputed static tiles; the numbers are unaffected either way.
