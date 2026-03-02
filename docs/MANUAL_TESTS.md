# Manual Validation Scenarios

## Clickable Instagram Usernames

### Web dashboard

1. Open the dashboard from desktop and mobile.
2. Go to `Selected Day New` and tap/click a username.
   - Expected: opens `https://www.instagram.com/<username>/`.
3. Go to `Selected Day Lost` and tap/click a username.
   - Expected: opens `https://www.instagram.com/<username>/`.
4. Go to `Current Snapshot` and tap/click a username.
   - Expected: opens `https://www.instagram.com/<username>/`.
5. Select a target and click `Open target profile`.
   - Expected: opens the selected target profile URL.
6. Set target to `(all)`.
   - Expected: `Open target profile` button is disabled.

### GUI desktop

1. Open GUI and load `Daily compare`.
2. Select a day with results.
3. In `New on selected day`, double-click a row.
   - Expected: opens profile URL in browser/app.
4. In `Lost on selected day`, double-click a row.
   - Expected: opens profile URL in browser/app.
5. Double-click with no valid row selected.
   - Expected: no crash, status message explains what to do.

### Regression checks

1. Run `python report.py --help`.
2. Run `python db_tools.py --help`.
3. Open web dashboard and verify API data still loads.
