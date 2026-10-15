from urllib.parse import urlparse
import ipaddress
def check_url(value):
 if not isinstance(value,str) or len(value)>4000:raise ValueError('Expected a public HTTP(S) URL')
 u=urlparse(value);h=u.hostname or ''
 if u.scheme not in {'https','http'} or not h or u.username or u.password or h.lower()=='localhost' or h.lower().endswith(('.localhost','.local','.internal')):raise ValueError('Expected a public HTTP(S) URL without credentials')
 try:ip=ipaddress.ip_address(h)
 except ValueError:ip=None
 if ip is not None and not ip.is_global:raise ValueError('Private addresses are not supported')
 return value
