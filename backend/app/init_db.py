from app.core.database import Base, engine
from app.models import user, document, audit_log

print(" Creating database tables...")
Base.metadata.create_all(bind=engine)
print(" Tables created successfully!")
