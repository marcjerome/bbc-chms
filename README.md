# BBC Barani ChMS

Church management system for Bible Baptist Church Barani. Phase 1: member records, households,
attendance. Django 6.1 + Postgres 17, HTMX + Alpine.js + Tailwind 4 ("Sanctuary Modern" theme
shared with the bbc/yesgo/bba sites), Unfold admin.

## Run (Docker)
    cp .env.example .env          # optional
    docker compose up --build     # http://localhost:8002  (admin / admin)

Dev compose loads fictional demo data (`SEED_DEMO=false` to start empty) and runs a Tailwind watcher.
Production runs **on a computer at the church** (on-premise): `docker compose -f docker-compose.prod.yml up -d --build`
(needs SECRET_KEY and POSTGRES_PASSWORD in `.env`). Phones and tablets on the church network open
`http://<computer's address>:8002`; any private network address is accepted, public ones are refused.
It listens on port 8002 on the church network; give the computer a fixed address in the router. See the deployment
plan in `docs/requirements.md` §5.

## Roles
`setup_roles` (runs on start) creates groups; assign users in /admin/ → Users:
- **Church Admin**: everything
- **Secretary**: add/edit members & households, view attendance
- **Usher**: look up members, take attendance, add first-time visitors

## Phase 2: self check-in modes (QR · Fingerprint · Face)
People check themselves into the service happening at that time. Three **modes** can run side by side; an admin
turns them on at **Self check-in → Modes** (only **QR** is on by default). `SELF_CHECKIN_ENABLED=false` in `.env`
turns all of them off.

| Mode | Hardware | What Flock stores | Consent |
|---|---|---|---|
| **QR stickers** (default) | kiosk tablet camera or USB scanner | a random code | not needed |
| **Fingerprint** | ZKTeco-type terminal at the door (ADMS push, `/iclock/`) | the person's device user number; prints stay on the terminal | signed form (RA 10173) |
| **Face** | a face terminal (as above) **and/or** the kiosk tablet camera | tablet: 5 × 128 numbers computed in the browser from the face, never a photo | signed form (RA 10173) |

- **Face at the kiosk:** record consent on the profile → *Enroll face* (5 pictures, about 10 seconds) → people just
  look at the kiosk. Runs offline in the browser (`@vladmandic/face-api`, models in `static/models/face/`). Match
  strictness defaults to 0.45 (measured: same person ≈ 0.2–0.35, different people ≥ 0.5). A good photo could fool it:
  fine for attendance, not for security. `?modes=qr` or `?modes=face` on the kiosk URL narrows one station.
- **Door terminals:** menu *Door terminals* (shown when Fingerprint or Face is on): approve terminals, a simulator for
  demos, consent and *Register on terminals* on each profile. Withdrawing consent removes the person from the kiosk
  and every terminal.

- **Kiosk decorations** (Modes page): Christmas lights, snow, the nativity under the star of Bethlehem and Luke 2:11,
  plus "Merry Christmas!" with each welcome. Automatic from Dec 1 to Jan 6, or switched on/off by hand. Drawn in
  SVG/CSS (offline); snow stays behind the camera box; reduced-motion devices get a still scene.

### QR stickers
- **Give codes / print stickers:** a member's profile → *Give QR code*, or Self check-in → *Print stickers* (2.5×1.4 in stickers, A4).
  The QR is branded (Flock sheep in the middle, navy *BBC BARANI* band) and tested to scan as well as a plain code.
- **Recorded demo:** `python manage.py prepare_demo "First Last"` makes the presenter, their QR and an all-day demo service; add `--reset` between takes.
  The QR holds only a random code (`FLOCK-XXXXXXXX`); *Lost sticker? New code* makes the old one stop working.
- **Kiosk:** Self check-in → *Open kiosk* on a tablet, laptop or phone, logged in as an usher or a user in the
  **Check-in Kiosk** role. A USB/Bluetooth QR scanner also works (it types into the code box), with no camera needed. The *Camera* button picks which camera to use (front, back or a USB webcam) and whether to mirror it; the choice is remembered on that device.
- **Camera over plain http (on-premise):** browsers only open the camera on HTTPS or `localhost`. On the kiosk device,
  in Chrome/Edge open `chrome://flags/#unsafely-treat-insecure-origin-as-secure`, add the server address
  (e.g. `http://192.168.1.10:8002`), enable it and relaunch. The kiosk shows these steps itself. iPhone/iPad can't do
  this; use Android, a laptop, a USB scanner, or put HTTPS in front.
- See `docs/pitch-demo.md` for a scripted walkthrough.

## Tests
    docker compose exec web python manage.py test     # unit tests

End-to-end browser tests (Playwright) run against a separate throwaway copy of the app: see `e2e/README.md`.

    docker compose -f docker-compose.e2e.yml up -d --build
    cd e2e && npm ci && npx playwright install chromium && npm test

## Docs
- `docs/stitch-prompt.md`: Google Stitch prompt for the UI design
