from django.shortcuts import render
from django.views import View
from django.http import HttpResponseForbidden,JsonResponse
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin
import json
from django_redis import get_redis_connection

from .models import GoodsCategory,GoodsVisitCount
from .utils import get_breadcrumb
from contents.utils import get_categories
from meiduo_mall.utils.response_code import RETCODE
from .models import SKU
from carts.models import OrderGoods
#商品列表界面
# class ListView(View):
#     def get(self,request,category_id, page_num):
#         """
#         :param category_id: 点击的三级数据id
#         :param page_num: 第几页
#         :return:
#         """
#         #获取三级数据对象
#         try:
#             category = GoodsCategory.objects.get(id=category_id)
#         except GoodsCategory.DoesNotExist:
#             return HttpResponseForbidden('没有数据')
#         #获取字符串参数中的排序规则
#         sort = request.GET.get('sort','default')
#
#         #判断当前排序规则
#         if sort == 'price':#价格排序
#             sort_fields = 'price'
#         elif sort == 'hot':#销量排序
#             sort_fields = '-sales'
#         else:#时间排序
#             sort_fields = 'create_time'
#
#         #查询当前三级数据下的所有sku
#         sku_qs = category.sku_set.filter(is_launched=True).order_by(sort_fields)
#
#         #创建分页对象
#         from django.core.paginator import Paginator
#         paginator = Paginator(sku_qs,5)#Paginator(进行分页的所有数据,要显示的页数)
#         page_sku = paginator.page(page_num)#获取指定界面的sku数据
#         total_page = paginator.num_pages#获取当前的总页数
#
#         context = {
#             'categories': get_categories(),  # 频道分类
#             'breadcrumb': get_breadcrumb(category),  # 面包屑导航
#             'sort': sort,  # 排序字段
#             'category': category,  # 第三级分类
#             'page_skus': page_sku ,  # 分页后数据
#             'total_page': total_page,  # 总页数
#             'page_num':page_num,  # 当前页码
#         }
#
#         return render(request,'list.html',context)
#
# #热销排行数据
# class HotGoodsView(View):
#     def get(self,reqeust,category_id):
#         try:
#             category = GoodsCategory.objects.get(id=category_id)
#         except GoodsCategory.DoesNotExist:
#             return HttpResponseForbidden('无数据')
#         #获取当前三级数据下销量最高的前两个sku
#         skus_qs = category.sku_set.filter(is_launched=True).order_by('-sales')[0:2]
#
#         #包装两个热销商品字典
#         host_skus = []
#         for sku in skus_qs:
#             host_skus.append({
#                 'id':sku.id,
#                 'name':sku.name,
#                 'price':sku.price,
#                 'default_image_url':sku.default_image.url
#             })
#
#         return JsonResponse({'code':RETCODE.OK,'errmsg':'OK','hot_skus':host_skus})
"""商品列表界面"""
class ListView(View):


    def get(self, request, category_id, page_num):
        """
        :param category_id: 当前选择的三级类别id
        :param page_num: 第几页
        """
        try:
            category = GoodsCategory.objects.get(id=category_id)
        except GoodsCategory.DoesNotExist:
            return HttpResponseForbidden('商品类别不存在')

        # 获取查询参数中的sort 排序规则
        sort = request.GET.get('sort', 'default')

        if sort == 'price':
            sort_fields = 'price'
        elif sort == 'hot':
            sort_fields = '-sales'
        else:
            sort_fields = 'create_time'

        # 面包屑导航数据
        # a = (page_num - 1) * 5
        # b = a + 5
        # 查询当前三级类别下面的所有sku
        # order_by(只能放当前查询集中每个模型中的字段)
        sku_qs = category.sku_set.filter(is_launched=True).order_by(sort_fields)

        # 创建分页对象
        from django.core.paginator import Paginator
        paginator = Paginator(sku_qs, 5)  # Paginator(要进行分页的所有数据, 每页显示多少条数据)
        page_skus = paginator.page(page_num)  # 获取指定界面的sku数据
        total_page = paginator.num_pages  # 获取当前的总页数

        context = {
            'categories': get_categories(),  # 频道分类
            'breadcrumb': get_breadcrumb(category),  # 面包屑导航
            'sort': sort,  # 排序字段
            'category': category,  # 第三级分类
            'page_skus': page_skus,  # 分页后数据
            'total_page': total_page,  # 总页数
            'page_num': page_num,  # 当前页码
        }

        return render(request, 'list.html', context)

"""热销排行数据"""
class HotGoodsView(View):


    def get(self, request, category_id):

        try:
            category = GoodsCategory.objects.get(id=category_id)
        except GoodsCategory.DoesNotExist:
            return HttpResponseForbidden('商品类别不存在')

        # 获取当前三级类别下面销量最高的前两个sku
        skus_qs = category.sku_set.filter(is_launched=True).order_by('-sales')[0:2]

        hot_skus = []  # 包装两个热销商品字典
        for sku in skus_qs:
            hot_skus.append({
                'id': sku.id,
                'name': sku.name,
                'price': sku.price,
                'default_image_url': sku.default_image.url
            })

        return JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'hot_skus': hot_skus})


"""商品详情页"""
class DetailView(View):
    def get(self,request,sku_id):
        # 获取当前的sku数据对象
        try:
            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return render(request, '404.html')
        # 获取当前sku的三级数据对象
        category = sku.category
        # 获取sku对应的spu,
        spu = sku.spu

        """商品规格选项"""
        # 获取当前sku的所有规格,以规格id排序
        sku_sepcigi_all = sku.specs.order_by('spec_id')
        # 创建一个列表，存储每个规格所选择的对应选项id
        sku_options_list = []
        # 遍历获得sku下的每个规格
        for sku_sepcigi in sku_sepcigi_all:
            # 向列表添加规格选项id
            sku_options_list.append(sku_sepcigi.option_id)

        # 创建选择仓库
        """2.构造规格选择仓库
                {(8, 11): 3, (8, 12): 4, (9, 11): 5, (9, 12): 6, (10, 11): 7, (10, 12): 8}
                """
        # 获取spu下的所有sku
        sku_spu_all = spu.sku_set.all()
        # 构建字典仓库
        sku_id_dict = {}
        # 获取每个sku
        for temp_sku in sku_spu_all:
            # 获取sku下的所有规格
            temp_sepcifi_all = temp_sku.specs.order_by('spec_id')
            # 创建存储每个规格对应选项id
            temp_sku_list = []
            # 获取每个规格
            for temp_sepcifi in temp_sepcifi_all:
                # 向列表添加选项id
                temp_sku_list.append(temp_sepcifi.option_id)
            # 构建仓库字典,每个规格选项的组合:sku对应的id
            sku_id_dict[tuple(temp_sku_list)] = temp_sku.id

        # 获取spu下的所有规格，以id排序
        spu_sepcifi_all = spu.specs.order_by('id')
        # 获取每个规格和索引
        for index, spu_sepcifi in enumerate(spu_sepcifi_all):
            # 获取规格下所有选项
            option_all = spu_sepcifi.options.all()
            # 复制当前sku选项列表
            sku_copy_list = sku_options_list[:]
            # 获取每个选项
            for option in option_all:
                # 如：选择颜色、版本对应的选项为[18,21],重新选择时,将选项值对应id赋值给选择的颜色、版本...
                sku_copy_list[index] = option.id
                # 在选项option添加sku_id,绑定对应的sku数据对象
                option.sku_id = sku_id_dict.get(tuple(sku_copy_list))
            # 给规格添加spu_op字段,该字段绑定规格下的所有选项
            spu_sepcifi.spu_op = option_all

        """商品规格选项"""

        context = {
            'categories': get_categories(),  # 返回调用封装好的商品类型
            'breadcrumb': get_breadcrumb(category),  # 返回面包屑导航
            'sku': sku,  # 返回当前的sku数据对象
            'category': category,  # 返回当前sku对应的三级数据对象
            'spu': spu,  # 返回当前sku对应的spu
            'spu_qs': spu_sepcifi_all,  # 返回绑定所有选项的规格查询集
        }
        # print(context)

        return render(request, 'detail.html', context)

"""统计商品类型访问量"""
class DdtailVisitView(View):
    def post(self,request,category_id):
        #获取用户当前访问商品类型(3级数据)
        try:
            category = GoodsCategory.objects.get(id=category_id)
        except GoodsCategory.DoesNotExist:
            return HttpResponseForbidden('无此商品')
        #获取当天日期
        today = timezone.localdate()
        #判断今天此类商品有没有访问
        try:
            #如果不要求只统计当天的访问量，不用加date=today条件
            visi_date = GoodsVisitCount.objects.get(date=today,category=category)
        #如果没有被访问,创建访问数据
        except GoodsVisitCount.DoesNotExist:
            visi_date = GoodsVisitCount(category=category)
        #每访问一次count字段自增1
        visi_date.count += 1
        #保存
        visi_date.save()
        #返回响应
        return JsonResponse({'code':RETCODE.OK,'errmsg':'OK'})

"""保存和获取浏览记录"""
class GetVisitView(LoginRequiredMixin,View):
    #登录用户才能访问用户中心
    def get(self,request):
        #获取登录用户
        user = request.user
        #建立数据库链接获取浏览的sku_id
        redis_connect = get_redis_connection('visit_history')
        skus_id = redis_connect.lrange('visit_history_%s' % user.id, 0, -1)
        #获取所有sku_id对应的商品
        skus = SKU.objects.filter(id__in=skus_id)
        #创建列表，包装每个商品对应的信息小字典
        sku_list = []
        #遍历获得每个商品
        for sku in skus:
            #往列表添加每个商品的数据，组成字典
            sku_list.append({
                'id':sku.id,
                'name':sku.name,
                'price':sku.price,
                'default_image_url':sku.default_image.url,
            })
        return JsonResponse({'code':RETCODE.OK,'errmsg':'OK','skus':sku_list})

    #保存浏览记录
    def post(self,request):
        #获取sku_id
        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get('sku_id')
        #获取当前登录用户
        user = request.user
        #建立redis数据库链接
        redis_connect = get_redis_connection('visit_history')
        #建立管道将sku_id保存到redis数据库中
        pl = redis_connect.pipeline()

        """以list类型存储"""
        #去重(先删除)
        pl.lrem('visit_history_%s' % user.id,0, sku_id)
        #添加,从左边添加,保证了浏览的顺序
        pl.lpush('visit_history_%s' % user.id, sku_id)
        #截取,只保留前5个浏览商品
        pl.ltrim('visit_history_%s' % user.id, 0, 4)
        #执行
        pl.execute()

        return JsonResponse({'code':RETCODE.OK,'errmsg':'OK'})

"""用户详情页获取评价"""
class GoodsCommentView(View):
    def get(self,request,sku_id):
        #获取已经下单的所有sku_id对应的商品
        goods_comment = OrderGoods.objects.filter(sku_id=sku_id,is_commented=True)
        #创建一个列表，包装每条商品信息
        comment_list = []
        #遍历获得每一条订单下的商品数据
        for order_goods in goods_comment:
            #获取当前已经下单的商品的用户名
            username = order_goods.order.user.username
            comment_list.append({
                'username':username[0]+'***' + username[-1] if order_goods.is_anonymous else username,
                'comment':order_goods.comment,
                'score':order_goods.score,
            })
        return JsonResponse({'code':RETCODE.OK,'errmsg':'OK','comment_list':comment_list})
