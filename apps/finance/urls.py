from django.urls import path

from apps.finance.views.users_contribution_view import UsersContributionView
from apps.finance.views.member_loan_view import MemberLoanView
from apps.finance.views.members_fine_view import MemberFineView
from apps.finance.views.admin_contribution_and_cycle_views import AdminContributionAndCycleView
from apps.finance.views.admin_contributions_view import AdminContributionsView
from apps.finance.views.contribution_api_view import SeasonAPI, CycleAPI, ContributionAPI, ContributionCycleAPI, ContributionRecordAPI, MemberSeasonContributionsAPI
from apps.finance.views.fine_api_view import FineEligibleMembersAPI, LaunchFinesAPI, FineListAPI, PayFineAPI, MemberFineListAPI
from apps.finance.views.fine_list_view import AdminFineListView
from apps.finance.views.njangi_api_view import NjangiRotationAPI, NjangiMeetingBeneficiaryAPI

app_name = "finance"
    
urlpatterns = [
    path('contribution/', UsersContributionView.as_view(), name='users_contribution'),
    path('loan/', MemberLoanView.as_view(), name='member_loan'),
    path('fine/', MemberFineView.as_view(), name='member_fine'),
    path('admin-fines/<uuid:community_id>/', AdminFineListView.as_view(), name='admin_fines'),
    path('admin-contribution/<uuid:community_id>/', AdminContributionAndCycleView.as_view(), name='admin_contribution'),
    path('admin-contributions/<uuid:community_id>/', AdminContributionsView.as_view(), name='admin_contributions'),
    # APIs
    path('api/community/<uuid:community_id>/seasons/', SeasonAPI.as_view(), name='season_api'),
    path('api/season/<uuid:season_id>/cycles/', CycleAPI.as_view(), name='cycle_api'),
    path('api/cycle/<uuid:cycle_id>/contributions/', ContributionAPI.as_view(), name='contribution_api'),
    path('api/cycle/<uuid:cycle_id>/fine-eligible/<str:fine_type>/', FineEligibleMembersAPI.as_view(), name='fine_eligible_api'),
    path('api/cycle/<uuid:cycle_id>/launch-fines/', LaunchFinesAPI.as_view(), name='launch_fines_api'),
    path('api/community/<uuid:community_id>/fines/', FineListAPI.as_view(), name='fine_list_api'),
    path('api/fine/<uuid:fine_id>/pay/', PayFineAPI.as_view(), name='pay_fine_api'),
    path('api/me/fines/', MemberFineListAPI.as_view(), name='member_fine_api'),
    # Njangi Rotation and Beneficiary
    path('api/season/<uuid:season_id>/njangi-rotation/', NjangiRotationAPI.as_view(), name='njangi_rotation_api'),
    path('api/njangi-rotation/<uuid:rotation_id>/', NjangiRotationAPI.as_view(), name='njangi_rotation_detail_api'),
    path('api/cycle/<uuid:cycle_id>/njangi-beneficiary/', NjangiMeetingBeneficiaryAPI.as_view(), name='njangi_meeting_beneficiary_api'),
    # Feature-type Contribution APIs (Savings, Entertainment, Sinking Fund, Project)
    path('api/season/<uuid:season_id>/feature-cycles/', ContributionCycleAPI.as_view(), name='feature_cycle_api'),
    path('api/cycle/<uuid:cycle_id>/feature-contributions/', ContributionRecordAPI.as_view(), name='feature_contribution_api'),
    path('api/season/<uuid:season_id>/membership/<uuid:membership_id>/contributions/', MemberSeasonContributionsAPI.as_view(), name='member_season_contributions_api'),
]

