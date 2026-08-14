# M21 — Real user phone test script

Per the milestone plan: *"As a real non-native user, I can complete the whole
journey on my phone without getting confused."* This needs 2 real people, on
real phones, genuinely trying the app — that's not something Claude can
simulate or fabricate (same principle as the golden-letter rule, D15: a
guessed-at "friction point" would be worse than no data, because it would
look like real evidence and isn't). This script is the part Claude *can*
prepare: what to hand your 2 testers, what to watch for, and how to turn
what they hit into concrete fixes.

## Who to recruit

Two people who genuinely aren't fluent German speakers — ideally people who
could plausibly receive a real Finanzamt/Ausländerbehörde/Krankenkasse
letter themselves. Friends, a language-exchange partner, a coworker who's
also new to Germany — anyone who isn't you and isn't a developer. A
developer's "confusion" isn't the signal this test needs; a real user's is.

## Before the session

1. Set up LAN phone testing per the README's "Testing on a real phone (LAN)"
   section — both `.env` files point at your machine's LAN IP, frontend
   rebuilt if it was previously built with `localhost` baked in.
2. Have 1–2 real (redacted) German letters ready, or ask the tester to bring
   one of their own if they have one — a real letter they'd actually want
   explained is a stronger test than a synthetic one.
3. Sit where you can watch their screen and their face, not just listen —
   most real confusion shows up as a pause or a wrong tap, not a verbal
   complaint.

## The task list (give this to the tester, then stay quiet)

Don't explain the app first. Handing someone a working product with no
tutorial and watching where they get stuck *is* the test.

1. "Here's a phone with a camera open to this app. You got a letter in the
   mail from a German office and you don't know what it says. Show me what
   you'd do."
2. Let them upload it however they try to (camera vs. photo library —
   note which).
3. Once results appear: "Tell me what this letter is asking you to do."
4. "Is there anything on this page you don't understand?" (Don't prompt
   further — see if they discover the glossary tap-to-define themselves.)
5. "How would you check that the app got this right?" (See if they discover
   tapping a field to highlight it in the original scan, M19.)
6. "Would you trust this enough to act on it?" — the single most important
   question in the whole session.

## Friction log

Fill this in live, one row per moment of hesitation, confusion, or a wrong
tap — not just verbal complaints. A 3-second pause before tapping something
is real data.

| # | What they were trying to do | What happened | Their reaction | Severity (blocks task / confusing / minor) |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |

## After both sessions

1. Sort the friction log by severity, then frequency (did both testers hit
   the same thing?).
2. Pick the top 3 and write each as a concrete, fixable problem statement —
   "the upload button wasn't obviously tappable" is fixable; "they seemed
   confused" is not.
3. Hand the top-3 list back for the actual fixes (a normal engineering
   session from there — this script's job ends at "here's what real users
   hit," not at fixing it).

## Screenshots

While each tester is going through the flow, grab 3–4 real screenshots
(with their permission, and with any personal letter content redacted or
using a sample letter) — landing page, mid-upload, results page, and
whatever moment produced the most friction. These are portfolio material
(M26/M27) as much as debugging material: a screenshot of a real person's
hand holding a real phone, mid-task, is a stronger signal than a staged one.
