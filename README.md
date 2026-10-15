# subagent-extract

Portable Agent Skill for extracting traceable photovoltaic collection-form, module, inverter, and roof-layout parameters.

## Compatibility

The package follows the open Agent Skills directory convention: `SKILL.md` plus relative `scripts/`, `references/`, and `schemas/`. It contains no Codex-only API calls. Any agent that can discover an Agent Skill directory can load its instructions. To run the bundled workflow end to end, the agent also needs local file access, Python 3.10+, PDF reading/rendering capability, and permission to run the bundled scripts.

## Install

Copy the complete `subagent-extract` directory into the target agent's skill directory. Common locations are:

- Claude Code project: `.claude/skills/subagent-extract/`; personal: `~/.claude/skills/subagent-extract/`.
- Cursor project: `.cursor/skills/subagent-extract/`; shared Agent Skills root: `.agents/skills/subagent-extract/`.
- Codex: `$CODEX_HOME/skills/subagent-extract/` (or `~/.codex/skills/subagent-extract/`).
- Other agents: use the skill directory configured by that product and confirm it discovers `SKILL.md` folders.

For upload-based skill interfaces, upload the packaged folder as a ZIP if the product supports it. Follow that product's own import UI and execution requirements.

## Runtime setup

Use Python 3.10 or newer. Install runtime dependencies in the agent's Python environment or a project virtual environment:

```sh
python -m pip install -r requirements.txt
```

`pdfplumber` is required for PDF text diagnostics. `pdftoppm` (Poppler) or an equivalent PDF rendering/viewing tool is required for visual verification of tables. Optional development/test dependencies are listed in `requirements-dev.txt`.

## Run

Read `SKILL.md` first. The full orchestrator accepts a collection form plus any supplied specs/drawing and a native-reviewed JSON file:

```sh
python scripts/run_extract.py \
  --collection-form form.json \
  --module-spec-pdf module.pdf \
  --inverter-spec-pdf inverter.pdf \
  --layout-drawing roof.pdf \
  --out-dir output \
  --native-reviews native_reviews.json
```

The native review file contains visually confirmed `module`, `inverter`, and/or `layout` evidence as described in `references/native_protocol.md`. Do not invent review values or skip the visual checks. The output is validated JSON under the selected output directory.

Run the included regression suite with:

```sh
python -m unittest discover -s tests -v
```
