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
START_DATE = datetime(2024,5,9,0,0)
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
        print(f"Request {offset} status of {response.status} with time {elapsed_time}")
        return offset, response.status, elapsed_time, result


async def main(request_count:int):
    async with aiohttp.ClientSession() as session:
        tasks = [request(session, r) for r in range(request_count)]
        results = await asyncio.gather(*tasks)
        
        # Process results
        success_count = 0
        total_response_time = 0
        max_response_time = 0
        min_response_time = 99999999999999999999999
        for result in results:
            if result[1] == 201:
                success_count += 1
                total_response_time += result[2] 
                max_response_time = max(result[2], max_response_time)
                min_response_time = min(result[2], min_response_time)
        
        print(f"Successes {success_count} out of {request_count}")
        print(f"Time Stats = average:{total_response_time / success_count}, min:{min_response_time}, max:{max_response_time}")


if __name__ == "__main__":
    asyncio.run(main(2000))