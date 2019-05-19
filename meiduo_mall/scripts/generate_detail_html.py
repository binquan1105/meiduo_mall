#!/usr/bin/env python
import os,sys
import django
sys.path.insert(0, '../')#添加python 导包路径
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "meiduo_mall.settings.dev")#dev django配置文件

django.setup()#启动django项目

#定义函数，生成所有商品详情页x.html
from django.conf import settings
from django.shortcuts import render

from goods.models import SKU
from contents.utils import get_categories  # 商品频道
from goods.utils import get_breadcrumb  # 面包屑导航


def generate_static_sku_detail_html(sku_id):
    """将商品详情页代码渲染页面拷贝"""
    sku = SKU.objects.get(id=sku_id)
    category = sku.category
    spu = sku.spu
    sku_sepcigi_all = sku.specs.order_by('spec_id')
    sku_options_list = []
    for sku_sepcigi in sku_sepcigi_all:
        sku_options_list.append(sku_sepcigi.option_id)
    sku_spu_all = spu.sku_set.all()
    sku_id_dict = {}
    for temp_sku in sku_spu_all:
        temp_sepcifi_all = temp_sku.specs.order_by('spec_id')
        temp_sku_list = []
        for temp_sepcifi in temp_sepcifi_all:

            temp_sku_list.append(temp_sepcifi.option_id)
        sku_id_dict[tuple(temp_sku_list)] = temp_sku.id

    spu_sepcifi_all = spu.specs.order_by('id')
    for index, spu_sepcifi in enumerate(spu_sepcifi_all):
        option_all = spu_sepcifi.options.all()
        sku_copy_list = sku_options_list[:]
        for option in option_all:
            sku_copy_list[index] = option.id
            option.sku_id = sku_id_dict.get(tuple(sku_copy_list))
        spu_sepcifi.spu_op = option_all

    """商品规格选项"""

    context = {
        'categories': get_categories(),
        'breadcrumb': get_breadcrumb(category),
        'sku': sku,
        'category': category,
        'spu': spu,
        'spu_qs': spu_sepcifi_all,
    }

    #获取render渲染页面返回的响应体
    response = render(None,'detail.html',context)
    #获取响应数据转成字符串,html文本数据
    html_text = response.content.decode()
    #创建写入文件路径
    file_path = os.path.join(settings.STATICFILES_DIRS[0], 'detail/' + str(sku_id) + '.html')
    with open(file_path,'w') as f:
        f.write(html_text)
if __name__ == '__main__':
    skus = SKU.objects.all()
    for sku in skus:
        print(sku.id)
        generate_static_sku_detail_html(sku.id)