from django.shortcuts import render,redirect
from django.views import View
from QQLoginTool.QQtool import OAuthQQ
from django.contrib.auth import settings,login
from django.http import JsonResponse,HttpResponseServerError,HttpResponseForbidden,HttpResponse
from meiduo_mall.libs.response_code import RETCODE
from .models import OAuthQQUser
from users.models import User
from django_redis import get_redis_connection

import re
import json

import logging
from carts.utils import merge_cart_cookie_to_redis
from .models import OAuthSinaUser
from .weipo3 import APIClient
from .utils import OAuth_WEIBO

logger = logging.getLogger('django')
class OAuthURLView(View):
    def get(self,request):

        next_url = request.GET.get('next','/')

        #在settings中填入QQ配置信息
        #创建工具对象，通过工具对象获取登录QQ链接
        oauth = OAuthQQ(client_id=settings.QQ_CLIENT_ID,
                        client_secret=settings.QQ_CLIENT_SECRET,
                        redirect_uri=settings.QQ_REDIRECT_URI,
                        state=next_url)

        login_url = oauth.get_qq_url()

        return JsonResponse({'code':RETCODE.OK,'errmsg':'ok','login_url':login_url})


# openid签名处理
# pip3 install itsdangerous
# 定义函数,将openid做签名处理
"""qq登录"""
def generate_access_token(openid):


    from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
    # Serializer(密钥,有效期)
    seri = Serializer(settings.SECRET_KEY, 300)

    # seri.dumps(数据),返回bytes类型,如
    # token = serializer.dumps({'mobile': '18512345678'})
    # token = token.decode()

    # 将openid用字典储存,供前端提取
    date = {'openid': openid}

    # 将date进行加密,返回bytes类型
    token = seri.dumps(date)

    # 将token转成字符串返回加密的Data数据
    return token.decode()

#自定义函数解密openid
def check_access_token(openid):
    # 解密 需要跟加密使用一样的秘钥以及有效期
    from itsdangerous import TimedJSONWebSignatureSerializer as Serializer,BadData
    seri = Serializer(settings.SECRET_KEY, 300)

    try:
        data = seri.loads(openid)
        return data.get('openid')
    # 验证失败，会抛出itsdangerous.BadData异常
    except BadData:

        return None


# QQ登录成功后的处理
class OAuthUserView(View):
    def get(self, request):
        # QQ登录成功后返回一个字符串参数code，提取code
        code = request.GET.get('code')
        if not code:
            return HttpResponseForbidden('缺少code')

        # 创建工具对象
        oauth = OAuthQQ(client_id=settings.QQ_CLIENT_ID,
                        client_secret=settings.QQ_CLIENT_SECRET,
                        redirect_uri=settings.QQ_REDIRECT_URI,
                        )

        # 使用code向QQ服务器发送请求获取access_token
        try:
            access_token = oauth.get_access_token(code)

            # 使用access_token向QQ服务器在发送请求获取openid
            openid = oauth.get_open_id(access_token)


        except Exception as e:
            logger.error(e)
            return HttpResponseServerError('OAuth2.0认证失败')

        # 判断openid是否绑定用户
        try:
            oauth_user = OAuthQQUser.objects.get(openid=openid)

        # openid未绑定用户处理
        except OAuthQQUser.DoesNotExist:
            # 为了能够在后续的操作中绑定用户，需要将openid做签名处理(防止泄露)返回给前端
            #函数调用
            access_token = generate_access_token(openid)

            # 前端用context变量接收签名处理后的openid
            openid = {'openid': access_token}

            # 重新渲染登录页面
            return render(request, 'oauth_callback.html', openid)

        # openid已绑定用户处理
        else:
            # 获取oauth_user对象的外键(user)(也就是user表的id)
            user = oauth_user.user

            # 状态保持
            login(request, user)

            # 获取state值(从哪个页面登录，登录后回到哪个页面)
            state = request.GET.get('state')

            # 重定向到state值的页面
            response = redirect(state)

            # 设置cookie值,展示登录信息
            response.set_cookie('username', user.username, max_age=3600 * 24 * 14)

            """登录即合并购物车"""
            merge_cart_cookie_to_redis(request, user, response)

        # 返回响应
        return response

    # 用户点击提交注册：post请求，在当前类视图中添加post方法
    def post(self, request):
        # 接收数据
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        # 图形验证码在发送短信前已经验证了，这里不再验证

        sms_code = request.POST.get('sms_code')

        # 加密的openid,openid作为隐藏标签发送数据
        openid = request.POST.get('openid')

        # 检查接收数据是否齐全
        if all([mobile, password, sms_code]) is False:
            return HttpResponseForbidden('缺少必传参数')
        # 判断手机号是否合法
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return HttpResponseForbidden('请输入正确的手机号码')
            # 判断密码是否合格
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return HttpResponseForbidden('请输入8-20位的密码')

            # 建立数据库链接，判断短信验证码是否正确
        redis_connet = get_redis_connection('verify_code')
        sms_code_server = redis_connet.get('sms_%s' % mobile)
        if not sms_code_server or sms_code != sms_code_server.decode():
            return render(request, 'oauth_callback.html', {'sms_code_errmsg': '无效的短信验证码'})

        # 调用自定义函数解密openid
        check_openid = check_access_token(openid)



        # print(date_openid)
        if not check_openid:
            return render(request, 'oauth_callback.html', {'openid_errmsg': '无效的openid'})

        # 保存注册用户,如果用户不存在

        try:
            user = User.objects.get(mobile=mobile)
        except User.DoesNotExcist:
            # 新建用户
            user = User.objects.create(username=mobile, password=password, mobile=mobile)

        # 用户存在，检查密码
        else:
            if not user.check_password(password):
                return render(request, 'oauth_callback.html', {'account_errmsg': '用户名或密码错误'})

        # 将用户绑定openid
        try:
            # 第一个user为外键,第二个user为主表的数据对象,
            OAuthQQUser.objects.create(user=user, openid=check_openid)
        except OAuthQQUser.DoesNotExist:
            return render(request, 'oauth_callback.html', {'qq_login_errmsg': 'QQ登录失败'})

        # 状态保持
        login(request, user)

        # 获取state值,哪来的往哪去,设置cookie值并返回响应
        state = request.GET.get('state', '/')
        response = redirect(state)
        """登录即合并购物车"""
        merge_cart_cookie_to_redis(request,user,response)

        response.set_cookie('username', user.username, max_age=3600 * 24 * 14)
        return response

"""构建微博登录跳转链接"""
class WeiBoOAuthUserView(View):
    def get(self, request):
        # 1、创建微博对象
        sina = APIClient(app_key=settings.APP_KEY, app_secret=settings.APP_SECRET,
                         redirect_uri=settings.REDIRECT_URI, )
        # 4、构建跳转连接
        login_url = sina.get_authorize_url()

        # 5、返回跳转连接
        return JsonResponse({'code':RETCODE.OK,'errmsg':'OK','login_url':login_url})

"""获取微博code，最终得到access_token的处理"""
class UnKnwoCode(View):
    def get(self,request):
        code = request.GET.get('code')
        if not code:
            return HttpResponse({'errors': '缺少code值'}, status=400)
        access_token= request.COOKIES.get('access_token_s')
        try:
            sina_user = OAuthSinaUser.objects.get(uid=access_token)
        except OAuthSinaUser.DoesNotExist:
            return JsonResponse({'code':RETCODE.OK,'errmsg':'OK','access_token':access_token})
        user = sina_user.user
        user_id = user.id
        username = user.username
        return JsonResponse({'code':RETCODE.OK,'errmsg':'OK','user_id':user_id,'username':username,'token':access_token})

    # 用户点击保存：post请求，在当前类视图中添加post方法
    def post(self, request):
        # 接收数据
        json_dict = json.loads(request.body.decode())
        password = json_dict.get('password')
        mobile = json_dict.get('mobile')

        # 图形验证码在发送短信前已经验证了，这里不再验证

        sms_code = json_dict.get('sms_code')

        access_token = request.COOKIES.get('access_token_s')

        # 检查接收数据是否齐全
        if all([mobile, password, sms_code,access_token]) is False:
            return HttpResponseForbidden('缺少必传参数')
        # 判断手机号是否合法
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return HttpResponseForbidden('请输入正确的手机号码')
        # 判断密码是否合格
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return HttpResponseForbidden('请输入8-20位的密码')

        # 建立数据库链接，判断短信验证码是否正确
        redis_connet = get_redis_connection('verify_code')
        sms_code_server = redis_connet.get('sms_%s' % mobile)
        if not sms_code_server or sms_code != sms_code_server.decode():
            return JsonResponse({'code':'400','message':'短信验证失败'})

        # print(date_openid)
        if not access_token:
            return HttpResponseForbidden('无效的access_token')

        # 保存注册用户,如果用户不存在
        try:
            user = User.objects.get(mobile=mobile)
        except User.DoesNotExcist:
            # 新建用户
            user = User.objects.create(username=mobile, password=password, mobile=mobile)

        # 用户存在，检查密码
        else:
            if not user.check_password(password):
                return render(request, 'sina_callback.html', {'error_phone_message': '用户名或密码错误'})

        # 将用户绑定access_token
        try:
            # 第一个user为外键,第二个user为主表的数据对象,
            OAuthSinaUser.objects.create(user=user, uid=access_token)
        except OAuthQQUser.DoesNotExist:
            return render(request, 'sina_callback.html', {'error_sms_code_message': '微博登录失败'})

        user_id = user.id
        username = user.username
        response = JsonResponse({'code':RETCODE.OK,'errmsg':'OK','user_id':user_id,'username':username,'token':access_token})
        """登录即合并购物车"""
        merge_cart_cookie_to_redis(request, user, response)
        return response

"""获取access_token"""
class GetWeiBoCode(View):
    def get(self, request):
        # 1、获取code值
        code = request.GET.get('code', None)

        # 2、判断code是否传递过来
        if not code:
            return HttpResponse({'errors': '缺少code值'}, status=400)

        # 3、通过code值获取access_token值
        # 创建sina对象
        sina = APIClient(app_key=settings.APP_KEY, app_secret=settings.APP_SECRET,
                           redirect_uri=settings.REDIRECT_URI, )
        try:
            access_token_dict = sina.request_access_token(code)
            access_token = access_token_dict.get('access_token')
        except:
            access_token = request.COOKIES.get('access_token_s')
        # 5、判断access_token是否绑定过用户
        try:
            sina_user = OAuthSinaUser.objects.get(uid=access_token)

        except OAuthSinaUser.DoesNotExist:
            response = render(request, 'sina_callback.html')
            response.set_cookie('access_token_s',access_token)
            return response
        else:
            # access_token已绑定用户处理
            # 获取sina_user对象的外键(user)(也就是user表的id)
            user = sina_user.user
            # 状态保持
            login(request, user)
            # 获取state值(从哪个页面登录，登录后回到哪个页面)
            state = request.GET.get('state','/')
            # 重定向到state值的页面
            response = redirect(state)

            # 设置cookie值,展示登录信息
            response.set_cookie('username', user.username, max_age=3600 * 24 * 14)

            """登录即合并购物车"""
            merge_cart_cookie_to_redis(request, user, response)

            # 返回响应
        return response

