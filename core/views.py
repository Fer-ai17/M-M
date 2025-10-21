from django.shortcuts import render, redirect, get_object_or_404
from .models import Events, Tickets, Bought
from .cart import Cart
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import login
from django.shortcuts import render, redirect
from django.contrib.auth.views import LoginView
from django.contrib.auth import logout
from .forms import EventsForm, ArtistForm
from django.urls import reverse_lazy
from .utils import convert_currency as convert_currency, format_price
from django.http import HttpResponseRedirect


def change_currency(request, code):
    """Cambia la moneda - solo permite COP y USD"""
    valid_currencies = ["COP", "USD"]
    code = code.upper()
    
    if code in valid_currencies:
        request.session["currency"] = code
        request.session["currency_manual"] = True
        print(f"✅ Moneda cambiada a: {code}")
    else:
        request.session["currency"] = "COP"
        print(f"⚠️ Moneda no válida, usando COP por defecto")
    
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))

@staff_member_required
def admin_dashboard(request):
    total_events = Events.objects.count()
    out_of_stock = Events.objects.filter(artist=0).count()
    total_orders = Tickets.objects.count()
    # last_orders = Tickets.objects.order_by("-created_at")[:5]

    context = {
        "total_events": total_events,
        "out_of_stock": out_of_stock,
        "total_orders": total_orders,
        # "last_orders": last_orders,
    }
    return render(request, "store/admin_dashboard.html", context)

@staff_member_required
def admin_dashboard_events(request):
    # events = Events.objects.all().order_by("-created_at") , {"events": events}
    return render(request, "store/admin_dashboard_products.html")


@staff_member_required
def edit_events(request, pk):
    events = get_object_or_404(Events, pk=pk)
    if request.method == "POST":
        form = EventsForm(request.POST, request.FILES, instance=events)
        if form.is_valid():
            form.save()
            return redirect("admin_dashboard")
    else:
        form = EventsForm(instance=events)
    return render(request, "store/edit_product.html", {"form": form, "events": events})


@staff_member_required
def delete_events(request, pk):
    events = get_object_or_404(Events, pk=pk)
    events.delete()
    return redirect("admin_dashboard")

@staff_member_required
def bought_list(request):
    orders = Bought.objects.all().order_by("-created_at")
    return render(request, "store/order_list.html", {"orders": orders})


@staff_member_required
def bought_detail(request, pk):
    order = get_object_or_404(Bought, pk=pk)
    return render(request, "store/order_detail.html", {"order": order})

def events_detail(request, pk):
    events = get_object_or_404(Events, pk=pk)
    
    currency = request.session.get("currency", "COP")
    if currency not in ["COP", "USD"]:
        currency = "COP"
    
    locale = "es_CO" if currency == "COP" else "en_US"
    
    # Conversión simple
    if currency == "COP":
        local_price = events.price
    else:
        local_price = convert_currency(events.price, "COP", "USD")
    
    context = {
        "events": events,
        "converted_price": format_price(local_price, currency, locale),
        "base_price": format_price(events.price, "COP", "es_CO"),
        "currency": currency,
    }
    return render(request, "store/product_detail.html", context)

@staff_member_required
def update_order_status(request, pk):
    order = get_object_or_404(Bought, pk=pk)
    if request.method == "POST":
        new_status = request.POST.get("status")
        order.status = new_status
        order.save()
        return redirect("order_detail", pk=order.pk)
    return render(request, "store/update_order_status.html", {"order": order})

def get_converted_cart_items(cart, currency):
    """Convierte los precios del carrito a la moneda seleccionada"""
    converted_items = []
    locale_map = {
        "COP": "es_CO",
        "USD": "en_US",
        "EUR": "es_ES",
        "MXN": "es_MX",
        "ARS": "es_AR",
    }
    locale = locale_map.get(currency, "es_CO")
    
    for item in cart:
        events = item['events']
        local_price = convert_currency_utils(events.price, "COP", currency)
        converted_items.append({
            'events': events,
            'quantity': item['quantity'],
            'converted_price': format_price(local_price, currency, locale),
            'converted_total': format_price(local_price * item['quantity'], currency, locale),
            'base_price': format_price(events.price, "COP", "es_CO"),
        })
    
    return converted_items

def register(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # inicia sesión automáticamente
            return redirect("events_list")  # o "home"
    else:
        form = UserCreationForm()
    return render(request, "registration/register.html", {"form": form})
    
class CustomLoginView(LoginView):
    template_name = "registration/login.html"

    def get_success_url(self):
        if self.request.user.is_staff:
            return reverse_lazy("admin_dashboard")
        return reverse_lazy("events_list") 

def custom_logout(request):
    logout(request)
    return redirect("events_list")

@login_required
def create_events(request):
    if not request.user.is_staff:  # solo admins o staff
        return redirect("events_list")

    if request.method == "POST":
        form = EventsForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect("events_list")
    else:
        form = EventsForm()
    return render(request, "store/create_product.html", {"form": form})

@login_required
def create_artist(request):
    if not request.user.is_staff:  # solo admins o staff
        return redirect("events_list")

    if request.method == "POST":
        form = ArtistForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect("events_list")
    else:
        form = ArtistForm()
    return render(request, "store/create_product.html", {"form": form})

def events_list(request):
    # obtiene eventos con location para evitar consultas N+1
    events = Events.objects.select_related("location").all()

    return render(request, "store/product_list.html", {
        "events": events
    })

def add_to_cart(request, pk):
    cart = Cart(request)
    events = get_object_or_404(Events, pk=pk)
    cart.add(events)
    return redirect("cart_detail")

def cart_detail(request):
    cart = Cart(request)
    currency = request.session.get("currency", "COP")
    locale = "es_CO" if currency == "COP" else "en_US"
    
    cart_items = []
    total = 0
    
    for item in cart:
        events = item['events']
        quantity = item['quantity']
        
        # Precio convertido
        if currency == "COP":
            price = events.price
        else:
            price = convert_currency(events.price, "COP", "USD")
        
        item_total = price * quantity
        total += item_total
        
        cart_items.append({
            'events': events,
            'quantity': quantity,
            'price': format_price(price, currency, locale),
            'total': format_price(item_total, currency, locale),
        })
    
    context = {
        'cart_items': cart_items,
        'total': format_price(total, currency, locale),
        'currency': currency,
    }
    return render(request, "store/cart_detail.html", context)

def checkout(request):
    cart = Cart(request)
    currency = request.session.get("currency", "COP")
    locale = "es_CO" if currency == "COP" else "en_US"
    
    # Calcular total (similar a cart_detail)
    total = 0
    for item in cart:
        events = item['events']
        if currency == "COP":
            price = events.price
        else:
            price = convert_currency(events.price, "COP", "USD")
        total += price * item['quantity']

    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        address = request.POST.get("address")

        # Crear pedido
        order = Bought.objects.create(
            customer_name=name,
            customer_email=email,
            customer_address=address,
        )

        # Crear items del pedido
        for item in cart:
            Tickets.objects.create(
                order=order,
                events=item["events"],
                quantity=item["quantity"],
                price=item["events"].price,
            )
            # Descontar stock
            events = item["events"]
            events.stock -= item["quantity"]
            events.save()

        cart.clear()
        return render(request, "store/checkout_done.html", {"order": order})

    context = {
        'cart': cart,
        'total': format_price(total, currency, locale),
        'currency': currency,
    }
    return render(request, "store/checkout.html", context)

