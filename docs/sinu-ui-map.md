# SINU SmartClient UI map
# Coordinates/selectors that the automation relies on. Update if the UI changes.

## Login screen
- Username field: `#isc_3Z`
- Password field: `#isc_42`
- "Entrar" button: (1059, 960)
- "Duplicate session" OK dialog: (675, 917)

## Left menu
- "Matrícula individual": found by text; click center of the element.
- After opening, press Escape to close any preference dialog.

## Student table (top)
- Program row (P217): click (700, 211) — the row for INGENIERÍA DE SISTEMAS.

## Course list ("Grupos ofertados")
- Expand a course: click `img[src*='row_collapsed']` inside `tr:has-text('COURSE_CODE')`.
- Group rows contain cells:
  - [0] conflict icon: `false_cruce.png` (no conflict) | `true_cruce.png` (conflict/full)
  - [1] capacity: number (available slots) or icon
  - [2] select icon: `true_select.png` / `false_select.png`
  - [3] group code (PIGxx)
  - [9] schedule (e.g. "Jueves 18:30 - 21:30")
  - [10] date

## Action toolbar (Grupos ofertados)
- "Cerrar matrícula" button: (526, 648)
- "Generar oferta" button: (660, 648)

## Confirmation dialog (closing enrollment)
- Message: "¿Está seguro que desea cerrar su matrícula académica? Luego de aceptar no podrá cambiarlo nuevamente."
- OK: (673, 586)
- Cancelar: (799, 586)

## Known limitations
- SmartClient selection icons (`true_select.png`) do not change state reliably via
  synthetic clicks. Verify selection visually before closing enrollment.
- Coordinates assume a 1431px-wide viewport with no page zoom.
