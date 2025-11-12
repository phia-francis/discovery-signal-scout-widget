# Signal Scout
Archetype-aware horizon scanning for Nesta missions. Outputs daily Markdown+CSV+JSON+HTML with symbols for mission links (ASF/AHL/AFS), social/tech focus, media/PH brand.

## Quick start
```bash
pip install -r requirements.txt
pip install -e .
signal-scout run --config config.yaml
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

Optional: install discovery_utils for GtR/Hansard enrichment.
Environment for LLM archetype (optional): LLM_PROVIDER=openai and OPENAI_API_KEY=...
