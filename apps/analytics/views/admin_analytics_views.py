from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.db.models import Avg, Sum, Count
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _

from apps.communities.models import Community, Membership
from apps.finance.models import LoanApplication
from apps.analytics.models import CreditProfile, RiskBand, LoanRiskAssessment
from apps.analytics.services.scoring_service import CreditScoringService
from apps.finance.utils.admin_mixins import AdminSeasonMixin

class AdminCreditRiskDashboardView(AdminSeasonMixin, LoginRequiredMixin, TemplateView):
    template_name = 'publics/admin/credit_risk_analytics/credit_risk_analytics.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        community = get_object_or_404(Community, id=self.kwargs['community_id'])
        context['community'] = community
        
        # Get all members with their credit profiles
        memberships = Membership.objects.filter(community=community, status='active').select_related('user', 'credit_profile')
        
        # Risk Distribution
        profiles = CreditProfile.objects.filter(membership__community=community)
        context['risk_stats'] = {
            'high': profiles.filter(risk_band__in=[RiskBand.HIGH, RiskBand.CRITICAL]).count(),
            'medium': profiles.filter(risk_band=RiskBand.MEDIUM).count(),
            'low': profiles.filter(risk_band=RiskBand.LOW).count(),
            'total_assessed': profiles.count(),
            'avg_score': profiles.aggregate(avg=Avg('current_score'))['avg'] or 0
        }
        
        # Top 5 Default Probability
        context['top_prob_defaults'] = profiles.order_by('-probability_of_default')[:5]
        
        context['memberships'] = memberships
        return context

class LoanRiskAssessmentAPI(LoginRequiredMixin, View):
    """
    API to get or generate a risk assessment for a specific loan application.
    """
    def get(self, request, application_id):
        application = get_object_or_404(LoanApplication, id=application_id)
        service = CreditScoringService()
        
        # Get or calculate current profile
        profile, _ = service.calculate_score(application.membership)
        
        # Generate assessment for this specific loan
        assessment, created = LoanRiskAssessment.objects.get_or_create(
            loan_application=application,
            defaults={
                'membership': application.membership,
                'score_used': profile.current_score,
                'risk_band': profile.risk_band,
                'creditworthiness': profile.creditworthiness,
                'probability_of_default': profile.probability_of_default,
                'recommended_max_loan_amount': profile.recommended_max_loan_amount,
                'recommendation': 'Approve' if profile.current_score >= 650 else 'Review Carefully'
            }
        )
        
        return JsonResponse({
            'success': True,
            'score': profile.current_score,
            'risk_band': profile.risk_band,
            'creditworthiness': profile.creditworthiness,
            'recommended_amount': str(profile.recommended_max_loan_amount),
            'explanation': profile.explanation.get('ai_summary', "No explanation generated yet."),
            'recommendation': assessment.recommendation
        })

class RecalculateCreditScoreAPI(LoginRequiredMixin, View):
    """
    API to trigger recalculation for a single member or all members in a community.
    """
    def post(self, request, *args, **kwargs):
        community_id = request.POST.get('community_id')
        membership_id = request.POST.get('membership_id')
        
        service = CreditScoringService()
        
        if membership_id:
            membership = get_object_or_404(Membership, id=membership_id)
            profile, explanation = service.calculate_score(membership)
            return JsonResponse({
                'status': 'success',
                'score': profile.current_score,
                'risk_band': profile.risk_band,
                'explanation': explanation
            })
        elif community_id:
            memberships = Membership.objects.filter(community_id=community_id, status='active')
            for member in memberships:
                service.calculate_score(member)
            return JsonResponse({'status': 'success', 'message': f'Recalculated for {memberships.count()} members.'})
            
        return JsonResponse({'status': 'error', 'message': 'Missing parameters.'}, status=400)
