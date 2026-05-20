import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.communities.models import Community, Membership
from apps.finance.models import FinancialSeason

print("--- Communities and Seasons ---")
communities = Community.objects.all()
for c in communities:
    print(f"Community: {c.name} (ID: {c.id})")
    seasons = FinancialSeason.objects.filter(community=c)
    for s in seasons:
        print(f"  Season Date: {s.season_date}, Title: {s.title}, Is Closed: {s.is_closed}")

print("\n--- Identifying Target Community and 2026 Season ---")
# Try to find a season with title "2026" or season_date in 2026
target_season = FinancialSeason.objects.filter(title__icontains="2026").first()
if not target_season:
    from datetime import date
    target_season = FinancialSeason.objects.filter(season_date__year=2026).first()

if target_season:
    community = target_season.community
    print(f"Target Community: {community.name} (ID: {community.id})")
    print(f"Target Season: {target_season.title} ({target_season.season_date})")
    memberships = Membership.objects.filter(community=community, status='active')
    print(f"Active Members count: {memberships.count()}")
    for m in memberships:
         print(f"  User: {m.user.email} ({m.user.fullname})")
else:
    print("No 2026 Season found.")
