from django.db import models
from django.utils.translation import gettext_lazy as _


class CommunityType(models.TextChoices):
    NJANGI = "njangi", _("Njangi")
    SAVINGS = "savings", _("Savings Group")
    COOPERATIVE = "cooperative", _("Cooperative")
    MEETING = "meeting", _("Meeting Group")
    INVESTMENT = "investment", _("Investment Group")
    OTHER = "other", _("Other")

class CommunitySpaceRole(models.TextChoices):
    OWNER = "owner", _("Owner")
    ADMIN = "admin", _("Admin")
    MANAGER = "manager", _("Manager")
    VIEWER = "viewer", _("Viewer")


class CommunitySpaceStatus(models.TextChoices):
    ACTIVE = "active", _("Active")
    SUSPENDED = "suspended", _("Suspended")
    ARCHIVED = "archived", _("Archived")

class MembershipRole(models.TextChoices):
    MEMBER = "member", _("Member")
    ADMIN = "admin", _("Admin")
    CHAIRPERSON = "chairperson", _("Chairperson")
    SECRETARY = "secretary", _("Secretary")
    TREASURER = "treasurer", _("Treasurer")
    AUDITOR = "auditor", _("Auditor")
    LOAN_OFFICER = "loan_officer", _("Loan Officer")


class MembershipStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    APPROVED = "approved", _("Approved")
    ACTIVE = "active", _("Active")
    SUSPENDED = "suspended", _("Suspended")
    REJECTED = "rejected", _("Rejected")
    EXITED = "exited", _("Exited")


class RegistrationFeeMode(models.TextChoices):
    NONE = "none", _("No Registration Fee")
    FIXED = "fixed", _("Fixed Registration Fee")


class ContributionFrequency(models.TextChoices):
    WEEKLY = "weekly", _("Weekly")
    MONTHLY = "monthly", _("Monthly")
    QUARTERLY = "quarterly", _("Quarterly")
    YEARLY = "yearly", _("Yearly")
    CUSTOM = "custom", _("Custom")


class ContributionStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    PARTIAL = "partial", _("Partial")
    PAID = "paid", _("Paid")
    OVERDUE = "overdue", _("Overdue")
    WAIVED = "waived", _("Waived")


class LoanApplicationStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    SUBMITTED = "submitted", _("Submitted")
    UNDER_REVIEW = "under_review", _("Under Review")
    APPROVED = "approved", _("Approved")
    REJECTED = "rejected", _("Rejected")
    DISBURSED = "disbursed", _("Disbursed")
    CANCELLED = "cancelled", _("Cancelled")


class LoanStatus(models.TextChoices):
    ACTIVE = "active", _("Active")
    PARTIAL = "partial", _("Partially Paid")
    PAID = "paid", _("Paid")
    UNPAID = "unpaid", _("Unpaid")
    OVERDUE = "overdue", _("Overdue")
    DEFAULTED = "defaulted", _("Defaulted")
    CANCELLED = "cancelled", _("Cancelled")


class FineType(models.TextChoices):
    LATE_CONTRIBUTION = "late_contribution", _("Late Contribution")
    ABSENCE = "absence", _("Absence")
    LATE_REPAYMENT = "late_repayment", _("Late Repayment")
    MANUAL = "manual", _("Manual")


class FineStatus(models.TextChoices):
    UNPAID = "unpaid", _("Unpaid")
    PARTIAL = "partial", _("Partial")
    PAID = "paid", _("Paid")
    WAIVED = "waived", _("Waived")


class MinuteStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    FINAL = "final", _("Final")


class RiskBand(models.TextChoices):
    LOW = "low", _("Low")
    MEDIUM = "medium", _("Medium")
    HIGH = "high", _("High")
    CRITICAL = "critical", _("Critical")


class CreditworthinessLevel(models.TextChoices):
    EXCELLENT = "excellent", _("Excellent")
    GOOD = "good", _("Good")
    FAIR = "fair", _("Fair")
    POOR = "poor", _("Poor")
    VERY_POOR = "very_poor", _("Very Poor")


class LogSystemStatus(models.TextChoices):
    SUCCESS = "SUCCESS", _("Success")
    FAILED = "FAILED", _("Failed")
    WARNING = "WARNING", _("Warning")

class CommunityFeatureType(models.TextChoices):
    NJANGI = "njangi", _("Njangi")
    SAVINGS = "savings", _("Savings")
    LOANS = "loans", _("Loans")
    PROJECT = "project", _("Project")
    ENTERTAINMENT = "entertainment", _("Entertainment")
    SINKING_FUND = "sinking_fund", _("Sinking Fund")
    EVENTS = "events", _("Events")
    MEETINGS = "meetings", _("Meetings")

class RepaymentFrequency(models.TextChoices):
    WEEKLY = "weekly", _("Weekly")
    BIWEEKLY = "biweekly", _("Biweekly")
    MONTHLY = "monthly", _("Monthly")
    