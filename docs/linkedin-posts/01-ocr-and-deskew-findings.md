# LinkedIn post #1 — draft (Sprint-1 close)

**Status:** draft only. Claude drafts; publishing is yours — edit freely, this
is a starting point, not a final copy. Per the plan: concrete numbers, no hype.

---

Spent Sprint 1 of my portfolio project (BriefPilot — an AI tool that explains
German bureaucratic letters) on the part everyone skips past: OCR.

Two honest findings, no hype:

**1. The "OCR bake-off" I planned didn't happen — and that's the right call.**
The plan was to compare Azure Document Intelligence, Google Vision, and
Tesseract on real scans. But the project has a hard $0 budget, so provisioning
two paid APIs just to benchmark them would have broken the constraint before
writing a line of extraction code. I went with Tesseract (free, self-hosted)
by design, not by winning a comparison — and built the OCR layer behind an
interface so a paid provider is a config change later if the accuracy ever
demands it. Sometimes the right engineering answer is "we didn't run the
experiment, and here's why that's fine."

**2. My first deskew implementation was confidently wrong.**
To straighten tilted phone photos before OCR, I reached for the obvious
OpenCV function — `minAreaRect` on the text pixels. I tested it against known
rotations before trusting it: a 5° tilt came back as **−84°**. A 12° tilt came
back as **−77°**. Completely unusable — the angle is ambiguous for a wide
block of text, which is exactly what a page of text is.

Switched to projection-profile maximization instead — rotate through
candidate angles, keep the one where text rows line up sharpest. Same test,
every angle recovered within half a degree: 5° → −5.00°, −7° → +7.00°,
12° → −12.00°.

The lesson wasn't really about OpenCV. It was: **check a plausible-looking
library call against ground truth before you build on top of it.** Would
have shipped a broken deskew otherwise, silently.

Sprint 2 is extraction and the eval scorecard. More soon.

#buildinpublic #softwareengineering #ocr #computervision
