# Discovery Signal Scout Monorepo

This repository houses the production-ready Signal Scout agent, the Mission-Radar widget and
supporting automation for publishing daily signals. The layout mirrors the recommended
mono-repo structure:

```
.
├─ agent/                 # Python Signal Scout package, CLI, tests and CI config
├─ widget/                # React/Vite widget that consumes the latest JSON
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
