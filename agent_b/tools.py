from pymongo import MongoClient
import statistics

client = MongoClient("mongodb://mongo:27017")
db = client.testdb

def calculateEggAverage():
    col = db.monthly_egg_prices
    docs = list(col.find({}, {"price": 1}))
    print("DEBUG - Retrieved docs:", docs)  # 👈 print here
    if not docs:
        return None
    prices = [d["price"] for d in docs]
    print("DEBUG - Prices list:", prices)   # 👈 another print here
    return round(statistics.mean(prices), 2)

def calculateMilkAverage():
    col = db.monthly_milk_prices
    docs = list(col.find({}, {"price": 1}))
    if not docs: return None
    prices = [d["price"] for d in docs]
    return round(statistics.mean(prices), 2)

def calculateBreadAverage():
    col = db.monthly_bread_prices
    docs = list(col.find({}, {"price": 1}))
    if not docs: return None
    prices = [d["price"] for d in docs]
    return round(statistics.mean(prices), 2)

TOOL_REGISTRY = {
    "calculateEggAverage": calculateEggAverage,
    "calculateMilkAverage": calculateMilkAverage,
    "calculateBreadAverage": calculateBreadAverage,
}