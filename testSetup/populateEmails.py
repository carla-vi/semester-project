from pymongo import MongoClient
from datetime import datetime, timezone

# Connect to MongoDB (default local Docker setup)
client = MongoClient("mongodb://mongo:27017")

# Choose database and collection
db = client.testdb
col = db.messages

# Clean previous test data (optional)
col.delete_many({})

# Insert test messages
emails = [
    {
        "id": "mail-1",
        "from": "robert@example.com",
        "subject": "Market quick check",
        "received_at": datetime(2025, 9, 18, 10, 0, tzinfo=timezone.utc),
        "body_text": "Fetch the company’s EUR->USD, EUR->GBP, EUR->CHF rates and compare to the ECB."
    },
    {
        "id": "mail-2",
        "from": "alice@example.com",
        "subject": "Morning brief",
        "received_at": datetime(2025, 9, 18, 8, 30, tzinfo=timezone.utc),
        "body_text": "Some notes about today’s meeting..."
    },
    {
        "id": "mail-3",
        "from": "carla@example.com",
        "subject": "Follow-up",
        "received_at": datetime(2025, 9, 17, 16, 45, tzinfo=timezone.utc),
        "body_text": "Quick reminder about the project status."
    }
]

col.insert_many(emails)
print("Inserted test emails:")
for e in emails:
    print("-", e["id"], e["subject"])