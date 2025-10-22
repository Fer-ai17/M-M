from django.contrib import admin
from django.urls import path, include
from core import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("", views.events_list, name="events_list"),
    path("admin/", admin.site.urls),
    path("dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("dashboard/events/", views.admin_dashboard_events, name="admin_dashboard_events"),
    
    # CRUD - Events
    path("events/new/", views.create_events, name="create_events"),
    path("events/<int:pk>/edit/", views.edit_events, name="edit_events"),
    path("events/<int:pk>/delete/", views.delete_events, name="delete_events"),
    path("events/<int:pk>/", views.events_detail, name="events_detail"),
    path("artists/new/", views.create_artist, name="create_artist"),

    # CRUD - Orders - Bought
    path("bought/", views.bought, name="bought"),
    path("bought/<int:pk>/", views.bought_detail, name="bought_detail"),

    path("order/", views.order_list, name="order_list"),
    path("order/<int:pk>/", views.order_detail, name="order_detail"),
    path("order/<int:pk>/update/", views.update_order_status, name="update_order_status"),


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