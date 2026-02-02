import argparse
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_DB = "instagram_tracker.db"


def _timestamp():
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def export_db(src_path: Path, out_path: Path | None, overwrite: bool) -> Path:
    if not src_path.exists():
        raise FileNotFoundError(f"Source DB not found: {src_path}")

    if out_path is None:
        out_path = Path("exports") / f"instagram_tracker_{_timestamp()}.db"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists() and not overwrite:
        raise FileExistsError(f"Export path already exists: {out_path}")

    shutil.copy2(src_path, out_path)
    return out_path


def _run(conn: sqlite3.Connection, sql: str) -> int:
    cur = conn.execute(sql)
    return cur.rowcount


def _parse_dt(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def _pick_min_dt(a, b):
    if a is None:
        return b
    if b is None:
        return a
    da = _parse_dt(a)
    db = _parse_dt(b)
    if da is None:
        return a
    if db is None:
        return b
    return a if da <= db else b


def _pick_max_dt(a, b):
    if a is None:
        return b
    if b is None:
        return a
    da = _parse_dt(a)
    db = _parse_dt(b)
    if da is None:
        return a
    if db is None:
        return b
    return a if da >= db else b


def _merge_is_lost(a, b):
    if a is None:
        return b
    if b is None:
        return a
    return 0 if int(a) == 0 or int(b) == 0 else 1


def preview_merge(dest_path: Path, src_path: Path) -> dict:
    if not dest_path.exists():
        raise FileNotFoundError(f"Destination DB not found: {dest_path}")
    if not src_path.exists():
        raise FileNotFoundError(f"Source DB not found: {src_path}")

    conn = sqlite3.connect(str(dest_path))
    try:
        conn.execute("ATTACH DATABASE ? AS srcdb", (str(src_path),))
        result = {}
        result["new_targets"] = conn.execute(
            """
            SELECT COUNT(1)
            FROM srcdb.targets st
            WHERE NOT EXISTS (
              SELECT 1 FROM targets t WHERE t.username = st.username
            )
            """
        ).fetchone()[0]

        result["new_run_history"] = conn.execute(
            """
            SELECT COUNT(1)
            FROM srcdb.run_history r
            JOIN srcdb.targets st ON st.id = r.target_id
            JOIN targets t ON t.username = st.username
            WHERE NOT EXISTS (
              SELECT 1 FROM run_history r2
              WHERE r2.target_id = t.id AND r2.run_started_at = r.run_started_at
            )
            """
        ).fetchone()[0]

        source_ff_rows = conn.execute(
            """
            SELECT
              st.username,
              ff.follower_following_username,
              ff.is_follower
            FROM srcdb.followers_followings ff
            JOIN srcdb.targets st ON st.id = ff.target_id
            GROUP BY st.username, ff.follower_following_username, ff.is_follower
            """
        ).fetchall()

        ff_insert = 0
        ff_update = 0
        for target_name, follower_name, is_follower in source_ff_rows:
            target_row = conn.execute("SELECT id FROM targets WHERE username = ?", (target_name,)).fetchone()
            if target_row is None:
                ff_insert += 1
                continue
            target_id = target_row[0]
            existing = conn.execute(
                """
                SELECT 1 FROM followers_followings
                WHERE target_id = ? AND follower_following_username = ? AND is_follower = ?
                LIMIT 1
                """,
                (target_id, follower_name, is_follower),
            ).fetchone()
            if existing:
                ff_update += 1
            else:
                ff_insert += 1

        result["followers_followings_insert"] = ff_insert
        result["followers_followings_update"] = ff_update

        result["new_counts"] = conn.execute(
            """
            SELECT COUNT(1)
            FROM srcdb.counts c
            JOIN srcdb.targets st ON st.id = c.target_id
            JOIN targets t ON t.username = st.username
            WHERE NOT EXISTS (
                SELECT 1 FROM counts c2
                WHERE c2.target_id = t.id
                  AND c2.count_type = c.count_type
                  AND c2.timestamp = c.timestamp
            )
            """
        ).fetchone()[0]

        result["new_change_logs"] = conn.execute(
            """
            SELECT COUNT(1)
            FROM srcdb.change_logs c
            WHERE NOT EXISTS (
                SELECT 1 FROM change_logs c2
                WHERE c2.timestamp = c.timestamp
                  AND c2.change_type = c.change_type
                  AND c2.username = c.username
            )
            """
        ).fetchone()[0]

        conn.execute("DETACH DATABASE srcdb")
        return result
    finally:
        conn.close()


def cleanup_targets(dest_path: Path, usernames, apply: bool, backup: bool) -> dict:
    if not dest_path.exists():
        raise FileNotFoundError(f"Destination DB not found: {dest_path}")

    usernames = [u.strip() for u in usernames if u.strip()]
    if not usernames:
        raise ValueError("No target usernames provided.")

    conn = sqlite3.connect(str(dest_path))
    try:
        placeholders = ",".join("?" for _ in usernames)
        target_rows = conn.execute(
            f"SELECT id, username FROM targets WHERE username IN ({placeholders})",
            usernames,
        ).fetchall()
        target_ids = [row[0] for row in target_rows]
        matched_usernames = [row[1] for row in target_rows]

        result = {
            "matched_targets": matched_usernames,
            "counts_rows": 0,
            "followers_followings_rows": 0,
            "run_history_rows": 0,
            "targets_rows": len(target_rows),
            "backup_path": None,
            "applied": apply,
        }

        if not target_ids:
            return result

        id_ph = ",".join("?" for _ in target_ids)
        result["counts_rows"] = conn.execute(
            f"SELECT COUNT(1) FROM counts WHERE target_id IN ({id_ph})",
            target_ids,
        ).fetchone()[0]
        result["followers_followings_rows"] = conn.execute(
            f"SELECT COUNT(1) FROM followers_followings WHERE target_id IN ({id_ph})",
            target_ids,
        ).fetchone()[0]
        result["run_history_rows"] = conn.execute(
            f"SELECT COUNT(1) FROM run_history WHERE target_id IN ({id_ph})",
            target_ids,
        ).fetchone()[0]

        if not apply:
            return result

        if backup:
            backup_path = dest_path.with_name(f"{dest_path.stem}.bak_{_timestamp()}{dest_path.suffix}")
            shutil.copy2(dest_path, backup_path)
            result["backup_path"] = str(backup_path)

        with conn:
            conn.execute(f"DELETE FROM counts WHERE target_id IN ({id_ph})", target_ids)
            conn.execute(f"DELETE FROM followers_followings WHERE target_id IN ({id_ph})", target_ids)
            conn.execute(f"DELETE FROM run_history WHERE target_id IN ({id_ph})", target_ids)
            conn.execute(f"DELETE FROM targets WHERE id IN ({id_ph})", target_ids)
        return result
    finally:
        conn.close()


def integrity_check(dest_path: Path) -> dict:
    if not dest_path.exists():
        raise FileNotFoundError(f"Destination DB not found: {dest_path}")
    conn = sqlite3.connect(str(dest_path))
    try:
        quick = conn.execute("PRAGMA quick_check(1);").fetchone()
        full = conn.execute("PRAGMA integrity_check(1);").fetchone()
    finally:
        conn.close()
    quick_result = (quick[0] if quick and quick[0] else "").strip().lower()
    full_result = (full[0] if full and full[0] else "").strip().lower()
    return {
        "quick_check": quick_result or "unknown",
        "integrity_check": full_result or "unknown",
        "ok": quick_result == "ok" and full_result == "ok",
    }


def vacuum_db(dest_path: Path) -> dict:
    if not dest_path.exists():
        raise FileNotFoundError(f"Destination DB not found: {dest_path}")
    before_size = dest_path.stat().st_size
    conn = sqlite3.connect(str(dest_path))
    try:
        conn.execute("VACUUM;")
        conn.execute("ANALYZE;")
        conn.commit()
    finally:
        conn.close()
    after_size = dest_path.stat().st_size
    return {
        "before_size": before_size,
        "after_size": after_size,
        "saved_bytes": before_size - after_size,
    }


def merge_db(dest_path: Path, src_path: Path, backup: bool) -> dict:
    if not dest_path.exists():
        raise FileNotFoundError(f"Destination DB not found: {dest_path}")
    if not src_path.exists():
        raise FileNotFoundError(f"Source DB not found: {src_path}")

    backup_path = None
    if backup:
        backup_path = dest_path.with_name(
            f"{dest_path.stem}.bak_{_timestamp()}{dest_path.suffix}"
        )
        shutil.copy2(dest_path, backup_path)

    counts = {
        "targets": 0,
        "run_history": 0,
        "followers_followings_inserted": 0,
        "followers_followings_updated": 0,
        "counts": 0,
        "change_logs": 0,
    }

    conn = sqlite3.connect(str(dest_path))
    try:
        conn.execute("ATTACH DATABASE ? AS srcdb", (str(src_path),))
        with conn:
            counts["targets"] = _run(
                conn,
                """
                INSERT OR IGNORE INTO targets (username)
                SELECT username FROM srcdb.targets
                """,
            )

            counts["run_history"] = _run(
                conn,
                """
                INSERT INTO run_history
                    (target_id, run_started_at, run_finished_at, status, followers_collected, followings_collected)
                SELECT t.id, r.run_started_at, r.run_finished_at, r.status, r.followers_collected, r.followings_collected
                FROM srcdb.run_history r
                JOIN srcdb.targets st ON st.id = r.target_id
                JOIN targets t ON t.username = st.username
                WHERE NOT EXISTS (
                    SELECT 1 FROM run_history r2
                    WHERE r2.target_id = t.id AND r2.run_started_at = r.run_started_at
                )
                """,
            )

            src_rows = conn.execute(
                """
                SELECT
                    st.username AS target_username,
                    ff.follower_following_username,
                    ff.is_follower,
                    MIN(ff.added_at) AS min_added_at,
                    MIN(ff.first_seen_run_at) AS min_first_seen_run_at,
                    MAX(ff.last_seen_run_at) AS max_last_seen_run_at,
                    MAX(ff.lost_at) AS max_lost_at,
                    MAX(ff.lost_at_run_at) AS max_lost_at_run_at,
                    MIN(ff.estimated_added_at) AS min_estimated_added_at,
                    MAX(ff.estimated_removed_at) AS max_estimated_removed_at,
                    MIN(ff.is_lost) AS min_is_lost
                FROM srcdb.followers_followings ff
                JOIN srcdb.targets st ON st.id = ff.target_id
                GROUP BY st.username, ff.follower_following_username, ff.is_follower
                """
            ).fetchall()

            for row in src_rows:
                (
                    target_username,
                    follower_username,
                    is_follower,
                    min_added_at,
                    min_first_seen,
                    max_last_seen,
                    max_lost_at,
                    max_lost_run,
                    min_est_added,
                    max_est_removed,
                    min_is_lost,
                ) = row

                dest_target = conn.execute(
                    "SELECT id FROM targets WHERE username = ?",
                    (target_username,),
                ).fetchone()
                if dest_target is None:
                    conn.execute(
                        "INSERT INTO targets (username) VALUES (?)",
                        (target_username,),
                    )
                    dest_target_id = conn.execute(
                        "SELECT id FROM targets WHERE username = ?",
                        (target_username,),
                    ).fetchone()[0]
                else:
                    dest_target_id = dest_target[0]

                dest_row = conn.execute(
                    """
                    SELECT id, added_at, first_seen_run_at, last_seen_run_at,
                           lost_at, is_lost, lost_at_run_at, estimated_added_at, estimated_removed_at
                    FROM followers_followings
                    WHERE target_id = ? AND follower_following_username = ? AND is_follower = ?
                    ORDER BY COALESCE(first_seen_run_at, added_at) ASC
                    LIMIT 1
                    """,
                    (dest_target_id, follower_username, is_follower),
                ).fetchone()

                if dest_row:
                    (
                        row_id,
                        dest_added,
                        dest_first_seen,
                        dest_last_seen,
                        dest_lost_at,
                        dest_is_lost,
                        dest_lost_run,
                        dest_est_added,
                        dest_est_removed,
                    ) = dest_row

                    merged_is_lost = _merge_is_lost(dest_is_lost, min_is_lost)
                    merged_added = _pick_min_dt(dest_added, min_added_at)
                    merged_first_seen = _pick_min_dt(dest_first_seen, min_first_seen)
                    merged_last_seen = _pick_max_dt(dest_last_seen, max_last_seen)
                    merged_est_added = _pick_min_dt(dest_est_added, min_est_added)

                    if merged_is_lost == 0:
                        merged_lost_at = None
                        merged_lost_run = None
                        merged_est_removed = None
                    else:
                        merged_lost_at = _pick_max_dt(dest_lost_at, max_lost_at)
                        merged_lost_run = _pick_max_dt(dest_lost_run, max_lost_run)
                        merged_est_removed = _pick_max_dt(dest_est_removed, max_est_removed)

                    conn.execute(
                        """
                        UPDATE followers_followings
                        SET added_at = ?,
                            first_seen_run_at = ?,
                            last_seen_run_at = ?,
                            lost_at = ?,
                            is_lost = ?,
                            lost_at_run_at = ?,
                            estimated_added_at = ?,
                            estimated_removed_at = ?
                        WHERE id = ?
                        """,
                        (
                            merged_added,
                            merged_first_seen,
                            merged_last_seen,
                            merged_lost_at,
                            merged_is_lost,
                            merged_lost_run,
                            merged_est_added,
                            merged_est_removed,
                            row_id,
                        ),
                    )
                    counts["followers_followings_updated"] += 1
                else:
                    insert_is_lost = 1 if min_is_lost else 0
                    insert_lost_at = max_lost_at if insert_is_lost else None
                    insert_lost_run = max_lost_run if insert_is_lost else None
                    insert_est_removed = max_est_removed if insert_is_lost else None
                    conn.execute(
                        """
                        INSERT INTO followers_followings
                            (target_id, follower_following_username, is_follower, added_at, lost_at, is_lost,
                             first_seen_run_at, last_seen_run_at, lost_at_run_at, estimated_added_at, estimated_removed_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            dest_target_id,
                            follower_username,
                            is_follower,
                            min_added_at,
                            insert_lost_at,
                            insert_is_lost,
                            min_first_seen,
                            max_last_seen,
                            insert_lost_run,
                            min_est_added,
                            insert_est_removed,
                        ),
                    )
                    counts["followers_followings_inserted"] += 1

            counts["counts"] = _run(
                conn,
                """
                INSERT INTO counts (target_id, count_type, count, timestamp, run_id)
                SELECT t.id, c.count_type, c.count, c.timestamp, rdest.id
                FROM srcdb.counts c
                JOIN srcdb.targets st ON st.id = c.target_id
                JOIN targets t ON t.username = st.username
                LEFT JOIN srcdb.run_history rsrc ON rsrc.id = c.run_id
                LEFT JOIN run_history rdest ON rdest.target_id = t.id AND rdest.run_started_at = rsrc.run_started_at
                WHERE NOT EXISTS (
                    SELECT 1 FROM counts c2
                    WHERE c2.target_id = t.id
                      AND c2.count_type = c.count_type
                      AND c2.timestamp = c.timestamp
                )
                """,
            )

            counts["change_logs"] = _run(
                conn,
                """
                INSERT INTO change_logs (timestamp, change_type, username)
                SELECT c.timestamp, c.change_type, c.username
                FROM srcdb.change_logs c
                WHERE NOT EXISTS (
                    SELECT 1 FROM change_logs c2
                    WHERE c2.timestamp = c.timestamp
                      AND c2.change_type = c.change_type
                      AND c2.username = c.username
                )
                """,
            )
        conn.execute("DETACH DATABASE srcdb")
    finally:
        conn.close()

    counts["backup_path"] = str(backup_path) if backup_path else None
    return counts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export or merge Instagram tracker databases")
    sub = parser.add_subparsers(dest="command", required=True)

    p_export = sub.add_parser("export", help="Export the local DB to a file")
    p_export.add_argument("--src", default=DEFAULT_DB, help="Source DB path")
    p_export.add_argument("--out", help="Output DB path (default: exports/instagram_tracker_YYYYmmdd_HHMMSS.db)")
    p_export.add_argument("--overwrite", action="store_true", help="Overwrite if output exists")

    p_merge = sub.add_parser("merge", help="Merge another DB into the local DB")
    p_merge.add_argument("--src", required=True, help="Source DB path to merge")
    p_merge.add_argument("--dest", default=DEFAULT_DB, help="Destination DB path (default: instagram_tracker.db)")
    p_merge.add_argument("--no-backup", action="store_true", help="Do not create a backup of destination DB")

    p_preview = sub.add_parser("preview-merge", help="Preview merge results without writing")
    p_preview.add_argument("--src", required=True, help="Source DB path to merge")
    p_preview.add_argument("--dest", default=DEFAULT_DB, help="Destination DB path (default: instagram_tracker.db)")

    p_cleanup = sub.add_parser("cleanup-targets", help="Preview or remove unwanted targets and related rows")
    p_cleanup.add_argument("--dest", default=DEFAULT_DB, help="Destination DB path (default: instagram_tracker.db)")
    p_cleanup.add_argument(
        "--usernames",
        nargs="+",
        default=["followers", "following"],
        help="Target usernames to clean up (default: followers following)",
    )
    p_cleanup.add_argument("--apply", action="store_true", help="Apply deletion (default is preview only)")
    p_cleanup.add_argument("--no-backup", action="store_true", help="Do not create backup when applying deletions")

    p_integrity = sub.add_parser("integrity-check", help="Run SQLite quick_check + integrity_check")
    p_integrity.add_argument("--dest", default=DEFAULT_DB, help="Destination DB path (default: instagram_tracker.db)")

    p_vacuum = sub.add_parser("vacuum", help="Run SQLite VACUUM + ANALYZE")
    p_vacuum.add_argument("--dest", default=DEFAULT_DB, help="Destination DB path (default: instagram_tracker.db)")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "export":
        out_path = Path(args.out) if args.out else None
        exported = export_db(Path(args.src), out_path, args.overwrite)
        print(f"Exported DB to {exported}")
        return

    if args.command == "merge":
        counts = merge_db(Path(args.dest), Path(args.src), backup=not args.no_backup)
        if counts["backup_path"]:
            print(f"Backup created: {counts['backup_path']}")
        print("Merge completed.")
        print(
            "Inserted rows -> "
            f"targets: {counts['targets']}, "
            f"run_history: {counts['run_history']}, "
            f"followers_followings: {counts['followers_followings_inserted']}, "
            f"counts: {counts['counts']}, "
            f"change_logs: {counts['change_logs']}"
        )
        print(
            "Updated rows -> "
            f"followers_followings: {counts['followers_followings_updated']}"
        )
        return

    if args.command == "preview-merge":
        preview = preview_merge(Path(args.dest), Path(args.src))
        print("Merge preview (no changes applied):")
        print(f"- targets to insert: {preview['new_targets']}")
        print(f"- run_history rows to insert: {preview['new_run_history']}")
        print(f"- followers_followings rows to insert: {preview['followers_followings_insert']}")
        print(f"- followers_followings rows to update: {preview['followers_followings_update']}")
        print(f"- counts rows to insert: {preview['new_counts']}")
        print(f"- change_logs rows to insert: {preview['new_change_logs']}")
        return

    if args.command == "cleanup-targets":
        result = cleanup_targets(
            Path(args.dest),
            args.usernames,
            apply=args.apply,
            backup=not args.no_backup,
        )
        if not result["matched_targets"]:
            print("No matching targets found.")
            return
        mode = "Applied" if result["applied"] else "Preview"
        print(f"{mode} cleanup for targets: {', '.join(result['matched_targets'])}")
        print(
            f"- target rows: {result['targets_rows']}\n"
            f"- run_history rows: {result['run_history_rows']}\n"
            f"- followers_followings rows: {result['followers_followings_rows']}\n"
            f"- counts rows: {result['counts_rows']}"
        )
        if result["backup_path"]:
            print(f"Backup created: {result['backup_path']}")
        if not result["applied"]:
            print("No changes applied. Re-run with --apply to execute deletion.")
        return

    if args.command == "integrity-check":
        result = integrity_check(Path(args.dest))
        print(f"quick_check: {result['quick_check']}")
        print(f"integrity_check: {result['integrity_check']}")
        print(f"status: {'ok' if result['ok'] else 'not_ok'}")
        return

    if args.command == "vacuum":
        result = vacuum_db(Path(args.dest))
        print(f"VACUUM completed for: {args.dest}")
        print(f"Size before: {result['before_size']} bytes")
        print(f"Size after: {result['after_size']} bytes")
        print(f"Saved: {result['saved_bytes']} bytes")
        return


if __name__ == "__main__":
    main()
