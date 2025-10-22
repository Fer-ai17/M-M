from django.contrib import admin
from django.urls import path, include
from core import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("", views.events_list, name="events_list"),
    path("admin/", admin.site.urls),
    path("dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("dashboard/products/", views.admin_dashboard_events, name="admin_dashboard_products"),
    
    # CRUD - Events
    path("products/new/", views.create_events, name="create_product"),
    path("products/<int:pk>/edit/", views.edit_events, name="edit_product"),
    path("products/<int:pk>/delete/", views.delete_events, name="delete_product"),
    path("products/<int:pk>/", views.events_detail, name="product_detail"),
    path("artists/new/", views.create_artist, name="create_artist"),

    # CRUD - Orders
    path("bought/", views.bought, name="bought"),
    path("bought/<int:pk>/", views.bought_detail, name="bought_detail"),
    path("bought/<int:pk>/update/", views.update_bought_status, name="update_bought_status"),
    path("bought/<int:pk>/delete/", views.delete_bought, name="delete_bought"),

    # User Authentication
    path("register/", views.register, name="register"),
    path("login/", views.CustomLoginView.as_view(), name="login"),
    path("logout/", views.custom_logout, name="logout"),
    path("edit/profile/", views.profile, name="edit_profile"),
   
    # Cart, Checkout and Search
    path("cart/", views.cart_detail, name="cart_detail"),
    path("cart/add/<int:pk>/", views.add_to_cart, name="add_to_cart"),
    path("checkout/", views.checkout, name="checkout"),
    path("search/", views.search_events, name="search_events"),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)