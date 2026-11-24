# Pitch video walkthrough (about 3 minutes)

Setup: `docker compose up`, then log in at http://localhost:8002 as admin/admin. Demo data is fictional.
Use two browser windows side by side: **A** = check-in page and **B** = the self check-in kiosk.

1. **Login** (10 s): the church name, the verse, and "Remember this computer" for shared office PCs.
2. **Dashboard** (30 s): congregation numbers, the 8-week Sunday Worship trend, birthdays this week, and Visitation.
3. **Birthdays → Print** (15 s): the list the pastor announces and prays over on Sunday.
4. **Members** (30 s): live search, status filters, and a profile with attendance rate and household.
5. **Services** (20 s): service types, then "Change" an afternoon service to a new time, which shows "Rescheduled".
6. **Usher check-in** (30 s), window A: search a name, tap Check in, + a guest, "Add first-time visitor", then "Not yet seen".
7. **Self check-in** (45 s):
   - On a member with no QR code: *Give QR code*, then *Print sticker* (show the sticker sheet).
   - Window B (kiosk): open *Demo: pretend it's another time* and set the service time, then hold a printed sticker up to the camera (or type its code). The screen says "Welcome, Bro. …"
   - Window A updates within 5 s with a QR icon. Scan again for "Already checked in"; any other QR gives "We don't know this code".
   - Self check-in page: live scans and the privacy note (the QR holds only a random code).
8. **Close** (10 s): Visitation: "We missed you", ready for a call or a visit. End on Ephesians 5:16.

Tip: before recording, reset demo data with `docker compose down -v && docker compose up`.
