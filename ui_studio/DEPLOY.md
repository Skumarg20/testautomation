# Test Studio: deploying it for the QA team (server mode)

One machine runs the Studio. QAs open it in the browser, log in with their own Studio account, and run tests with
**their own MargBooks login**. Nothing needs to be installed on a QA's PC, except for recording (see 7).

## Quick deploy (5 steps)

On the server (Windows 10/11 or Server 2019+, Python 3.12, from an **Administrator** command prompt):

1. **Code:** `git clone <repo> D:\TestStudio` (or copy the folder), then `cd D:\TestStudio`.
2. **Install:** `deploy\install.bat`. It installs the exact tested libraries (`deploy\requirements-lock.txt`) and
   Chromium, the Python-scripts environment, asks the **first admin's e-mail** and password, opens the firewall port
   (8778) and installs the **TestStudio** Windows service if NSSM is present (`deploy\service.bat`), then runs the
   pre-flight check.
3. **App under test:** if the check says it is missing, run `studio.bat` once on the server, open
   Settings > App under test (MargBooks URL, login, company, *Allow tests that create or change data*), Save, close.
4. **Check:** `.venv\Scripts\python -m ui_studio.preflight` must say **READY** (0 fail). Fix each FAIL line it shows.
5. **Team:** open `http://<server>:8778`, log in with the admin e-mail, set your own MargBooks login in Settings,
   then Team > Users & access > **+ Add user** for every QA and send them the message it shows (a one-time
   *set your password* link). Open the Studio by the server's network address so the link has that address.

Every day: `deploy\backup.bat` (schedule it: `schtasks /create /tn "Test Studio backup" /sc daily /st 21:00 /tr
"D:\TestStudio\deploy\backup.bat"`). New version: `deploy\update.bat` (backup, `git pull`, libraries, unit tests,
restart, check; nothing goes live when a test fails).

## 1. What the server needs

| | |
|---|---|
| OS | Windows 10/11 or Windows Server 2019+ (MargBooks passwords are encrypted with Windows DPAPI) |
| Python | 3.12 (`python --version`) |
| RAM | 2 GB + about 600 MB for every browser that may run at the same time (`STUDIO_MAX_BROWSERS`, default 3) |
| Disk | 10 GB+ for run screenshots / videos / traces (old ones are deleted after `STUDIO_KEEP_RUN_DAYS`, default 30) |
| Network | The server must reach the MargBooks URLs; QAs must reach the server's port (default 8778) |

## 2. Install (once)

1. Copy this project folder to the server, e.g. `D:\TestStudio` (or `git clone`).
2. Run `setup.bat` (makes `.venv`, installs the libraries and Chromium).
3. Start the Studio once in local mode (`studio.bat`) on the server, open **Settings > App under test**, and set
   the MargBooks URL, the company and *Allow tests that create or change data*. Writes are only ever allowed inside
   the QA test companies (the QA-company guard checks every save, whatever the setting).
4. Make the first Studio admin:

   ```
   .venv\Scripts\python -m ui_studio.accounts add you@margerp.net --admin --name "Your Name"
   ```

   From a script or a remote shell (no console), pipe the password in: add `--password-stdin`. Other commands:
   `reset`, `role <email> admin|qa`, `name <email> "Full Name"`, `email <old> <new email>`, `disable`, `enable`, `list`.

## 3. Start the server

```
studio-server.bat
```

It listens on `0.0.0.0:8778` and refuses to start until an admin exists. Settings (environment variables, set them
before the .bat or in the service):

| Variable | Default | Meaning |
|---|---|---|
| `STUDIO_MODE` | `server` (set by the .bat) | `local` = the single-PC Studio |
| `STUDIO_HOST` | `0.0.0.0` | address to listen on. Use `127.0.0.1` when a reverse proxy (HTTPS) is in front |
| `STUDIO_PORT` | `8778` | port |
| `STUDIO_MAX_BROWSERS` | `3` | browsers running at the same time on this machine |
| `STUDIO_SECURE_COOKIE` | off | set `1` when QAs reach the Studio over **HTTPS** (recommended) |
| `STUDIO_KEEP_RUN_DAYS` | `30` | run folders older than this are deleted; `0` keeps them forever (a folder younger than a day, or of a run still going, is never deleted) |
| `STUDIO_DB` | `config\studio.db` | where users, sessions and run history are kept |

Health check for monitoring: `GET /healthz` or `HEAD /healthz` (no login) → `{"ok": true, "mode": "server",
"busy": n, "max_browsers": n, "running": n, "waiting": n}`. Only counts: no usernames or test names.

### Run it as a Windows service (keeps running after logoff, restarts on boot)

With NSSM (https://nssm.cc):

```
nssm install TestStudio D:\TestStudio\.venv\Scripts\python.exe -m ui_studio.server
nssm set TestStudio AppDirectory D:\TestStudio
nssm set TestStudio AppEnvironmentExtra STUDIO_MODE=server STUDIO_HOST=127.0.0.1 STUDIO_SECURE_COOKIE=1
nssm set TestStudio ObjectName .\studio-svc <password>
nssm start TestStudio
```

**Important:** run the service as ONE fixed Windows account (`studio-svc` above). Saved MargBooks passwords are
encrypted for that account; if the account changes, every QA must enter their MargBooks password again
(Settings > My MargBooks login).

### HTTPS

Put a reverse proxy in front (IIS + URL Rewrite/ARR, nginx or Caddy) with your certificate, forward to
`http://127.0.0.1:8778`, keep the `Host` header (or send `X-Forwarded-Host`), set `STUDIO_HOST=127.0.0.1` and
`STUDIO_SECURE_COOKIE=1`. Open only the proxy's port (443) in the firewall. Without HTTPS, passwords cross the
network in clear text: use plain HTTP only on a trusted internal network.

## 4. Users

* **Admin**: Team > *Users & access*: add a user (their **e-mail address** is their login; name, first password, role), change a login e-mail, reset a password,
  disable a user (logs them out at once). The last admin cannot be disabled or demoted.
  Command line: `python -m ui_studio.accounts list | add | reset | disable | enable`.
* **Every QA, once**: log in, open **Settings > My MargBooks login**, enter their own MargBooks user id and
  password. Runs use it, so two QAs never log each other out. The password is stored encrypted and never shown
  again. Change the Studio password in the same card.
* Roles: `qa` writes, records, runs and reads reports. `admin` also changes the shared settings (App under test,
  AI, recorder), runs Learn app / code reading / Python scripts, and manages users.
* 5 wrong passwords lock that login for 5 minutes. Sessions last 12 hours of inactivity.

## 5. How runs are scheduled

Each run is a separate process with the QA's own MargBooks login. A run waits (the Run screen says why) when:

* all `STUDIO_MAX_BROWSERS` browsers are busy;
* the same MargBooks login is already running a test (a second login of one user logs the first one out);
* another run is in the **same company** (tests change that company's settings and data).

Waiting runs start first come, first served: when a browser, login or company frees up, the run that has waited
longest for it goes first.

The run timer counts only the time a test has a browser; the wait is shown next to it. After the last step the Run
screen says "Saving the video and the bug pack" while the trace and video are written. A QA can stop their own
run (**■ Stop run** on the Run screen; an admin can stop any run): tests that have not started are not run, the
running test stops at its next step and its clean-up steps and setting undo still run (the run process gets a stop
signal; it is ended by force only if it has not finished 4 minutes later). After a reload the Run screen picks the
run up again.

`GET /api/queue` (logged in) shows what is running and what waits. A QA sees only their own live runs; reports of
all runs are shared with the team. Admins see everything.

## 5b. Feedback from the team

Every QA can report a problem from where it happened; the details are added for them:

| Where | Button | Added automatically |
|---|---|---|
| Any screen | **Feedback** in the left menu > *+ Give feedback* | name, screen, environment |
| Run screen (a test failed / was not run) | *Report a problem* | test, run, failed step, error |
| Reports > a run | *Report a problem* | test, run, failed step, error, result |
| Test cases > a case | *Report a problem with this test case* | test, title |
| Record > replay failed | *Report a problem* | script line, error, AI fix |
| Record > Verify suggestion | *Wrong suggestion?* | the suggestion and its lines |
| Write > a line marked ✗ | *Studio is wrong?* | the line, module |
| Settings > My MargBooks login / App under test | *Login not working?* | (never the password) |

Kinds: app bug, test case wrong, Studio/runner problem, test data/company setup, login/access, suggestion.
Known MargBooks passwords are replaced by `***` before it is saved.

* **Admin**: the **Feedback** screen lists everything (filter by status, kind, text; *Only mine*), opens the run,
  the bug pack or the test, and sets a status (Open, In progress, Fixed, Won't fix) with a reply. The menu shows a
  red count of open feedback.
* **QA**: the Feedback screen shows their own feedback with the admin's status and reply.
* A test with open feedback shows **⚠ known issue** in Test cases and Run, and the run/case shows the last report,
  so others do not report it again.
* Stored in `config\studio.db` (table `feedback`), included in the daily backup.

## 6. Backups

Back up daily: `config\studio.db` (users, run history), `testcases\`, `locators\`, `config\qa_data.json`,
`config\qa_baseline\`, `config\environments.json`. Run screenshots/videos (`artifacts\studio\`) are optional.

## 7. Recording a test

The server's browser window is not on the QA's screen, so in server mode **Record** shows *Paste recorded code*:

1. On the QA's PC (Python + `setup.bat` once): `record.bat <URL>`, with the URL the Record screen shows (the app
   URL of the environment the Studio tests, Settings > App under test). With no URL, `record.bat` asks for it.
   Verify warns (and can fix) when the pasted code opens a different MargBooks address.
2. Test the screen by hand in the Chrome window; copy all code from the Playwright Inspector.
3. In the Studio: Record > paste > **Use this code** > Verify > Replay > Save, as before.

## 8. Logs and troubleshooting

* `logs\studio_access.log`: time, IP, user, method, path, status of every request (rotates at 20 MB).
* A run's own console output is in its run log (Run screen > log) and its bug pack.
* "Add your own MargBooks login first": the QA has not filled Settings > My MargBooks login.
* "Waiting: another run is using qa garment": normal; the run starts when the company is free.
* "Could not sign in": check the QA's MargBooks login (they can re-enter it), or the URL in App under test.
* After moving the server or changing the service account: QAs re-enter their MargBooks password.

## 9. Updating

Stop the service, replace the code (keep `config\studio.db`, `config\environments.json`, `testcases\`, `locators\`,
`config\qa_*`), run `setup.bat` if `requirements.txt` changed, run the unit tests
(`.venv\Scripts\python -m pytest tests\unit -q`), start the service. The database is upgraded on first start.
