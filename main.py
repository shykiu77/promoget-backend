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
