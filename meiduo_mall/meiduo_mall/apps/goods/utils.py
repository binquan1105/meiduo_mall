
#面包屑导航
def get_breadcrumb(category):
    cat1 = category.parent.parent
    cat1.url = cat1.goodschannel_set.all()[0].url
    breadcrumb = {
        'cat1': cat1,
        'cat2': category.parent,
        #三级数据
        'cat3': category
    }

    return breadcrumb