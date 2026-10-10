# -*- coding: utf-8 -*-
"""
Nightly deemed-approval job.

Under the Purvanchal Right to Public Services Act, an application not processed
within the statutory SLA stands approved. This job marks such applications
DEEMED_APPROVED and notifies the applicant by SMS.

Scheduled hourly via cron. The scheduler entrypoint also runs this once at
startup so old pending applications are caught up immediately.
"""

import os
import sys
import argparse
import configparser
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import psycopg2
import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

config = configparser.ConfigParser()
CONFIG_PATH = os.path.join(BASE_DIR, "config", "app.ini")
if not os.path.exists(CONFIG_PATH):
    legacy_path = os.path.join(BASE_DIR, "config", "settings.ini")
    if os.path.exists(legacy_path):
        CONFIG_PATH = legacy_path

with open(CONFIG_PATH) as fh:
    config.read_file(fh)

SLA_DAYS = config.getint("pension", "sla_days")
SMS_GATEWAY_URL = config.get("app", "sms_gateway_url")
IST = ZoneInfo("Asia/Kolkata")


def now_ist():
    return datetime.now(IST).replace(tzinfo=None)


def run_deemed_approval(dry_run=False):
    conn = psycopg2.connect(
        host=config.get("database", "host"),
        port=config.get("database", "port"),
        dbname=config.get("database", "name"),
        user=config.get("database", "user"),
        password=os.environ["SEWASETU_DB_PASSWORD"],
    )
    cur = conn.cursor()
    run_time = now_ist()
    cutoff = run_time - timedelta(days=SLA_DAYS)
    cur.execute(
        """CREATE TABLE IF NOT EXISTS job_runs (
               id BIGSERIAL PRIMARY KEY,
               job_name VARCHAR(100) NOT NULL,
               started_at TIMESTAMP NOT NULL,
               completed_at TIMESTAMP,
               success BOOLEAN NOT NULL DEFAULT FALSE,
               approved_count INTEGER NOT NULL DEFAULT 0,
               error_message TEXT
           )"""
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS job_runs_name_started_idx "
        "ON job_runs (job_name, started_at DESC)"
    )
    conn.commit()
    cur.execute(
        """INSERT INTO job_runs (job_name, started_at)
           VALUES ('deemed_approval', %s) RETURNING id""",
        (run_time,))
    run_id = cur.fetchone()[0]
    conn.commit()

    try:
        if dry_run:
            cur.execute(
                """SELECT count(*), min(submitted_at), max(submitted_at)
                   FROM applications
                   WHERE status = 'PENDING' AND submitted_at < %s""",
                (cutoff,))
            row = cur.fetchone()
            count = row[0]
            min_sub = row[1]
            max_sub = row[2]
            cur.execute(
                "UPDATE job_runs SET completed_at = %s, success = TRUE, "
                "approved_count = %s WHERE id = %s",
                (now_ist(), count, run_id))
            conn.commit()
            print("DRY RUN: %d applications eligible for deemed approval." % count)
            if count > 0:
                print("Earliest submitted: %s, Latest eligible: %s" % (min_sub, max_sub))
                print("Decision dates will be back-dated to submitted_at + %d days." % SLA_DAYS)
            return count

        cur.execute(
            """UPDATE applications
               SET status = 'DEEMED_APPROVED',
                   decided_at = submitted_at + (%s || ' days')::interval,
                   decided_by = 'RTPS-AUTO'
               WHERE status = 'PENDING' AND submitted_at < %s
               RETURNING application_no, mobile, decided_at""",
            (SLA_DAYS, cutoff))
        rows = cur.fetchall()
        conn.commit()

        sms_success = 0
        sms_failed = 0
        for app_no, mobile, decided_at in rows:
            try:
                resp = requests.post(
                    SMS_GATEWAY_URL + "/api/send",
                    json={
                        "to": mobile,
                        "text": "Sewa Setu: your pension application %s stands approved under the RTPS Act." % app_no,
                    },
                    timeout=5,
                )
                if resp.status_code in (200, 201):
                    sms_success += 1
                else:
                    sms_failed += 1
                    print("SMS notification gateway error for %s: %s" % (app_no, resp.status_code), file=sys.stderr)
            except requests.RequestException as exc:
                sms_failed += 1
                print("SMS notification failed for %s: %s" % (app_no, exc), file=sys.stderr)

        cur.execute(
            "UPDATE job_runs SET completed_at = %s, success = TRUE, "
            "approved_count = %s WHERE id = %s",
            (now_ist(), len(rows), run_id))
        conn.commit()
        print("%s deemed approval: %d applications approved (SMS sent: %d, failed: %d)"
              % (run_time.strftime("%Y-%m-%d %H:%M:%S"), len(rows), sms_success, sms_failed))
        return len(rows)
    except Exception as exc:
        conn.rollback()
        cur.execute(
            "UPDATE job_runs SET completed_at = %s, error_message = %s WHERE id = %s",
            (now_ist(), str(exc)[:1000], run_id))
        conn.commit()
        raise
    finally:
        cur.close()
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Nightly deemed-approval job")
    parser.add_argument("--dry-run", action="store_true", help="Report counts without updating database or sending SMS")
    args = parser.parse_args()

    try:
        run_deemed_approval(dry_run=args.dry_run)
    except Exception as exc:
        print("FATAL error in deemed_approval: %s" % exc, file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
