import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logging.basicConfig(
    filename='requests.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
)

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        method = request.method
        url = request.url.path

        # Считываем тело запроса только для POST/PUT/PATCH (безопасно)
        body = None
        if method in ("POST", "PUT", "PATCH"):
            try:
                body_bytes = await request.body()
                body = body_bytes.decode('utf-8', errors='ignore')
            except Exception as e:
                body = f"<<error reading body: {e}>>"
        else:
            body = ""

        # Сохраняем headers, но не логируем большие/секретные поля
        headers = dict(request.headers)
        for k in list(headers.keys()):
            if k.lower() in ["authorization", "cookie", "set-cookie"]:
                headers[k] = "<<hidden>>"

        # Логируем запрос
        log_msg = (
            f"{method} {url} | "
            f"Headers: {headers} | "
            f"Body: {body[:200]}{'...' if len(body) > 200 else ''}"  # Ограничение на длину body
        )
        logging.info(log_msg)
        print(log_msg)  # можно убрать в проде

        try:
            response: Response = await call_next(request)
            status_code = response.status_code

            # Для ошибок логируем часть ответа
            if status_code >= 400:
                resp_body = b""
                async for chunk in response.body_iterator:
                    resp_body += chunk
                # Если JSON — покажи только часть
                try:
                    resp_data = resp_body.decode("utf-8")
                    if len(resp_data) > 200:
                        resp_data = resp_data[:200] + "..."
                except Exception:
                    resp_data = "<<binary data>>"
                error_log = f"RESPONSE {status_code} | {url} | Body: {resp_data}"
                logging.warning(error_log)
                print(error_log)
                # Восстановить response body для клиента
                response = Response(content=resp_body, status_code=status_code, headers=dict(response.headers), media_type=response.media_type)

            return response
        except Exception as exc:
            # Если сервер упал, мы всё равно залогируем
            error_log = f"EXCEPTION in {method} {url}: {exc}"
            logging.error(error_log)
            print(error_log)
            raise exc
