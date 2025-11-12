# Discovery Signal Scout Monorepo

This repository houses the production-ready Signal Scout agent and (future) widget surfaces.
The layout mirrors the recommended mono-repo structure:

```
.
├─ agent/                 # Python Signal Scout package, CLI, tests and CI config
├─ widget/                # Placeholder for the web widget (to be added later)
├─ signals/               # Output artefacts written by the agent (ignored from Git)
└─ README.md
```

The `agent/` directory contains the installable Python package along with configuration,
Dockerfile and GitHub Actions workflow. See `agent/README.md` for full usage instructions.
