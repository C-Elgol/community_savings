import logging
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.conf import settings
from openai import OpenAI

from apps.communities.models import Membership
from apps.finance.models import (
    Contribution, ContributionCycle, Loan, LoanPayment, 
    LoanRepaymentSchedule, LoanPenalty, Fine, FinancialSeason
)
from apps.meetings.models import MeetingAttendance, Meeting
from apps.analytics.models import CreditProfile, MemberBehaviorSnapshot, CreditScoreHistory
from apps.global_data.enum import RiskBand, CreditworthinessLevel, ContributionStatus, LoanStatus

logger = logging.getLogger(__name__)

class CreditScoringService:
    """
    Service to calculate credit scores and risk profiles for community members.
    Score range: 300 - 850
    """
    
    BASE_SCORE = 300
    MAX_ADDITIONAL_SCORE = 550
    
    WEIGHTS = {
        'savings_consistency': Decimal('0.30'),
        'repayment_reliability': Decimal('0.40'),
        'financial_stability': Decimal('0.20'),
        'engagement': Decimal('0.10'),
    }

    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY) if hasattr(settings, 'OPENAI_API_KEY') else None

    def calculate_score(self, membership: Membership):
        """
        Main entry point for score calculation.
        """
        community = membership.community
        
        # 1. Savings Consistency (30%)
        savings_score = self._calculate_savings_consistency(membership)
        
        # 2. Repayment Reliability (40%)
        repayment_score = self._calculate_repayment_reliability(membership)
        
        # 3. Financial Stability (20%)
        stability_score = self._calculate_financial_stability(membership)
        
        # 4. Engagement (10%)
        engagement_score = self._calculate_engagement(membership)
        
        total_relative_score = (
            (savings_score * self.WEIGHTS['savings_consistency']) +
            (repayment_score * self.WEIGHTS['repayment_reliability']) +
            (stability_score * self.WEIGHTS['financial_stability']) +
            (engagement_score * self.WEIGHTS['engagement'])
        )
        total_relative_score = max(Decimal('0'), min(Decimal('1'), total_relative_score))
        
        final_score = int(self.BASE_SCORE + (total_relative_score * self.MAX_ADDITIONAL_SCORE))
        final_score = max(self.BASE_SCORE, min(850, final_score))
        
        # Determine Risk Band and Creditworthiness
        risk_band = self._determine_risk_band(final_score)
        creditworthiness = self._determine_creditworthiness(final_score)
        
        # Calculate Recommended Safe Loan Amount
        recommended_loan = self._calculate_safe_loan_amount(membership, final_score)
        
        # Generate AI Explanation
        explanation_text = self._generate_ai_explanation(membership, {
            'score': final_score,
            'risk_band': risk_band,
            'savings_score': savings_score,
            'repayment_score': repayment_score,
            'stability_score': stability_score,
            'engagement_score': engagement_score,
        })
        explanation_json = {'ai_summary': explanation_text, 'timestamp': timezone.now().isoformat()}
        
        # Update or Create Credit Profile
        profile, created = CreditProfile.objects.update_or_create(
            membership=membership,
            defaults={
                'current_score': final_score,
                'risk_band': risk_band,
                'creditworthiness': creditworthiness,
                'recommended_max_loan_amount': recommended_loan,
                'probability_of_default': max(Decimal('0'), Decimal('1.0') - total_relative_score),
                'explanation': explanation_json,
                'last_assessed_at': timezone.now(),
            }
        )
        
        # Save History
        active_season = FinancialSeason.objects.filter(community=community, is_closed=False).first()
        if active_season:
            CreditScoreHistory.objects.create(
                membership=membership,
                season=active_season,
                score=final_score,
                risk_band=risk_band,
                creditworthiness=creditworthiness,
                probability_of_default=profile.probability_of_default,
                recommended_max_loan_amount=recommended_loan,
                explanation=explanation_json
            )
            
        return profile, explanation_text

    def _calculate_savings_consistency(self, membership):
        cycles = ContributionCycle.objects.filter(community=membership.community)
        if not cycles.exists():
            return Decimal('0.5') # Neutral for new groups
            
        total_cycles = cycles.count()
        paid_contributions = Contribution.objects.filter(
            membership=membership,
            status=ContributionStatus.PAID
        ).count()
        
        consistency = Decimal(paid_contributions) / Decimal(total_cycles)
        return max(Decimal('0'), min(Decimal('1'), consistency))

    def _calculate_repayment_reliability(self, membership):
        loans = Loan.objects.filter(membership=membership)
        if not loans.exists():
            return Decimal('0.7') # Higher neutral for those who haven't borrowed yet
            
        # Check for defaults or overdue
        total_loans = loans.count()
        problem_loans = loans.filter(status__in=[LoanStatus.DEFAULTED, LoanStatus.OVERDUE, LoanStatus.UNPAID]).count()
        
        # Check penalties
        penalties = LoanPenalty.objects.filter(loan__membership=membership).count()
        
        reliability = Decimal(1.0) - (Decimal(problem_loans) / Decimal(total_loans))
        if penalties > 0:
            reliability *= Decimal('0.8') # Penalty for any penalty
            
        return max(Decimal('0'), min(Decimal('1'), reliability))

    def _calculate_financial_stability(self, membership):
        total_savings = Contribution.objects.filter(
            membership=membership,
            status=ContributionStatus.PAID
        ).aggregate(total=Sum('amount_paid'))['total'] or Decimal('0')
        
        active_loans_balance = Loan.objects.filter(
            membership=membership,
            status=LoanStatus.ACTIVE
        ).aggregate(total=Sum('amount_borrowed'))['total'] or Decimal('0')
        
        if total_savings == 0:
            return Decimal('0')
            
        ratio = active_loans_balance / total_savings
        # 1.0 is neutral (borrowed exactly what they saved)
        # > 3.0 is risky
        stability = Decimal('1.0') - (ratio / Decimal('3.0'))
        return max(Decimal('0'), min(Decimal('1'), stability))

    def _calculate_engagement(self, membership):
        attendances = MeetingAttendance.objects.filter(membership=membership)
        if not attendances.exists():
            return Decimal('0.5')
            
        present = attendances.filter(was_present=True).count()
        late = attendances.filter(arrived_late=True).count()
        
        rate = (Decimal(present) + (Decimal(late) * Decimal('0.5'))) / Decimal(attendances.count())
        
        # Also factor in fines
        fines = Fine.objects.filter(membership=membership).count()
        if fines > 2:
            rate *= Decimal('0.9')
            
        return max(Decimal('0'), min(Decimal('1'), rate))

    def _determine_risk_band(self, score):
        if score >= 750: return RiskBand.LOW
        if score >= 650: return RiskBand.MEDIUM
        if score >= 550: return RiskBand.HIGH
        return RiskBand.CRITICAL

    def _determine_creditworthiness(self, score):
        if score >= 800: return CreditworthinessLevel.EXCELLENT
        if score >= 700: return CreditworthinessLevel.GOOD
        if score >= 600: return CreditworthinessLevel.FAIR
        if score >= 450: return CreditworthinessLevel.POOR
        return CreditworthinessLevel.VERY_POOR

    def _calculate_safe_loan_amount(self, membership, score):
        # Look at community policy
        policy = getattr(membership.community, 'policy', None)
        max_multiple = Decimal('2.0')
        if policy:
            max_multiple = policy.max_loan_multiple_of_savings
            
        total_savings = Contribution.objects.filter(
            membership=membership,
            status=ContributionStatus.PAID
        ).aggregate(total=Sum('amount_paid'))['total'] or Decimal('0')
        
        # Adjust multiple by score
        score_multiplier = Decimal(score - 300) / Decimal(550)
        adjusted_multiple = max_multiple * score_multiplier
        
        return total_savings * adjusted_multiple

    def _generate_ai_explanation(self, membership, metrics):
        if not self.client:
            return "AI explanation unavailable (API key missing)."
            
        prompt = f"""
        Analyze the following credit risk data for {membership.user.fullname}:
        - Credit Score: {metrics['score']}/850
        - Risk Band: {metrics['risk_band']}
        - Savings consistency: {metrics['savings_score']:.2%}
        - Repayment reliability: {metrics['repayment_score']:.2%}
        - Financial stability: {metrics['stability_score']:.2%}
        - Engagement score: {metrics['engagement_score']:.2%}
        
        Provide a concise, professional summary (max 3 sentences) explaining why this member has this risk level.
        Focus on their strengths and weaknesses in the context of a community savings group.
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error generating AI explanation: {e}")
            return "Failed to generate AI explanation."
