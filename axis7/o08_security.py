"""Bound request bodies for the opt-in prospective API, including chunked input."""
from starlette.responses import JSONResponse


class O08BodyLimit:
    def __init__(self,app,max_bytes=524288):
        self.app=app;self.max_bytes=max_bytes

    async def __call__(self,scope,receive,send):
        if scope['type']!='http' or not scope.get('path','').startswith('/api/v6/o08'):
            return await self.app(scope,receive,send)
        lengths=[v for k,v in scope.get('headers',[]) if k==b'content-length']
        try: length=int(lengths[0]) if lengths else 0
        except ValueError:
            return await JSONResponse({'detail':'Invalid content length'},status_code=400)(scope,receive,send)
        if length>self.max_bytes:
            return await JSONResponse({'detail':'O08 request exceeds 512 KiB'},status_code=413)(scope,receive,send)
        # Bound memory before framework JSON parsing; works without Content-Length.
        chunks=[];total=0
        while True:
            message=await receive()
            if message['type']=='http.disconnect':return
            chunk=message.get('body',b'');total+=len(chunk)
            if total>self.max_bytes:
                return await JSONResponse({'detail':'O08 request exceeds 512 KiB'},status_code=413)(scope,receive,send)
            chunks.append(chunk)
            if not message.get('more_body',False):break
        replayed=False
        async def replay():
            nonlocal replayed
            if not replayed:
                replayed=True
                return {'type':'http.request','body':b''.join(chunks),'more_body':False}
            return await receive()
        await self.app(scope,replay,send)
