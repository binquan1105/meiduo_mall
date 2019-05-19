"""meiduo_mall URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url,include
from django.contrib import admin

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^', include('users.urls',namespace='users')),
    url(r'^', include('contents.urls', namespace='contents')),  # 首页模块
    url(r'^', include('graphics.urls',namespace='graphics')),#图形验证码
    url(r'^', include('oauth.urls')),#qq用户登录
    url(r'^',include('areas.urls')),#收货地址
    url(r'^',include('goods.urls')),#商品列表
    url(r'^search/',include('haystack.urls')),#配置haystack路由
    url(r'^',include('carts.urls')),#购物车
    url(r'^',include('orders.urls')),#提交订单
    url(r'^',include('payment.urls')),#支付页面
]
