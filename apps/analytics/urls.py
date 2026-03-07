from django.urls import path

from apps.analytics.views.member_creditscore_view import MemberCreditScoreView

app_name = "analytics"
    
urlpatterns = [
    path('creditscore/', MemberCreditScoreView.as_view(), name='member_credit_score'),
]