"""SINU Auto-Enrollment — CLI entry point.

Usage:
    python -m sinu_auto check  [--config PATH] [--env PATH]
    python -m sinu_auto enroll [--config PATH] [--env PATH] [--dry-run]
    python -m sinu_auto watch  [--config PATH] [--env PATH] [--interval SEC]

Every mode prints a single JSON object to stdout.
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
import time
from typing import List

from .browser import BrowserSession
from .config import SinusSettings, load_settings
from .enroller import Enroller
from .login import LoginError, login
from .navigator import Navigator
from .parser import Group, GroupParser


def _run(s: SinusSettings, enroll: bool, dry_run: bool = False) -> dict:
    """Run one check/enroll cycle. Returns a result dict."""
    ts = datetime.datetime.now().isoformat()
    session = BrowserSession()
    try:
        context = session.connect()
        page = context.new_page()
        try:
            login(page, s.url, s.username, s.password)

            nav = Navigator(page)
            nav.open_matricula_individual()
            nav.select_program()
            nav.expand_course(s.course_code)

            parser = GroupParser()
            groups = parser.parse(page, group_prefix=s.group_prefix)

            if not groups:
                return {
                    "estado": "sin_grupos",
                    "timestamp": ts,
                    "mensaje": f"No groups found for {s.course_code}",
                    "grupos": [],
                    "matriculado": None,
                }

            # Apply filters
            candidates: List[Group] = []
            for g in groups:
                if s.require_no_conflict and not g.sin_cruce:
                    continue
                if not g.cupo_disp:
                    continue
                candidates.append(g)

            result = {
                "estado": "con_cupo" if candidates else "sin_cupo",
                "timestamp": ts,
                "grupos": json.loads(GroupParser.to_json(groups)),
                "candidatos": [g.grupo for g in candidates],
                "matriculado": None,
            }

            if candidates and enroll:
                target = candidates[0]
                if dry_run:
                    result["matriculado"] = f"DRY-RUN would enroll {target.grupo}"
                    return result

                enr = Enroller(page)
                enr.select_group(target)
                time.sleep(2)
                ok = enr.close_enrollment()
                if ok:
                    result["estado"] = "matriculado"
                    result["matriculado"] = target.grupo
                    result["mensaje"] = f"Enrolled in {target.grupo}"
                else:
                    result["estado"] = "error_matricula"
                    result["mensaje"] = f"Had a candidate ({target.grupo}) but enrollment failed"

            return result
        finally:
            try:
                page.close()
            except Exception:
                pass
    except LoginError as e:
        return {"estado": "error", "error": str(e)[:200], "timestamp": ts}
    except Exception as e:
        return {"estado": "error", "error": str(e)[:200], "mensaje": f"Error: {str(e)[:120]}", "timestamp": ts}
    finally:
        session.close()


def cmd_check(s: SinusSettings) -> int:
    result = _run(s, enroll=False)
    print(json.dumps(result, ensure_ascii=False))
    return 0


def cmd_enroll(s: SinusSettings, dry_run: bool) -> int:
    result = _run(s, enroll=True, dry_run=dry_run)
    print(json.dumps(result, ensure_ascii=False))
    return 0


def cmd_watch(s: SinusSettings, interval: int) -> int:
    """Loop: check every `interval` seconds until a candidate appears, then enroll."""
    while True:
        result = _run(s, enroll=True)
        print(json.dumps(result, ensure_ascii=False), flush=True)
        if result.get("estado") in ("matriculado", "error_matricula", "error"):
            return 0
        time.sleep(interval)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="sinu_auto", description="SINU USC auto-enrollment")
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("check", "enroll", "watch"):
        p = sub.add_parser(name)
        p.add_argument("--config", default="config/settings.yaml", help="Path to settings YAML")
        p.add_argument("--env", default=".env", help="Path to .env credentials file")
        if name == "enroll":
            p.add_argument("--dry-run", action="store_true", help="Show what would happen without enrolling")
        if name == "watch":
            p.add_argument("--interval", type=int, default=None, help="Watch interval in seconds")

    args = parser.parse_args(argv)

    try:
        s = load_settings(args.config, args.env)
    except ValueError as e:
        print(json.dumps({"estado": "error", "error": str(e)}))
        return 1

    if args.command == "check":
        return cmd_check(s)
    if args.command == "enroll":
        return cmd_enroll(s, getattr(args, "dry_run", False))
    if args.command == "watch":
        interval = args.interval or s.watch_interval
        return cmd_watch(s, interval)
    return 1


if __name__ == "__main__":
    sys.exit(main())
