import argparse
from datetime import datetime, timedelta, date, time as dt_time, timezone
from typing import Optional, List, Tuple, Dict
from zoneinfo import ZoneInfo

import pytz
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from rich import box
import questionary
from sqlalchemy import func

from database import Database, FollowerFollowing, Target, RunHistory, Counts

console = Console()


def _resolve_tz(tz_name: Optional[str]):
    tz_value = (tz_name or "local").strip().lower()
    if tz_value in {"", "local"}:
        return datetime.now().astimezone().tzinfo
    if tz_value == "utc":
        return timezone.utc
    try:
        return ZoneInfo(tz_name)
    except Exception:
        console.print(f"[yellow]Unknown timezone '{tz_name}', using local time.[/yellow]")
        return datetime.now().astimezone().tzinfo


def format_ts(ts, tz_name: Optional[str]):
    if ts is None:
        return "-"
    dt = ts if isinstance(ts, datetime) else datetime.fromisoformat(str(ts))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    tz = _resolve_tz(tz_name)
    return dt.astimezone(tz).strftime("%Y-%m-%d %H:%M:%S")


def parse_iso(dt_str: str) -> datetime:
    return datetime.fromisoformat(dt_str)


def utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def resolve_time(ts: Optional[str]) -> datetime:
    return parse_iso(ts) if ts else utcnow_naive()


def resolve_range(from_date: Optional[str], to_date: Optional[str], days: Optional[int]) -> Tuple[datetime, datetime]:
    if from_date and to_date:
        return parse_iso(from_date), parse_iso(to_date)
    if days is None:
        days = 7
    end = utcnow_naive()
    start = end - timedelta(days=days)
    return start, end


def resolve_day(day_str: str) -> Tuple[datetime, datetime]:
    day_dt = datetime.fromisoformat(day_str).date()
    start = datetime.combine(day_dt, dt_time.min)
    end = start + timedelta(days=1) - timedelta(microseconds=1)
    return start, end


def build_table(title: str, columns: List[str]):
    table = Table(title=title, box=box.MINIMAL_DOUBLE_HEAD, show_lines=False)
    for col in columns:
        table.add_column(col)
    return table


def _export(rows, columns, out_csv=None, out_json=None):
    if out_csv:
        import csv
        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            for row in rows:
                writer.writerow(row)
        console.print(f"[green]Saved CSV to {out_csv}[/green]")
    if out_json:
        import json
        data = [dict(zip(columns, row)) for row in rows]
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        console.print(f"[green]Saved JSON to {out_json}[/green]")


def cmd_list_current(db: Database, args):
    q = db.session.query(FollowerFollowing, Target.username.label("target"))\
        .join(Target, Target.id == FollowerFollowing.target_id)
    q = filter_type(q, args.type)
    q = q.filter(FollowerFollowing.is_lost.is_(False))
    if args.target:
        q = q.filter(Target.username == args.target)
    rows = q.order_by(Target.username, FollowerFollowing.follower_following_username).all()
    table = build_table("Current followers/followings", ["target", "username", "type", "first_seen_run_at", "last_seen_run_at"])
    export_rows = []
    for ff, target in rows:
        r = [target,
             ff.follower_following_username,
             "follower" if ff.is_follower else "following",
             format_ts(ff.first_seen_run_at, args.tz),
             format_ts(ff.last_seen_run_at, args.tz)]
        table.add_row(*(str(x) for x in r))
        export_rows.append(r)
    console.print(table)
    _export(export_rows, ["target", "username", "type", "first_seen_run_at", "last_seen_run_at"],
            out_csv=getattr(args, "out_csv", None), out_json=getattr(args, "out_json", None))


def filter_type(query, type_filter: str):
    if type_filter == "followers":
        return query.filter(FollowerFollowing.is_follower.is_(True))
    if type_filter == "followings":
        return query.filter(FollowerFollowing.is_follower.is_(False))
    return query


def cmd_new(db: Database, args):
    start = parse_iso(args.from_date)
    end = parse_iso(args.to_date)
    q = db.session.query(FollowerFollowing, Target.username.label("target"))\
        .join(Target, Target.id == FollowerFollowing.target_id)
    q = filter_type(q, args.type)
    q = q.filter(FollowerFollowing.first_seen_run_at >= start, FollowerFollowing.first_seen_run_at <= end)
    if args.target:
        q = q.filter(Target.username == args.target)
    rows = q.order_by(FollowerFollowing.first_seen_run_at.asc()).all()
    table = build_table("New followers/followings", ["target", "username", "type", "first_seen_run_at", "estimated_added_at"])
    for ff, target in rows:
        table.add_row(target, ff.follower_following_username, "follower" if ff.is_follower else "following",
                      format_ts(ff.first_seen_run_at, args.tz), format_ts(ff.estimated_added_at, args.tz))
    console.print(table)


def cmd_lost(db: Database, args):
    start = parse_iso(args.from_date)
    end = parse_iso(args.to_date)
    q = db.session.query(FollowerFollowing, Target.username.label("target"))\
        .join(Target, Target.id == FollowerFollowing.target_id)
    q = filter_type(q, args.type)
    q = q.filter(FollowerFollowing.lost_at_run_at != None)\
         .filter(FollowerFollowing.lost_at_run_at >= start, FollowerFollowing.lost_at_run_at <= end)
    if args.target:
        q = q.filter(Target.username == args.target)
    rows = q.order_by(FollowerFollowing.lost_at_run_at.asc()).all()
    table = build_table("Lost followers/followings", ["target", "username", "type", "lost_at_run_at", "estimated_removed_at"])
    for ff, target in rows:
        table.add_row(target, ff.follower_following_username, "follower" if ff.is_follower else "following",
                      format_ts(ff.lost_at_run_at, args.tz), format_ts(ff.estimated_removed_at, args.tz))
    console.print(table)


def cmd_snapshot(db: Database, args):
    at_time = parse_iso(args.at) if args.at else utcnow_naive()
    q = db.session.query(FollowerFollowing, Target.username.label("target"))\
        .join(Target, Target.id == FollowerFollowing.target_id)
    q = filter_type(q, args.type)
    q = q.filter(FollowerFollowing.first_seen_run_at <= at_time)
    q = q.filter((FollowerFollowing.lost_at_run_at == None) | (FollowerFollowing.lost_at_run_at > at_time))
    if args.target:
        q = q.filter(Target.username == args.target)
    rows = q.order_by(Target.username, FollowerFollowing.follower_following_username).all()
    table = build_table(f"Snapshot @ {at_time.isoformat()}", ["target", "username", "type", "first_seen_run_at", "last_seen_run_at"])
    for ff, target in rows:
        table.add_row(target, ff.follower_following_username, "follower" if ff.is_follower else "following",
                      format_ts(ff.first_seen_run_at, args.tz), format_ts(ff.last_seen_run_at, args.tz))
    console.print(table)


def cmd_summary(db: Database, args):
    days = args.days
    end = utcnow_naive()
    start = end - timedelta(days=days)
    q_new = db.session.query(FollowerFollowing.first_seen_run_at, FollowerFollowing.is_follower)
    q_lost = db.session.query(FollowerFollowing.lost_at_run_at, FollowerFollowing.is_follower)

    buckets = {}
    day_cursor = start.date()
    while day_cursor <= end.date():
        buckets[day_cursor] = {
            "new_followers": 0,
            "new_followings": 0,
            "lost_followers": 0,
            "lost_followings": 0,
        }
        day_cursor += timedelta(days=1)

    for ts, is_follower in q_new.filter(FollowerFollowing.first_seen_run_at >= start).all():
        if ts is None:
            continue
        day = ts.date()
        if day in buckets:
            key = "new_followers" if is_follower else "new_followings"
            buckets[day][key] += 1

    for ts, is_follower in q_lost.filter(FollowerFollowing.lost_at_run_at != None, FollowerFollowing.lost_at_run_at >= start).all():
        if ts is None:
            continue
        day = ts.date()
        if day in buckets:
            key = "lost_followers" if is_follower else "lost_followings"
            buckets[day][key] += 1

    table = build_table(f"Summary last {days} days", ["date", "new_followers", "new_followings", "lost_followers", "lost_followings"])
    for day, vals in sorted(buckets.items()):
        table.add_row(str(day), *(str(vals[k]) for k in ["new_followers", "new_followings", "lost_followers", "lost_followings"]))

    console.print(table)


def cmd_daily_counts(db: Database, args):
    start, end = resolve_range(getattr(args, "from_date", None), getattr(args, "to_date", None), getattr(args, "days", None))

    sub = (
        db.session.query(
            func.date(Counts.timestamp).label("day"),
            Counts.count_type.label("count_type"),
            Counts.target_id.label("target_id"),
            func.max(Counts.timestamp).label("max_ts"),
        )
        .filter(Counts.timestamp >= start, Counts.timestamp <= end)
        .group_by(func.date(Counts.timestamp), Counts.count_type, Counts.target_id)
    )

    if args.target:
        sub = sub.join(Target, Target.id == Counts.target_id).filter(Target.username == args.target)

    sub = sub.subquery()

    q = (
        db.session.query(
            sub.c.day,
            sub.c.count_type,
            sub.c.target_id,
            Counts.count,
        )
        .join(
            Counts,
            (Counts.target_id == sub.c.target_id)
            & (Counts.count_type == sub.c.count_type)
            & (Counts.timestamp == sub.c.max_ts),
        )
        .join(Target, Target.id == sub.c.target_id)
    )

    rows = q.all()
    if not rows:
        console.print("[yellow]No daily counts found for the selected range.[/yellow]")
        return

    target_names = {}
    for tid in {row[2] for row in rows}:
        target_names[tid] = db.session.query(Target.username).filter_by(id=tid).scalar()

    data: Dict[Tuple[str, str], Dict[str, Optional[int]]] = {}
    for day, count_type, target_id, count in rows:
        target_name = target_names.get(target_id) or "-"
        key = (str(day), target_name)
        data.setdefault(key, {"followers": None, "followings": None})
        if count_type == "followers":
            data[key]["followers"] = count
        elif count_type == "followings":
            data[key]["followings"] = count

    if args.target:
        table = build_table(
            f"Daily counts ({start.date()} to {end.date()})",
            ["date", "followers", "followings"],
        )
        for (day, _target), vals in sorted(data.items()):
            table.add_row(day, str(vals["followers"] or "-"), str(vals["followings"] or "-"))
    else:
        table = build_table(
            f"Daily counts ({start.date()} to {end.date()})",
            ["date", "target", "followers", "followings"],
        )
        for (day, target_name), vals in sorted(data.items()):
            table.add_row(day, target_name, str(vals["followers"] or "-"), str(vals["followings"] or "-"))
    console.print(table)


def cmd_day_details(db: Database, args):
    start, end = resolve_day(args.date)

    console.print(f"[bold]Daily counts for {args.date}[/bold]")
    daily_args = argparse.Namespace(
        from_date=start.isoformat(),
        to_date=end.isoformat(),
        days=None,
        target=args.target,
        tz=args.tz,
    )
    cmd_daily_counts(db, daily_args)

    console.print(f"[bold]New {args.type} on {args.date}[/bold]")
    cmd_new(
        db,
        argparse.Namespace(
            from_date=start.isoformat(),
            to_date=end.isoformat(),
            type=args.type,
            target=args.target,
            tz=args.tz,
        ),
    )

    console.print(f"[bold]Lost {args.type} on {args.date}[/bold]")
    cmd_lost(
        db,
        argparse.Namespace(
            from_date=start.isoformat(),
            to_date=end.isoformat(),
            type=args.type,
            target=args.target,
            tz=args.tz,
        ),
    )


def menu(db: Database):
    action = questionary.select(
        "Choose report",
        choices=[
            "New in range",
            "Lost in range",
            "Snapshot at time",
            "Summary last N days",
            "Daily counts",
            "Day details",
            "Current followers/followings",
            "Quit"
        ]).ask()
    if action == "Quit" or action is None:
        return
    if action == "New in range":
        from_date = Prompt.ask("From (YYYY-MM-DD)")
        to_date = Prompt.ask("To (YYYY-MM-DD)")
        cmd_new(db, argparse.Namespace(from_date=from_date+"T00:00:00", to_date=to_date+"T23:59:59", type="both", target=None, tz="local"))
    elif action == "Lost in range":
        from_date = Prompt.ask("From (YYYY-MM-DD)")
        to_date = Prompt.ask("To (YYYY-MM-DD)")
        cmd_lost(db, argparse.Namespace(from_date=from_date+"T00:00:00", to_date=to_date+"T23:59:59", type="both", target=None, tz="local"))
    elif action == "Snapshot at time":
        at = Prompt.ask("At (YYYY-MM-DDTHH:MM:SS, blank for now)", default="")
        cmd_snapshot(db, argparse.Namespace(at=at if at else None, type="both", target=None, tz="local"))
    elif action == "Summary last N days":
        days = int(Prompt.ask("Days", default="7"))
        cmd_summary(db, argparse.Namespace(days=days))
    elif action == "Daily counts":
        days = int(Prompt.ask("Days", default="7"))
        target = Prompt.ask("Target username (blank for all)", default="")
        cmd_daily_counts(db, argparse.Namespace(days=days, target=target or None, from_date=None, to_date=None, tz="local"))
    elif action == "Day details":
        day = Prompt.ask("Day (YYYY-MM-DD)")
        target = Prompt.ask("Target username (blank for all)", default="")
        ftype = questionary.select("Type", choices=["both", "followers", "followings"]).ask()
        cmd_day_details(db, argparse.Namespace(date=day, target=target or None, type=ftype or "both", tz="local"))
    elif action == "Current followers/followings":
        target = Prompt.ask("Target username (blank for all)", default="")
        ftype = questionary.select("Type", choices=["both", "followers", "followings"]).ask()
        out_csv = Prompt.ask("Save to CSV path (blank to skip)", default="")
        out_json = Prompt.ask("Save to JSON path (blank to skip)", default="")
        cmd_list_current(db, argparse.Namespace(type=ftype or "both", target=target or None,
                                                out_csv=out_csv or None, out_json=out_json or None, tz="local"))


def build_parser():
    parser = argparse.ArgumentParser(description="Report on Instagram tracker data")
    parser.add_argument("--tz", default="local", help="Timezone for displayed timestamps (e.g. local, UTC, America/New_York)")
    sub = parser.add_subparsers(dest="command")

    p_new = sub.add_parser("new", help="List new followers/followings in date range")
    p_new.add_argument("--from", dest="from_date", required=True, help="ISO datetime start")
    p_new.add_argument("--to", dest="to_date", required=True, help="ISO datetime end")
    p_new.add_argument("--type", choices=["followers", "followings", "both"], default="both")
    p_new.add_argument("--target", help="Target account to filter")

    p_lost = sub.add_parser("lost", help="List lost followers/followings in date range")
    p_lost.add_argument("--from", dest="from_date", required=True)
    p_lost.add_argument("--to", dest="to_date", required=True)
    p_lost.add_argument("--type", choices=["followers", "followings", "both"], default="both")
    p_lost.add_argument("--target", help="Target account to filter")

    p_snap = sub.add_parser("snapshot", help="Show snapshot at a given time")
    p_snap.add_argument("--at", help="ISO datetime (default now)")
    p_snap.add_argument("--type", choices=["followers", "followings", "both"], default="both")
    p_snap.add_argument("--target", help="Target account to filter")

    p_summary = sub.add_parser("summary", help="Summary over last N days")
    p_summary.add_argument("--days", type=int, default=7)

    p_daily = sub.add_parser("daily", help="Daily follower/following counts")
    p_daily.add_argument("--days", type=int, default=7)
    p_daily.add_argument("--from", dest="from_date", help="ISO datetime start")
    p_daily.add_argument("--to", dest="to_date", help="ISO datetime end")
    p_daily.add_argument("--target", help="Target account to filter")

    p_day = sub.add_parser("day", help="Counts and changes for a specific day")
    p_day.add_argument("--date", required=True, help="YYYY-MM-DD")
    p_day.add_argument("--type", choices=["followers", "followings", "both"], default="both")
    p_day.add_argument("--target", help="Target account to filter")

    p_list = sub.add_parser("list", help="List current followers/followings")
    p_list.add_argument("--type", choices=["followers", "followings", "both"], default="both")
    p_list.add_argument("--target", help="Target account to filter")
    p_list.add_argument("--out-csv", help="Path to save CSV output")
    p_list.add_argument("--out-json", help="Path to save JSON output")

    parser.add_argument("--menu", action="store_true", help="Launch interactive menu")
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    db = Database()
    try:
        if args.menu:
            menu(db)
            return
        if args.command == "new":
            cmd_new(db, args)
        elif args.command == "lost":
            cmd_lost(db, args)
        elif args.command == "snapshot":
            cmd_snapshot(db, args)
        elif args.command == "summary":
            cmd_summary(db, args)
        elif args.command == "daily":
            cmd_daily_counts(db, args)
        elif args.command == "day":
            cmd_day_details(db, args)
        elif args.command == "list":
            cmd_list_current(db, args)
        else:
            parser.print_help()
    finally:
        db.close()


if __name__ == "__main__":
    main()
