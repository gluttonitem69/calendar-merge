#!/usr/bin/env python3
"""
merge_calendars.py
Reads calendar URLs from urls.txt (one per line), merges all VEVENTs,
writes combined.ics, then commits+pushes to the git repo in this folder
(which should be connected to a GitHub Pages repo).
"""
import sys, os, subprocess, datetime, pytz, requests
from icalendar import Calendar, Event

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
URLS_FILE = os.path.join(BASE_DIR, "urls.txt")
OUTPUT_FILE = os.path.join(BASE_DIR, "combined.ics")
LOG_FILE = os.path.join(BASE_DIR, "merge.log")

def log(msg):
    with open(LOG_FILE, "a") as f:
        f.write(f"{datetime.datetime.now()} - {msg}\n")

def main():
    today = datetime.datetime.utcnow().replace(tzinfo=pytz.utc).date()

    if not os.path.exists(URLS_FILE):
        log("ERROR: urls.txt not found")
        sys.exit(1)

    urls = [u.strip() for u in open(URLS_FILE).readlines() if u.strip() and not u.startswith("#")]

    combined_cal = Calendar()
    combined_cal.add('prodid', '-//merged-calendar//combine//EN')
    combined_cal.add('version', '2.0')
    combined_cal.add('x-wr-calname', 'My Combined Calendar')

    seen_uids = set()
    ok_count, fail_count = 0, 0

    for url in urls:
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            cal = Calendar.from_ical(resp.text)
            for event in cal.walk("VEVENT"):
                uid = str(event.get('uid', ''))
                end = event.get('dtend')
                is_future = True
                if end:
                    date = end.dt.date() if hasattr(end.dt, 'date') else end.dt
                    is_future = (date >= today) or ('RRULE' in event)
                if is_future and (uid == '' or uid not in seen_uids):
                    if uid:
                        seen_uids.add(uid)
                    copied = Event()
                    for attr in event:
                        val = event[attr]
                        if isinstance(val, list):
                            for element in val:
                                copied.add(attr, element)
                        else:
                            copied.add(attr, val)
                    combined_cal.add_component(copied)
            ok_count += 1
        except Exception as e:
            fail_count += 1
            log(f"FAILED fetching {url}: {e}")

    with open(OUTPUT_FILE, "wb") as f:
        f.write(combined_cal.to_ical())

    log(f"Merge complete. {ok_count} feeds ok, {fail_count} failed.")

    try:
        subprocess.run(["git", "add", "combined.ics", "merge.log"], cwd=BASE_DIR, check=True)
        subprocess.run(["git", "commit", "-m", "Auto-update merged calendar"], cwd=BASE_DIR, check=False)
        subprocess.run(["git", "push"], cwd=BASE_DIR, check=True)
        log("Pushed to GitHub Pages successfully.")
    except Exception as e:
        log(f"GIT PUSH FAILED: {e}")

if __name__ == "__main__":
    main()
