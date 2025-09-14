from pymongo import MongoClient, ASCENDING
from config import Config
from datetime import datetime

client = MongoClient(Config.MONGO_URI)
db = client["talktotext"] 
users = db.users
notes = db.notes
uploads = db.uploads

# Indexes
users.create_index([("email", ASCENDING)], unique=True)
notes.create_index([("user_id", ASCENDING), ("created_at", ASCENDING)])
uploads.create_index([("status", ASCENDING)]) 
