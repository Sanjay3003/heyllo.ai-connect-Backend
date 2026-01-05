"""
Quick fix script to create missing tenant and profile for existing users
Run this if you get "No tenant assigned" error
"""

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models import User, Tenant, Profile

def fix_user_tenants():
    """Create tenants and profiles for users that don't have them"""
    db: Session = SessionLocal()
    
    try:
        # Get all users
        users = db.query(User).all()
        
        for user in users:
            # Check if user has a profile
            profile = db.query(Profile).filter(Profile.user_id == user.id).first()
            
            if not profile:
                print(f"Fixing user: {user.email}")
                
                # Create tenant
                tenant = Tenant(name=f"{user.full_name}'s Organization")
                db.add(tenant)
                db.flush()
                
                # Create profile
                profile = Profile(user_id=user.id, tenant_id=tenant.id)
                db.add(profile)
                db.commit()
                
                print(f"  ✓ Created tenant: {tenant.id}")
                print(f"  ✓ Created profile linking user to tenant")
            else:
                print(f"User {user.email} already has tenant: {profile.tenant_id}")
        
        print("\n✅ All users now have tenants!")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("Fixing user tenants...\n")
    fix_user_tenants()
