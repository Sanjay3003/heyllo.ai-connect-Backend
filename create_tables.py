"""
Script to create all database tables
Run this with: python create_tables.py
"""

from app.database import Base, engine
from app.models import User, Profile, Tenant, Lead, Campaign, CampaignLead, Call

print("Creating all database tables...")

try:
    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("✅ All tables created successfully!")
    print("\nCreated tables:")
    print("- users")
    print("- profiles")
    print("- tenants")
    print("- leads")
    print("- campaigns")
    print("- campaign_leads")
    print("- calls")
except Exception as e:
    print(f"❌ Error creating tables: {e}")
    import traceback
    traceback.print_exc()
