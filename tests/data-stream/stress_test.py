import os
from datetime import datetime, timedelta

from dotenv import load_dotenv 

import asyncio
import aiohttp
import time

load_dotenv()

URL = 'http://staging.monitormywatershed.org/api/data-stream/'
HEADERS = {
    'TOKEN' : os.getenv("TOKEN")
}
START_DATE = datetime.now()
SAMPLING_FEATURE = os.getenv("SAMPLINGFEATUREUUID")
RESULT = os.getenv("RESULTUUID")

async def format_payload(offset:int):
    timestamp =  (START_DATE + timedelta(seconds=offset)).strftime('%Y-%m-%dT%H:%M:%S+00:00')
    payload = {}
    payload['sampling_feature'] = SAMPLING_FEATURE
    payload['timestamp'] = timestamp
    payload[RESULT] = -9999
    return payload
    

async def request(session, offset:int):
    payload = await format_payload(offset) 
    start = time.time()
    async with session.post(URL, headers=HEADERS, data=payload) as response:
        result = await response.json()
        elapsed_time = time.time() - start
        return response.status, offset, elapsed_time, result


async def main(request_count:int):
    async with aiohttp.ClientSession() as session:
        tasks = [request(session, r) for r in range(request_count)]
        results = await asyncio.gather(*tasks)
        
        # Process results
        for result in results:
            print(f"Request {result[0]} status of {result[1]} with time {result[2]}")

if __name__ == "__main__":
    asyncio.run(main(45))