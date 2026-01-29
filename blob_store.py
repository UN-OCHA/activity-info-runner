import os
import pickle
import uuid
from typing import Any, Union
import aiofiles
from pydantic import BaseModel

BLOB_STORE_PATH = os.getenv("BLOB_STORE_PATH", ".blobs")

class BlobRef(BaseModel):
    ref_id: str
    path: str

async def save_blob(data: Any) -> BlobRef:
    """
    Saves data to the blob store and returns a reference.
    """
    # Ensure directory exists (in case it wasn't mounted or local dev)
    os.makedirs(BLOB_STORE_PATH, exist_ok=True)
    
    ref_id = str(uuid.uuid4())
    file_path = os.path.join(BLOB_STORE_PATH, f"{ref_id}.pkl")
    
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(pickle.dumps(data))
        
    return BlobRef(ref_id=ref_id, path=file_path)

async def load_blob(ref: Union[BlobRef, Any]) -> Any:
    """
    Loads data from a BlobRef. If input is not a BlobRef, returns it as is.
    """
    if isinstance(ref, BlobRef):
        async with aiofiles.open(ref.path, "rb") as f:
            content = await f.read()
            return pickle.loads(content)
            
    # Check if it's a dict that looks like a BlobRef (serialization artifact)
    if isinstance(ref, dict) and 'ref_id' in ref and 'path' in ref:
         async with aiofiles.open(ref['path'], "rb") as f:
            content = await f.read()
            return pickle.loads(content)
            
    return ref
