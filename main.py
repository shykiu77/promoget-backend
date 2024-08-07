import os
from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta

MONGODB_USERNAME = os.environ.get("MONGODB_USERNAME")
MONGODB_PASSWORD = os.environ.get("MONGODB_PASSWORD")
DATABASE_NAME = "gemini_ocr"
COLLECTION_NAME = "products"

MONGODB_URL = f"mongodb+srv://{MONGODB_USERNAME}:{MONGODB_PASSWORD}@promoget.vqlcely.mongodb.net/?retryWrites=true&w=majority&appName=promoget"

client = AsyncIOMotorClient(MONGODB_URL)
database = client[DATABASE_NAME]
collection = database[COLLECTION_NAME]

app = FastAPI()

origins = ["http://localhost:4200", "https://promoget.pages.dev"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ProductData(BaseModel):
    label: str
    unit: str
    normal_price: Optional[float]
    discounted_price: Optional[float]
    true_price: Optional[float]
    description: str
    base64_image: str
    location: str
    created_at: datetime

@app.get("/products", response_model=List[ProductData])
async def get_products(
    query: Optional[str] = None,
    order: str = "asc",
    page: int = 1,
    limit: int = 30,  # Updated page size
    priceMin: Optional[float] = None,
    priceMax: Optional[float] = None,
    daysAgo: Optional[int] = None,
    sort_by: str = "true_price"
):
    sort_order = 1 if order == "asc" else -1

    filter_criteria = {}
    if query:
        filter_criteria["label"] = {"$regex": query, "$options": "i"}

    if priceMin is not None or priceMax is not None:
        price_filters = {}
        if priceMin is not None:
            price_filters["$gte"] = priceMin
        if priceMax is not None:
            price_filters["$lte"] = priceMax
        filter_criteria["true_price"] = price_filters

    if daysAgo is not None:
        now = datetime.utcnow()
        dateMin = now - timedelta(days=daysAgo)
        filter_criteria["created_at"] = {"$gte": dateMin}

    valid_sort_fields = ["true_price", "created_at", "label"]
    if sort_by not in valid_sort_fields:
        raise HTTPException(status_code=400, detail=f"Invalid sort_by field. Must be one of: {valid_sort_fields}")

    cursor = collection.aggregate([
        {"$match": filter_criteria},
        {"$sort": {sort_by: sort_order}},
        {"$skip": (page - 1) * limit},
        {"$limit": limit}
    ])
    results = await cursor.to_list(length=limit)

    if not results:
        raise HTTPException(status_code=404, detail="No products found")

    return [ProductData(**result) for result in results]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, port=8000)