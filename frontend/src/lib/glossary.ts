// M16: a curated Amtsdeutsch (German bureaucratic language) glossary — real
// terms that actually appear on the 8 in-scope letter types (CLAUDE.md §1),
// with plain-English definitions. Curated, not exhaustive (same posture as
// backend/app/services/validators.py's § whitelist): a term missing here is
// simply not tappable yet, never a wrong or invented definition.
export const GLOSSARY: Record<string, string> = {
  // -- General / cross-cutting bureaucratic terms --
  Bescheid: "An official written decision or notice from a government office.",
  Frist: "A deadline — a date by which you must respond or act.",
  Widerspruch: "A formal written objection to a decision, filed within a set deadline.",
  Einspruch: "A formal objection, most often used for tax or fine decisions.",
  Vollmacht: "A document that authorizes someone else to act or make decisions on your behalf.",
  Zustellung: "The official delivery of a document, which often starts a deadline running.",
  Anhörung: "A formal opportunity to respond before an office makes a final decision.",
  Antrag: "A formal application or request.",
  Bearbeitungsgebühr: "A processing fee charged for handling an application.",
  Mahnung: "A formal payment reminder, often the step before further collection action.",
  Vollstreckung: "Forced legal collection of a debt, e.g. via a bailiff.",
  Amtsgericht: "A local court that handles everyday legal matters.",
  Aktenzeichen: "A case or file reference number — quote it in any reply.",
  "Zuständige Behörde": "The specific office responsible for handling your case.",

  // -- Finanzamt (tax office) --
  Steuerbescheid: "An official notice stating how much tax you owe or will be refunded.",
  Steuernummer: "Your personal tax number, used on all correspondence with the tax office.",
  "Steuer-ID": "Your permanent, lifelong German tax identification number.",
  Einkommensteuer: "Income tax, charged on your personal earnings.",
  Umsatzsteuer: "Value-added tax (VAT) charged on goods and services.",
  Veranlagung: "The tax office's assessment of your tax return.",
  Freibetrag: "An amount of income or value that is exempt from tax.",
  Vorauszahlung: "An advance/prepayment made toward tax owed for the current year.",
  Säumniszuschlag: "A surcharge added for paying tax after the deadline.",
  Steuererklärung: "Your annual tax return/declaration.",

  // -- Ausländerbehörde (immigration office) --
  Aufenthaltstitel: "The general legal term for permission to reside in Germany.",
  Aufenthaltserlaubnis: "A temporary residence permit, usually tied to a specific purpose.",
  Niederlassungserlaubnis: "A permanent, unlimited settlement permit.",
  Duldung: "A temporary suspension of deportation — not a residence permit.",
  Fiktionsbescheinigung:
    "A certificate confirming your permit is still valid while a renewal is processed.",
  Aufenthaltsgestattung:
    "Permission to stay in Germany while an asylum application is being decided.",
  Erwerbstätigkeit: "Paid work or employment.",
  Ausweisung: "An order to leave Germany, issued by the immigration office.",
  Einbürgerung: "The process of becoming a naturalized German citizen.",

  // -- Krankenkasse (health insurance) --
  Versichertennummer: "Your personal health insurance member number.",
  Beitragsbescheid: "A notice stating the health insurance contribution amount you owe.",
  Zuzahlung: "A co-payment you make yourself toward a medical service or medicine.",
  Selbstbeteiligung:
    "The portion of a cost you must pay yourself before insurance covers the rest.",
  Krankengeld:
    "Sick pay — an income replacement paid by your health insurer during long-term illness.",
  Pflegeversicherung: "Mandatory long-term care insurance, paired with health insurance.",
  Versicherungspflicht: "The legal requirement to have health insurance in Germany.",

  // -- Bußgeld (fines) --
  Bußgeldbescheid: "An official notice of a fine, usually for a traffic or minor offense.",
  "Punkte in Flensburg": "Penalty points recorded on a national driving register.",
  Fahrverbot: "A temporary ban from driving, separate from losing your license entirely.",
  Führerscheinentzug: "Permanent or long-term revocation of your driving license.",
  Owi: "Short for Ordnungswidrigkeit — a minor offense punished with a fine, not a criminal charge.",

  // -- Rundfunkbeitrag (broadcasting fee) --
  Rundfunkbeitrag: "The mandatory household fee that funds German public broadcasting.",
  Beitragsservice:
    "The organization (ARD/ZDF/Deutschlandradio) that collects the broadcasting fee.",
  Befreiung: "An exemption from paying a fee, usually based on low income or disability.",

  // -- Jobcenter (benefits) --
  Arbeitslosengeld: "Unemployment benefit, paid based on your previous salary and contributions.",
  Bürgergeld: "Basic income support for jobseekers and low-income households.",
  Regelsatz: "The standard monthly benefit amount used to calculate Bürgergeld.",
  Eingliederungsvereinbarung:
    "An agreement between you and the Jobcenter about job-search steps and support.",
  Sanktion: "A temporary benefit reduction, usually for missing an appointment or requirement.",

  // -- Rental / utility --
  Nebenkostenabrechnung:
    "The annual statement settling your actual utility costs against what you prepaid.",
  Kaution: "A rental deposit, held by the landlord until you move out.",
  Betriebskosten:
    "Ongoing running costs of a building (heating, water, waste, etc.) billed to tenants.",
  Mietspiegel: "A local reference table showing typical rents, used to judge if rent is fair.",
  Kündigung: "A formal notice ending a contract, such as a rental agreement.",
};
