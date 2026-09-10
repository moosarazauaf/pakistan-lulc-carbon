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

## Cost and quota

The free tier is enough; the app does no heavy computation at request time.
Earth Engine tile requests count against the service account's quota, so real
traffic generates real tile load. If that becomes a problem the map can move to
precomputed static tiles; the numbers are unaffected either way.
