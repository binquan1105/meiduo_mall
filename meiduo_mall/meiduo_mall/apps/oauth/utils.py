
from urllib import parse,request
from urllib.request import Request,urlopen
import json

class OAuth_Base(object):  # 基类，将相同的方法写入到此类中
    def __init__(self, client_id, client_key, redirect_url):  # 初始化，载入对应的应用id、秘钥和回调地址
        self.client_id = client_id
        self.client_key = client_key
        self.redirect_url = redirect_url

    def _get(self, url, data):  # get方法
        request_url = '%s?%s' % (url, parse.urlencode(data))
        response = request.urlopen(request_url)
        return response.read()

    def _post(self, url, data):  # post方法
        request = Request(url, data= parse.urlencode(data).encode(encoding='UTF8'))  # 1
        response = urlopen(request)
        return response.read()


# 微博类
class OAuth_WEIBO(OAuth_Base):
    def get_auth_url(self):
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_url,
            # 'forcelogin' : 'true'
        }
        url = 'https://api.weibo.com/oauth2/authorize?%s&state=/' % parse.urlencode(params)
        return url

    def get_access_token(self, code):
        params = {
            'grant_type': 'authorization_code',
            'client_id': self.client_id,
            'client_secret': self.client_key,
            'code': code,
            'redirect_uri': self.redirect_url
        }
        response = self._post('https://api.weibo.com/oauth2/access_token', params)
        result = json.loads(response.decode('utf-8'))
        self.access_token = result["access_token"]
        return self.access_token