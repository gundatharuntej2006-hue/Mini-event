"""
Create the event-day staff accounts over the API.

Render's Shell is a paid feature, so `python cli.py create-user` is not
reachable on a free instance. This does the same job from your own machine
against the deployed API: it signs in as the organiser and posts to
/auth/register, which is organiser-only and accepts a role.

    python scripts/create_staff.py --api https://event-hq-api.onrender.com \
                                   --email you@bmsit.in

It prompts for the organiser password without echoing, generates a strong
password per account, and prints the credentials ONCE at the end. Save that
output somewhere before closing the terminal — the passwords are hashed on
the server and cannot be read back.

Re-running is safe: an account that already exists is reported and skipped,
not duplicated or overwritten.

The roster below comes from the event structure, not from guesswork:
three Round 1 gates each need a marshal to log timings and rule violations;
the Black Market desk needs one, because ODDyssey requires two organiser
signatures per transaction and the second cannot be the person recording it;
Round 4 runs four simultaneous pairings, so four judges; and the hall screen
needs a read-only projector account.
"""

import argparse
import getpass
import secrets
import sys
import urllib.error
import urllib.request
import json

ROSTER = [
    ("gate1@bmsit.in",   "Gate 1 Marshal",     "MARSHAL"),
    ("gate2@bmsit.in",   "Gate 2 Marshal",     "MARSHAL"),
    ("gate3@bmsit.in",   "Gate 3 Marshal",     "MARSHAL"),
    ("market@bmsit.in",  "Black Market Desk",  "MARSHAL"),
    ("judge1@bmsit.in",  "Courtroom 1 Judge",  "JUDGE"),
    ("judge2@bmsit.in",  "Courtroom 2 Judge",  "JUDGE"),
    ("judge3@bmsit.in",  "Courtroom 3 Judge",  "JUDGE"),
    ("judge4@bmsit.in",  "Courtroom 4 Judge",  "JUDGE"),
    ("screen@bmsit.in",  "Hall Projector",     "PUBLIC_PROJECTOR"),
]


def post(url, payload, token=None):
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {"message": e.reason}
    except urllib.error.URLError as e:
        raise SystemExit(f"Could not reach {url}: {e.reason}")


def main():
    ap = argparse.ArgumentParser(description="Create EVENT HQ staff accounts over the API.")
    ap.add_argument("--api", required=True, help="e.g. https://event-hq-api.onrender.com")
    ap.add_argument("--email", required=True, help="the organiser account's email")
    ap.add_argument("--domain", default="bmsit.in",
                    help="replace the roster's email domain (default: bmsit.in)")
    args = ap.parse_args()

    base = args.api.rstrip("/") + "/api/v1"
    password = getpass.getpass("Organiser password: ")

    # A free instance spins down when idle, so the first request can take the
    # better part of a minute to wake it. That is not a failure.
    print("\nSigning in (a sleeping free instance can take ~50s to wake)...")
    status, body = post(f"{base}/auth/login", {"email": args.email, "password": password})
    if status != 200 or not body.get("success"):
        raise SystemExit(f"Login failed: {body.get('message', body)}")

    data = body.get("data") or {}
    token = data.get("access_token") or data.get("accessToken") or data.get("token")
    if not token:
        raise SystemExit(f"Signed in, but no token in the response: {list(data)}")
    print("Signed in.\n")

    created, skipped, failed = [], [], []
    for email, name, role in ROSTER:
        email = email.replace("bmsit.in", args.domain)
        pw = secrets.token_urlsafe(9)
        status, body = post(
            f"{base}/auth/register",
            {"email": email, "name": name, "password": pw, "role": role},
            token=token,
        )
        if status == 200 and body.get("success"):
            created.append((email, name, role, pw))
            print(f"  created  {role:17} {email}")
        elif "already exists" in str(body.get("message", "")).lower():
            skipped.append(email)
            print(f"  exists   {role:17} {email}")
        else:
            failed.append((email, body.get("message", body)))
            print(f"  FAILED   {role:17} {email}  — {body.get('message', body)}")

    if created:
        print("\n" + "=" * 68)
        print("SAVE THESE NOW — the passwords cannot be read back afterwards.")
        print("=" * 68)
        for email, name, role, pw in created:
            print(f"{role:17} {email:24} {pw}")
        print("=" * 68)

    print(f"\n{len(created)} created, {len(skipped)} already existed, {len(failed)} failed.")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
