# Flock end-to-end tests (Playwright)

Real-browser tests of whole flows: signing in, roles, member/household/service forms and their validation,
usher check-in, QR stickers, the self check-in kiosk (typed codes, a USB scanner, **and the camera**),
Android phone screens, and a health check of every page.

They run against a **throwaway copy of the app** with its own in-memory database
(`docker-compose.e2e.yml`, port 8004). Each run wipes and reloads that database with fixed test data
(`manage.py seed_e2e`), so your dev and production data are never touched.

## First time
    cd e2e
    npm ci
    npx playwright install chromium

## Run
    docker compose -f docker-compose.e2e.yml up -d --build   # from the project root; leave it running
    cd e2e
    npm test                      # all tests (desktop, Android phone, fake camera)
    npx playwright test -g kiosk  # only tests whose name matches "kiosk"
    npm run test:headed           # watch the browser
    npm run report                # open the HTML report (screenshots + traces of failures)

When done: `docker compose -f docker-compose.e2e.yml down`.

## What's where
| File | Covers |
|---|---|
| `tests/auth.spec.js` | Login, wrong password, logout, what each role can and can't open |
| `tests/members.spec.js` | Add/edit/delete members, **field validation** (names, email, phone, dates, photo), search, filters, CSV |
| `tests/attendance.spec.js` | Households, service types, scheduling and rescheduling, usher check-in, visitors, guest counter |
| `tests/checkin.spec.js` | QR codes and stickers, lost-sticker reissue, the kiosk, live updates on the usher's page |
| `tests/camera.spec.js` | The kiosk reading a QR sticker from a (fake) webcam, camera menu |
| `tests/mobile.spec.js` | Pixel 7 screen: menu, check-in, no sideways scrolling |
| `tests/pages.spec.js` | Every page opens with no server error, JavaScript error or broken image |

Every test also fails automatically on any JavaScript error, console error or server error (5xx)
on the page (see `tests/helpers.js`).

## Writing tests
- Test users (password `e2e-pass-123`): `admin`, `secretary`, `usher`, `kiosk`. Pick one with
  `test.use({ role: "usher" })`; `role: null` means signed out.
- Tests run in parallel against one database: create your own records with `uniq("Name")`, or use a
  record no other test changes. Fixed data lives in `core/management/commands/seed_e2e.py`.
- To check the server's validation (not just the browser's `required`), call `submitWithoutBrowserChecks(page)`
  before submitting, then look for `fieldError(page, "field_name")`.
