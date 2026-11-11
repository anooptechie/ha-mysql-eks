#!/usr/bin/env python3
"""Compare the ack log with the database: lost writes, unacked rows, gaps, duplicate acks."""
import argparse
import os
import re
import sys

import pymysql

HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
PORT = int(os.getenv("MYSQL_PORT", "3306"))
USER = os.getenv("MYSQL_USER", "writer")
PASSWORD = os.environ["MYSQL_WRITER_PASSWORD"]
DB = os.getenv("MYSQL_DB", "chaos")


def load_acks(path):
    seen, dups = set(), []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            seq = int(line.split(",")[0])
            if seq in seen:
                dups.append(seq)
            seen.add(seq)
    return seen, dups


def load_db_seqs():
    conn = pymysql.connect(
        host=HOST, port=PORT, user=USER, password=PASSWORD, database=DB,
        connect_timeout=10, read_timeout=60,
    )
    seqs = set()
    with conn.cursor(pymysql.cursors.SSCursor) as cur:
        cur.execute("SELECT seq FROM writes")
        for (seq,) in cur:
            seqs.add(seq)
    conn.close()
    return seqs


def load_downtimes(path):
    if not os.path.exists(path):
        return []
    values = []
    with open(path) as fh:
        for line in fh:
            m = re.search(r"RECOVERED .*\bdowntime_s=([0-9.]+)", line)
            if m:
                values.append(float(m.group(1)))
    return values


def compress(nums):
    """[1,2,3,7,9,10] -> '1-3, 7, 9-10'"""
    nums = sorted(nums)
    spans, start, prev = [], None, None
    for n in nums:
        if start is None:
            start = prev = n
        elif n == prev + 1:
            prev = n
        else:
            spans.append((start, prev))
            start = prev = n
    if start is not None:
        spans.append((start, prev))
    return ", ".join(str(a) if a == b else f"{a}-{b}" for a, b in spans) or "none"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ack-log", default="runs/ack.log")
    parser.add_argument("--event-log", default="runs/events.log")
    args = parser.parse_args()

    acked, dup_acks = load_acks(args.ack_log)
    in_db = load_db_seqs()
    downtimes = load_downtimes(args.event_log)

    lost = acked - in_db
    unacked = in_db - acked
    everything = acked | in_db
    gaps = (
        set(range(min(everything), max(everything) + 1)) - everything
        if everything else set()
    )

    print(f"acked in log      : {len(acked)}")
    print(f"rows in database  : {len(in_db)}")
    print(f"LOST (acked, missing from DB): {len(lost)}  [{compress(lost)}]")
    print(f"unacked rows (in DB, never acked): {len(unacked)}  [{compress(unacked)}]")
    print(f"gaps (in neither) : {len(gaps)}  [{compress(gaps)}]")
    print(f"duplicate acks    : {len(dup_acks)}  [{compress(set(dup_acks))}]")
    if downtimes:
        print(f"failure windows   : {len(downtimes)}  downtime_s={downtimes}")

    ok = not lost and not dup_acks
    print("RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
