# Signal Scout
Archetype-aware horizon scanning for Nesta missions. Outputs daily Markdown+CSV+JSON+HTML with symbols for mission links (ASF/AHL/AFS), social/tech focus, media/PH brand.

## Quick start
```bash
pip install -r requirements.txt
pip install -e .
signal-scout run --config config.yaml

# Excel-enhanced shortlist (includes mission/category tags + Mission-Radar summaries)
python signal_scout_excel_enhanced.py \
  --config config.yaml \
  --excel_keywords "Auto horizon scanning_ keywords.xlsx" \
  --out_dir signals
```

The workbook is committed as a base64 text asset at `data/auto_keywords.xlsx.b64`.
The runner will materialise `Auto horizon scanning_ keywords.xlsx` on demand, so
if you remove or overwrite the file you can regenerate the default version by
rerunning the command above.

```

### Working behind a proxy / offline installs

If your environment blocks outbound traffic to PyPI, make sure the bundled
`setuptools` wheel that ships with Python is activated before installing the
package dependencies:

```bash
python -m ensurepip --upgrade
```

This uses the standard-library wheel instead of attempting to fetch a newer
release through the proxy. After running the command once per virtualenv you
can proceed with `pip install -e .[dev]` without extra network hops.

Deploy

Docker: docker build -t signal-scout . && docker run -v $PWD/signals:/app/signals signal-scout

Cron: 0 9 * * 1-7 /usr/local/bin/signal-scout run --config /opt/signal-scout/config.yaml >> /var/log/signal-scout.log 2>&1

GitHub Actions: the `deploy` job in `.github/workflows/ci.yml` is gated behind the
`prod` environment. Configure that environment with secrets named
`OPENAI_API_KEY` (and optionally `OPENAI_MODEL`) so that the LLM fallback can run
without storing credentials in the repository.

The scheduled `daily-agent.yml` workflow uses the Excel-enhanced runner to publish
`signals/latest.json` and date-stamped snapshots to the `gh-pages` branch. Update the
workbook (`Auto horizon scanning_ keywords.xlsx`) to tweak mission/category matches.

Discovery Utils: the default requirements install `discovery_utils` (from the Nesta
GitHub repository) so the agent can enrich the shortlist with GtR, Hansard and
Crunchbase queries. If you run Crunchbase searches you must provide
`CRUNCHBASE_API_KEY` (export locally or add it as an Actions secret/environment
variable) so the helper library can authenticate.
Optional: install discovery_utils for GtR/Hansard enrichment.
Environment for LLM archetype (optional): LLM_PROVIDER=openai and OPENAI_API_KEY=...
