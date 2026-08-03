"""SINU Auto-Enrollment — group table parser (DOM → structured data)."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import List, Optional

from playwright.sync_api import Page


@dataclass
class Group:
    """A course group as shown in the SINU enrollment table."""

    grupo: str
    sin_cruce: bool
    cupo_disp: bool
    cupo_valor: object
    horario: str
    fecha: str
    raw_cruce: str = ""
    raw_cupo: str = ""


class GroupParser:
    """Parses the 'Grupos ofertados' table into structured Group objects."""

    def parse(self, page: Page, group_prefix: str = "PIG") -> List[Group]:
        """Extract all group rows matching the prefix from the visible table."""
        rows = page.evaluate(
            """(prefix) => {
                var out = [];
                var trs = document.querySelectorAll('tr');
                trs.forEach(function(tr) {
                    var t = (tr.innerText || '').trim();
                    if (t.includes(prefix)) {
                        var cells = [];
                        tr.querySelectorAll('td').forEach(function(td) {
                            var imgs = [];
                            td.querySelectorAll('img').forEach(function(im) {
                                imgs.push((im.src || '').split('/').pop().slice(0, 30));
                            });
                            cells.push({
                                txt: (td.innerText || '').trim().slice(0, 60),
                                imgs: imgs
                            });
                        });
                        out.push(cells);
                    }
                });
                return out;
            }""",
            group_prefix,
        )

        groups: List[Group] = []
        for row in rows:
            if len(row) < 4:
                continue

            cruce_img = row[0].get("imgs", [""])[0] if row[0].get("imgs") else ""
            cupo_raw = row[1].get("txt", "") or (row[1].get("imgs", [""])[0] if row[1].get("imgs") else "")

            # Group code: search all cells for the prefix pattern (e.g. PIG03)
            grupo = ""
            for cell in row:
                m = re.search(r"({prefix}\d+)".format(prefix=re.escape(group_prefix)), cell.get("txt", ""))
                if m:
                    grupo = m.group(1)
                    break

            horario = row[9].get("txt", "") if len(row) > 9 else ""
            fecha = row[10].get("txt", "") if len(row) > 10 else ""

            sin_cruce = "false_cruce" in cruce_img
            cupo_es_numero = cupo_raw.isdigit()
            cupo_valor = int(cupo_raw) if cupo_es_numero else (cupo_raw if cupo_raw else "?")

            groups.append(
                Group(
                    grupo=grupo,
                    sin_cruce=sin_cruce,
                    cupo_disp=cupo_es_numero and int(cupo_raw) > 0,
                    cupo_valor=cupo_valor,
                    horario=horario,
                    fecha=fecha,
                    raw_cruce=cruce_img,
                    raw_cupo=cupo_raw,
                )
            )

        return groups

    @staticmethod
    def to_json(groups: List[Group]) -> str:
        """Serialize groups to JSON (for CLI output)."""
        return json.dumps(
            [
                {
                    "grupo": g.grupo,
                    "sin_cruce": g.sin_cruce,
                    "cupo_disp": g.cupo_disp,
                    "cupo_valor": g.cupo_valor,
                    "horario": g.horario,
                    "fecha": g.fecha,
                }
                for g in groups
            ],
            ensure_ascii=False,
        )
