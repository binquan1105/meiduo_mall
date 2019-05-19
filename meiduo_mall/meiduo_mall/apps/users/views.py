from django.shortcuts import render,redirect,reverse
from django.http import HttpResponseForbidden,JsonResponse
from meiduo_mall.libs.response_code import RETCODE
from django.views import View
# from django.core.mail import send_mail
from django.conf import settings
import re,json
from django.contrib.auth import login,logout
from .models import User
import logging
from django_redis import get_redis_connection
from django.core.paginator import Paginator


from .models import Address
from celery_tasks.emai.tasks import send_email_celery
from carts.utils import merge_cart_cookie_to_redis
from carts.models import OrderInfo
#注册接收数据、校验、贮存数据
class RegisterUser(View):
    def get(self,request):
        # user = User.objects.values().filter(id=2)
        # user_list = list(user)
        # print(json.dumps(user_list[0].get('username')))
        # print(type(json.dumps(user_list[0].get('username'))))
        return render(request,'register.html')

    def post(self,request):
        #获取用户注册信息
        username = request.POST.get('username')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        mobile = request.POST.get('mobile')
        sms_code = request.POST.get('sms_code')
        allow = request.POST.get('allow')
        #判断是否有数据，输入数据是否正确
        if not all([username,password,password2,mobile,sms_code,allow]):
            return HttpResponseForbidden('缺少必传参数')

        if not re.match('[a-zA-Z0-9_-]{5,20}',username):
            return HttpResponseForbidden('请输入5-20个字符的用户名')
        if not re.match('^[0-9A-Za-z]{8,20}',password):
            return HttpResponseForbidden('您输入的手机号格式不正确')
        if password != password2:
            return HttpResponseForbidden('两次密码不一致')
        if not re.match('^1[345789]\d{9}$',mobile):
            return HttpResponseForbidden('您输入的手机号格式不正确')
        if allow != 'on':
            return HttpResponseForbidden('请勾选用户协议')
        #获取短信验证码
        redis_connet = get_redis_connection('verify_code')
        sms_data = redis_connet.get('sms_%s' % mobile)
        if sms_data is None or sms_code != sms_data.decode():
            return HttpResponseForbidden('手机验证码错误')
        #保存数据
        try:
            user = User.objects.create_user(username = username,password=password,mobile=mobile)

        except Exception as e:
            #工程日记记录
            logger = logging.getLogger('django')
            logger.error(e)
            return render(request,'register.html',{'register_errmsg': '用户注册失败'})
        #状态保持,(如果注册成功需要重新登陆,不用记录登陆状态)
        login(request,user)#保存用户的ID到SESSION中记录他的登陆状态

        #注册成功进入首页并显示登录信息
        response = redirect('/')
        response.set_cookie('username', user.username, max_age=3600 * 24 * 15)
        return response
        #前端失去焦点事件发送axios,通过get请求发送用户名
        #获取用户名与数据库对比，要么有要么没有，返回数字1或者0

#用户名重复
class UserRegisterView(View):

    def get(self,request,username):
        #获取数据库username的数据,返回1或者0
        count = User.objects.filter(username=username).count()
        #给前端返回json数据格式,根据前端要求返回什么就是什么
        return JsonResponse({'count':count,'code':RETCODE.OK,'error_msg':'OK'})

#密码重复
class MobilRegisterView(View):
    def get(self,requset,mobile):
        count = User.objects.filter(mobile=mobile).count()
        return JsonResponse({'count':count,'code':RETCODE.OK,'error_msg':'OK'})

#登录页面
class LoginView(View):
    def get(self,request):
        return render(request,'login.html')
    def post(self,request):
        #获取数据
        username = request.POST.get('username')
        password = request.POST.get('password')
        allo = request.POST.get('remembered')
        if all([username,password]) is False:
            return HttpResponseForbidden('缺少参数')
        #数据对比，从数据库中提取到的密码是私密的，所以用django的后端认证
        from django.contrib.auth import authenticate

        #数据对比,django验证密码的方法，认证通过返回true,不通过返回False
        # u = User.objects.get(username=username)
        #验证数据库密码与传进来的密码是否一致
        # u.check_password(password)


        #authticate认证一组凭据,默认认证username,password,认证通过返回一个user对象
        #用户名或者密码认证失败引发异常返回None

        #通
        user = authenticate(username=username,password=password)


        if user is None:
            return render(request,'login.html',{'account_errmsg':'用户名或密码错误'})

        #状态保持(1)
        login(request,user)#默认保持两周
        #如果不勾选记住登录,设置关闭浏览器即关闭
        if allo != 'on':
            request.session.set_expiry(0)

        #在首页展示登录信息,
        # response = redirect(reverse('contents:index'))

        # 当用户没登录就访问用户中心时返回登录页面, 这时的地址变成.. / login /?next = / info /
        # 需求：用户登录直接进入访问用户中心
        # 实现：获取字符串next的值, 重定向到该地址
        #get()第二个参数是默认值,前面的找不到时使用默认值
        response = redirect(request.GET.get('next','/'))

        """登录即合并购物车"""
        merge_cart_cookie_to_redis(request,user,response)

        #账号有可能是手机号或者用户名
        if username == user.mobile:
            response.set_cookie('username', user.mobile, max_age=3600 * 24 * 15)
        else:
            response.set_cookie('username',user.username,max_age=3600 * 24 * 15)
        return response
#多账号登录实现：创建utils模块

#退出登录
class LoginOutView(View):
    def get(self,request):

        logout(request)

        # state = request.GET.get('next','/')

        response = redirect(reverse('contents:index'))
        # response = redirect(state)

        response.delete_cookie('username')
        
        return response


#展示用户中心：登录即可访问，每登录重定向登录页面
#方法一:缺点：登录验证逻辑很多地方都需要，所以该代码需要重复编码好多次。
# class UserInfo(View):
#     #django里面设置了判断用户是否登录的方法request.user.is_authenticate(),登录返回True,未登录返回False
#     def get(self,request):
#         if request.user.is_authenticated():
#             return render(request,'user_center_info.html')
#         else:
#             return redirect(reverse('users:login'))

#方法二：用django的装饰器login_requried装饰as_view()的返回值
#装饰类视图as_view的返回值
from django.contrib.auth.decorators import login_required
## urlpatterns = [
##     url(r'login/',login_required(vews.UserInfo.as_view()),name='info')
## ]
#类视图函数
# class UserInfo(View):
#     def get(self,request):
#         return render(request,'user_center_info.html')


# 方法三：定义View子类封装login_required装饰器
# ​LoginRequired(object)`依赖于视图类`View`，复用性很差。
# 重写View的as_view()方法
# class AsUserView(object):
#     # 静态方法
#     @classmethod
#     def as_view(cls, **initkwargs):
#         # 自定义as_view方法,调用父类的as_view()方法
#         view = super().as_view()
#
#         # 用login_required()装饰入口函数
#         from django.contrib.auth.decorators import login_required
#         return login_required(view)
# # 创建子类,继承父类AsUserView
# class UserInfo(AsUserView, View):
#     def get(self, request):
#         return render(request, 'user_center_info.html')


# 方法四：使用django封装号的minxins的LoginRequiredMixin类判断用户名是否登录
#继承mixins的LoginRequiredMixin类

from django.contrib.auth.mixins import LoginRequiredMixin

# 方法四：使用django封装号的minxins的LoginRequiredMixin类判断用户名是否登录
class UserInfo(LoginRequiredMixin,View):
    def get(self,request):

        content = {
            'username':request.user.username,
            'mobile':request.user.mobile,
            'email': request.user.email,
            'email_active': request.user.email_active
        }

        return render(request,'user_center_info.html',context=content)

#加密邮箱链接处理函数
def sign_send_email(user):
    from itsdangerous import TimedJSONWebSignatureSerializer as Sery
    seri = Sery(settings.SECRET_KEY,3600*24)
    dict_url = {'user_id': user.id,'email_id':user.email}
    #生成加密的url,转成字符窜并接路由
    verify_url = seri.dumps(dict_url).decode()
    verify_url = settings.EMAIL_VERIFY_URL + '?token=' + verify_url

    return verify_url

#保存邮箱
class SaveEmail(LoginRequiredMixin,View):
    def put(self,request):

        #获取请求体数据,转成字符串
        j_dict = request.body.decode()

        #把json格式的字典转成普通的python字典
        p_dict = json.loads(j_dict)

        #获取email数据,获取字典数据用get方法比较好
        email = p_dict.get('email')

        #校验数据
        if not email:
            return HttpResponseForbidden('缺少参数')
        if not re.match('[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}',email):
            return HttpResponseForbidden('邮箱格式错误')

        try:
            #通过user数据对象给email字段赋值
            save_email = request.user
            save_email.email = email
            #保存数据
            save_email.save()

        except Exception as e:
            return JsonResponse({'code':RETCODE.SESSIONERR,'errmsg':'添加邮箱失败'})

        #发送邮件：
        # subject：邮件标题
        # message：普通邮件正文，普通字符串
        # from_email：发件人
        # recipient_list：收件人列表
        # html_message：多媒体邮件正文，可以是html字符串
        # send_mail(邮件标题,普通邮件字符串(不写要为空),发件人邮箱,收件人列表(实现多人发送),超文本)
        #将邮件发送进行异步处理
        # send_mail('美多商城','',settings.EMAIL_FROM,['itheima_cast@163.com'],'<p>hello</p>')

        #调用异步任务传邮箱链接、用户邮箱
        #因为邮箱地址是一样的,为了区分激活的是哪个用户的邮箱，在后面加上字符串参数,如'http://www.meiduo.site:8000/emails/verification/？token=1'
        #token值根据用户id改变,进行加密处理,调用自定义的加密函数把用户对象传过去
        verify_url = sign_send_email(save_email)
        #异步处理,将加密后的邮箱url作为参数
        send_email_celery.delay(email,verify_url)

        return JsonResponse({'code':RETCODE.OK,'errmsg':'添加邮箱成功'})


#邮箱解密处理
def check_token_user(token):
    from itsdangerous import TimedJSONWebSignatureSerializer as Sery
    seri = Sery(settings.SECRET_KEY, 3600 * 24)
    #解密
    try:
        dict_token = seri.loads(token)
        return dict_token.get('user_id'),dict_token.get('email_id')
        #获取user的id
    except Exception as e:
        return None


#邮箱激活处理
class VerifyEmailView(View):
    def get(self,request):
        #获取token值
        token = request.GET.get('token')
        #对token进行解密,调用自定义解密函数，返回用户id
        user_id,email_id = check_token_user(token)

        try:
            #获取对象
            save_email = User.objects.get(id=user_id,email=email_id)
        except User.DoesNotExist:
            return None
        # 给email_active改成True
        save_email.email_active = True

        #保存数据
        save_email.save()

        #返回响应
        return redirect('/info/')


#新添收货地址
class CreateAddressView(LoginRequiredMixin,View):
    def post(self,request):
        #获取当前用户
        user = request.user
        #获取当前用户地址的数量,不包括逻辑删除的
        address_count = Address.objects.filter(user=user,is_deleted=False).count()
        if address_count >= 20:
            return JsonResponse({'code':RETCODE.THROTTLINGERR,'errmsg':'新增数据上限'})

        #前端通过请求体发送数据,后端接收数据,转成一个字典,通过get方法获取参数
        json_dict = json.loads(request.body.decode())
        title = json_dict.get('title')
        receiver = json_dict.get('receiver')
        province_id = json_dict.get('province_id')
        city_id = json_dict.get('city_id')
        district_id = json_dict.get('district_id')
        place = json_dict.get('place')
        mobile = json_dict.get('mobile')
        tel = json_dict.get('tel')
        email = json_dict.get('email')

        #校验参数
        if not all([title,receiver,province_id,city_id,district_id,place,mobile]):
            return HttpResponseForbidden('缺少必传参数')
        # # 校验
        # if all([title, receiver, province_id, city_id, district_id, place, mobile]) is False:
        #     return HttpResponseForbidden('缺少必传参数')

        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return HttpResponseForbidden('参数mobile有误')

        #固定电话和邮箱为选填,如果填了,判断数据格式是否正确
        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
                return HttpResponseForbidden('参数tel有误')
        if email:
            if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
                return HttpResponseForbidden('参数email有误')

        try:
            #新增地址
            address = Address.objects.create(
                user = user,
                title = title,
                receiver = receiver,
                province_id =province_id,
                city_id = city_id,
                district_id = district_id,
                place = place,
                mobile = mobile,
                tel = tel,
                email = email,
            )
            #如果当前地址不是默认,把当前地址改成默认地址
            if user.default_address is None:
                user.default_address = address
                user.save()
        except Exception:
            return HttpResponseForbidden('新增地址出错')

        #为了一添加收货地址不用刷新就能看到,把数据返回去
        date = {
            'id':address.id,
            'title':address.title,
            'receiver':address.receiver,
            'province_id':address.province_id,
            'city_id':address.city_id,
            'district_id':address.district_id,
            'place':address.place,
            'mobile':address.mobile,
            'email':address.email,
        }

        return JsonResponse({'code':RETCODE.OK,'errmsg':'OK','address':date})


#修改收货地址
class UpdateDestroyAddressView(LoginRequiredMixin,View):
    def put(self,request,address_id):
        #获取参数,转成一个普通字典
        all_body_date = json.loads(request.body.decode())
        #get()方法获取全部参数
        receiver = all_body_date.get('receiver')
        province_id = all_body_date.get('province_id')
        city_id = all_body_date.get('city_id')
        district_id = all_body_date.get('district_id')
        place = all_body_date.get('place')
        mobile = all_body_date.get('mobile')
        tel = all_body_date.get('tel')
        email = all_body_date.get('email')

        #校验参数
        if not all([receiver,province_id,city_id,district_id,place,mobile]):
            return HttpResponseForbidden('缺少必传参数')
        if not re.match(r'1[3-9]\d{9}',mobile):
            return HttpResponseForbidden('无效的手机号码')
        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
                return HttpResponseForbidden('参数tel有误')
        if email:
            if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
                return HttpResponseForbidden('参数email有误')
        try:
            #根据传入的address_id选择修改的地址id
            Address.objects.filter(id = address_id).update(
                #根据字段赋值,新值覆盖旧值
                user=request.user,
                title=receiver,
                receiver=receiver,
                province_id=province_id,
                city_id=city_id,
                district_id=district_id,
                place=place,
                mobile=mobile,
                tel=tel,
                email=email,
            )
        except Exception:
            return JsonResponse({'code':RETCODE.DBERR,'errmsg':'修改失败'})
        #获取新修改的数据返回前端
        adress = Address.objects.get(id=address_id)
        #创建字典
        new_adress_dict = {
            'id':adress.id,
            'title':adress.title,
            'receiver':adress.receiver,
            'province_id':adress.province_id,
            'province':adress.province.name,
            'city_id':adress.city_id,
            'city':adress.city.name,
            'district_id':adress.district_id,
            'district':adress.district.name,
            'place':adress.place,
            'mobile':adress.mobile,
            'tel':adress.tel,
            'email':adress.email,

        }

        return JsonResponse({'code':RETCODE.OK,'errmsg':'OK','address':new_adress_dict})

    # 删除地址
    def delete(self,request,address_id):
        #获取需要逻辑删除的数据对象
        delete_adress = Address.objects.get(id=address_id)
        #把is_deleted字段改成True
        delete_adress.is_deleted = True
        delete_adress.save()
        return JsonResponse({'code':RETCODE.OK,'errmsg':'OK'})


#修改默认地址
class ChangeDefaultView(LoginRequiredMixin,View):
    def put(self,request,address_id):
        #获取当前用户的数据对象
        user = request.user
        #获取设置默认的地址
        adress = Address.objects.get(id = address_id)
        #将当前的用户默认地址设置为获取到的adress数据对象
        user.default_address_id = adress
        #保存
        user.save()
        return JsonResponse({'code':RETCODE.OK,'errmsg':'OK'})

#修改地址标题
class ChangeAdressTitle(LoginRequiredMixin,View):
    def put(self,request,address_id):
        #获取前端发送的数据
        title_dict = json.loads(request.body.decode())
        title = title_dict.get('title')
        try:
            change_adress = Address.objects.get(id=address_id)
        except Address.DoesNotExist:
            return JsonResponse({'code':RETCODE.SESSIONERR,'errmsg':'修改失败'})
        #更新标题
        change_adress.title = title
        change_adress.save()
        return JsonResponse({'code':RETCODE.OK,'errmsg':'OK'})


#修改密码
class ChangePassword(LoginRequiredMixin,View):
    def get(self,request):
        return render(request,'user_center_pass.html')

    def post(self,request):
        #获取表单数据
        old_password = request.POST.get('old_pwd')
        new_password = request.POST.get('new_pwd')
        agind_new_password = request.POST.get('new_cpwd')

        #校验数据
        if not all([old_password,new_password,agind_new_password]):
            return HttpResponseForbidden('缺少必要参数')
        if not re.match(r'[0-9A-Za-z]{8,20}',old_password):
            return HttpResponseForbidden('密码格式不对')

        #数据库加密密码用django的check_password(password)检查
        try:
            request.user.check_password(old_password)
        except Exception:
            return render(request, 'user_center_pass.html', {'origin_pwd_errmsg': '原始密码错误'})
        if new_password != agind_new_password:
            return HttpResponseForbidden('密码不一致')
        #获取当前用户的数据对象
        user = request.user
        print(user.password)

        try:#设置新密码(加密的)

            user.set_password(new_password)
            user.save()
            print(user.password)
        except Exception:
            return render(request, 'user_center_pass.html', {'origin_pwd_errmsg': '原始密码错误'})
        #清楚登录状态
        logout(request)
        #清楚cookie重定向到登录页面
        response = redirect('/login/')
        response.delete_cookie('username')
        return response

"""我的订单页面"""
class UserOrderInfoView(LoginRequiredMixin,View):

    def get(self, request, page_num):
        #获取当前用户
        user = request.user
        # 查询当前登录用户的所有订单
        order_qs = OrderInfo.objects.filter(user=user).order_by('-create_time')
        #遍历获得每一个订单
        for order in order_qs:
            # 给每个订单多定义两个属性, 订单支付方式中文名字, 订单状态中文名字,元祖根据下标取值
            order.pay_method_name = OrderInfo.PAY_METHOD_CHOICES[order.pay_method - 1][1]
            order.status_name = OrderInfo.ORDER_STATUS_CHOICES[order.status - 1][1]
            # 再给订单模型对象定义sku_list属性,用它来包装订单中的每一种商品
            order.sku_list = []

            # 获取订单中的所有类型商品
            order_good_qs = order.skus.all()
            # 遍历获取每个订单中的每一条商品数据
            for good_model in order_good_qs:
                sku = good_model.sku  # 获取到订单商品所对应的sku
                #给sku字段添加商品购买的数量和总价字段
                sku.count = good_model.count
                sku.amount = sku.price * sku.count
                # 把sku添加到订单sku_list列表中
                order.sku_list.append(sku)

        # 创建分页器对订单数据进行分页
        # 创建分页对象,把所有定单数据作为参数传入分页对象，每页显示2条
        paginator = Paginator(order_qs, 2)
        # 获取指定页的所有数据
        page_orders = paginator.page(page_num)
        # 获取总页数
        total_page = paginator.num_pages

        context = {
            'page_orders': page_orders,  # 当前这一页要显示的所有订单数据
            'page_num': page_num,  # 当前是第几页
            'total_page': total_page  # 总页数
        }
        return render(request, 'user_center_order.html', context)
