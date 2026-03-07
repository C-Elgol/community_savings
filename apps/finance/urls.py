from django.urls import path

from apps.finance.views.users_contribution_view import UsersContributionView
from apps.finance.views.member_loan_view import MemberLoanView
from apps.finance.views.members_fine_view import MemberFineView

app_name = "finance"
    
urlpatterns = [
    path('contribution/', UsersContributionView.as_view(), name='users_contribution'),
    path('loan/', MemberLoanView.as_view(), name='member_loan'),
    path('fine/', MemberFineView.as_view(), name='member_fine'),
]