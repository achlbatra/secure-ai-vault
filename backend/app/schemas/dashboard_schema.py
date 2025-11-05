from pydantic import BaseModel

class DashboardItemCreate(BaseModel):
    documents_processed: int
    security_score: int
    pii_items_protected: int
    pending_reviews: int

    class Config:
        from_attributes = True  # replaces orm_mode in Pydantic v2
