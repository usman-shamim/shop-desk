# Shop Desk

A customer-service desk for a small shop. A customer asks a question in plain language;
the Desk answers price and stock questions from the shop's own catalogue, holds a basket
across the conversation, produces a **typed order** when the customer confirms, and hands
a conversation it cannot finish to a colleague with a **typed reason**.

Built with the [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/), with a
Chainlit browser front end and a command-line Desk for demos.

The distinguishing rule: **a price, stock figure or SKU that is not in the catalogue cannot
reach the customer.** A finished answer is scanned and every price-shaped and SKU-shaped
token in it is looked up in the catalogue loaded for that run. This is a set comparison
against the file, not a judgement by a model, so editing a catalogue price makes a
previously passing answer trip.

The worked example is a small electronics shop in Pakistan (`catalogue.json`, PKR), but the
catalogue is a single file. Point `CATALOGUE_PATH` at another one and the Desk sells that.

## Quickstart

Requires Python 3.10+ (`openai-agents` needs it; this repo is developed on 3.11+).

```bash
git clone https://github.com/usman-shamim/shop-desk.git
cd shop-desk
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Paste your OpenAI key into OPENAI_API_KEY. .env is gitignored.
```

Run the command-line Desk:

```bash
python main.py                          # interactive
python main.py --message "how much is the kettle?"   # one turn, then the cost line
python main.py --print-prompt           # the resolved instructions, before any model call
python main.py --tier regular --hour 21 # tier and a simulated clock
```

Run the browser session:

```bash
chainlit run chainlit_app.py
```

Inside the chat, `/cost` reports what the conversation has spent and `/history` reports what
is being carried and what has been trimmed.

## Tests run with no API key

```bash
pytest -q     # 38 passed
```

The suite is offline by design. Tool implementations are plain Python functions, so they are
callable without the SDK runtime, and nothing in the guardrails or catalogue modules loads
configuration at import time.

There are also scripted evidence checks:

```bash
python scripts/demo_checks.py price-call-count
python scripts/demo_checks.py catalogue-edit
python scripts/demo_checks.py total-mismatch
python scripts/demo_checks.py tools-by-tier
python scripts/demo_checks.py escalation
```

## What is actually interesting here

**Prices cannot be invented.** The output guardrail (`shopdesk/guardrails.py`) extracts every
price-shaped and SKU-shaped token from a finished answer and checks each against the run's
catalogue. It is deliberately not a model. Two refinements keep it from trapping honest
answers: a figure below the cheapest catalogue price is read as a quantity or a stock count,
and figures the run computed from the catalogue itself (a basket total, a recomputed order
total) are passed in as legitimately allowed.

**One model configuration, at three levels, each named once.** The process default is
`OPENAI_DEFAULT_MODEL` in `.env`. One agent, the order assembler, overrides it at agent level.
One run overrides it through `RunConfig`. No model is named anywhere else in the codebase, so
changing the cost of the system is a one-line change in one of three known places.

**Two specialists are clones of one agent.** The pricing and escalation specialists are
`.clone()`s of a single base agent, differing only in instructions and model settings. The demo
asserts this by object identity: which fields the clones *share* with the base, and which they
*own*. A clone that failed to override a field it was meant to own is reported as a defect.

**Tools return sentences, never exceptions.** Every tool implementation catches its own
failures and returns a sentence in the Desk's voice, so a bad SKU or a broken catalogue
degrades the conversation instead of crashing the runner. The SDK's failure function routes
unexpected errors through the same door.

**The clock changes the promise.** Instructions are built per turn from the shop's hours. The
same price question at 11:00 says same-day collection is possible; at 21:00 it says when the
shop opens. Because the prompt is a pure function of context and clock, it can be printed
before any model call, which is what `--print-prompt` does.

**Tool visibility is a decision, not a list.** The seasonal-offer tool is constructed disabled,
so it appears in no tool interface at all. The loyalty tool is enabled by a callable that admits
the regular tier only. A walk-in customer and a regular customer are offered different toolsets,
and the difference is verifiable from a script.

**Identity is never written into the prompt.** The customer and session identifiers live in the
run context, which is also kept out of every generated tool schema. The Desk is not told who is
asking and cannot leak it.

## House rules

These are the project's non-functional requirements, enforced rather than aspirational.

- Configuration failures exit with one readable sentence on stderr, never a traceback.
- No price, stock figure or SKU reaches a customer unless it came from the catalogue in that run.
- No tool raises into the runner.
- Secrets live only in `.env`, and `.env.example` is the only committed copy.

## Layout

```
main.py                 CLI Desk: tier, simulated clock, prompt preview, one-shot turn
chainlit_app.py         browser session, per-window context, /cost and /history
shopdesk/
  agents.py             the Desk, the order assembler, the base specialist and its clones
  guardrails.py         catalogue truth guardrail: prices and SKUs checked against the file
  tools.py              function tools, tier-gated visibility, sentence-shaped failures
  instructions.py       dynamic instructions resolved from context and the clock
  runner.py             one runner per session, cost accounting, history trimming
  fastpath.py           tool-output handling so a lookup does not cost a reasoning call
  escalation.py         typed handover reasons
  catalogue.py          the catalogue file, and its errors
  config.py             dotenv, validation, shop hours
scripts/demo_checks.py  scripted evidence for the claims above
specs/001-shop-desk/    specification, plan, tasks, data model, contracts, quickstart
history/adr/            architecture decision records
history/prompts/        prompt history records
.specify/               spec-kit plus templates, scripts and the project constitution
```

## Built spec-first

The repository carries its own working record. `.specify/memory/constitution.md` holds the
governing principles, `specs/001-shop-desk/` holds the numbered requirements, plan and task
breakdown, `history/adr/` holds the two architectural decisions (three-level model
configuration; the tool-output fast path), and `history/prompts/` holds the prompt history for
every working session. The specification was committed before the code.

## License

No license is set. The code is public for reading; ask before reusing it.
