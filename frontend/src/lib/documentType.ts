import type { DocumentType } from "@/types/job";

const LABELS: Record<DocumentType, string> = {
  finanzamt: "Finanzamt (tax office)",
  auslaenderbehoerde: "Ausländerbehörde (immigration office)",
  krankenkasse: "Krankenkasse (health insurance)",
  bussgeld: "Bußgeld (fine)",
  rundfunkbeitrag: "Rundfunkbeitrag (broadcasting fee)",
  jobcenter: "Jobcenter",
  rental_utility: "Rental / utility",
  other: "Other",
};

export function formatDocumentType(docType: DocumentType): string {
  return LABELS[docType];
}
