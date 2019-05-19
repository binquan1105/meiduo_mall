from django.conf.urls import url

from . import views

urlpatterns = [
    #商品列表界面
    url(r'list/(?P<category_id>\d+)/(?P<page_num>\d+)/$',views.ListView.as_view()),

    #热销排行
    url(r'^hot/(?P<category_id>\d+)/$', views.HotGoodsView.as_view()),

    #商品详情页
    url(r'^detail/(?P<sku_id>\d+)/$',views.DetailView.as_view()),

    #统计商品访问量
    url(r'^detail/visit/(?P<category_id>\d+)/$',views.DdtailVisitView.as_view()),

    #获取浏览记录
    url(r'^browse_histories/$',views.GetVisitView.as_view()),
    
    #商品详情页获取评价
    url(r'^comments/(?P<sku_id>\d+)/$', views.GoodsCommentView.as_view()),
]