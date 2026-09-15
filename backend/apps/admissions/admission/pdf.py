"""GET /admissions/{id}/print/ — the filled direct-admission form as PDF,
for the desk's own paper trail. Same reportlab pattern as
apps.admissions.trial.pdf.render_trial_sheet_pdf.
"""

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .models import Admission


def _kv_table(rows: list[tuple[str, str]]) -> Table:
    table = Table(rows, colWidths=[55 * mm, 110 * mm])
    table.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#4b5563")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
            ]
        )
    )
    return table


def render_direct_admission_form(admission: Admission) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=15 * mm, bottomMargin=15 * mm)
    styles = getSampleStyleSheet()

    intake = getattr(admission, "intake", None)
    story = [
        Paragraph("Adamas Cricket Academy — Direct Admission Form", styles["Title"]),
        Paragraph(
            f"{admission.application_no} — status: {admission.get_step_display()}",
            styles["Normal"],
        ),
        Spacer(1, 6 * mm),
    ]

    if intake is not None:
        story.append(Paragraph("Seat", styles["Heading2"]))
        story.append(
            _kv_table(
                [
                    ("Season", intake.season.name),
                    ("Category", intake.get_admission_category_display()),
                    ("Days / week", str(intake.days_per_week or "—")),
                    (
                        "Preferred slot",
                        intake.get_preferred_slot_display() if intake.preferred_slot else "—",
                    ),
                ]
            )
        )
        story.append(Spacer(1, 4 * mm))

        story.append(Paragraph("Student", styles["Heading2"]))
        story.append(
            _kv_table(
                [
                    ("Full name", intake.full_name),
                    ("Date of birth", f"{intake.date_of_birth:%d-%m-%Y}"),
                    ("Age category", intake.age_category.name),
                    ("Gender", intake.get_gender_display()),
                ]
            )
        )
        story.append(Spacer(1, 4 * mm))

        story.append(Paragraph("Contact", styles["Heading2"]))
        story.append(
            _kv_table(
                [
                    (
                        "Address",
                        f"{intake.present_address}, {intake.city}, "
                        f"{intake.state} {intake.pin_code}",
                    ),
                    (
                        "Guardian",
                        f"{intake.guardian_name} "
                        f"({intake.get_guardian_relationship_display()})",
                    ),
                    ("Guardian mobile", intake.guardian_mobile),
                    ("Emergency contact", intake.emergency_contact),
                ]
            )
        )
        story.append(Spacer(1, 6 * mm))

    fee_lines = list(
        admission.fee_lines.select_related("fee_head").order_by("fee_head__display_order")
    )
    if fee_lines:
        story.append(Paragraph("Fee collected", styles["Heading2"]))
        rows = [["Head", "Amount"]] + [
            [line.fee_head.label, f"{line.amount:,.2f}"] for line in fee_lines
        ]
        rows.append(["Total", f"{admission.fee_total:,.2f}"])
        fee_table = Table(rows, colWidths=[110 * mm, 55 * mm])
        fee_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2933")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ]
            )
        )
        story.append(fee_table)
        story.append(Paragraph(admission.fee_total_in_words, styles["Italic"]))
        story.append(Spacer(1, 6 * mm))

    consents = list(admission.consent_records.select_related("consent_type"))
    if consents:
        story.append(Paragraph("Consents", styles["Heading2"]))
        story.append(
            _kv_table(
                [
                    (c.consent_type.label, "Granted" if c.granted else "Refused")
                    for c in consents
                ]
            )
        )

    doc.build(story)
    return buffer.getvalue()
