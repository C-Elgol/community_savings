from django.urls import path

from apps.analytics.views.member_creditscore_view import MemberCreditScoreView
from apps.analytics.views.admin_analytics_views import AdminCreditRiskDashboardView, RecalculateCreditScoreAPI, LoanRiskAssessmentAPI

app_name = "analytics"
    
urlpatterns = [
    path('creditscore/', MemberCreditScoreView.as_view(), name='member_credit_score'),
    path('admin-credit-risk/<uuid:community_id>/', AdminCreditRiskDashboardView.as_view(), name='admin_credit_risk'),
    path('api/recalculate-scoring/', RecalculateCreditScoreAPI.as_view(), name='recalculate_scoring_api'),
    path('api/loan-assessment/<uuid:application_id>/', LoanRiskAssessmentAPI.as_view(), name='loan_assessment_api'),
]