// 📁 LOCATION: frontend/src/utils/helpers.ts
import { format, formatDistanceToNow, parseISO } from "date-fns";

// ── Smart title (primary UX feature: show readable name, not filename) ────────
const SMART_MAP: [RegExp, string][] = [
  [/\b(resume|cv|curriculum[_\s]?vitae)\b/i,        "Resume / CV"],
  [/\b(ielts)\b/i,                                    "IELTS Certificate"],
  [/\b(toefl)\b/i,                                    "TOEFL Certificate"],
  [/\b(gre)\b/i,                                      "GRE Score Card"],
  [/\b(gmat)\b/i,                                     "GMAT Score Card"],
  [/\b(passport)\b/i,                                 "Passport"],
  [/\b(visa)\b/i,                                     "Visa Document"],
  [/\b(aps)\b/i,                                      "APS Certificate"],
  [/\b(bank[_\s]?statement|bank)\b/i,                 "Bank Statement"],
  [/\b(offer[_\s]?letter)\b/i,                        "Offer Letter"],
  [/\b(appointment[_\s]?letter)\b/i,                  "Appointment Letter"],
  [/\b(degree|graduation)\b/i,                        "Degree Certificate"],
  [/\b(transcript|marksheet|marks)\b/i,               "Academic Transcript"],
  [/\b(certificate|cert|certification)\b/i,           "Certificate"],
  [/\b(invoice)\b/i,                                  "Invoice"],
  [/\b(receipt)\b/i,                                  "Receipt"],
  [/\b(admission)\b/i,                                "Admission Letter"],
  [/\b(motivation[_\s]?letter|sop|statement)\b/i,     "Motivation Letter"],
  [/\b(recommendation|lor)\b/i,                       "Recommendation Letter"],
  [/\b(project)\b/i,                                  "Project File"],
  [/\b(blocked[_\s]?account)\b/i,                     "Blocked Account Proof"],
  [/\b(ticket|flight)\b/i,                            "Travel Ticket"],
  [/\b(hotel|booking)\b/i,                            "Hotel Booking"],
  [/\b(tax|itr)\b/i,                                  "Tax Document"],
  [/\b(medical|prescription|hospital)\b/i,            "Medical Document"],
  [/\b(udemy|coursera|edx)\b/i,                       "Online Course Certificate"],
  [/\b(photo|selfie|portrait)\b/i,                    "Photo"],
  [/\b(screenshot|screen)\b/i,                        "Screenshot"],
  [/\b(scan|scanned)\b/i,                             "Scanned Document"],
];

const FILE_TYPE_NAMES: Record<string, string> = {
  pdf: "PDF Document", docx: "Word Document", doc: "Word Document",
  jpg: "Photo", jpeg: "Photo", png: "Image", webp: "Image",
  txt: "Text File", csv: "Spreadsheet", md: "Note",
};

export function smartTitle(source: string, storedTitle?: string): string {
  const candidates = [storedTitle || "", source || ""];

  for (const text of candidates) {
    if (!text) continue;
    const lower = text.toLowerCase();
    for (const [pattern, label] of SMART_MAP) {
      if (pattern.test(lower)) return label;
    }
  }

  // Clean stored title if it exists and isn't just a filename
  if (storedTitle && !/\.(pdf|jpg|jpeg|png|docx|txt|webp)$/i.test(storedTitle)) {
    return storedTitle
      .replace(/[_\-]+/g, " ")
      .replace(/\s+v?\d+(\.\d+)?\s*$/i, "")
      .replace(/\s+/g, " ")
      .trim()
      .replace(/\b\w/g, c => c.toUpperCase());
  }

  // Clean filename stem
  const stem = source.replace(/\.[^/.]+$/, "");
  const cleaned = stem
    .replace(/[_\-\.]+/g, " ")
    .replace(/\b\w/g, c => c.toUpperCase())
    .replace(/\s+v?\d+(\.\d+)?\s*$/i, "")
    .trim();

  if (cleaned.length > 2) return cleaned;

  const ext = source.split(".").pop()?.toLowerCase() || "";
  return FILE_TYPE_NAMES[ext] || "File";
}

// ── Dates ──────────────────────────────────────────────────────────────────────
export function relativeDate(d: string | null): string {
  if (!d) return "";
  try { return formatDistanceToNow(parseISO(d), { addSuffix: true }); }
  catch { return d; }
}

export function fmtDate(d: string | null, fmt = "dd MMM yyyy"): string {
  if (!d) return "";
  try { return format(parseISO(d), fmt); }
  catch { return d; }
}

// ── File type helpers ─────────────────────────────────────────────────────────
export function fileTypeIcon(type: string): string {
  const m: Record<string, string> = {
    pdf:"📄", docx:"📝", doc:"📝",
    jpg:"🖼️", jpeg:"🖼️", png:"🖼️", webp:"🖼️", bmp:"🖼️",
    txt:"📃", csv:"📊", md:"📓", mp4:"🎥",
  };
  return m[type?.toLowerCase()] || "📁";
}

export function fileTypeColor(type: string): string {
  const m: Record<string, string> = {
    pdf:"text-red-400", docx:"text-blue-400", doc:"text-blue-400",
    jpg:"text-green-400", jpeg:"text-green-400", png:"text-green-400",
    webp:"text-green-400", txt:"text-gray-400", csv:"text-yellow-400",
  };
  return m[type?.toLowerCase()] || "text-purple-400";
}

export function fileTypeBadgeColor(type: string): string {
  const m: Record<string, string> = {
    pdf:"badge-red", docx:"badge-blue", doc:"badge-blue",
    jpg:"badge-green", jpeg:"badge-green", png:"badge-green",
  };
  return m[type?.toLowerCase()] || "badge-gray";
}

// ── Score helpers ──────────────────────────────────────────────────────────────
export function scoreColor(score: number): string {
  if (score >= 0.7) return "text-green-400";
  if (score >= 0.4) return "text-yellow-400";
  return "text-red-400";
}

export function scoreLabel(score: number): string {
  if (score >= 0.7) return "High";
  if (score >= 0.4) return "Medium";
  return "Low";
}

export function scoreBarColor(score: number): string {
  if (score >= 0.7) return "bg-green-500";
  if (score >= 0.4) return "bg-yellow-500";
  return "bg-red-400";
}

// ── Image URL ────────────────────────────────────────────────────────────────
import { API_BASE_URL } from "@/services/api";

export function imageUrl(path: string | null): string | null {
  if (!path) return null;
  if (path.startsWith("http")) return path;
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE_URL}${cleanPath}`;
}

// ── CSS classname helper ──────────────────────────────────────────────────────
export function cn(...classes: (string | boolean | undefined | null)[]): string {
  return classes.filter(Boolean).join(" ");
}
