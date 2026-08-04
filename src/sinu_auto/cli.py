"""SINU Auto-Enrollment — CLI entry point.

Usage:
    python -m sinu_auto check  [--config PATH] [--env PATH]
    python -m sinu_auto enroll [--config PATH] [--env PATH] [--dry-run]
    python -m sinu_auto watch  [--config PATH] [--env PATH] [--interval SEC] [--dry-run]

Every mode prints a single JSON object to stdout.
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
import time
from typing import List

from . import __version__
from .browser import BrowserSession
from .config import SinusSettings, load_settings
from .enroller import Enroller
from .logging_setup import get_logger, setup_logging
from .login import LoginError, login
from .navigator import Navigator
from .parser import Group, GroupParser

log = get_logger()


def filter_candidates(groups: List[Group], require_no_conflict: bool = True) -> List[Group]:
    """Apply the enrollment filters: skip conflicting groups and full groups.

    Pure function — no browser needed, so it is easy to unit test.
    """
    candidates: List[Group] = []
    for g in groups:
        if require_no_conflict and not g.sin_cruce:
            log.info("  skip %s: schedule conflict", g.grupo)
            continue
        if not g.cupo_disp:
            log.info("  skip %s: no capacity (cupo_valor=%s)", g.grupo, g.cupo_valor)
            continue
        candidates.append(g)
    return candidates


def _run(s: SinusSettings, enroll: bool, dry_run: bool = False) -> dict:
    """Run one check/enroll cycle. Returns a result dict."""
    ts = datetime.datetime.now().isoformat()
    log.info("Starting %s run | course=%s prefix=%s require_no_conflict=%s",
             "enroll" if enroll else "check", s.course_code, s.group_prefix, s.require_no_conflict)
    session = BrowserSession()
    try:
        log.info("Connecting to browser session (CDP or local)")
        context = session.connect()
        page = context.new_page()
        try:
            log.info("Logging into SINU: %s", s.url)
            login(page, s.url, s.username, s.password)
            log.info("Login OK")

            nav = Navigator(page)
            log.info("Opening 'Matrícula individual'")
            nav.open_matricula_individual()
            log.info("Selecting program row")
            nav.select_program()
            log.info("Expanding course %s", s.course_code)
            nav.expand_course(s.course_code)

            parser = GroupParser()
            groups = parser.parse(page, group_prefix=s.group_prefix)
            log.info("Parsed %d group row(s)", len(groups))
            for g in groups:
                log.info("  group=%s sin_cruce=%s cupo_disp=%s cupo_valor=%s horario=%s",
                         g.grupo, g.sin_cruce, g.cupo_disp, g.cupo_valor, g.horario)

            if not groups:
                log.warning("No groups found for %s", s.course_code)
                return {
                    "estado": "sin_grupos",
                    "timestamp": ts,
                    "mensaje": f"No groups found for {s.course_code}",
                    "grupos": [],
                    "candidatos": [],
                    "matriculado": None,
                }

            candidates = filter_candidates(groups, s.require_no_conflict)
            log.info("Candidates after filters: %s", [g.grupo for g in candidates] or "none")

            result = {
                "estado": "con_cupo" if candidates else "sin_cupo",
                "timestamp": ts,
                "grupos": json.loads(GroupParser.to_json(groups)),
                "candidatos": [g.grupo for g in candidates],
                "matriculado": None,
            }

            if candidates and enroll:
                target = candidates[0]
                log.info("Enroll mode: targeting %s", target.grupo)
                if dry_run:
                    log.info("DRY-RUN: would enroll %s", target.grupo)
                    result["matriculado"] = f"DRY-RUN would enroll {target.grupo}"
                    return result

                enr = Enroller(page)
                for attempt in range(1, s.max_attempts + 1):
                    log.info("Enrollment attempt %d/%d: %s", attempt, s.max_attempts, target.grupo)
                    enr.select_group(target)
                    time.sleep(2)
                    log.info("Closing enrollment (IRREVERSIBLE)")
                    ok = enr.close_enrollment()
                    if ok:
                        log.info("Enrollment dialog accepted — enrolled in %s", target.grupo)
                        result["estado"] = "matriculado"
                        result["matriculado"] = target.grupo
                        result["mensaje"] = f"Enrolled in {target.grupo}"
                        break
                    log.warning("Attempt %d failed for %s", attempt, target.grupo)
                    if attempt < s.max_attempts:
                        # UI state may have shifted (slot taken, dialog closed) — re-read the table
                        time.sleep(1)
                        groups = parser.parse(page, group_prefix=s.group_prefix)
                        candidates = filter_candidates(groups, s.require_no_conflict)
                        result["grupos"] = json.loads(GroupParser.to_json(groups))
                        result["candidatos"] = [g.grupo for g in candidates]
                        if not candidates:
                            log.warning("No candidates left after attempt %d", attempt)
                            result["estado"] = "sin_cupo"
                            break
                        target = candidates[0]
                else:
                    # Loop exhausted without success
                    result["estado"] = "error_matricula"
                    result["mensaje"] = f"Had a candidate ({target.grupo}) but enrollment failed after {s.max_attempts} attempts"

            return result
        finally:
            try:
                page.close()
            except Exception:
                pass
    except LoginError as e:
        log.error("Login error: %s", e)
        return {"estado": "error", "error": str(e)[:200], "timestamp": ts}
    except Exception as e:
        log.exception("Unexpected error")
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


def cmd_watch(s: SinusSettings, interval: int, dry_run: bool = False) -> int:
    """Loop: check every `interval` seconds until a candidate appears, then enroll."""
    while True:
        result = _run(s, enroll=True, dry_run=dry_run)
        print(json.dumps(result, ensure_ascii=False), flush=True)
        if result.get("estado") in ("matriculado", "error_matricula", "error"):
            return 0
        time.sleep(interval)


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", default="config/settings.yaml", help="Path to settings YAML")
    parser.add_argument("--env", default=".env", help="Path to .env credentials file")
    parser.add_argument("--verbose", action="store_true", help="Enable DEBUG logging (stderr)")
    parser.add_argument("--log-file", default=None, help="Write logs to a file too (default: stderr only)")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="sinu_auto", description="SINU USC auto-enrollment")
    parser.add_argument("--version", action="version", version=f"sinu-auto {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("check", "enroll", "watch"):
        p = sub.add_parser(name)
        _add_common_args(p)
        if name == "enroll":
            p.add_argument("--dry-run", action="store_true", help="Show what would happen without enrolling")
        if name == "watch":
            p.add_argument("--interval", type=int, default=None, help="Watch interval in seconds")
            p.add_argument("--dry-run", action="store_true", help="Show what would happen without enrolling")

    args = parser.parse_args(argv)
    setup_logging(verbose=args.verbose, log_file=args.log_file)

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
        interval = args.interval if args.interval is not None else s.watch_interval
        return cmd_watch(s, interval, dry_run=getattr(args, "dry_run", False))
    return 1


if __name__ == "__main__":
    sys.exit(main())
