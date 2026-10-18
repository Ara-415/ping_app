import time
import uuid
from collections import defaultdict, deque

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

EMAIL = "23f2000571@ds.study.iitm.ac.in"
ALLOWED_ORIGINS = [
    "https://app-stzyqn.example.com",
    "https://exam.sanand.workers.dev",
]
LIMIT = 14       # requests
WINDOW = 10.0    # seconds

app = FastAPI()
hits = defaultdict(deque)


# Middleware are added innermost-first: rate limiter, then context, then CORS.
@app.middleware("http")
async def rate_limiter(request: Request, call_next):
    if request.method == "OPTIONS":
        return await call_next(request)
    client = request.headers.get("x-client-id")
    if not client:
        fwd = request.headers.get("x-forwarded-for", "")
        ip = fwd.split(",")[0].strip() or (request.client.host if request.client else "unknown")
        client = "ip:" + ip
    now = time.monotonic()
    q = hits[client]
    while q and now - q[0] >= WINDOW:
        q.popleft()
    if len(q) >= LIMIT:
        retry = max(1, int(WINDOW - (now - q[0])) + 1)
        return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429,
                            headers={"Retry-After": str(retry)})
    q.append(now)
    return await call_next(request)


@app.middleware("http")
async def request_context(request: Request, call_next):
    rid = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.request_id = rid
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


@app.get("/ping")
def ping(request: Request):
    return {"email": EMAIL, "request_id": request.state.request_id}
