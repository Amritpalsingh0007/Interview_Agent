import redis
from mongo.mongo_client import getCandidateDBData

client = redis.Redis(host='localhost', port=6379, decode_responses=True)


def addCandidateData(id:str):
    data = getCandidateDBData()
    client.hset(id, mapping={"resume": data.get("resume")})
    return data

def getCandidateData(id:str):
    data = client.hget(id, "resume")
    if data:
        return data
    return addCandidateData(id=id)