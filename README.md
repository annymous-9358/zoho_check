# Zoho People auto check-in / check-out

`zoho_attendance.py` calls the Zoho People attendance API (`/people/api/attendance`) to check in or out. A GitHub Actions workflow runs it on a schedule.

## 1. Get OAuth credentials (one time)

1. Open the Zoho API Console for your data centre (e.g. https://api-console.zoho.com) → **Add Client** → **Self Client**.
2. Copy the **Client ID** and **Client Secret**.
3. In **Generate Code**, use scope `ZOHOPEOPLE.attendance.ALL`, duration 10 minutes, then **Create** and copy the code.
4. Exchange it for a refresh token (the code expires fast; do this immediately):
   ```
   curl -X POST "https://accounts.zoho.com/oauth/v2/token" \
     -d grant_type=authorization_code -d client_id=CLIENT_ID \
     -d client_secret=CLIENT_SECRET -d code=CODE
   ```
   Save the `refresh_token` from the response. It does not expire; the script uses it to get a fresh access token on every run.

Replace `.com` with `.eu`, `.in`, `.com.au`, `.jp` etc. if your account is in another data centre, and set `ZOHO_DC` to match.

## 2. Configure GitHub

Repo → Settings → Secrets and variables → Actions:

| Type | Name | Value |
|---|---|---|
| Secret | `ZOHO_CLIENT_ID`, `ZOHO_CLIENT_SECRET`, `ZOHO_REFRESH_TOKEN` | from step 1 |
| Secret | `ZOHO_EMP_ID` | your Zoho People employee ID |
| Variable | `ZOHO_DC` | `com` (default), `eu`, `in`, ... |
| Variable | `ZOHO_TIMEZONE` | e.g. `Asia/Kolkata` (default) |
| Variable | `SKIP_DATES` | optional, e.g. `2026-12-25,2026-01-26` |

Edit the cron times in `.github/workflows/attendance.yml` (they are UTC). GitHub may delay scheduled runs by several minutes, and disables scheduled workflows after 60 days without repo activity.

## 3. Test

```
ZOHO_EMP_ID=... python zoho_attendance.py checkin --dry-run      # prints the request only
```
Then trigger **Actions → Zoho attendance → Run workflow** to do a real check-in.

## Notes

- Timestamps are sent in `ZOHO_TIMEZONE`; it must match your Zoho People timezone.
- Weekends are skipped by default (`SKIP_WEEKENDS=false` to disable).
- Check your employer's policy permits automated attendance before using this.
