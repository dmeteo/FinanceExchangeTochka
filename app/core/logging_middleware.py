import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logging.basicConfig(
    filename='requests.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
)

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "POST":
            body = await request.body()
            msg = (
                f"POST {request.url.path} | "
                f"Headers: {dict(request.headers)} | "
                f"Body: {body.decode('utf-8', errors='ignore')}"
            )
            logging.info(msg)
            print(msg) 
        response = await call_next(request)
        return response
