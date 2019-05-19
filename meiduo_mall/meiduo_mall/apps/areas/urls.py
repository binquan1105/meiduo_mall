from django.conf.urls import url

from . import views
urlpatterns = [
    #收货地址
    url(r'^addresses/$', views.AddressView.as_view()),
    #新增收货地址
    url(r'areas/$',views.AreasAdd.as_view()),

]