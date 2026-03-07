from django.urls import path

from apps.finance.views.users_contribution_view import UsersContributionView

app_name = "finance"
    
urlpatterns = [
    path('contribution/', UsersContributionView.as_view(), name='users_contribution'),
]