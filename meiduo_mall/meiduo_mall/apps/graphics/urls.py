from django.conf.urls import url

from . import views
urlpatterns = [
    #图形验证码请求路径:this.host + "/image_codes/" + this.uuid + "/"
    #图形验证码uuid的正则表达式为[\w-]+
    url(r'^image_codes/(?P<uuid>[\w-]+)/$', views.ImageCodeView.as_view(),name='image_codes'),

    # url(r'^sms_codes/(1[345789]\d{9})/?image_code=[a-zA-Z0-9]+&uuid=[\w-]+',views.GrapHicsView.as_view())
    url(r'^sms_codes/(?P<mobile>1[3-9]\d{9})/$', views.SMSCodeView.as_view(),name='sms_codes')
]