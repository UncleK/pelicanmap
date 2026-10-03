"""Verify current public static bytes, not a previously cached release.

API/MCP requests are never modified: their query keys are allowlisted.
Static verification follows the same versioned-URL convention as browse assets.
"""
import time
import urllib.request
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

REVISION=str(time.time_ns())

def live_url(request,revision=REVISION):
    url=request.full_url if isinstance(request,urllib.request.Request) else request
    parsed=urlsplit(url)
    if parsed.scheme!='https' or parsed.netloc!='pelicanmap.aveniqa.com' or parsed.path.startswith('/api/') or parsed.path=='/mcp':
        return url
    query=[(key,value) for key,value in parse_qsl(parsed.query,keep_blank_values=True) if key!='live-verification']
    query.append(('live-verification',revision))
    return urlunsplit((parsed.scheme,parsed.netloc,parsed.path,urlencode(query),parsed.fragment))

def live_urlopen(request,*args,**kwargs):
    url=live_url(request)
    if isinstance(request,urllib.request.Request) and url!=request.full_url:
        request=urllib.request.Request(url,data=request.data,headers=dict(request.header_items()),method=request.get_method(),origin_req_host=request.origin_req_host,unverifiable=request.unverifiable)
    elif not isinstance(request,urllib.request.Request):
        request=url
    return urllib.request.urlopen(request,*args,**kwargs)
