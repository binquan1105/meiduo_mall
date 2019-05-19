from django.conf.urls import url
from django.contrib.auth.decorators import login_required

from . import views


urlpatterns = [
    # 注册
    url(r'^register/$', views.RegisterUser.as_view(), name='register'),
    # 判断用户名是否已注册
    url(r'^usernames/(?P<username>[a-zA-Z0-9_-]{5,20})/count/$', views.UserRegisterView.as_view()),
    # 判断手机号是否已注册
    url(r'^mobiles/(?P<mobile>1[3-9]\d{9})/count/$', views.MobilRegisterView.as_view()),
    # 用户登录
    url(r'^login/$', views.LoginView.as_view(), name='login'),
    # 退出登录
    url(r'^logout/$', views.LoginOutView.as_view()),
    # 用户中心
    # url(r'^info/$', login_required(views.UserInfoView.as_view()), name='info'),
    url(r'^info/$', views.UserInfo.as_view(), name='info'),
    # 设置用户邮箱
    url(r'^emails/$', views.SaveEmail.as_view()),
    # 激活邮箱
    url(r'^emails/verification/$', views.VerifyEmailView.as_view()),
    # 用户收货地址,在areas应用下
    # 用户新增收货地址
    url(r'^addresses/create/$', views.CreateAddressView.as_view()),
    # 用户收货地址修改和删除
    url(r'^addresses/(?P<address_id>\d+)/$', views.UpdateDestroyAddressView.as_view()),
    # 用户设置默认地址
    url(r'^addresses/(?P<address_id>\d+)/default/$', views.ChangeDefaultView.as_view()),
    # 修改用户地址标题
    url(r'^addresses/(?P<address_id>\d+)/title/$', views.ChangeAdressTitle.as_view()),
    # 修改用户密码
    url(r'^password/$', views.ChangePassword.as_view()),
    # 我的订单页面
    url(r'^orders/info/(?P<page_num>\d+)/$', views.UserOrderInfoView.as_view()),
]