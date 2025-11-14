# Discovery Signal Scout Monorepo

This repository houses the production-ready Signal Scout agent, the Mission-Radar widget and
supporting automation for publishing daily signals. The layout mirrors the recommended
mono-repo structure:
This repository houses the production-ready Signal Scout agent and (future) widget surfaces.
The layout mirrors the recommended mono-repo structure:

```
.
├─ agent/                 # Python Signal Scout package, CLI, tests and CI config
├─ widget/                # React/Vite widget that consumes the latest JSON
├─ widget/                # Placeholder for the web widget (to be added later)
├─ signals/               # Output artefacts written by the agent (ignored from Git)
└─ README.md
```

## Automation

- `.github/workflows/ci.yml` lint/tests the Python package, runs a smoke job against the
  config and verifies the generated shortlist using the Excel keyword workbook.
- `.github/workflows/daily-agent.yml` runs on a schedule (or manual dispatch), executes the
  Excel-enhanced agent and publishes `signals/latest.json` alongside date-stamped snapshots to
  the `gh-pages` branch.
- `.github/workflows/deploy-widget.yml` builds `widget/` with Vite and deploys the static
  bundle to GitHub Pages without removing the published signals.

The Pages site serves the widget at the repository root and the JSON under `/signals/latest.json`.

See `agent/README.md` for detailed agent usage and `widget/README.md` for embed guidance.

## Run everything on GitHub (zero local install)

You can operate the full stack straight from the GitHub UI:

1. **Add secrets once.**
   - Open **Settings → Secrets and variables → Actions**.
   - For the optional LLM fallback used by the gated `deploy` job in `ci.yml`, add
     `OPENAI_API_KEY` (and `OPENAI_MODEL` if you want to override the default model)
     under the `prod` environment.
   - If your widget build needs a custom npm registry or proxy, add `NPM_REGISTRY_URL`,
     `NPM_HTTP_PROXY`, and `NPM_HTTPS_PROXY` repository secrets (the deploy workflow
     reads them automatically).
2. **Trigger the daily agent run.** Go to **Actions → daily-agent → Run workflow** and
   target the `main` branch. The workflow installs the agent, materialises the Excel
   keywords, writes `agent/signals/YYYY-MM-DD.json` plus `agent/signals/latest.json`,
   and publishes them to the `gh-pages` branch under `/signals/`.
3. **Serve via GitHub Pages.** In **Settings → Pages**, choose Branch `gh-pages`,
   folder `/`. Once the first workflow completes, GitHub Pages serves the widget bundle
   (from `deploy-widget.yml`) at `https://<user>.github.io/<repo>/` and the JSON feed at
   `https://<user>.github.io/<repo>/signals/latest.json`.
4. **Verify.** Visit the Pages URL above. The bundled widget automatically loads the
   published JSON, so you should see a populated table without installing anything
   locally.

Repeat step 2 whenever you need a fresh run; everything else is automated.
The `agent/` directory contains the installable Python package along with configuration,
Dockerfile and GitHub Actions workflow. See `agent/README.md` for full usage instructions.
