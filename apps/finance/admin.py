from django.contrib import admin
from .models import (
    FinancialSeason, RegistrationPayment, ContributionCycle,
    Contribution, MemberFinanceSnapshot, NjangiBenefit,
    LoanProduct, LoanApplication, LoanGuarantor, Loan,
    LoanRepaymentSchedule, LoanPayment, Fine, FinePayment,
    InterestDistribution, InterestPayout, Expenditure
)


@admin.register(FinancialSeason)
class FinancialSeasonAdmin(admin.ModelAdmin):
    list_display = ('community', 'season_date', 'title', 'is_closed')
    list_filter = ('community', 'is_closed')
    search_fields = ('title', 'community__name')


@admin.register(RegistrationPayment)
class RegistrationPaymentAdmin(admin.ModelAdmin):
    list_display = ('application', 'amount', 'paid_at', 'is_confirmed')
    list_filter = ('is_confirmed', 'paid_at')
    raw_id_fields = ('application', 'received_by')


@admin.register(ContributionCycle)
class ContributionCycleAdmin(admin.ModelAdmin):
    list_display = ('community', 'title', 'due_date', 'expected_amount', 'is_special', 'is_closed')
    list_filter = ('community', 'is_special', 'is_closed')
    search_fields = ('title', 'community__name')


@admin.register(Contribution)
class ContributionAdmin(admin.ModelAdmin):
    list_display = ('membership', 'cycle', 'amount_paid', 'status', 'paid_at')
    list_filter = ('status', 'cycle__community', 'paid_at')
    search_fields = ('membership__user__email', 'cycle__title', 'payment_reference')
    raw_id_fields = ('membership', 'cycle', 'received_by')
    date_hierarchy = 'paid_at'


@admin.register(MemberFinanceSnapshot)
class MemberFinanceSnapshotAdmin(admin.ModelAdmin):
    list_display = ('membership', 'season', 'net_income', 'savings', 'njangi')
    list_filter = ('season', 'membership__community')
    raw_id_fields = ('membership', 'season', 'recorded_by')


@admin.register(NjangiBenefit)
class NjangiBenefitAdmin(admin.ModelAdmin):
    list_display = ('membership', 'season', 'amount', 'benefited_date')
    list_filter = ('season', 'membership__community', 'benefited_date')
    search_fields = ('membership__user__email', 'transaction_id')
    raw_id_fields = ('membership', 'season')


@admin.register(LoanProduct)
class LoanProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'community', 'interest_rate', 'max_amount', 'is_active')
    list_filter = ('community', 'is_active')
    search_fields = ('name', 'description')


@admin.register(LoanApplication)
class LoanApplicationAdmin(admin.ModelAdmin):
    list_display = ('membership', 'loan_product', 'amount_requested', 'status', 'submitted_at')
    list_filter = ('status', 'loan_product', 'submitted_at')
    search_fields = ('membership__user__email', 'purpose')
    raw_id_fields = ('membership', 'loan_product', 'season', 'decided_by')


@admin.register(LoanGuarantor)
class LoanGuarantorAdmin(admin.ModelAdmin):
    list_display = ('loan_application', 'guarantor_membership', 'is_confirmed', 'confirmed_at')
    list_filter = ('is_confirmed', 'confirmed_at')
    raw_id_fields = ('loan_application', 'guarantor_membership')


class LoanRepaymentScheduleInline(admin.TabularInline):
    model = LoanRepaymentSchedule
    extra = 0


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ('membership', 'amount_borrowed', 'amount_paid', 'status', 'borrow_date', 'maturity_date')
    list_filter = ('status', 'season', 'borrow_date')
    search_fields = ('membership__user__email', 'id_card_number')
    raw_id_fields = ('application', 'membership', 'season')
    inlines = [LoanRepaymentScheduleInline]


@admin.register(LoanPayment)
class LoanPaymentAdmin(admin.ModelAdmin):
    list_display = ('loan', 'amount', 'payment_date', 'recorded_by')
    list_filter = ('payment_date', 'season')
    raw_id_fields = ('loan', 'season', 'recorded_by')


@admin.register(Fine)
class FineAdmin(admin.ModelAdmin):
    list_display = ('membership', 'fine_type', 'amount', 'status', 'issued_date')
    list_filter = ('status', 'fine_type', 'issued_date')
    search_fields = ('membership__user__email', 'reason')
    raw_id_fields = ('membership', 'season', 'related_contribution', 'related_loan')


@admin.register(FinePayment)
class FinePaymentAdmin(admin.ModelAdmin):
    list_display = ('fine', 'amount', 'paid_at', 'received_by')
    list_filter = ('paid_at',)
    raw_id_fields = ('fine', 'received_by')

@admin.register(InterestDistribution)
class InterestDistributionAdmin(admin.ModelAdmin):
    list_display = ('season', 'community', 'total_interest_pool', 'distributed_at', 'status')
    list_filter = ('community', 'season', 'status')
    search_fields = ('season__title', 'community__name')

@admin.register(InterestPayout)
class InterestPayoutAdmin(admin.ModelAdmin):
    list_display = ('membership', 'interest_amount', 'is_paid', 'paid_at', 'distribution')
    list_filter = ('is_paid', 'distribution__season')
    search_fields = ('membership__user__email', 'membership__user__first_name', 'membership__user__last_name')

@admin.register(Expenditure)
class ExpenditureAdmin(admin.ModelAdmin):
    list_display = ('reference_number', 'community', 'source_fund', 'amount', 'expenditure_date', 'status')
    list_filter = ('status', 'source_fund', 'community', 'expenditure_date', 'season')
    search_fields = ('reference_number', 'description', 'community__name')
    raw_id_fields = ('community', 'season', 'created_by')
    date_hierarchy = 'expenditure_date'
    readonly_fields = ('reference_number', 'created')
