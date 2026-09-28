# Quickstart: Shop Desk

## 1. Prerequisites

- Python 3.10+ (3.11+ recommended)
- An OpenAI API key with access to the configured models

## 2. Configure secrets (NFR-1)

```bash
cp .env.example .env      # then edit .env — never commit it (.env is gitignored)
```

`.env` keys:

| Key | Purpose |
|-----|---------|
| `OPENAI_API_KEY` | model calls and trace export |
| `OPENAI_DEFAULT_MODEL` | the **process default** model (level 1 of FR-1), e.g. `gpt-5-nano` |
| `SHOP_OPEN_HOUR` / `SHOP_CLOSE_HOUR` | opening hours used by the dynamic instructions (FR-4) |
| `SHOP_SIMULATED_HOUR` | optional: freeze the clock so hour-dependent behaviour can be shown (FR-4) |
| `TURN_CEILING` | optional: overrides the default 10-turn ceiling (FR-8) |
| `CATALOGUE_PATH` | optional: path to `catalogue.json` (default: repo root) |

A missing key fails at startup with one readable sentence, not a stack trace (NFR-1).

## 3. Install and run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt        # openai-agents, python-dotenv, chainlit, pytest

python main.py                          # CLI conversation
python main.py --tier regular           # same session with the regular-tier tool set (FR-7)
python main.py --hour 21                # simulated out-of-hours conversation (FR-4)
python main.py --print-prompt --hour 11 # print the resolved instructions before any model call

chainlit run chainlit_app.py            # browser interface (FR-12)
```

## 4. Check the Definition of Done

| Claim | Command / action |
|-------|------------------|
| Spec preceded code (NFR-5) | `git log --oneline` — spec artifacts first, source after |
| One model call for a price question (SC-001) | ask "what does the kettle cost?"; read the cost line and the trace — 1 turn, fast path |
| An order costs more (SC-001) | ask "can I order three kettles?"; cost line shows reasoning turns |
| Three config levels exist (FR-1) | point at `.env`, the order agent, the re-quote `RunConfig`; then delete `OPENAI_DEFAULT_MODEL` and watch only the plain-question model change |
| Prices come from the file (SC-002) | `python scripts/demo_checks.py catalogue-edit` — a previously passing answer trips the guardrail |
| Total is recomputed (SC-003) | `python scripts/demo_checks.py total-mismatch` — planted mismatch reported |
| Tools differ by tier (SC-004) | `--tier walk_in` vs `--tier regular`; seasonal tool in neither schema |
| Escalation is typed and trimmed (SC-006) | `python scripts/demo_checks.py escalation` — reason value plus before/after history |
| Ten turns and still coherent (SC-005) | eleven turns in one Chainlit window; a second window keeps a separate basket |
| Cost line and one trace (SC-007) | read the printed cost line; open the session trace |

## 5. Tests

```bash
pytest -q
```

Covers: total recomputation and planted mismatch, guardrail truth checking, tool failure
sentences (no raise into the runner), and tool visibility by tier.
