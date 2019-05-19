from django.shortcuts import render
from contents.models import ContentCategory
from .utils import get_categories
from django.conf import settings
from django.utils import timezone

import os,time

"""首页静态化"""
def generate_static_index_html():
    """将首页视图函数粘贴过来"""

    #设置定时器，将输入内容保存到指定文件
    print('%s: generate_static_index_html' % timezone.now())
    contents = {}
    contents_qs = ContentCategory.objects.all()
    for category in contents_qs:
        contents[category.key] = category.content_set.filter(status=True).order_by('sequence')
    context = {
        'categories': get_categories(),
        'contents': contents
    }

    """修改的地方"""
    response = render(None, 'index.html', context)#render渲染返回一个响应体
    #通过响应体的centent方法获取响应体数据,bytes类型，转成字符串
    html_text = response.content.decode()#获取到的数据为文本数据，通过浏览器识别HTML标签渲染

    #将新的html_text写入到static目录下
    file_path = os.path.join(settings.STATICFILES_DIRS[0],'index.html')
    with open(file_path,'w',encoding='utf-8') as f:
        f.write(html_text)#把html_text文本数据写入到index.html中