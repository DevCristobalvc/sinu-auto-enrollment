# SINU Auto-Enrollment

Automated enrollment monitor for **SINU USC** (Universidad Santiago de Cali academic system).

Detects when a course group becomes available (no schedule conflict + open slot) and enrolls automatically — no LLM calls, pure Playwright automation.

## Why

Manually refreshing SINU every few minutes to catch a freed slot in a full course (e.g. *Proyecto Integrador de Grado*) is tedious. This tool does it for you:

- Logs into SINU with your credentials
- Navigates to *Matrícula individual*
- Reads the group table (schedule conflict + capacity state per group)
- **Optionally enrolls** in the first group matching your criteria
- Prints a machine-readable JSON result (for cron/CI or an agent to interpret)

## Features

- 🔐 **Credentials via environment variables or `.env`** — never hardcoded
- ⚙️ **Fully configurable**: course code, program code, period, conflict rules
- 🚫 **No LLM dependency** — deterministic Playwright automation only
- 🧩 **Two modes**: `check` (read-only) and `enroll` (auto-enroll)
- 📦 **JSON output** — easy to parse from cron, CI, or a chatbot agent
- 🎯 **Conflict awareness** — ignores groups that clash with your fixed schedule

## Requirements

- Python 3.10+
- A Chrome/Chromium browser (Playwright uses the system browser via CDP)

```bash
pip install -r requirements.txt
playwright install chromium  # only if you don't have a system Chrome
```

## Quick start

### 1. Configure credentials

Copy the example config and fill in your SINU credentials:

```bash
cp config/example.env .env
```

```bash
# .env
SINU_USERNAME=your_student_id_here
SINU_PASSWORD=your_password_here
SINU_URL=https://sinu.usc.edu.co:8443/sinugwt/
```

### 2. Check availability (read-only)

```bash
python -m sinu_auto check --config config/settings.yaml
```

Example output:

```json
{
  "estado": "con_cupo",
  "grupos": [
    {"grupo": "PIG03", "sin_cruce": true, "cupo": 1, "horario": "Jueves 18:30 - 21:30"}
  ]
}
```

### 3. Auto-enroll

```bash
python -m sinu_auto enroll --config config/settings.yaml
```

## Configuration

All behavior lives in `config/settings.yaml`:

```yaml
sinu:
  url: "https://sinu.usc.edu.co:8443/sinugwt/"
  period: "2026B"
  program: "P217"

target:
  course_code: "ISI51"        # course to watch
  group_prefix: "PIG"         # group name prefix
  require_no_conflict: true   # only enroll groups without schedule conflict
  fixed_schedule:             # courses you already have (conflict sources)
    - name: "ECUACIONES DIFERENCIALES"
      days: ["Martes"]
      time: "18:30-21:30"

enroll:
  auto: true                  # enroll when a matching group is found
  max_attempts: 3
  wait_between_checks: 1800   # seconds (only used by the loop mode)
```

## CLI reference

```
usage: python -m sinu_auto {check,enroll,watch} [options]

check   Read-only availability check. Prints JSON.
enroll  Enroll in the first matching group (if available).
watch   Loop mode: check every N seconds until a slot opens.
```

| Flag | Description |
|---|---|
| `--config PATH` | Path to settings YAML (default `config/settings.yaml`) |
| `--env PATH` | Path to `.env` file (default `.env`) |
| `--dry-run` | Print what would happen without doing it |
| `--interval SEC` | Watch interval in seconds (default from config) |

## JSON output schema

Every run prints one JSON object to stdout:

```json
{
  "estado": "con_cupo | sin_cupo | error | matriculado",
  "timestamp": "2026-08-03T22:13:29",
  "grupos": [
    {
      "grupo": "PIG03",
      "sin_cruce": true,
      "cupo_disp": true,
      "cupo_valor": 1,
      "horario": "Jueves 18:30 - 21:30"
    }
  ],
  "matriculado": null
}
```

- `estado=matriculado` → enrollment succeeded (only in `enroll` mode)
- `estado=error` → something failed (see `error` field)

## Architecture

```
sinu-auto-enrollment/
├── src/sinu_auto/
│   ├── __init__.py
│   ├── cli.py          # CLI entry point
│   ├── browser.py      # Playwright/CDP session management
│   ├── login.py        # SINU authentication
│   ├── navigator.py    # UI navigation (SmartClient clicks)
│   ├── parser.py       # Group table parsing (DOM → structured data)
│   ├── enroller.py     # Enrollment logic
│   └── config.py       # Settings + env loading
├── config/
│   ├── example.env     # Credential template
│   └── settings.yaml   # Behavior configuration
├── scripts/
│   └── sinu_monitor.sh # Cron wrapper
├── docs/
│   └── sinu-ui-map.md  # SmartClient UI coordinates reference
└── tests/
```

## SmartClient notes

SINU is a SmartClient (Isomorphic) app — the DOM is canvas/grid based and buttons are rendered as images. The automation relies on:

1. **CSS/locator selectors** for text-bearing elements (`tr:has-text(...)`)
2. **Image-based detection** for state icons:
   - `false_cruce.png` → no schedule conflict
   - `true_cruce.png` → schedule conflict / full
   - `true_select.png` → group selectable
   - `row_collapsed.gif` → expandable row
3. **Coordinate clicks** only where no selector exists (SmartClient buttons)

If the UI changes, update `docs/sinu-ui-map.md` and the selectors in `navigator.py`.

## License

MIT
