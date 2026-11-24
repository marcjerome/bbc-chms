# BBC Barani ChMS: Requirements (Phase 1 MVP)

**Sign-off authority:** Marc, acting as proxy for church leadership (validate with the pastor before go-live).
**Provenance tags:** `[M]` = decided by Marc on 2026-11-22 · `[P]` = Claude's proposal, **not yet confirmed**. Confirm or strike each `[P]`.
**Status:** ✅ built and tested · ⬜ to build

## Definition of done (MVP) `[M]`
Running on the **church computer** (on-premise), **all current members entered by hand**, and attendance taken in the app for **4 consecutive Sundays**.

## 1. Members
| ID | Requirement | Src | Status |
|---|---|---|---|
| MEM-1 | Record personal, contact, household and church-life details (status, salvation, baptism, membership date) | [P] | ✅ |
| MEM-2 | Search by name, mobile or email, and filter by status | [P] | ✅ |
| MEM-3 | Group members into households with roles (head, spouse, child…) | [P] | ✅ |
| MEM-4 | **No import tool**: records start empty, so the add-member form must be quick to fill in | [M] | ✅ |
| MEM-5 | Export members to CSV | [P] | ✅ |
| MEM-6 | Mark people Inactive or Transferred instead of deleting them, so their history is kept | [P] | ✅ |
| MEM-7 | Title (Bro., Sis., Pastor, Deacon) and church-role tag (e.g. Head Usher) shown on lists, check-in and profile | [M] from Stitch design | ✅ |

## 2. Attendance
| ID | Requirement | Src | Status |
|---|---|---|---|
| ATT-1 | **Ushers check people in** by searching a name and tapping it, on a phone | [M] | ✅ |
| ATT-2 | One service per type per date (Sunday Worship, Sunday School, Evening, Prayer Meeting, Youth) | [P] | ✅ |
| ATT-3 | Count unnamed guests with + and − buttons | [P] | ✅ |
| ATT-4 | Add a first-time visitor during check-in, who is then checked in automatically | [P] | ✅ |
| ATT-5 | **Absent = missed that one service.** Each service lists members and regular attendees who weren't checked in | [M] | ✅ |
| ATT-6 | **Service manager**: service types (Sunday Worship, Sunday School, Sunday Afternoon, Wednesday Prayer Meeting…) managed in the app with a usual day and time | [M] | ✅ |
| ATT-7 | Schedule services ahead, and change one occurrence's date or time (the afternoon service moves sometimes); it's marked "Rescheduled" | [M] | ✅ |

## 3. Reports `[M]`
| ID | Requirement | Src | Status |
|---|---|---|---|
| REP-1 | Attendance trends per service (8-week chart on the dashboard) | [M] | ✅ |
| REP-2 | **Birthdays this week (Sunday–Saturday)**, printable, for the Sunday announcement and prayer | [M] | ✅ |
| ~~REP-3~~ | ~~Baptism/membership anniversaries~~: **dropped**. The church doesn't celebrate them; the dates are kept as optional records | [M] | — |
| REP-4 | **Absentee follow-up**: members and regular attendees absent from the latest main service, with tap-to-call | [M] | ✅ |
| REP-5 | **Ministry follow-ups** panel on the dashboard and a Follow-ups page: first-time visitors from the last 14 days, plus absentees | [M] | ✅ |

## 4. Access `[P]`
Three roles: Church Admin (everything, including service types), Secretary (members, households, scheduling services; views attendance), Usher (takes attendance, adds visitors, can reschedule a service). Members don't log in. The usual service times seeded at setup are placeholders; correct them in Service types.

## 5. Deployment: on-premise at the church `[M]` (decided 2026-11-23; replaces the DigitalOcean droplet plan)
The app runs on a computer at the church and is used over the church network. Kiosks and staff connect by plain http.

| ID | Requirement | Src | Status |
|---|---|---|---|
| DEP-1 | Runs in Docker (Postgres 17) | [M] | ✅ |
| DEP-2 | **Church computer (Linux)** runs it and starts it by itself after a restart or power cut (Docker set to start at boot; containers use `restart: unless-stopped`). At least 4 GB RAM and an SSD | [M] / specs [P] | ⬜ |
| DEP-3 | **Reachable on the church network** at a fixed address (DHCP reservation in the router, e.g. `http://192.168.1.10:8002`). Production listens on the LAN and accepts any private network address (public ones refused) | [M] | ⬜ (app side ✅) |
| DEP-4 | **Kiosk at the door:** Android tablet or phone with Chrome, one-time camera setting for http (shown on the kiosk), logged in with a *Check-in Kiosk* account. A USB QR scanner as backup | [M] | ⬜ |
| DEP-5 | **Works when the internet is down:** fonts and icons are bundled with the app (no Google Fonts or other outside links) | [M] | ✅ |
| DEP-6 | **Nightly backup** (`pg_dump`) to a second drive or USB, plus a copy kept **off-site** weekly (a USB taken home, or cloud). One machine in one building can be stolen, flooded or fail | [P] | ⬜ |
| DEP-7 | **UPS** for the computer and router (brownouts during service) | [P] | ⬜ |
| DEP-8 | **Kept private:** no port forwarding on the router; strong passwords; the computer in a locked room with its own login (RA 10173: the records are physically at the church) | [P] | ⬜ |
| DEP-9 | Remote access for maintenance (e.g. Tailscale), or updates done on-site only. **Open question** | [P] | ⬜ |

## Design `[M]`
The Stitch export in `docs/design/` is the visual reference. Adopted on 2026-11-22: dashboard extras (stat progress bars, 8-week average/peak/guest ratio, "Today" bar), check-in extras (registered progress, total card, check-in time, undo), login extras (seal placeholder, show password, "Remember this computer").
**Rejected:** member ID numbers, service sign-off / head usher, top bar with global search, notification bell. Stitch's sample names and facts (e.g. "Founded 1984") are made up and must not be used.

## Phase 2: self check-in `[M]`
Modes decided 2026-11-23: **QR (default), Fingerprint, Face**, several at once; face on both the door terminal and the kiosk tablet. `SELF_CHECKIN_ENABLED=false` hides all of it.

| ID | Requirement | Src | Status |
|---|---|---|---|
| MODE-1 | Three check-in modes, any combination on at once; only QR on by default; admins switch them at Self check-in → Modes | [M] | ✅ |
| MODE-2 | Fingerprint and face **door terminals** (ZKTeco ADMS) restored from the pre-QR build; terminal scans of a mode that is off are logged, not counted | [M] | ✅ (no real terminal tried yet) |
| MODE-3 | **Face at the kiosk tablet**: enroll 5 pictures on the profile, recognised by the same kiosk camera as QR, offline, no photos stored | [M] | ✅ (tried with test images; not yet with real people on the tablet) |
| MODE-4 | Fingerprint/face need signed consent (RA 10173); withdrawing it removes the person from the kiosk and all terminals | [P] | ✅ |
| MODE-5 | Attendance shows how each person checked in (QR / fingerprint / face icons) | [P] | ✅ |

### QR stickers
| ID | Requirement | Src | Status |
|---|---|---|---|
| QR-1 | Each person can be given a QR code; stickers print 2.5×1.4 in on A4, to stick inside their Bible. Branded: sheep logo + "BBC BARANI" (2026-11-23), tested to scan at door-camera sizes | [M] | ✅ |
| QR-2 | A camera kiosk page at the door reads the QR and checks the person in by themselves | [M] | ✅ |
| QR-3 | Works on-premise over plain http: the kiosk explains the one-time Chrome/Edge setting; a USB QR scanner or typing the code works with no camera | [M] | ✅ (not yet tried on the real tablet) |
| QR-4 | A scan checks the person into the service happening at that time (60 min before to 3 h after its start `[P]`); that day's services open automatically | [P] | ✅ |
| QR-5 | The QR holds only a random code, no name or personal details. A lost sticker gets a new code and the old one stops working | [P] | ✅ |
| QR-6 | A "Check-in Kiosk" role that can only use the kiosk, for a device left at the door | [P] | ✅ |
| QR-7 | Check-in page updates live (every 5 s) and marks QR check-ins with a QR icon | [P] | ✅ |

## Phase 3: Care groups `[M]` (approved idea 2026-11-22, not built)
Assign families to workers or deacons, so the "We missed you" list and new visitors go straight to the person responsible. The growing-church problem (Acts 6:1–3).

## Out of scope for phase 1 `[P]`
Giving and tithes, ministries and groups, SMS or email, member self-service portal.
