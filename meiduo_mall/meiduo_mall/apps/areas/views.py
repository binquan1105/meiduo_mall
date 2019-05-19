from django.shortcuts import render
from django.views import View
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin

from meiduo_mall.libs.response_code import RETCODE
from .models import Area
from users.models import Address

#收货地址，显示收货地址
class AddressView(LoginRequiredMixin,View):
    def get(self,request):
        #获取当前用户所有的收货地址
        user = request.user
        all_address = Address.objects.filter(user=user,is_deleted=False)
        print(all_address)
        if not all_address:
            return render(request, 'user_center_site.html')
        #遍历数据,添加到列表
        adress_list = []
        for adress_model in all_address:
            #获取所有字段的值重新组成字典,前端已经写死了,所以建值对顺序要跟前端匹配，
            #这里要多填province，city，place三个建,因为点击编辑时如果没有传这三个值,省市区的名字就不会显示
            adress_dict = {
                'id': adress_model.id,
                'title': adress_model.title,
                'receiver': adress_model.receiver,
                'province_id': adress_model.province_id,
                'province': adress_model.province.name,
                'city_id': adress_model.city_id,
                'city': adress_model.city.name,
                'district_id': adress_model.district_id,
                'district': adress_model.district.name,
                'place': adress_model.place,
                'mobile': adress_model.mobile,
                'tel': adress_model.tel,
                'email': adress_model.email,
            }
            adress_list.append(adress_dict)

        context = {
            'addresses': adress_list,
            'default_address_id': user.default_address_id,
        }

        return render(request, 'user_center_site.html',context)




#新增收货地址
class AreasAdd(View):
    def get(self,request):
        #根据所选的地区id通过字符串采纳数传递,
        areas_id = request.GET.get('area_id')

        #如果省部数据为空,获取省级数据
        if not areas_id:
            from django.core.cache import cache
            #读取缓存数据,有缓存数据就不用往下执行
            parent_list = cache.get('area_id')

            # 没有缓存的情况下
            if not parent_list:

                try:
                    # 根据外建=null来获取省部数据
                    parent_models_list = Area.objects.filter(parent__isnull=True)
                    #创建列表,将数据添加进列表
                    parent_list = []
                    #遍历数据,返回id,name
                    for parent_model in parent_models_list:
                        parent_list.append({'id':parent_model.id,'name':parent_model.name})


                except Exception as e:
                    #返回特定的响应状态
                    return JsonResponse({'code': RETCODE.DBERR, 'errmsg': '省份数据错误'})

                #设置缓存:格式：cache.set(建,值,过期时间)#将来根据公司规定
                cache.set('area_id',parent_list,3600)

             # 返回json数据格式
            return JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'province_list': parent_list})
        #如果省部数据不为空，则获取市级或者区级数据
        else:

            #获取缓存
            from django.core.cache import cache
            date = cache.get('area_%s' % areas_id)

            if not date:
                #通过主键的id=父建的外建获取市或区的父集数据对象
                try:
                    areas_parent_model = Area.objects.get(id=areas_id)
                    #通过在models模型类修改的subs方法获得父集的所有子集
                    areas_list_model = areas_parent_model.subs.all()
                    # print(areas_list_model)
                    #遍历数据获得每一条子集数据对象,添加id和name字段内容用字典储存到列表中
                    areas_parent_list = []
                    for areas_model in areas_list_model:
                        areas_parent_list.append({'id':areas_model.id,'name':areas_model.name})
                    date = {
                        'id':areas_model.id,#父级id
                        'name':areas_model.name,#父级地名
                        'subs':areas_parent_list#父级所有子集的id和地名
                    }
                except Area.DoesNotExist:
                    return JsonResponse({'code':RETCODE.DBERR,'errmsg':'市区数据错误'})

                #设置缓存
                cache.set('area_%s' % areas_id,date,3600)

            return JsonResponse({'code': RETCODE.OK, 'errmsg': '获取数据成功', 'sub_data': date})
