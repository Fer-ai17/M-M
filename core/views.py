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
from django.core.exceptions import ValidationError
from .utils import convert_currency as convert_currency_utils
from .forms import ArtistForm
from .models import EventArtist
from .models import Artist
from django.contrib import messages
from django.db import transaction
from django.utils import timezone


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


def index(request):
    return render(request, "store/index.html")

def search_events(request):
    query = request.GET.get("q", "")
    events = Events.objects.filter(name__icontains=query) | Events.objects.filter(description__icontains=query)
    # Filtrar por ubicación

    return render(request, "store/product_list.html", {
        "events": events,
        "search_query": query,
    })

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
        local_price = convert_currency_utils(events.price, "COP", currency) # type: ignore
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
            artist = form.save(commit=False)
            artist.save()
            events = form.cleaned_data.get("events")
            errors = []
            for ev in events:
                link = EventArtist(artist=artist, event=ev)
                try:
                    link.full_clean()
                    link.save()
                except ValidationError as e:
                    errors.extend(e.messages)
            if errors:
                artist.delete()
                form.add_error(None,errors)
            else:
                artist.save()
                return redirect("artist_list")
    else:
        form = ArtistForm()
    return render(request, "store/create_artist.html", {"form": form})

def artist_list(request):
    artist = Artist.objects.all()

    return render(request, "store/artist_list.html")

def events_list(request):
    # obtiene eventos con location para evitar consultas N+1
    events = Events.objects.select_related("location").all()

    # moneda válida: COP o USD (por defecto COP)
    currency = request.session.get("currency", "COP")
    if currency not in ["COP", "USD"]:
        currency = "COP"
        request.session["currency"] = currency

    locale = "es_CO" if currency == "COP" else "en_US"

    converted_events = []
    for e in events:
        base_price = e.location.price
        if currency == "COP":
            local_price = base_price
        else:
            # convert_currency(amount, from_currency, to_currency)
            local_price = convert_currency(base_price, "COP", currency)

        converted_events.append({
            "obj": e,
            "converted_price": format_price(local_price, currency, locale),
            "currency": currency,
            "base_price": format_price(base_price, "COP", "es_CO"),
        })

    return render(request, "store/product_list.html", {
        "events": converted_events,
        "current_currency": currency
    })

@login_required
def add_to_cart(request, pk):
    cart = Cart(request)
    events = get_object_or_404(Events, pk=pk)

    # cantidad a añadir (si el form envía quantity, úsala)
    try:
        add_qty = int(request.POST.get("quantity", 1)) if request.method == "POST" else 1
    except Exception:
        add_qty = 1
        
    if add_qty < 1:
        add_qty = 1

    # calcular total actual en carrito
    total_qty = sum(int(item.get("quantity", 0)) for item in cart)

    if total_qty + add_qty > 10:
        messages.error(request, "No puede añadir más de 10 boletas en un solo pedido.")
        return redirect("cart_detail")

    # evitar añadir más del stock disponible
    if add_qty > events.stock:
        messages.error(request, f"Sólo hay {events.stock} boletas disponibles para '{events.name}'.")
        return redirect("cart_detail")

    # añadir al carrito
    cart.add(events, quantity=add_qty)
    messages.success(request, "Boleta(s) añadidas al carrito.")
    return redirect("cart_detail")

def cart_detail(request):
    cart = Cart(request)
    currency = request.session.get("currency", "COP")
    locale = "es_CO" if currency == "COP" else "en_US"

    cart_items = []
    total = 0
    total_qty = 0

    for item in cart:
        events = item["events"]
        quantity = int(item.get("quantity", 0))
        total_qty += quantity

        # Precio convertido
        if currency == "COP":
            price = events.price
        else:
            price = convert_currency(events.price, "COP", "USD")

        item_total = price * quantity
        total += item_total

        cart_items.append({
            "events": events,
            "quantity": quantity,
            "price": format_price(price, currency, locale),
            "total": format_price(item_total, currency, locale),
        })

    context = {
        "cart_items": cart_items,
        "total": format_price(total, currency, locale),
        "currency": currency,
        "total_qty": total_qty,
    }
    return render(request, "store/cart_detail.html", context)

@login_required
def checkout(request):
    cart = Cart(request)
    total_qty = sum(int(item.get("quantity", 0)) for item in cart)
    if total_qty == 0:
        messages.error(request, "El carrito está vacío.")
        return redirect("events_list")
    if total_qty > 10:
        messages.error(request, "No se puede procesar la compra: máximo 10 boletas por pedido.")
        return redirect("cart_detail")

    if request.method == "POST":
        profile = getattr(request.user, "profile", None)
        if not profile:
            messages.error(request, "Debe completar su perfil antes de comprar.")
            return redirect("cart_detail")

        with transaction.atomic():
            errors = []
            reserve = []  # (event_obj, qty, unit_price)

            # Bloquear y validar stock
            for item in cart:
                ev = item["events"]
                qty = int(item.get("quantity", 0))
                event = Events.objects.select_for_update().get(pk=ev.pk)
                if event.stock < qty:
                    errors.append(f"No hay suficientes boletas para '{event.name}' (disponible: {event.stock}).")
                else:
                    reserve.append((event, qty, float(getattr(event, "price", 0))))

            if errors:
                for e in errors:
                    messages.error(request, e)
                return redirect("cart_detail")

            # Crear Bought y Tickets, decrementar stock
            order = Bought.objects.create(
                profile=profile,
                total_qty=sum(q for _, q, _ in reserve),
                total_price=sum(q * p for _, q, p in reserve),
            )

            for event, qty, unit_price in reserve:
                Tickets.objects.create(
                    bought=order,
                    events=event,
                    quantity=qty,
                    price=unit_price,
                    purchase_date=timezone.now(),
                )
                event.stock -= qty
                event.save()

            cart.clear()

        messages.success(request, "Compra realizada correctamente.")
        return render(request, "store/checkout_done.html", {"order": order})

    # resumen de checkout
    items = []
    total = 0
    for item in cart:
        ev = item["events"]
        qty = int(item.get("quantity", 0))
        price = getattr(ev, "price", 0)
        items.append({"events": ev, "quantity": qty, "price": price, "subtotal": price * qty})
        total += price * qty

    context = {"cart": cart, "items": items, "total": total, "total_qty": total_qty}
    return render(request, "store/checkout.html", context)

