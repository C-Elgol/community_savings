from django.views.generic import TemplateView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.communities.models import Community
from apps.finance.models import FinancialSeason
from apps.finance.services.interest_sharing_service import InterestSharingService
from apps.finance.services.dashboard_service import DashboardService
from decimal import Decimal

from apps.finance.utils.admin_mixins import AdminSeasonMixin
from django.utils.decorators import method_decorator
from apps.log.decorators import log_activity_and_errors

class AdminInterestSharingView(AdminSeasonMixin, LoginRequiredMixin, TemplateView):
    template_name = "publics/admin/interest_shared/interest_shared.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        community_id = self.kwargs.get('community_id')
        community = get_object_or_404(Community, id=community_id)
        
        # Get active season from session (provided by AdminSeasonMixin)
        active_season = context.get('active_season')
        
        # Get interest earned from loans (as pool suggestion)
        db_service = DashboardService(community_id, season_id=active_season.id if active_season else None)
        loan_stats = db_service.loan_stats()
        
        context.update({
            'community': community,
            'seasons': FinancialSeason.objects.filter(community=community).order_by('-season_date'),
            'suggested_interest': loan_stats.get('interest_earned', '0.00'),
            'penalties_earned': loan_stats.get('penalties_earned', '0.00'),
        })
        return context

class InterestSharingAPI(APIView):
    """
    API for calculating and processing interest distribution.
    """
    def get(self, request, community_id):
        season_id = request.GET.get('season_id')
        total_interest = request.GET.get('total_interest')
        
        if not season_id or not total_interest:
            return Response({'success': False, 'error': 'Missing parameters'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            community = get_object_or_404(Community, id=community_id)
            service = InterestSharingService(community)
            
            # Check if distribution already exists for this season
            from apps.finance.models import InterestDistribution
            existing_dist = InterestDistribution.objects.filter(season_id=season_id).first()
            
            if existing_dist:
                # Return existing distribution data
                payouts = []
                for p in existing_dist.payouts.all().select_related('membership__user'):
                    payouts.append({
                        'payout_id': str(p.id),
                        'membership_id': str(p.membership_id),
                        'member_name': p.membership.user.fullname or p.membership.user.email,
                        'total_savings': str(p.total_savings),
                        'weighted_savings': str(p.weighted_savings),
                        'share_percentage': float(p.share_percentage),
                        'interest_amount': str(p.interest_amount),
                        'is_paid': p.is_paid,
                        'paid_at': p.paid_at.isoformat() if p.paid_at else None,
                        'expenditure_ref': p.expenditure_reference,
                        'transaction_ref': p.transaction_reference
                    })
                
                return Response({
                    'success': True,
                    'is_initialized': True,
                    'distribution_id': str(existing_dist.id),
                    'season_title': existing_dist.season.title or str(existing_dist.season.season_date),
                    'total_interest_pool': str(existing_dist.total_interest_pool),
                    'total_weighted_savings': str(existing_dist.total_weighted_savings),
                    'member_breakdown': payouts
                })

            # Otherwise return a preview
            preview = service.calculate_distribution_preview(season_id, total_interest)
            return Response({'success': True, 'is_initialized': False, **preview})
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @method_decorator(log_activity_and_errors())
    def post(self, request, community_id):
        action = request.data.get('action')
        community = get_object_or_404(Community, id=community_id)
        service = InterestSharingService(community)
        
        try:
            if action == 'distribute':
                season_id = request.data.get('season_id')
                total_interest = request.data.get('total_interest')
                dist, payouts = service.process_distribution(season_id, total_interest, request.user)
                return Response({'success': True, 'distribution_id': str(dist.id), 'payouts': payouts})

            elif action == 'pay':
                payout_id = request.data.get('payout_id')
                payout = service.record_payout(payout_id, request.user)
                return Response({
                    'success': True, 
                    'message': 'Payout recorded successfully',
                    'expenditure_ref': payout.expenditure_reference,
                    'transaction_ref': payout.transaction_reference
                })
            
            return Response({'success': False, 'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
