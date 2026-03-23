from django.urls import path

from apps.finance.views.users_contribution_view import UsersContributionView
from apps.finance.views.member_loan_view import MemberLoanView
from apps.finance.views.members_fine_view import MemberFineView
from apps.finance.views.admin_contribution_and_cycle_views import AdminContributionAndCycleView
from apps.finance.views.contribution_api_view import SeasonAPI, CycleAPI, ContributionAPI
from apps.finance.views.fine_api_view import FineEligibleMembersAPI, LaunchFinesAPI

app_name = "finance"
    
urlpatterns = [
    path('contribution/', UsersContributionView.as_view(), name='users_contribution'),
    path('loan/', MemberLoanView.as_view(), name='member_loan'),
    path('fine/', MemberFineView.as_view(), name='member_fine'),
    path('admin-contribution/<uuid:community_id>/', AdminContributionAndCycleView.as_view(), name='admin_contribution'),
    # APIs
    path('api/community/<uuid:community_id>/seasons/', SeasonAPI.as_view(), name='season_api'),
    path('api/season/<uuid:season_id>/cycles/', CycleAPI.as_view(), name='cycle_api'),
    path('api/cycle/<uuid:cycle_id>/contributions/', ContributionAPI.as_view(), name='contribution_api'),
    path('api/cycle/<uuid:cycle_id>/fine-eligible/<str:fine_type>/', FineEligibleMembersAPI.as_view(), name='fine_eligible_api'),
    path('api/cycle/<uuid:cycle_id>/launch-fines/', LaunchFinesAPI.as_view(), name='launch_fines_api'),
]
