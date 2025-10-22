from django.contrib import admin
from django.urls import path
from core import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [

    path("admin/", admin.site.urls),

    path("dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("dashboard/products/", views.admin_dashboard_events, name="admin_dashboard_products"),
    
    path("index/", views.index, name="index"),

    path("products/new/", views.create_events, name="create_events"),
    path("products/<int:pk>/edit/", views.edit_events, name="edit_events"),
    path("products/<int:pk>/delete/", views.delete_events, name="delete_events"),
    path("products/<int:pk>/", views.events_detail, name="events_detail"),

    path("artists/new/", views.create_artist, name="create_artist"),
    path("artist_list/", views.artist_list, name="artist_list"),

    path("orders/", views.bought_list, name="order_list"),
    path("orders/<int:pk>/", views.bought_detail, name="order_detail"),
    path("orders/<int:pk>/update/", views.update_order_status, name="update_order_status"),

    path("register/", views.register, name="register"),
    path("login/", views.CustomLoginView.as_view(), name="login"),
    path("logout/", views.custom_logout, name="logout"),

    path("cart/", views.cart_detail, name="cart_detail"),
    path("cart/add/<int:pk>/", views.add_to_cart, name="add_to_cart"),
    path("checkout/", views.checkout, name="checkout"),

    path("search/", views.search_events, name="search_events"),

    path("", views.events_list, name="events_list"),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
