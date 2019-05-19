from django.conf.urls import url

from . import views

urlpatterns  = [
    #加入购物车
    url(r'^carts/$',views.AddToCart.as_view()),
    #全选购物车
    url(r'^carts/selection/$',views.CartSelecteAllView.as_view()),
    #商品页面右上角购物车
    url(r'^carts/simple/$',views.CartsSimpleView.as_view()),
    #结算页面
    url(r'^orders/settlement/$',views.OrderSettlementView.as_view()),
]