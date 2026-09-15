"""GET /trials/slots/{id}/sheet.pdf — docs/02-api-spec.md: "Printable
ground fallback" (docs/05-build-sequence.md T-506: "Coaches can print the
day's trial sheet as a fallback"). `reportlab` added to requirements/
base.txt for this — no PDF library existed in the project before Phase 1
needed one; declared here rather than silently assumed.
"""

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .models import TrialSlot


def render_trial_sheet_pdf(slot: TrialSlot) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=15 * mm, bottomMargin=15 * mm)
    styles = getSampleStyleSheet()

    registrations = slot.registrations.select_related("person", "enquiry").order_by("trial_id")

    header = (
        f"Trial Sheet — {slot.venue.name} — {slot.date:%d-%m-%Y} {slot.reporting_time:%H:%M}"
        f" — {slot.age_category.name}"
    )
    story = [Paragraph(header, styles["Title"]), Spacer(1, 8 * mm)]

    rows = [["#", "Trial ID", "Candidate", "Attended", "Batting", "Bowling", "Fielding", "Remarks"]]
    for i, registration in enumerate(registrations, start=1):
        name = (
            registration.person.first_name
            if registration.person
            else registration.enquiry.student_name
        )
        rows.append([str(i), registration.trial_id, name, "", "", "", "", ""])

    table = Table(rows, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2933")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
            ]
        )
    )
    story.append(table)

    doc.build(story)
    return buffer.getvalue()
