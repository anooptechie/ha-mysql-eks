#!/usr/bin/env python3
"""Continuously insert rows; log every ACKNOWLEDGED seq; record failure windows."""
import os
import signal
import time
from datetime import datetime, timezone

import pymysql

HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
PORT = int(os.getenv("MYSQL_PORT", "3306"))
USER = os.getenv("MYSQL_USER", "writer")
PASSWORD = os.environ["MYSQL_WRITER_PASSWORD"]
DB = os.getenv("MYSQL_DB", "chaos")
WRITER_ID = os.getenv("WRITER_ID", "w1")
INTERVAL = float(os.getenv("WRITE_INTERVAL", "0.1"))
ACK_LOG = os.getenv("ACK_LOG", "runs/ack.log")
EVENT_LOG = os.getenv("EVENT_LOG", "runs/events.log")

stop = False


def handle_stop(signum, frame):
    global stop
    stop = True


def connect():
    return pymysql.connect(
        host=HOST, port=PORT, user=USER, password=PASSWORD, database=DB,
        autocommit=True,  # one row = one commit
        connect_timeout=2, read_timeout=2, write_timeout=2,
    )


def log_event(fh, msg):
    line = f"{datetime.now(timezone.utc).isoformat(timespec='milliseconds')} {msg}"
    print(line, flush=True)
    fh.write(line + "\n")


def main():
    signal.signal(signal.SIGINT, handle_stop)
    signal.signal(signal.SIGTERM, handle_stop)
    os.makedirs(os.path.dirname(ACK_LOG) or ".", exist_ok=True)
    ack = open(ACK_LOG, "a", buffering=1)
    ev = open(EVENT_LOG, "a", buffering=1)

    conn = connect()  # first connection must succeed
    with conn.cursor() as cur:
        cur.execute("SELECT COALESCE(MAX(seq), 0) FROM writes")
        seq = cur.fetchone()[0] + 1
    log_event(ev, f"START writer={WRITER_ID} first_seq={seq}")

    acked = failures = 0
    last_ok = time.time()
    fail_start = None
    max_down = 0.0
    backoff = 0.1

    while not stop:
        try:
            if conn is None:
                conn = connect()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO writes (seq, writer_id) VALUES (%s, %s)",
                        (seq, WRITER_ID),
                    )
            except pymysql.err.IntegrityError as e:
                # 1062 = duplicate key: an earlier attempt DID commit but its
                # reply was lost. The row exists, so count it as acknowledged.
                if e.args[0] != 1062:
                    raise
            now = time.time()
            ack.write(f"{seq},{now:.6f}\n")  # logged only AFTER the DB confirmed
            acked += 1
            if fail_start is not None:
                down = now - last_ok  # last good write -> first good write after
                max_down = max(max_down, down)
                log_event(ev, f"RECOVERED seq={seq} downtime_s={down:.3f}")
                fail_start = None
                backoff = 0.1
            last_ok = now
            seq += 1
            if acked % 100 == 0:
                print(f"acked={acked} last_seq={seq - 1}", flush=True)
            time.sleep(INTERVAL)
        except (pymysql.MySQLError, OSError) as e:
            if fail_start is None:
                fail_start = time.time()
                failures += 1
                log_event(ev, f"FAIL_START seq={seq} err={type(e).__name__}: {e}")
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
                conn = None
            time.sleep(backoff)
            backoff = min(backoff * 2, 0.5)

    log_event(ev, f"STOP acked={acked} failure_windows={failures} max_downtime_s={max_down:.3f}")


if __name__ == "__main__":
    main()
