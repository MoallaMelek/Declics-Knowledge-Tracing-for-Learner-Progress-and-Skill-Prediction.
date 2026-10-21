import asyncio
import pytest
from axis7.o08_security import O08BodyLimit

@pytest.mark.parametrize('headers', [[(b'content-length',b'-1')],[(b'content-length',b'1'),(b'content-length',b'2')],[(b'content-length',b'bad')]])
def test_invalid_content_lengths_are_rejected_before_body_read(headers):
    sent=[]
    async def app(*args):raise AssertionError('must not reach app')
    async def receive():raise AssertionError('must not read body')
    async def send(message):sent.append(message)
    asyncio.run(O08BodyLimit(app)({'type':'http','path':'/api/v7/o08/test','headers':headers},receive,send))
    assert sent[0]['status']==400

def test_chunked_body_is_bounded_without_content_length():
    sent=[];chunks=iter([{'type':'http.request','body':b'abc','more_body':True},{'type':'http.request','body':b'def','more_body':False}])
    async def app(*args):raise AssertionError('must not reach app')
    async def receive():return next(chunks)
    async def send(message):sent.append(message)
    asyncio.run(O08BodyLimit(app,max_bytes=5)({'type':'http','path':'/api/v7/o08/test','headers':[]},receive,send))
    assert sent[0]['status']==413
