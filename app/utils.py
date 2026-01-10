from hashids import Hashids
import os


salt = os.getenv("salt")
if not salt:
    raise ValueError("No salt set")

hashids = Hashids(salt, min_length=7)

def encode_id(db_id: int) -> str:
    return hashids.encode(db_id)

def decode(hashed: str) -> int:
    decoded = hashids.decode(hashed)
    if not decoded:
        return None
    return decoded[0]

x = encode_id(324234)
print(x)
print(decode(x))
