# Google Stitch prompt: BBC Barani ChMS (Phase 1)

Paste everything below the line into Google Stitch (stitch.withgoogle.com). Use "Web" mode.
After it generates, ask for the mobile variants of screens 4 and 5 separately.

---

Design a web app UI for "BBC Barani ChMS", the internal church management system of
Bible Baptist Church Barani (Batac City, Ilocos Norte, Philippines). The people using it are the
pastor, the church secretary, and volunteer ushers. Many of them aren't very technical, and the
ushers use phones at the church door. The app should feel calm, trustworthy and reverent:
an organized church office, not a flashy SaaS product.

DESIGN SYSTEM: "Sanctuary Modern" (must match the church's public website)
- Background/surface: warm paper #FBF9F5; cards #FFFFFF; subtle panels #F5F3EF / #EFEEEA; paper-dark #F2EEE6
- Primary (deep navy): #041632; primary container #1B2B48; ink text #121C2F
- Secondary (antique gold accent): #775A19; gold container #FED488; gold-light #E3D1AC
- Tertiary (deep forest green, use for "present"/success states): #153121, light #CAEAD3
- Error: #BA1A1A on #FFDAD6. Body text #1B1C1A, muted text #44474D, borders #C5C6CE
- Typography: Playfair Display for page titles and big numbers (serif, elegant);
  Inter for everything else (body 14–16px, labels 12px uppercase with letter spacing)
- Corners: 4px default, 8px cards, 12px large panels, full-round for pills/avatars
- Soft shadow only: 0 4px 20px rgba(4,22,50,0.08). Lots of whitespace, thin dividers.
- Icons: Material Symbols Outlined
- Navy is for structure (sidebar, primary buttons). Gold is a sparing accent (active nav
  indicator, key highlights, a thin rule under page titles), never large gold fills.

LAYOUT
- Desktop: left sidebar in navy #041632 with the church name in Playfair Display, gold active-item
  indicator, nav items: Dashboard, Members, Households, Attendance, Admin. The user's name and
  Log out are at the bottom. The main content sits on warm paper, max width 1280px.
- Mobile: top bar with menu; sidebar becomes a drawer. Attendance screens are thumb-friendly.

SCREENS
1. Login: centered card on warm paper, church name in serif, a short verse line in italic
   ("Let all things be done decently and in order." 1 Cor 14:40), username, password, navy button.

2. Dashboard: greeting + date. Four stat cards (Active congregation, Members, Visitors this
   month, Last Sunday attendance) with big Playfair numbers. A bar chart of the last 8 weeks of
   Sunday Worship attendance (navy bars, gold highlight on the latest). Lists for "Birthdays
   this month" and "Recent services" (name, date, present count). Quick actions:
   "Take attendance", "Add member".

3. Members list: page title + count, search field (live search), status filter pills
   (All active, Visitor, Regular attendee, Member, Inactive, Transferred, Deceased), "Export CSV"
   ghost button, "Add member" navy button. Table: avatar with initials or photo, full name +
   nickname, status pill (Member = navy, Regular attendee = gold, Visitor = green outline,
   Inactive = gray), mobile number, household, age. Pagination. On mobile the rows become cards.

4. Member profile: header with large photo/initials avatar, full name in Playfair, status pill,
   Edit / Delete actions. Info cards: Personal (gender, birthday, age, civil status, occupation),
   Contact (mobile, email, address, emergency contact), Church life (first visit, salvation date,
   baptized + date, membership date), Household (linked family members as chips). Attendance
   panel: 90-day attendance rate as a ring/progress, total services attended, and a list of
   recent attendance (service name, date).

5. Member form (add/edit): sectioned form in cards (Personal, Contact, Household, Church life)
   with a 2-column grid on desktop, date pickers, photo upload with preview, a sticky
   Save/Cancel bar at the bottom.

6. Households: list of family cards (family name, address, member count, avatar stack), and a
   household detail with members and their roles (Head, Spouse, Child).

7. Attendance – services list: "New service" form (service type dropdown such as Sunday School,
   Sunday Worship, Evening Service, Prayer Meeting, Youth Fellowship; date; optional title). Table
   of services: date, type, present count, guests, total.

8. Attendance – check-in (most important, mobile-first): service name + date header; three
   counters (Checked in, Guests, Total) with big numbers; guests counter with − / + buttons.
   A large search field "Search name to check in…" with results as big tappable rows
   (avatar, name, status). Each row has a toggle button: "Check in" (navy outline) / "Present ✓"
   (filled forest green). A collapsible "Add first-time visitor" mini form (first name, last name,
   mobile) that adds and checks them in at once. A "Checked in" list below, newest first, with
   check-in time and an undo action.

STATES: show empty states (no members yet, no services yet) with a friendly serif line and
an action button, success toasts in green, and a delete confirmation dialog.

Accessibility: WCAG AA contrast, 44px minimum touch targets on mobile, visible focus rings in gold.
