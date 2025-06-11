from pydantic import BaseModel

class Ok(BaseModel):
    success: bool = True