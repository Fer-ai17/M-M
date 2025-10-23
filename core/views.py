import json
from django.shortcuts import render, redirect, get_object_or_404
from urllib3 import request
from .models import Events, Tickets, Bought, Location, Municipality, Venue, Section, Seat 
from decimal import Decimal, InvalidOperation
from .cart import Cart
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import login
from django.shortcuts import render, redirect
from django.contrib.auth.views import LoginView
from django.contrib.auth import logout
from django.core.serializers.json import DjangoJSONEncoder
from .forms import EventsForm, ArtistForm, RegisterForm
from django.urls import reverse_lazy
from .utils import convert_currency as convert_currency, format_price
from django.http import HttpResponseRedirect, JsonResponse
import uuid

#Mapa Interactivo
def seat_map(request, event_id):
    """Muestra el mapa de asientos para un evento"""
    event = get_object_or_404(Events, pk=event_id)
    
    if not event.venue or not event.has_seat_map:
        messages.error(request, "Este evento no tiene mapa de asientos configurado")
        return redirect('events_detail', pk=event_id)
    
    # Obtener secciones y asientos
    sections = Section.objects.filter(venue=event.venue)
    
    # Preparar datos para JS
    sections_data = []
    for section in sections:
        sections_data.append({
            'id': section.id,
            'name': section.name,
            'price': float(section.price),
            'color': section.color
        })

    seats_data = []
    for section in sections:
        for seat in section.seats.all():
            seats_data.append({
                'id': seat.id,
                'section': {
                    'id': section.id,
                    'name': section.name,
                    'price': float(section.price),
                    'color': section.color
                },
                'row': seat.row,
                'number': seat.number,
                'x_position': seat.x_position,
                'y_position': seat.y_position,
                'status': seat.status
            })
    # Generar ID de sesión para reserva temporal
    reservation_session_id = request.session.get('reservation_session_id')
    if not reservation_session_id:
        reservation_session_id = str(uuid.uuid4())
        request.session['reservation_session_id'] = reservation_session_id
    
    context = {
        'event': event,
        'sections': sections,
        'sections_json': json.dumps(sections_data, cls=DjangoJSONEncoder),
        'seats_json': json.dumps(seats_data, cls=DjangoJSONEncoder),
        'reservation_session_id': reservation_session_id
    }
    return render(request, "store/seat_map.html", context)

def toggle_seat(request, seat_id):
    """API para reservar/liberar un asiento temporalmente"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'})
    
    reservation_session_id = request.session.get('reservation_session_id')
    if not reservation_session_id:
        return JsonResponse({'success': False, 'message': 'Sesión inválida'})
    try:
        seat = Seat.objects.get(pk=seat_id)
        action = request.POST.get('action')
        
        if action == 'select' and seat.status == 'available':
            # Marcar como temporalmente reservado por este usuario
            seat.status = 'reserved'
            seat.reserved_by = reservation_session_id
            seat.save()
            return JsonResponse({
                'success': True,
                'status': 'reserved',
                'seat': {
                    'id': seat.id,
                    'section': seat.section.name,
                    'row': seat.row,
                    'number': seat.number,
                    'price': float(seat.section.price)
                }
            })
        
        elif action == 'deselect' and seat.status == 'reserved' and seat.reserved_by == reservation_session_id:
            # Liberar la reserva temporal
            seat.status = 'available'
            seat.reserved_by = None
            seat.save()
            return JsonResponse({'success': True, 'status': 'available'})
        
        else:
            return JsonResponse({'success': False, 'message': 'Operación no permitida'})
    
    except Seat.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Asiento no encontrado'})
    
def reserve_seats(request, event_id):
    """API para confirmar la reserva de asientos y añadirlos al carrito"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'})
    
    # Obtener datos
    event = get_object_or_404(Events, pk=event_id)
    reservation_session_id = request.session.get('reservation_session_id')
    if not reservation_session_id:
        return JsonResponse({'success': False, 'message': 'Sesión inválida'})
    
    # Buscar asientos reservados por este usuario
    seats = Seat.objects.filter(
        section__venue=event.venue,
        status='reserved',
        reserved_by=reservation_session_id
    )
    
    if not seats:
        return JsonResponse({'success': False, 'message': 'No hay asientos seleccionados'})
    
    # Añadir al carrito (simplificado - necesitarás adaptar a tu lógica de carrito)
    cart = Cart(request)
    
    # Guardar IDs de asientos en el item del carrito
    seat_ids = list(seats.values_list('id', flat=True))
    cart.add(event, seat_ids=seat_ids)
    
    # Actualizar estado de los asientos
    seats.update(status='sold')
    
    # Crear nueva sesión para futuras reservas
    request.session['reservation_session_id'] = str(uuid.uuid4())
    
    return JsonResponse({'success': True, 'redirect': reverse_lazy('cart_detail')})

@staff_member_required
def seat_map_designer(request, section_id):
    """Herramienta de diseño de asientos para una sección específica"""
    section = get_object_or_404(Section, pk=section_id)
    venue = section.venue
    
    if request.method == "POST":
        data = json.loads(request.POST.get('seat_data', '[]'))
        
        # Crear o actualizar asientos
        for seat_data in data:
            seat_id = seat_data.get('id')
            
            seat_obj = None
            if seat_id and int(seat_id) > 0:
                try:
                    seat_obj = Seat.objects.get(id=seat_id)
                except Seat.DoesNotExist:
                    pass
            
            if not seat_obj:
                seat_obj = Seat(section=section)
            
            seat_obj.row = seat_data.get('row', 'A')
            seat_obj.number = seat_data.get('number', '1')
            seat_obj.x_position = seat_data.get('x', 0)
            seat_obj.y_position = seat_data.get('y', 0)
            seat_obj.status = seat_data.get('status', 'available')
            seat_obj.save()
            
        return JsonResponse({'success': True})
    
    seats = Seat.objects.filter(section=section).values(
        'id', 'row', 'number', 'x_position', 'y_position', 'status'
    )
    
    context = {
        'section': section,
        'venue': venue,
        'seats_json': json.dumps(list(seats), cls=DjangoJSONEncoder)
    }
    return render(request, 'admin/seat_map_designer.html', context)

@staff_member_required
def venue_designer(request, venue_id):
    """Herramienta para diseñar la estructura del venue (secciones)"""
    venue = get_object_or_404(Venue, pk=venue_id)
    
    if request.method == "POST":
        section_data = json.loads(request.POST.get('section_data', '[]'))
        seat_data = json.loads(request.POST.get('seat_data', '[]')) if 'seat_data' in request.POST else []
        
        # Procesar secciones
        for data in section_data:
            section_id = data.get('id')
            
            if section_id and int(section_id) > 0:
                try:
                    section = Section.objects.get(id=section_id)
                except Section.DoesNotExist:
                    section = Section(venue=venue)
            else:
                section = Section(venue=venue)
            
            section.name = data.get('name', 'Nueva Sección')
            section.price = data.get('price', 0)
            section.color = data.get('color', '#CCCCCC')
            section.x_position = data.get('x_position', 0)
            section.y_position = data.get('y_position', 0)
            section.width = data.get('width', 200)
            section.height = data.get('height', 150)
            section.save()
        
        # Procesar asientos si los hay
        for data in seat_data:
            section_id = data.get('section_id')
            
            # Si no hay section_id o es negativo (temporal), saltamos este asiento
            if not section_id or int(section_id) < 0:
                continue
                
            try:
                section = Section.objects.get(id=section_id)
                
                # Buscar si ya existe un asiento con la misma fila y número en esta sección
                try:
                    seat = Seat.objects.get(
                        section=section,
                        row=data.get('row', 'A'),
                        number=data.get('number', '1')
                    )
                except Seat.DoesNotExist:
                    seat = Seat(section=section)
                
                seat.row = data.get('row', 'A')
                seat.number = data.get('number', '1')
                seat.x_position = data.get('x_position', 0)
                seat.y_position = data.get('y_position', 0)
                seat.status = data.get('status', 'available')
                seat.save()
            except Section.DoesNotExist:
                pass  # Ignorar asientos de secciones que no existen
        
        return JsonResponse({'success': True})
    
    sections = Section.objects.filter(venue=venue).values(
        'id', 'name', 'price', 'color', 
        'x_position', 'y_position', 'width', 'height'
    )
    
    # También obtener todos los asientos existentes
    seats = Seat.objects.filter(section__venue=venue).values(
        'id', 'section__id', 'row', 'number', 
        'x_position', 'y_position', 'status'
    )
    
    context = {
        'venue': venue,
        'sections_json': json.dumps(list(sections), cls=DjangoJSONEncoder),
        'seats_json': json.dumps(list(seats), cls=DjangoJSONEncoder)
    }
    return render(request, 'store/venue_designer.html', context)

#REGISTER - LOGIN - LOGOUT
def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # inicia sesión automáticamente
            return redirect("events_list")  # o "home"
    else:
        form = RegisterForm()
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

#EDIT PROFILE
@login_required
def profile(request):
    if request.method == "POST":
        form = RegisterForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect("events_list")
    else:
        form = RegisterForm(instance=request.user)
    return render(request, "registration/profile.html", {"form": form})

#ADMIN DASHBOARD - SEARCH
@staff_member_required
def admin_dashboard(request):
    total_events = Events.objects.count()
    out_of_stock = Events.objects.filter(artist=0).count()
    total_orders = Tickets.objects.count()
    venues = Venue.objects.all()
    
    context = {
        "total_events": total_events,
        "out_of_stock": out_of_stock,
        "total_orders": total_orders,
        "venues": venues,
    }
    return render(request, "store/admin_dashboard.html", context)

@staff_member_required
def admin_dashboard_events(request):
    # events = Events.objects.all().order_by("-created_at") , {"events": events}
    return render(request, "store/admin_dashboard_products.html")

def search_events(request):
    query = request.GET.get("q", "")
    events = Events.objects.filter(name__icontains=query) | Events.objects.filter(description__icontains=query)
    # Filtrar por ubicación
    municipality_q = request.GET.get("place", "").strip()
    if municipality_q:
        events = events.filter(municipality__name__icontains=municipality_q)

    return render(request, "store/product_list.html", {
        "events": events,
        "search_query": query,
    })

#CRUD-Events
@staff_member_required
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

#LISTS - DETAILS - ORDERS

@login_required
def bought(request):
    orders = Bought.objects.all().order_by("-created_at")
    
    return render(request, "store/bought.html", {"orders": orders})

@staff_member_required
def bought_detail(request, pk):
    order = get_object_or_404(Bought, pk=pk)
    return render(request, "store/order_detail.html", {"order": order})

@login_required
def order_list(request):
    orders = Bought.objects.all().order_by("-created_at")

    return render(request, "store/order_list.html", {"orders": orders})

@staff_member_required
def order_detail(request, pk):
    order = get_object_or_404(Bought , pk=pk)
    return render(request, "store/order_detail.html", {"order": order})

def events_detail(request, pk):
    events = get_object_or_404(Events, pk=pk)
    
    context = {
        "events": events,
        "base_price": format_price(events.price, "COP", "es_CO"),
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

def events_list(request):
    qs = Events.objects.select_related("location", "artist", "place").all()

    q = request.GET.get("q", "").strip()
    location_q = request.GET.get("location", "").strip()
    municipality_q = request.GET.get("municipality", "").strip()
    label = request.GET.get("label", "").strip()

    if q:
        qs = qs.filter(name__icontains=q)

    if location_q:
        qs = qs.filter(location__name__icontains=location_q)

    if municipality_q:
        # intenta filtrar por id o por nombre parcial
        if municipality_q.isdigit():
            qs = qs.filter(place__id=int(municipality_q))
        else:
            qs = qs.filter(place__name__icontains=municipality_q)


    if label:
        qs = qs.filter(label=label)

    events = qs

    context = {
        "events": events,
        "q": q,
        "location_q": location_q,
        "municipality_q": municipality_q,
        "label": label,
        "locations": Location.objects.all(),
        "municipalities": Municipality.objects.all(),
    }
    return render(request, "store/product_list.html", context)

def add_to_cart(request, pk):
    cart = Cart(request)
    events = get_object_or_404(Events, pk=pk)

    # cantidad a añadir: si tu UI envía quantity en POST, úsala; por defecto 1
    add_qty = 1
    if request.method == "POST":
        try:
            add_qty = int(request.POST.get("quantity", 1))
            if add_qty < 1:
                add_qty = 1
        except Exception:
            add_qty = 1

    # calcular cantidad total actual en carrito
    total_qty = 0
    for item in cart:
        try:
            total_qty += int(item.get("quantity", 0))
        except Exception:
            pass

    if total_qty + add_qty > 10:
        messages.error(request, "No puede añadir más de 10 boletas en un solo pedido.")
        return redirect("cart_detail")
    
    if add_qty > events.stock:
        messages.error(request, "No hay suficiente stock disponible para la cantidad solicitada.")
        return redirect("cart_detail")

    # añadir al carrito (ajusta según tu implementación de Cart)
    cart.add(events, quantity=add_qty)
    messages.success(request, "Boleta(s) añadidas al carrito.")
    return redirect("cart_detail")

def cart_detail(request):
    cart = Cart(request)
    
    cart_items = []
    total = 0
    total_qty = 0

    for item in cart:
        events = item['events']
        quantity = item['quantity']
        seat_ids = item.get('seat_ids', [])
        
        price = events.price
        item_total = price * quantity
        total += item_total
        
        # Si hay asientos seleccionados, obtenerlos
        seats = []
        if seat_ids:
            seats = Seat.objects.select_related('section').filter(id__in=seat_ids)
        
        cart_items.append({
            'events': events,
            'quantity': quantity,
            'seats': seats,
            'price': format_price(price),
            'total': format_price(item_total),
        })

    context = {
        'cart_items': cart_items,
        'total': format_price(total),
    }
    return render(request, "store/cart_detail.html", context)

@login_required
def checkout(request):
    cart = Cart(request)
    
    # Calcular total (similar a cart_detail)
    total = 0
    total_qty = 0
    for item in cart:
        events = item['events']
        price = events.price
        total += price * item['quantity']

    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        address = request.POST.get("address")

        order = Bought.objects.create(
            customer_name=name,
            customer_email=email,
            customer_address=address,
        )

        errors = []
        for item in cart:
            try:
                Tickets.objects.create(
                    order=order,
                    events=item["events"],
                    quantity=item["quantity"],
                    price=item["events"].price,
                )
                events = item["events"]
                events.stock -= item["quantity"]
                events.save()
            except Exception as e:
                errors.append(str(e))

        if errors:
            for e in errors:
                messages.error(request, e)
            return redirect("cart_detail")

        cart.clear()
        messages.success(request, "Compra realizada correctamente.")
        return render(request, "store/checkout_done.html", {"order": order})

    context = {
        'cart': cart,
        'total': format_price(total),
    }
    return render(request, "store/checkout.html", context)

