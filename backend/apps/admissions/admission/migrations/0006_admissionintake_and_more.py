import uuid

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Schema-only, additive changes. Nothing here can lose data — the
    unsafe part (removing trial_waiver_reason/trial_waiver_approval, and
    the CheckConstraint that would reject any pre-existing row whose
    `source` doesn't yet reflect whether it has an enquiry) is split into
    0007, after a data migration backfills every existing row first.
    """

    dependencies = [
        ("admission", "0005_admission_fee_amount"),
        ("core", "0005_consenttype_feehead_documenttype_required_stage_and_more"),
        ("enquiry", "0001_initial"),
        ("people", "0002_guardian_staff_studentguardian"),
        ("trial", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="AdmissionIntake",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "admission_category",
                    models.CharField(
                        choices=[
                            ("residential", "Residential"),
                            ("non_residential", "Non-residential"),
                        ],
                        max_length=16,
                    ),
                ),
                (
                    "days_per_week",
                    models.SmallIntegerField(
                        blank=True,
                        choices=[(2, "2 days a week"), (3, "3 days a week")],
                        null=True,
                    ),
                ),
                (
                    "preferred_slot",
                    models.CharField(
                        blank=True,
                        choices=[("morning", "Morning"), ("evening", "Evening")],
                        max_length=10,
                    ),
                ),
                ("full_name", models.CharField(max_length=120)),
                ("date_of_birth", models.DateField()),
                (
                    "gender",
                    models.CharField(
                        choices=[("M", "Male"), ("F", "Female"), ("O", "Other")], max_length=1
                    ),
                ),
                (
                    "playing_role",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("batsman", "Batsman"),
                            ("bowler", "Bowler"),
                            ("all_rounder", "All-rounder"),
                            ("wicketkeeper", "Wicketkeeper"),
                        ],
                        max_length=20,
                    ),
                ),
                ("present_address", models.TextField()),
                ("city", models.CharField(max_length=80)),
                ("state", models.CharField(max_length=80)),
                (
                    "pin_code",
                    models.CharField(
                        max_length=6,
                        validators=[
                            django.core.validators.RegexValidator(
                                "^[1-9][0-9]{5}$", "Enter a valid 6-digit PIN code."
                            )
                        ],
                    ),
                ),
                ("student_mobile", models.CharField(blank=True, max_length=16)),
                ("guardian_name", models.CharField(max_length=120)),
                (
                    "guardian_relationship",
                    models.CharField(
                        choices=[
                            ("father", "Father"),
                            ("mother", "Mother"),
                            ("guardian", "Guardian"),
                            ("other", "Other"),
                        ],
                        max_length=20,
                    ),
                ),
                ("guardian_mobile", models.CharField(max_length=16)),
                ("emergency_contact", models.CharField(max_length=16)),
                ("local_guardian_name", models.CharField(blank=True, max_length=120)),
                ("local_guardian_mobile", models.CharField(blank=True, max_length=16)),
                (
                    "admission",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="intake",
                        to="admission.admission",
                    ),
                ),
                (
                    "age_category",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="core.agecategory",
                    ),
                ),
                (
                    "season",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="core.season",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.AddField(
            model_name="admission",
            name="cancelled_reason",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="admission",
            name="direct_admission_reason",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="admission",
            name="source",
            field=models.CharField(
                choices=[("enquiry", "Enquiry"), ("direct", "Direct")],
                default="enquiry",
                max_length=10,
            ),
        ),
        migrations.AlterField(
            model_name="admission",
            name="person",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="admissions",
                to="people.person",
            ),
        ),
        migrations.AlterField(
            model_name="admission",
            name="programme",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="admissions",
                to="core.programme",
            ),
        ),
        migrations.AlterField(
            model_name="admission",
            name="step",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("documents_pending", "Documents pending"),
                    ("documents_verified", "Documents verified"),
                    ("fee_pending", "Fee pending"),
                    ("fee_cleared", "Fee cleared"),
                    ("approved", "Approved"),
                    ("rejected", "Rejected"),
                    ("payment_recorded", "Payment recorded"),
                    ("payment_verified", "Payment verified"),
                    ("ready_for_approval", "Ready for approval"),
                    ("cancelled", "Cancelled"),
                ],
                default="draft",
                max_length=20,
            ),
        ),
    ]
