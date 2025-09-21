from pymongo import MongoClient
from datetime import datetime, timezone, timedelta

# Connect to MongoDB
client = MongoClient("mongodb://mongo:27017")

# Choose database and collection
db = client.testdb
col = db.monthly_egg_prices

# Clean previous test data
col.delete_many({})

# Generate dummy monthly egg prices for the last 6 months
base_price = 2.10  # starting price
egg_prices = []
today = datetime.now(tz=timezone.utc)

for i in range(6):
    # Compute month (going backwards from current month)
    month_date = (today.replace(day=1) - timedelta(days=30 * i))
    
    # Simulate some variation in price
    price = round(base_price + (i * 0.05), 2)  
    
    egg_prices.append({
        "id": f"egg-{i+1}",
        "product": "eggs",
        "unit": "dozen",
        "price": price,
        "currency": "EUR",
        "month": month_date.strftime("%Y-%m"),  # "2025-09"
        "date": month_date  # full datetime for reference
    })

# Insert into MongoDB
col.insert_many(egg_prices)

print("Inserted test monthly egg prices:")
for e in egg_prices:
    print("-", e["month"], "->", e["price"], e["currency"])