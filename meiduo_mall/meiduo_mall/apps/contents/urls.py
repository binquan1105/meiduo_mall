from django.conf.urls import url

from . import views
urlpatterns = [
    #首页
    url(r'^$',views.IndexView.as_view(),name='index'),

    #密码找回
    url(r'^password/backe/$',views.PsswordbBack.as_view(),name='passwordb'),

    #密码找回第一步，严重表单数据
    url(r'^accounts/(?P<username>[a-zA-Z0-9_-]{5,20})/sms/token/$',views.CheckDate.as_view()),

    #第二步
    url(r'^sms_codes/$',views.GetSmsCode.as_view()),

    #第二步发送短信
    url(r'^accounts/(?P<username>[a-zA-Z0-9_-]{5,20})/password/token/$',views.OrderSmsCode.as_view()),

    #第三步，重置密码
    url(r'^users/(?P<user_id>\d+)/password/$',views.ToResetPassword.as_view()),

    #设置密码成功，返回登录页面
    url(r'^getbacklongin/$',views.BackLogin.as_view()),


]