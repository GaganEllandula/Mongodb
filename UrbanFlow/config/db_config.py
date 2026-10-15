"""
Database Connection Manager using PyMongo.
Manages singleton connection client and connection pooling.
"""
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import sys

MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "urbanflow_telemetry"

class DatabaseManager:
    _client = None

    @classmethod
    def get_client(cls) -> MongoClient:
        if cls._client is None:
            try:
                cls._client = MongoClient(
                    MONGO_URI,
                    serverSelectionTimeoutMS=5000,
                    maxPoolSize=50,
                    minPoolSize=10
                )
                # Force connection verification
                cls._client.admin.command('ping')
            except (ConnectionFailure, ServerSelectionTimeoutError) as err:
                print(f"[ERROR] Failed to connect to MongoDB server: {err}")
                sys.exit(1)
        return cls._client

    @classmethod
    def get_database(cls):
        client = cls.get_client()
        return client[DB_NAME]

    @classmethod
    def close_connection(cls):
        if cls._client:
            cls._client.close()
            cls._client = None