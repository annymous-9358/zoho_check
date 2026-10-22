#!/usr/bin/env python3
"""Zoho People check-in / check-out via the attendance API.

Usage:  python zoho_attendance.py checkin|checkout|check [--dry-run]

"check" is read-only: it verifies your credentials and API access without marking attendance.

Environment variables:
  ZOHO_CLIENT_ID, ZOHO_CLIENT_SECRET, ZOHO_REFRESH_TOKEN   OAuth credentials (required)
  ZOHO_EMP_ID        Employee ID, or ZOHO_EMAIL for the email address (one required)
  ZOHO_DC            Data centre domain suffix: com (default), eu, in, com.au, jp, zohocloud.ca
  ZOHO_TIMEZONE      IANA timezone used for the timestamp (default Asia/Kolkata)
  SKIP_WEEKENDS      "true" (default) to do nothing on Sat/Sun
  SKIP_DATES         Comma-separated YYYY-MM-DD holidays to skip
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

DATE_FORMAT = "dd-MM-yyyy HH:mm:ss"
PY_FORMAT = "%d-%m-%Y %H:%M:%S"


def env(name, default=None, required=False):
    value = os.environ.get(name, default)
    if required and not value:
        sys.exit(f"Missing required environment variable: {name}")
    return value


def post(url, params):
    req = urllib.request.Request(url + "?" + urllib.parse.urlencode(params), method="POST")
    return req


def request_json(req):
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code} from {req.full_url.split('?')[0]}: {e.read().decode()[:500]}")


def get_access_token(dc):
    req = post(f"https://accounts.zoho.{dc}/oauth/v2/token", {
        "refresh_token": env("ZOHO_REFRESH_TOKEN", required=True),
        "client_id": env("ZOHO_CLIENT_ID", required=True),
        "client_secret": env("ZOHO_CLIENT_SECRET", required=True),
        "grant_type": "refresh_token",
    })
    data = request_json(req)
    if "access_token" not in data:
        sys.exit(f"Token refresh failed: {data}")
    return data["access_token"]


def check_access(dc):
    """Read-only diagnosis: token refresh, then a harmless attendance read."""
    print("1/2 Refreshing access token ...")
    token = get_access_token(dc)
    print("    OK: client ID, secret and refresh token are valid.")

    print("2/2 Calling the attendance API (read-only) ...")
    now = datetime.now(ZoneInfo(env("ZOHO_TIMEZONE", "Asia/Kolkata")))
    params = {"date": now.strftime("%d-%m-%Y"), "dateFormat": "dd-MM-yyyy"}
    if env("ZOHO_EMP_ID"):
        params["empId"] = env("ZOHO_EMP_ID")
    else:
        params["emailId"] = env("ZOHO_EMAIL", required=True)
    url = f"https://people.zoho.{dc}/people/api/attendance/getAttendanceEntries"
    req = urllib.request.Request(url + "?" + urllib.parse.urlencode(params))
    req.add_header("Authorization", f"Zoho-oauthtoken {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode()
        print("    OK: your role CAN access the attendance API.")
        print(body[:500])
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"    FAILED: HTTP {e.code}: {body[:500]}")
        if "7077" in body:
            print("    -> Your Zoho People role is not allowed to use APIs. Ask your admin to enable API access.")
        elif e.code in (401, 403):
            print("    -> Permission/scope problem: check the token scope (ZOHOPEOPLE.attendance.ALL) and role.")
        else:
            print("    -> Check ZOHO_EMP_ID, ZOHO_DC and the request details above.")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("action", choices=["checkin", "checkout", "check"])
    parser.add_argument("--dry-run", action="store_true", help="print what would be sent")
    args = parser.parse_args()

    dc = env("ZOHO_DC", "com")
    if args.action == "check":
        check_access(dc)
        return
    now = datetime.now(ZoneInfo(env("ZOHO_TIMEZONE", "Asia/Kolkata")))

    skip_dates = {d.strip() for d in env("SKIP_DATES", "").split(",") if d.strip()}
    if env("SKIP_WEEKENDS", "true").lower() == "true" and now.weekday() >= 5:
        print(f"{now:%A}: weekend, skipping.")
        return
    if now.strftime("%Y-%m-%d") in skip_dates:
        print(f"{now:%Y-%m-%d} is in SKIP_DATES, skipping.")
        return

    params = {"dateFormat": DATE_FORMAT}
    params["checkIn" if args.action == "checkin" else "checkOut"] = now.strftime(PY_FORMAT)
    if env("ZOHO_EMP_ID"):
        params["empId"] = env("ZOHO_EMP_ID")
    else:
        params["emailId"] = env("ZOHO_EMAIL", required=True)

    url = f"https://people.zoho.{dc}/people/api/attendance"
    if args.dry_run:
        print("POST", url, params)
        return

    req = post(url, params)
    req.add_header("Authorization", f"Zoho-oauthtoken {get_access_token(dc)}")
    result = request_json(req)
    print(json.dumps(result, indent=2))
    # Zoho returns HTTP 200 even for logical errors; they show up in response.status.
    if result.get("response", {}).get("status") not in (0, "0", None):
        sys.exit(1)


if __name__ == "__main__":
    main()
