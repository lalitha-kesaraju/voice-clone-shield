"""Evidence-pack PDF: a match report the artist can attach to a takedown filing."""
import datetime

from fpdf import FPDF
from fpdf.enums import XPos, YPos

BAND_LABELS = {
    "likely_match": "LIKELY MATCH -- voice is highly similar to the enrolled voiceprint",
    "review": "REVIEW -- moderate similarity; human review recommended",
    "no_match": "NO MATCH -- no enrolled voiceprint is similar to this clip",
}


class _Report(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(20, 20, 30)
        self.cell(0, 8, "Voice-Clone Shield -- Match Evidence Report",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(255, 176, 32)
        self.set_line_width(0.8)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 130)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def section(self, title: str):
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(20, 20, 30)
        self.cell(0, 7, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)

    def kv(self, key: str, value: str):
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(60, 60, 70)
        self.cell(52, 6, key)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(20, 20, 30)
        self.multi_cell(0, 6, value, new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def build_evidence_pdf(check, user, match_threshold: float, review_threshold: float) -> bytes:
    """Render the evidence pack for one MatchCheck row. Returns PDF bytes."""
    pdf = _Report()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(True, margin=20)
    pdf.add_page()

    generated = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    pdf.kv("Report ID", f"VCS-{check.id:06d}")
    pdf.kv("Generated", generated)
    pdf.kv("Artist", f"{user.artist_name} <{user.email}>")
    pdf.ln(3)

    pdf.section("1. Suspect clip (uploaded by artist)")
    pdf.kv("Filename", check.filename)
    pdf.kv("Duration", f"{check.duration_sec:.1f} seconds")
    pdf.kv("Voiced audio", f"{check.voiced_ratio:.0%} of clip")
    pdf.kv("Uploaded at", check.created_at.strftime("%Y-%m-%d %H:%M UTC") if check.created_at else "--")
    pdf.ln(3)

    pdf.section("2. Match analysis vs enrolled voiceprints")
    pdf.kv("Match threshold", f"{match_threshold:.2f} cosine similarity")
    pdf.kv("Review threshold", f"{review_threshold:.2f} cosine similarity")
    pdf.kv("Overall verdict", BAND_LABELS.get(check.verdict, check.verdict))
    pdf.ln(2)

    results = check.results or []
    if results:
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(240, 240, 245)
        pdf.cell(70, 7, "Enrolled voiceprint", border=1, fill=True)
        pdf.cell(40, 7, "Similarity", border=1, fill=True, align="C")
        pdf.cell(0, 7, "Assessment", border=1, fill=True,
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", "", 9)
        for r in results:
            pdf.set_x(pdf.l_margin)
            pdf.cell(70, 7, str(r.get("label", f'#{r.get("voiceprint_id")}')), border=1)
            pdf.cell(40, 7, f'{float(r.get("score", 0.0)):.3f}', border=1, align="C")
            pdf.cell(0, 7, BAND_LABELS.get(r.get("band", ""), ""), border=1,
                     new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    else:
        pdf.set_font("Helvetica", "I", 9)
        pdf.multi_cell(0, 6, "No enrolled voiceprints were compared for this check.")
    pdf.ln(3)

    pdf.section("3. Artist feedback")
    pdf.kv("Feedback", check.feedback or "not yet provided")
    pdf.kv("Note", check.feedback_note or "--")
    pdf.ln(3)

    pdf.section("4. Methodology")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(20, 20, 30)
    pdf.multi_cell(
        0, 6,
        "Both the enrolled voiceprint and the suspect clip were converted to mono 16 kHz, "
        "gated with an energy-based voice activity detector, and encoded with the "
        "ECAPA-TDNN speaker-embedding model (SpeechBrain, CPU). Identity comparison is the "
        "cosine similarity between L2-normalised 192-dimensional embeddings. Long clips are "
        "embedded in 30-second chunks and averaged. Audio fingerprinting is deliberately NOT "
        "used: it matches recordings, not voices, so an AI clone singing a brand-new song "
        "would never match a fingerprint database.",
    )
    pdf.ln(3)

    pdf.section("5. Disclaimer")
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(90, 90, 100)
    pdf.multi_cell(
        0, 6,
        "This report is a technical similarity assessment produced at the artist's request. "
        "It is not legal advice and does not by itself prove authorship, ownership, or "
        "infringement. Similarity scores should be weighed alongside release metadata, "
        "distribution records, and other evidence when filing a takedown or complaint.",
    )

    return bytes(pdf.output())
