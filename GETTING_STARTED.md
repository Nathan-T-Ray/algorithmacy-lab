# Getting started

This is the contributor path from a fresh clone to a pull request, by hand. It does not depend
on any automation: the `org_frontier/protocol/question_pipeline.js` orchestration runs the same
stages but needs the Claude Code Workflow tool, which an ordinary contributor does not have. The
manual path below is the authoritative one, and the protocol calls it the fallback for exactly
that reason.

## 1. Environment

PyPhi's IIT-4.0 line requires **Python 3.10 or newer**. Check your interpreter first — a stock machine's
default `python3` is often 3.9, and the install below fails with `requires a different Python` if it is.
Build the venv with an explicit modern interpreter when the default is too old:

```bash
python3 --version                 # if < 3.10, use python3.12 (or any 3.10+) explicitly on the next line
python3.12 -m venv venv           # plain `python -m venv venv` is fine only if `python` is already 3.10+
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

`requirements.txt` pulls PyPhi's IIT-4.0 line and `phyid` from git at pinned commits, and
`constraints.txt` pins the remaining wheels. The install needs network access and takes a few
minutes. Install with both files so the environment matches CI:

```bash
pip install -r requirements.txt -c constraints.txt
```

Every command below assumes this venv is active and that you run **from the repo root**, so that
`org_frontier.*` and `foundations.*` resolve.

### Run in a container

A `Dockerfile` at the repo root builds the same pinned environment. From the repo root:

```bash
docker build -t algorithmacy-lab .
docker run --rm algorithmacy-lab
```

The default command is the instrument control and must print `Instrument validated`. To run another
check, pass it as the command:

```bash
docker run --rm algorithmacy-lab python ci/reproduce.py instrument-controls
```

## 2. Confirm the instrument before you trust anything

```bash
python -m org_frontier.classifier.validate
```

This must print `Instrument validated`. It checks two controls — a decoupled form that must read
`dyadic`, a fully coupled form that must read `triadic` — plus the built-in regression forms. If
it fails, stop: no verdict is trustworthy until it passes. This control gate is non-negotiable and
every probe you write repeats it.

## 3. Run an existing experiment

```bash
python -m org_frontier.probes.probe_conjunctive_law
```

A "probe" is one script that tests one hypothesis with exact Φ and prints a verdict. The log of
every probe run is `org_frontier/probes/PROBES.md`; the worked end-to-end question is
`org_frontier/questions/q43_thompson_interdependence/`. Read one of each before writing your own.

## 4. The model in one paragraph

A coordination form is a small Boolean dynamical system. Each party — Worker (`W`), the
mediating System (`S`), Counterpart (`C`), and any others — is a node whose next value is a fixed
function of the current node values. `classify_rules(rules, labels)` returns a verdict:
`Φ_MIP = 0` means the form factors along a party-line cut (**dyadic** → literacy); `Φ_MIP > 0`
means no cut factors it (**triadic** → algorithmacy). `major_complex(rules, labels)` returns which
nodes form the irreducible core. Rules are little-endian: `rules[j](x)` reads `x[0], x[1], ...` and
returns node `j`'s next bit.

```python
from org_frontier.probes.lib import verdict, major_complex
rules  = [lambda x: x[1], lambda x: x[0] & x[2], lambda x: x[1]]  # W'=S, S'=W∧C, C'=S
labels = ("W", "S", "C")
v = verdict(rules, labels)                 # v.structure -> "triadic", v.max_phi -> 2.0
core, phi = major_complex(rules, labels)   # ("W","S","C"), 2.0
```

The shared API lives in `org_frontier/classifier/classifier.py` (`classify_rules`,
`tpm_from_rules`, `cm_from_rules`), `org_frontier/probes/lib.py` (`verdict`, `major_complex`,
`max_phi_float`), and `foundations/proxy_audit/exact_phi.py` (`exact_big_phi`, `reachable_states`).
Exact Φ is feasible up to roughly 10–12 nodes; keep forms small.

## 5. Scaffold a new question

```bash
python -m org_frontier.protocol.new_question --slug your_slug \
    --question "Your one-line research question"
```

This copies `org_frontier/protocol/template/` to `org_frontier/questions/q<NN>_<slug>/`, fills in
the next free question number and probe number, and prints the next steps. Read
`org_frontier/protocol/RESEARCH_PROTOCOL.md` for what each artifact (`review.md`, `hypotheses.md`,
`methods.md`, the `probe_*.py` scripts, `FINDINGS.md`, `paper.md`) must contain.

The one rule that makes the record credible: **commit `hypotheses.md` before you compute the
results.** The git history is the evidence that the claims were fixed first.

For qualitative research — reading a real coordination setting against the priors through interviews,
observation, or document work — start instead from
[`org_frontier/qualitative/`](org_frontier/qualitative/): the arm's [README](org_frontier/qualitative/README.md),
its [methods](org_frontier/qualitative/METHODS.md), the open [topics](org_frontier/qualitative/TOPICS.md), and
the study [template](org_frontier/qualitative/template/). The same pre-commitment rule applies in qualitative
form: commit the coding scheme before the fieldwork.

For the recurrence program — pairing exact Φ with cross-recurrence quantification, the behavioral reading of
how the parties' states track each other — start from [`org_frontier/recurrence/`](org_frontier/recurrence/):
the arm's [README](org_frontier/recurrence/README.md) and [CONCEPTS.md](org_frontier/recurrence/CONCEPTS.md),
then the worked [bridge demonstration](org_frontier/recurrence/bridge_demo.py) and its
[findings](org_frontier/recurrence/FINDINGS.md). Each experiment script is seeded so its numbers reproduce.

For the survey program — the human-subjects arm measuring algorithmacy as a lived competence through
self-report — start from [`org_frontier/survey/`](org_frontier/survey/): the arm's README and its first
pre-registered three-wave panel study. The same pre-commitment rule applies in survey form: commit the
instrument, scoring, and hypotheses before any data.

## 6. Register your numbers and check reproduction

Every published number is re-derived by CI from its script. After your probes run, add one entry
per number to `ci/reproduce.json`:

```json
{
  "name": "your-check-name",
  "cmd": "python -m org_frontier.questions.q<NN>_<slug>.probe_<slug>",
  "expect": ["a verbatim substring of the probe's stdout, including the number"],
  "timeout": 300,
  "source": "org_frontier/questions/q<NN>_<slug>/FINDINGS.md"
}
```

The `expect` strings must appear verbatim in the command's stdout, so copy them from a real run —
match the printed precision (`Φ=2.000`, not `Φ = 2.0`). Then confirm it passes locally:

```bash
python ci/reproduce.py your-check-name      # one check
python ci/reproduce.py                       # the full manifest
```

## 7. Refresh the README directory

The README carries a generated directory of every question, study, essay, and review
(`tools/build_index.py`). Regenerate it so your work shows up:

```bash
python tools/build_index.py
```

A pull request from this repo regenerates it automatically; the `directory-current` CI check
fails if it is stale, so run it before pushing (it commits a one-line change to README.md).

## 8. Open a pull request

Work lands through `contrib`, never `main` directly. Read `REPO_LAYOUT.md` first if you have not —
this tree nests a second, private git repo under `dissertation/`, and the directory you run git
from decides which repo you touch.

```bash
git checkout contrib && git pull
git checkout -b study/your-slug
git add <your files> && git commit -m "..."   # hypotheses committed before results
git push -u origin study/your-slug
gh pr create --base contrib
```

`PUBLISHING.md` describes the four-pass review your PR will get (reproduction, pre-commitment
audit, argument, prose) and `CONTRIBUTING.md` covers house style.
