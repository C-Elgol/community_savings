from django.contrib import admin
from .models import MemberBehaviorSnapshot, CreditProfile, LoanRiskAssessment, CreditScoreHistory


@admin.register(MemberBehaviorSnapshot)
class MemberBehaviorSnapshotAdmin(admin.ModelAdmin):
    list_display = ('membership', 'season', 'contribution_consistency', 'repayment_punctuality', 'attendance_rate')
    list_filter = ('season', 'membership__community')
    raw_id_fields = ('membership', 'season')


@admin.register(CreditProfile)
class CreditProfileAdmin(admin.ModelAdmin):
    list_display = ('membership', 'current_score', 'risk_band', 'creditworthiness', 'last_assessed_at')
    list_filter = ('risk_band', 'creditworthiness')
    search_fields = ('membership__user__email', 'membership__user__first_name', 'membership__user__last_name')
    raw_id_fields = ('membership',)
    readonly_fields = ('last_assessed_at',)


@admin.register(LoanRiskAssessment)
class LoanRiskAssessmentAdmin(admin.ModelAdmin):
    list_display = ('membership', 'loan_application', 'score_used', 'risk_band', 'creditworthiness', 'probability_of_default')
    list_filter = ('risk_band', 'creditworthiness')
    raw_id_fields = ('membership', 'loan_application')


@admin.register(CreditScoreHistory)
class CreditScoreHistoryAdmin(admin.ModelAdmin):
    list_display = ('membership', 'season', 'score', 'risk_band', 'creditworthiness', 'assessed_at')
    list_filter = ('risk_band', 'creditworthiness', 'assessed_at')
    raw_id_fields = ('membership', 'season')
    readonly_fields = ('assessed_at',)
