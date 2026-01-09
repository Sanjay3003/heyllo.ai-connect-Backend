from app.database import SessionLocal
from app.models import Call
from uuid import UUID

db = SessionLocal()
call_id = UUID('29a61ef4-1173-42ca-99e6-c9fa2fc64467')
tenant_id = UUID('6149403e-bcd1-4429-8d99-81aba04365b9')

print(f"Searching for Call ID: {call_id} (Type: {type(call_id)})")
print(f"Searching for Tenant ID: {tenant_id} (Type: {type(tenant_id)})")

# Try with UUID objects
call = db.query(Call).filter(Call.id == call_id, Call.tenant_id == tenant_id).first()
print(f"Result with UUID objects: {'Found' if call else 'Not Found'}")

# Try with strings
call_str = db.query(Call).filter(Call.id == str(call_id), Call.tenant_id == str(tenant_id)).first()
print(f"Result with Strings: {'Found' if call_str else 'Not Found'}")

db.close()
