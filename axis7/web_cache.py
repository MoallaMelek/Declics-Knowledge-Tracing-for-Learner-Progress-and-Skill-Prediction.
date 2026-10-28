"""Make the browser revalidate the local web pages instead of reusing a stale copy.

A tab restored from the browser cache while DÉCLIC was stopped (or after an update) could
show an old page whose scripts never run. ``no-cache`` keeps the ETag/304 path cheap while
forcing the browser to ask the local server first. API responses are unchanged.
"""


class RevalidateWeb:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        path = scope.get('path', '') if scope['type'] == 'http' else ''
        if not (path == '/' or path.startswith('/web/')):
            return await self.app(scope, receive, send)

        async def send_with_header(message):
            if message['type'] == 'http.response.start':
                headers = [(k, v) for k, v in message.get('headers', []) if k.lower() != b'cache-control']
                headers.append((b'cache-control', b'no-store' if path == '/' else b'no-cache'))
                message = {**message, 'headers': headers}
            await send(message)

        await self.app(scope, receive, send_with_header)
