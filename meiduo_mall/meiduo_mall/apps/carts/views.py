from django.shortcuts import render
from django.views import View
from django.http import HttpResponseForbidden,JsonResponse
from django_redis import get_redis_connection
from django.contrib.auth.mixins import LoginRequiredMixin

from decimal import Decimal

import json
from goods.models import SKU
import pickle,base64
from meiduo_mall.utils.response_code import RETCODE
from users.models import Address

"""
购物车
登录用户购物车数据存储在redis中:hash:{'ski_id':count...} set:{'sku_id'}set只保存勾选的sku_id
未登录用户存储在cookie中{sku_id:'count':count,'selected':(True或者False)}
"""
"""加入购物车"""
class AddToCart(View):

    """加入购物车"""
    def post(self,request):
        #获取json数据转成字典
        json_dict = json.loads(request.body.decode())
        #获取参数
        sku_id = json_dict.get('sku_id')
        count = json_dict.get('count')
        selected = json_dict.get('selected',True)

        #校验数据
        if not all([sku_id,count]):
            return HttpResponseForbidden('缺少必传参数')
        try:
            SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return HttpResponseForbidden('sku_id无效')
        #将count转成数字类型,如果传过来的是不能转成数字类型的会报错
        try:
            count = int(count)
        except Exception:
            return HttpResponseForbidden('无效字符')
        #判断是否为bool类型
        if selected:
            if not isinstance(selected,bool):
                return HttpResponseForbidden('不是bool值')
        #获取用户对象
        user = request.user

        """不管是否登录，返回的响应体是一样的，先设置响应体"""
        response = JsonResponse({'code':RETCODE.OK,'errmsg':'OK'})

        #判断是否登录
        if user.is_authenticated:
            #创建redis数据库链接
            redis_connect = get_redis_connection('carts')
            #创建管道
            pl = redis_connect.pipeline()
            #hash类型hincrby操作：如果建相同,count自动累加,'sku_id':count
            pl.hincrby('carts_%s' % user.id, sku_id, count)
            #设置购物车过期时间
            #pl.expire('carts_%s' % user.id,3600)
            """只存勾选的商品sku_id"""
            if selected:
                #set类型，存勾选商品的sku_id
                pl.sadd('selected_%s' % user.id, sku_id)
                # 设置购物车过期时间
                # pl.expire('carts_%s' % user.id,3600)
            #执行
            pl.execute()

        #未登录用户
        else:
            #获取cookie值
            carts = request.COOKIES.get('carts')
            #如果获取得到,将加密的cookie值转成字典,存到cookie的购物车数据进行了base64加密处理
            if carts:

                carts_dict = pickle.loads(base64.b64decode(carts.encode()))
            else:
                carts_dict = {}

            #判断sku_id是否存在carts_dict中
            if sku_id in carts_dict:
                old_count = carts_dict[sku_id]['count']
                # 现添加商品数量加上原有商品数量
                count += old_count
            #如果不存在，赋值
            else:
                carts_dict[sku_id] = {
                    'count':count,
                    'selected':selected,
                }
            #转成base64的加密bytes类型,在转成字符串类型
            carts_dict = base64.b64encode(pickle.dumps(carts_dict)).decode()

            #前面设置了响应体,这里不在设置
            response.set_cookie('carts',carts_dict,max_age=None)

        #返回响应
        return response

    """展示购物车"""
    def get(self,request):

        #获取当前用户数据对象
        user = request.user
        #判断用户是否登录
        if user.is_authenticated:
            #登录用户操作，建立数据库链接
            redis_connect = get_redis_connection('carts')
            #获取hash类型数据
            sku_id_count = redis_connect.hgetall('carts_%s' % user.id)#{b'7': b'1', b'5': b'1', b'3': b'1'}
            #获取set类型数据
            selected = redis_connect.smembers('selected_%s' % user.id)
            #创建一个空字典,包装成与cookie一样的数据格式
            carts_dict = {}
            #遍历hash数据，获得每个key,value
            for sku_ids,count in sku_id_count.items():
                carts_dict[int(sku_ids)] = {
                    'count':int(count),
                    'selected':sku_ids in selected#如果sku_id在selected里，返回True,否则返回False
                }
        else:
            #用户未登录,获取cookie值
            carts = request.COOKIES.get('carts')
            #判断cookie是否有购物车数据
            if carts:
                #将购物车数据转成字典
                carts_dict = pickle.loads(base64.b64decode(carts.encode()))
            else:
                carts_dict = {}
        #创建包装商品信息了字典列表
        carts_list = []
        #获取字典中所有的key(sku_id)
        for sku_id in carts_dict.keys():
            #获取商品
            sku = SKU.objects.get(id=sku_id)
            carts_list.append({
                'id': sku.id,
                'name': sku.name,
                'count': carts_dict.get(sku.id).get('count'),
                'selected': str(carts_dict.get(sku.id).get('selected')),  # 将True，转'True'，方便json解析
                'default_image_url': sku.default_image.url,
                'price': str(sku.price),  # 从Decimal('10.2')中取出'10.2'，方便json解析
                'amount': str(sku.price * carts_dict.get(sku.id).get('count')),
            })

        context = {
            'cart_skus':carts_list,
        }



        return render(request,'cart.html',context)

    """修改购物车"""
    def put(self,request):
        #接收数据转成字典，获取数据
        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get('sku_id')
        count = json_dict.get('count')
        selected = json_dict.get('selected',True)

        #校验参数
        if all([sku_id,count]) is False:
            return HttpResponseForbidden('缺少参数')
        try:
            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return HttpResponseForbidden('缺少参数')
        try:
            count = int(count)
        except Exception:
            return HttpResponseForbidden('参数错误')
        if selected:
            if not isinstance(selected,bool):
                return HttpResponseForbidden('bool值')

        #获取当前用户
        user = request.user
        #登录用户操作
        if user.is_authenticated:
            #建立redis链接
            redis_connect = get_redis_connection('carts')
            #设置管道
            pl = redis_connect.pipeline()
            #设置hash数据
            pl.hset('carts_%s' % user.id,sku_id,count)

            if selected:
                pl.sadd('selected_%s' % user.id,sku_id)
            else:
                pl.srem('selected_%s' % user.id,sku_id)

            pl.execute()
            # 创建响应对象
            cart_sku = {
                'id': sku_id,
                'count': count,
                'selected': selected,
                'name': sku.name,
                'default_image_url': sku.default_image.url,
                'price': sku.price,
                'amount': sku.price * count,
            }
            return JsonResponse({'code': RETCODE.OK, 'errmsg': '修改购物车成功', 'cart_sku': cart_sku})

        #未登录用户操作
        else:
            #获取cookie
            carts = request.COOKIES.get('carts')
            if carts:
                #解码转成字典
                cart_dict = pickle.loads(base64.b64decode(carts.encode()))
            else:
                cart_dict = {}

            #用现有的数据覆盖原有的
            cart_dict[sku_id] = {
                'count': count,
                'selected': selected
            }
            #构建响应
            cart_sku = {
                'id': sku_id,
                'count': count,
                'selected': selected,
                'name': sku.name,
                'default_image_url': sku.default_image.url,
                'price': sku.price,
                'amount': sku.price * count,
            }
            #将购物车数据加密转成字符串
            carts_dict = base64.b64encode(pickle.dumps(cart_dict)).decode()
            #设置cookie
            response = JsonResponse({'code':RETCODE.OK,'errmsg':'OK','cart_sku':cart_sku})
            response.set_cookie('carts',carts_dict,max_age=None)
            return response

    """删除购物车"""
    def delete(self,request):
        #接收参数
        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get('sku_id')
        try:
            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return HttpResponseForbidden('sku无效')
        #获取登录用户
        user = request.user
        #登录用户操作
        if user.is_authenticated:
            #建立数据库连接
            redis_connect = get_redis_connection('carts')
            pl = redis_connect.pipeline()
            #删除hash数据
            pl.hdel('carts_%s' % user.id,sku_id)
            #删除set数据
            pl.srem('selected_%s' % user.id,sku_id)
            #执行
            pl.execute()
            #响应
            return JsonResponse({'code':RETCODE.OK,'errmsg':'删除成功'})
        else:
            #未登录用户操作
            carts = request.COOKIES.get('carts')
            if carts:
                #解码转成字典
                carts_dict = pickle.loads(base64.b64decode(carts.encode()))
            else:
                carts_dict = {}


            response = JsonResponse({'code': RETCODE.OK, 'errmsg': '删除成功'})
            #如果sku_id在carts_dict字典中存在
            if sku_id in carts_dict:
                #删除建及对应的值
                del carts_dict[sku_id]

                #将字典加密转成字符串
                cart_dict = base64.b64encode(pickle.dumps(carts_dict)).decode()
                #设置cookie返回响应
                response.set_cookie('carts',cart_dict,max_age=None)
            return response


"""全选购物车"""
class CartSelecteAllView(View):
    """全选购物车"""
    def put(self,request):
        #接收参数
        json_dict = json.loads(request.body.decode())
        selected = json_dict.get('selected',True)

        #校验参数
        if selected:
            #判断是否为bool值
            if not isinstance(selected,bool):
                return HttpResponseForbidden('无效参数')
        #获取用户
        user = request.user
        #登录用户操作
        if user.is_authenticated:
            #建立redis连接
            redis_connect = get_redis_connection('carts')
            #获取hash数据,返回一个大字典，建和值都是bytes类型
            sku_id_dict = redis_connect.hgetall('carts_%s' % user.id)
            #获取字典中所有的建，自动组成一个元祖嵌套列表(sku_id1,sku_id2..)
            sku_id_all = sku_id_dict.keys()#dict_keys([b'7', b'3'])
            #如果全选
            if selected:
                #将sku_id_all解包以set类型存进redis
                redis_connect.sadd('selected_%s' % user.id, *sku_id_all)
            #取消全选
            else:
                #将set类型的数据删除
                redis_connect.srem('selected_%s' % user.id, *sku_id_all)
            #返回响应
            return JsonResponse({'code':RETCODE.OK,'errmsg':'OK'})
        #未登录用户
        else:
            #获取cookie数据
            carts = request.COOKIES.get('carts')
            response = JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})
            #如果有数据，解码转成字典
            if carts is not None:
                carts_dict = pickle.loads(base64.b64decode(carts.encode()))
                #遍历字典获得所有的建,全选/取消全选 通过selecte赋值就行
                for sku_id in carts_dict:
                    carts_dict[sku_id]['selected'] = selected

                #加密购物车数据转成字符串
                carts_dict = base64.b64encode(pickle.dumps(carts_dict)).decode()
                #设置cookie返回响应
                response.set_cookie('carts',carts_dict,max_age=None)
            return response


"""商品页面右上角购物车"""
class CartsSimpleView(View):
    """需求：用户鼠标悬停在商品页面右上角购物车标签上，以下拉框形式展示当前购物车数据。"""
    def get(self,request):
        #获取用户
        user = request.user
        #登录用户操作
        if user.is_authenticated:
            #建立redis数据库链接
            redis_connect = get_redis_connection('carts')
            #获取hash数据
            bytes_carts_dict = redis_connect.hgetall('carts_%s' % user.id)
            #获取set数据
            selected = redis_connect.smembers('selected_%s' % user.id)
            #创建一个字典，包装与cookie保存的数据格式相同
            carts_dict = {}
            #遍历获得每个建和值,获得的是bytes类型
            for sku_id,count in bytes_carts_dict.items():
                #将数据组成字典
                carts_dict[int(sku_id)] = {
                    'count':int(count),
                    'selected':sku_id in selected#如果sku_id不存在selected中返回False
                }
        else:
            #未登录用户,获取cookie购物车数据
            carts = request.COOKIES.get('carts')
            #如果有数据，解码转成字典
            if carts:
                carts_dict = pickle.loads(base64.b64decode(carts.encode()))
            else:
                carts_dict = {}
        #获取字典中所有的建(sku_id)
        sku_id_all = carts_dict.keys()
        #获取所有sku_id对应的商品
        skus_all = SKU.objects.filter(id__in=sku_id_all)
        #创建列表包装每一个商品信息
        sku_list = []
        #获取每一个sku
        for sku in skus_all:
            #往列表添加商品信息
            sku_list.append({
                'id':sku.id,
                'name':sku.name,
                'count':carts_dict[sku.id]['count'],
                'default_image_url':sku.default_image.url,
            })
        #返回响应
        return JsonResponse({'code':RETCODE.OK,'errmsg':'OK','cart_skus':sku_list})

"""结算订单"""
class OrderSettlementView(LoginRequiredMixin, View):
    def get(self, request):
        """提供订单结算页面"""
        #获取用户
        user = request.user

        #获取收货地址另一种写法
        # addresses = Address.objects.filter(user=user, is_deleted=False)
        #addresses.exist() 过滤查询，如果找不到返回False,使用None赋值
        #addresses = addresses if addresses.exists() else None

        #获取地址信息
        try:
            addresses = Address.objects.filter(user=user,is_deleted=False)
        #如果为空返回None,前端会渲染页面
        except Address.DoesNotExist:
            return None
        """获取redis数据库中勾选的商品sku_id"""
        redis_connect = get_redis_connection('carts')
        #获取hash数据
        sku_id_count = redis_connect.hgetall('carts_%s' % user.id)
        #获取set数据
        selected_sku = redis_connect.smembers('selected_%s' % user.id)
        #创建包装勾选的商品信息字典
        selected_dict = {}
        #遍历数据
        for sku_key,sku_value in sku_id_count.items():
            #用勾选的sku_id作为字典的建
            if sku_key in selected_sku:
                selected_dict[int(sku_key)] = int(sku_id_count[sku_key])
        #准备商品数量、商品总价的初始值
        total_count = 0
        #跟价格有关的数据不能使用浮点数直接相加
        total_amount = Decimal('0.00')
        #获取所有商品
        skus = SKU.objects.filter(id__in=selected_dict.keys())
        #获取每个商品
        for sku in skus:
            #给每个商品添加数量和总价两个属性
            sku.count = selected_dict[sku.id]
            sku.amount = sku.price*sku.count
            #数量
            total_count += sku.count
            #总价
            total_amount += sku.amount
        #补充运费,小数
        freight = Decimal('10.00')

        # 渲染界面
        context = {
            'addresses': addresses,
            'skus': skus,
            'total_count': total_count,
            'total_amount': total_amount,
            'freight': freight,
            'payment_amount': total_amount + freight
        }

        return render(request,'place_order.html',context)




