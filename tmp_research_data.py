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
        print(f"  Season: {s.name} (ID: {s.id}), Is Closed: {s.is_closed}")

print("\n--- Active Members for first community found with 2026 season ---")
target_season = FinancialSeason.objects.filter(name__icontains="2026").first()
if target_season:
    community = target_season.community
    print(f"Target Community: {community.name}")
    memberships = Membership.objects.filter(community=community, status='active')
    print(f"Active Members count: {memberships.count()}")
    for m in memberships:
        print(f"  User: {m.user.email} ({m.user.fullname})")
else:
    print("No 2026 Season found.")
