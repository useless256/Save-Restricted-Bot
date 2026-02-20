# Don't Remove Credit 
# Ask Doubt on telegram @theprofessorreport_bot

import motor.motor_asyncio
import time
from config import DB_NAME, DB_URI

class Database:
    def __init__(self, uri, database_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.col = self.db.users
        self.settings = self.db.settings  # New collection for admin settings

    def new_user(self, id, name):
        return dict(
            id=id, 
            name=name, 
            session=None, 
            api_id=None, 
            api_hash=None,
            custom_caption=None, 
            thumb=None, 
            target_chat=None,
            upload_mode="PM", # Default mode: Private Message
            verify_token=0  # Timestamp for verification expiry
        )

    async def add_user(self, id, name):
        if not await self.is_user_exist(id):
            user = self.new_user(id, name)
            await self.col.insert_one(user)

    async def is_user_exist(self, id):
        user = await self.col.find_one({'id': int(id)})
        return bool(user)

    async def total_users_count(self):
        return await self.col.count_documents({})

    async def get_all_users(self):
        return self.col.find({})

    async def delete_user(self, user_id):
        await self.col.delete_many({'id': int(user_id)})

    # --- Session & API Methods ---
    async def set_session(self, id, session):
        await self.col.update_one({'id': int(id)}, {'$set': {'session': session}})
    
    async def get_session(self, id):
        user = await self.col.find_one({'id': int(id)})
        return user.get('session') if user else None

    async def set_api_id(self, id, api_id):
        await self.col.update_one({'id': int(id)}, {'$set': {'api_id': api_id}})

    async def get_api_id(self, id):
        user = await self.col.find_one({'id': int(id)})
        return user.get('api_id') if user else None

    async def set_api_hash(self, id, api_hash):
        await self.col.update_one({'id': int(id)}, {'$set': {'api_hash': api_hash}})

    async def get_api_hash(self, id):
        user = await self.col.find_one({'id': int(id)})
        return user.get('api_hash') if user else None

    # --- Settings Methods (Caption, Thumb, Chat) ---
    async def set_caption(self, id, caption):
        await self.col.update_one({'id': int(id)}, {'$set': {'custom_caption': caption}})
    
    async def get_caption(self, id):
        user = await self.col.find_one({'id': int(id)})
        return user.get('custom_caption') if user else None

    async def set_thumb(self, id, thumb_id):
        await self.col.update_one({'id': int(id)}, {'$set': {'thumb': thumb_id}})
    
    async def get_thumb(self, id):
        user = await self.col.find_one({'id': int(id)})
        return user.get('thumb') if user else None

    async def set_target_chat(self, id, chat_id):
        await self.col.update_one({'id': int(id)}, {'$set': {'target_chat': chat_id}})
    
    async def get_target_chat(self, id):
        user = await self.col.find_one({'id': int(id)})
        return user.get('target_chat') if user else None

    # --- Upload Mode Logic (PM or Channel) ---
    async def set_upload_mode(self, id, mode):
        # mode can be "PM" or "Channel"
        await self.col.update_one({'id': int(id)}, {'$set': {'upload_mode': mode}})

    async def get_upload_mode(self, id):
        user = await self.col.find_one({'id': int(id)})
        return user.get('upload_mode', "PM") if user else "PM"

    # --- Verification Logic (6 Hours Access) ---
    async def verify_user(self, id):
        expiry_time = time.time() + 21600  # Current time + 6 Hours
        await self.col.update_one({'id': int(id)}, {'$set': {'verify_token': expiry_time}})

    async def get_verify_status(self, id):
        user = await self.col.find_one({'id': int(id)})
        if not user: return False
        expiry = user.get('verify_token', 0)
        return expiry > time.time() 

    # --- Admin Config Methods (Toggle & Shortener) ---
    async def set_verify_status(self, status: bool):
        await self.settings.update_one({'id': 'verify_config'}, {'$set': {'is_on': status}}, upsert=True)

    async def update_shortener(self, url, api):
        await self.settings.update_one(
            {'id': 'verify_config'}, 
            {'$set': {'url': url, 'api': api}}, 
            upsert=True
        )

    async def get_verify_config(self):
        config = await self.settings.find_one({'id': 'verify_config'})
        if not config:
            return {"is_on": False, "url": None, "api": None}
        return config

db = Database(DB_URI, DB_NAME)
