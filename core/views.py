import json
from django.shortcuts import render, redirect, get_object_or_404
from urllib3 import request
from .models import Events, Tickets, Bought, Location, Municipality, Venue, Section, Seat, Profile
from decimal import Decimal, InvalidOperation
from django.db import transaction
from django.db.models import Count, Q
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
from .forms import EventsForm, ArtistForm, RegisterForm, VenueForm
from django.urls import reverse_lazy
from .utils import convert_currency as convert_currency, format_price
from django.http import HttpResponseRedirect, JsonResponse
import uuid

#Mapa Interactivo
def seat_map(request, event_id):
    """Muestra selección por secciones para un evento (sin mapa visual)."""
    event = get_object_or_404(Events, pk=event_id)
    
    if not event.venue or not event.has_seat_map:
        messages.error(request, "Este evento no tiene mapa de asientos configurado")
        return redirect('events_detail', pk=event_id)

    # Generar ID de sesión para reserva temporal
    reservation_session_id = request.session.get('reservation_session_id')
    if not reservation_session_id:
        reservation_session_id = str(uuid.uuid4())
        request.session['reservation_session_id'] = reservation_session_id

    # Liberar reservas atascadas de otras sesiones para evitar asientos bloqueados indefinidamente.
    Seat.objects.filter(
        section__venue=event.venue,
        status='reserved'
    ).exclude(reserved_by=reservation_session_id).update(status='available', reserved_by=None)
    
    # Contar disponibilidad por sección (incluyendo reservados de esta sesión).
    sections_qs = Section.objects.filter(venue=event.venue).annotate(
        available_count=Count(
            'seats',
            filter=(Q(seats__status='available') | Q(seats__status='reserved', seats__reserved_by=reservation_session_id)),
        )
    ).order_by('name')

    sections = list(sections_qs)
    ranked_sections = sorted(sections, key=lambda s: (s.price, s.name), reverse=True)

    total_ranked = len(ranked_sections)
    for index, section in enumerate(ranked_sections):
        if total_ranked <= 1:
            description = "Vista general del escenario."
        elif index < max(1, total_ranked // 3):
            description = "Muy cerca del escenario."
        elif index < max(2, (2 * total_ranked) // 3):
            description = "Distancia media al escenario."
        else:
            description = "Zona más alejada del escenario."

        section.proximity_description = description

    current_cart_item = Cart(request).cart.get(str(event.id), {})
    selected_count = len(current_cart_item.get('seat_ids', []))
    context = {
        'event': event,
        'sections': sections,
        'selected_count': selected_count,
        'reservation_session_id': reservation_session_id,
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
    """Confirma selección de sección/cantidad y reserva asientos para el carrito."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'})
    
    # Obtener datos
    event = get_object_or_404(Events, pk=event_id)
    reservation_session_id = request.session.get('reservation_session_id')
    if not reservation_session_id:
        return JsonResponse({'success': False, 'message': 'Sesión inválida'})
    
    cart = Cart(request)

    # Nuevo flujo: selección por sección + cantidad.
    section_id = request.POST.get('section_id')
    if section_id:
        try:
            quantity = int(request.POST.get('quantity', '1'))
        except (TypeError, ValueError):
            quantity = 0

        if quantity < 1:
            messages.error(request, 'Cantidad inválida.')
            return redirect('seat_map', event_id=event.id)

        section = get_object_or_404(Section, pk=section_id, venue=event.venue)

        # Liberar selección previa de este evento para reemplazarla.
        previous_ids = cart.cart.get(str(event.id), {}).get('seat_ids', [])
        if previous_ids:
            Seat.objects.filter(
                id__in=previous_ids,
                status='reserved',
                reserved_by=reservation_session_id
            ).update(status='available', reserved_by=None)

        candidate_qs = Seat.objects.filter(
            section=section
        ).filter(
            Q(status='available') | Q(status='reserved', reserved_by=reservation_session_id)
        ).order_by('row', 'number')

        seat_ids = list(candidate_qs.values_list('id', flat=True)[:quantity])
        if len(seat_ids) < quantity:
            messages.error(request, f'No hay suficientes asientos disponibles en {section.name}.')
            return redirect('seat_map', event_id=event.id)

        Seat.objects.filter(id__in=seat_ids, status='available').update(
            status='reserved',
            reserved_by=reservation_session_id,
        )

        cart.add(event, quantity=len(seat_ids), update_quantity=True, seat_ids=seat_ids)
        messages.success(request, f'Seleccionaste {len(seat_ids)} asiento(s) en {section.name}.')

        return redirect('cart_detail')

    # Compatibilidad: flujo previo basado en asientos reservados por la sesión.
    seats = Seat.objects.filter(
        section__venue=event.venue,
        status='reserved',
        reserved_by=reservation_session_id
    )

    if not seats:
        return JsonResponse({'success': False, 'message': 'No hay asientos seleccionados'})

    seat_ids = list(seats.values_list('id', flat=True))
    cart.add(event, quantity=len(seat_ids), update_quantity=True, seat_ids=seat_ids)

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


PREDEFINED_VENUE_LAYOUTS = {
    "theater": [
        {"name": "VIP", "price": Decimal("220.00"), "color": "#d94f4f", "x": 150, "y": 160, "width": 700, "height": 170},
        {"name": "Preferencial", "price": Decimal("180.00"), "color": "#f08a4b", "x": 110, "y": 390, "width": 780, "height": 170},
        {"name": "General", "price": Decimal("130.00"), "color": "#4da261", "x": 70, "y": 620, "width": 860, "height": 170},
    ],
    "arena": [
        {"name": "Arena 1", "price": Decimal("160.00"), "color": "#d94f4f", "x": 450, "y": 120, "width": 170, "height": 120},
        {"name": "Arena 2", "price": Decimal("160.00"), "color": "#f08a4b", "x": 700, "y": 220, "width": 170, "height": 120},
        {"name": "Arena 3", "price": Decimal("160.00"), "color": "#e6c229", "x": 790, "y": 430, "width": 170, "height": 120},
        {"name": "Arena 4", "price": Decimal("160.00"), "color": "#4da261", "x": 700, "y": 640, "width": 170, "height": 120},
        {"name": "Arena 5", "price": Decimal("160.00"), "color": "#2a9d8f", "x": 450, "y": 740, "width": 170, "height": 120},
        {"name": "Arena 6", "price": Decimal("160.00"), "color": "#4f7bd9", "x": 200, "y": 640, "width": 170, "height": 120},
        {"name": "Arena 7", "price": Decimal("160.00"), "color": "#8b5cf6", "x": 110, "y": 430, "width": 170, "height": 120},
        {"name": "Arena 8", "price": Decimal("160.00"), "color": "#c24193", "x": 200, "y": 220, "width": 170, "height": 120},
    ],
    "stadium": [
        {"name": "Tribuna Norte", "price": Decimal("190.00"), "color": "#2a9d8f", "x": 70, "y": 150, "width": 860, "height": 120},
        {"name": "Occidental", "price": Decimal("170.00"), "color": "#4f7bd9", "x": 90, "y": 320, "width": 140, "height": 370},
        {"name": "Oriental", "price": Decimal("170.00"), "color": "#8b5cf6", "x": 770, "y": 320, "width": 140, "height": 370},
        {"name": "Tribuna Sur", "price": Decimal("140.00"), "color": "#4da261", "x": 70, "y": 620, "width": 860, "height": 140},
        {"name": "Gramilla Lateral", "price": Decimal("110.00"), "color": "#e6c229", "x": 120, "y": 790, "width": 760, "height": 110},
    ],
}


def _safe_decimal(value, default_value):
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal(str(default_value))


def _generate_default_seats_for_section(section):
    seat_width = 20
    seat_height = 20
    seat_margin = 5
    header_space = 30

    rows = max(1, (section.height - header_space) // (seat_height + seat_margin))
    seats_in_row = max(1, section.width // (seat_width + seat_margin))

    total_row_width = seats_in_row * (seat_width + seat_margin)
    start_x = section.x_position + max(0, (section.width - total_row_width) // 2)

    for row_index in range(rows):
        if row_index < 26:
            row_label = chr(65 + row_index)
        else:
            row_label = f"R{row_index + 1}"

        seat_y = section.y_position + header_space + (row_index * (seat_height + seat_margin))

        for seat_number in range(1, seats_in_row + 1):
            seat_x = start_x + ((seat_number - 1) * (seat_width + seat_margin))
            Seat.objects.create(
                section=section,
                row=row_label,
                number=str(seat_number),
                x_position=seat_x,
                y_position=seat_y,
                status='available',
            )


def _sync_location_from_venue(venue):
    min_section_price = Section.objects.filter(venue=venue).order_by('price').values_list('price', flat=True).first()
    if min_section_price is None:
        min_section_price = Decimal('0.00')

    available_seat_count = Seat.objects.filter(section__venue=venue, status='available').count()
    loc_code = f"VENUE-{venue.id}"

    location, _ = Location.objects.get_or_create(
        loc_code=loc_code,
        defaults={
            'name': venue.name,
            'price': min_section_price,
            'stock': available_seat_count,
        }
    )

    location.name = venue.name
    location.price = min_section_price
    location.stock = available_seat_count
    location.save()
    return location


@staff_member_required
def venue_designer(request, venue_id):
    """Configura un venue con plantillas predefinidas de areas y precios."""
    venue = get_object_or_404(Venue, pk=venue_id)
    
    if request.method == "POST":
        venue_type = request.POST.get('venue_type', 'theater')
        if venue_type not in PREDEFINED_VENUE_LAYOUTS:
            return JsonResponse({'success': False, 'message': 'Tipo de recinto invalido'})

        try:
            area_payload = json.loads(request.POST.get('areas', '[]'))
        except json.JSONDecodeError:
            area_payload = []

        # Reemplazar completamente la configuracion previa
        Section.objects.filter(venue=venue).delete()

        template_layout = PREDEFINED_VENUE_LAYOUTS[venue_type]
        for index, item in enumerate(template_layout):
            incoming = area_payload[index] if index < len(area_payload) and isinstance(area_payload[index], dict) else {}
            area_name = (incoming.get('name') or item['name']).strip()
            if not area_name:
                area_name = item['name']

            area_price = _safe_decimal(incoming.get('price'), item['price'])

            section = Section.objects.create(
                venue=venue,
                name=area_name[:50],
                price=area_price,
                color=item['color'],
                x_position=item['x'],
                y_position=item['y'],
                width=item['width'],
                height=item['height'],
            )
            _generate_default_seats_for_section(section)

        synced_location = _sync_location_from_venue(venue)
        Events.objects.filter(venue=venue).update(location=synced_location, has_seat_map=True)
        
        return JsonResponse({'success': True})

    sections_qs = Section.objects.filter(venue=venue)
    section_count = sections_qs.count()
    if section_count == len(PREDEFINED_VENUE_LAYOUTS['arena']):
        default_venue_type = 'arena'
    elif section_count == len(PREDEFINED_VENUE_LAYOUTS['stadium']):
        default_venue_type = 'stadium'
    else:
        default_venue_type = 'theater'

    sections = sections_qs.values(
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
        'default_venue_type': default_venue_type,
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
    out_of_stock = Events.objects.filter(location__stock=0).count()
    total_orders = Bought.objects.count()
    last_orders = Bought.objects.select_related("profile__user", "tickets__events").order_by("-created_at")[:8]
    venues = Venue.objects.all()
    
    context = {
        "total_events": total_events,
        "out_of_stock": out_of_stock,
        "total_orders": total_orders,
        "last_orders": last_orders,
        "venues": venues,
    }
    return render(request, "store/admin_dashboard.html", context)

@staff_member_required
def admin_dashboard_events(request):
    events = Events.objects.select_related("location", "artist").all().order_by("-id")
    return render(request, "store/admin_dashboard_products.html", {"events": events})


@staff_member_required
def venue_list(request):
    venues = Venue.objects.all().order_by("name")
    return render(request, "store/venue_list.html", {"venues": venues})

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


@staff_member_required
def create_venue(request):
    if request.method == "POST":
        form = VenueForm(request.POST)
        if form.is_valid():
            venue = form.save()
            messages.success(request, "Lugar creado correctamente.")
            return redirect("venue_designer", venue_id=venue.id)
    else:
        form = VenueForm()

    return render(request, "store/create_venue.html", {"form": form})


@staff_member_required
def delete_venue(request, venue_id):
    if request.method != "POST":
        messages.error(request, "Método no permitido para eliminar lugares.")
        return redirect("admin_dashboard")

    venue = get_object_or_404(Venue, pk=venue_id)
    venue_name = venue.name
    venue.delete()
    messages.success(request, f"Lugar '{venue_name}' eliminado correctamente.")
    return redirect("admin_dashboard")

#CRUD-Events
@staff_member_required
def create_events(request):
    if not request.user.is_staff:  # solo admins o staff
        return redirect("events_list")

    if request.method == "POST":
        form = EventsForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            selected_venue = form.cleaned_data["venue"]
            event.venue = selected_venue
            event.location = _sync_location_from_venue(selected_venue)
            event.has_seat_map = True
            event.save()
            return redirect("admin_dashboard_events")
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
            event = form.save(commit=False)
            selected_venue = form.cleaned_data["venue"]
            event.venue = selected_venue
            event.location = _sync_location_from_venue(selected_venue)
            event.has_seat_map = True
            event.save()
            return redirect("admin_dashboard_events")
    else:
        form = EventsForm(instance=events)
    return render(request, "store/edit_product.html", {"form": form, "events": events})

@staff_member_required
def delete_events(request, pk):
    events = get_object_or_404(Events, pk=pk)
    events.delete()
    return redirect("admin_dashboard_events")

#LISTS - DETAILS - ORDERS

@login_required
def bought(request):
    user_profile = Profile.objects.filter(user=request.user).first()
    if not user_profile:
        orders = Bought.objects.none()
    else:
        orders = Bought.objects.select_related("tickets__events", "profile__user").filter(profile=user_profile).order_by("-created_at")
    
    return render(request, "store/bought.html", {"orders": orders})

@login_required
def bought_detail(request, pk):
    if request.user.is_staff:
        order = get_object_or_404(Bought, pk=pk)
    else:
        user_profile = Profile.objects.filter(user=request.user).first()
        order = get_object_or_404(Bought, pk=pk, profile=user_profile)
    return render(request, "store/order_detail.html", {"order": order})

@staff_member_required
def order_list(request):
    orders = Bought.objects.select_related("tickets__events", "profile__user").all().order_by("-created_at")

    return render(request, "store/order_list.html", {"orders": orders})

@staff_member_required
def order_detail(request, pk):
    order = get_object_or_404(Bought , pk=pk)
    return render(request, "store/order_detail.html", {"order": order})

def events_detail(request, pk):
    events = get_object_or_404(Events, pk=pk)
    
    context = {
        "events": events,
        # Usar location.price en lugar de events.price
        "base_price": format_price(events.location.price, "COP", "es_CO"),
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

    # Para eventos con mapa de asientos, forzar selección de zona/asiento.
    if events.has_seat_map and events.venue:
        messages.info(request, "Para este evento debes seleccionar zona y asiento.")
        return redirect("seat_map", event_id=events.id)

    # cantidad a añadir
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
    
    # Verificar stock - el stock está en Location, no en Events
    if add_qty > events.location.stock:
        messages.error(request, "No hay suficiente stock disponible para la cantidad solicitada.")
        return redirect("cart_detail")

    # añadir al carrito
    cart.add(events, quantity=add_qty)
    messages.success(request, "Boleta(s) añadidas al carrito.")
    return redirect("cart_detail")

def remove_from_cart(request, pk):
    cart = Cart(request)
    events = get_object_or_404(Events, pk=pk)

    item = cart.cart.get(str(events.id), {})
    seat_ids = item.get("seat_ids", [])
    if seat_ids:
        Seat.objects.filter(id__in=seat_ids, status='reserved').update(status='available', reserved_by=None)

    cart.remove(events)
    messages.success(request, "Boleta(s) eliminadas del carrito.")
    return redirect("cart_detail")

def cart_detail(request):
    cart = Cart(request)
    
    cart_items = []
    total = 0
    total_qty = 0

    for item in cart:
        events = item['events']
        quantity = int(item.get('quantity', 0))
        seat_ids = item.get('seat_ids', [])

        # Si hay asientos seleccionados, obtenerlos
        seats = []
        if seat_ids:
            seats = Seat.objects.select_related('section').filter(id__in=seat_ids)

        if seats:
            item_total = sum((seat.section.price for seat in seats), Decimal("0.00"))
            quantity = len(seats)
            price = item_total / quantity if quantity else Decimal("0.00")
        else:
            price = events.location.price
            item_total = price * quantity

        total += item_total
        
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

    if not cart.cart:
        messages.error(request, "Tu carrito está vacío.")
        return redirect("cart_detail")
    
    # Calcular total (similar a cart_detail)
    total = Decimal("0.00")
    for item in cart:
        events = item['events']
        seat_ids = item.get('seat_ids', [])
        if seat_ids:
            seats = Seat.objects.select_related('section').filter(id__in=seat_ids)
            total += sum((seat.section.price for seat in seats), Decimal("0.00"))
        else:
            price = events.location.price
            total += price * int(item.get('quantity', 0))

    if request.method == "POST":
        profile, _ = Profile.objects.get_or_create(
            user=request.user,
            defaults={
                "name": request.user.first_name or "",
                "lastname": request.user.last_name or "",
                "email": request.user.email or "",
            }
        )

        profile_updated = False
        if request.user.first_name and not profile.name:
            profile.name = request.user.first_name
            profile_updated = True
        if request.user.last_name and not profile.lastname:
            profile.lastname = request.user.last_name
            profile_updated = True
        if request.user.email and not profile.email:
            profile.email = request.user.email
            profile_updated = True
        if profile_updated:
            profile.save()

        created_orders = []

        try:
            with transaction.atomic():
                for item in cart:
                    events = item["events"]
                    seat_ids = item.get("seat_ids", [])

                    if events.has_seat_map and not seat_ids:
                        raise ValueError(f"Debes seleccionar zona/asiento para {events.name}.")

                    # Si viene desde mapa de asientos, la cantidad real es la cantidad de asientos.
                    requested_qty = len(seat_ids) if seat_ids else int(item.get("quantity", 0))

                    if requested_qty < 1:
                        raise ValueError("La cantidad de boletas debe ser mayor a cero.")

                    location = events.location
                    if requested_qty > location.stock:
                        raise ValueError(f"No hay stock suficiente para {events.name}.")

                    if seat_ids:
                        reserved_seats = Seat.objects.select_related('section').filter(
                            id__in=seat_ids,
                            section__venue=events.venue,
                        )
                        if reserved_seats.count() != requested_qty:
                            raise ValueError(f"Algunos asientos de {events.name} ya no están disponibles.")

                        # No vender asientos bloqueados o ya vendidos.
                        invalid = reserved_seats.exclude(status__in=['reserved', 'available'])
                        if invalid.exists():
                            raise ValueError(f"Algunos asientos de {events.name} ya no están disponibles.")

                    ticket = Tickets.objects.create(
                        events=events,
                        quantity=requested_qty,
                    )

                    order = Bought.objects.create(
                        profile=profile,
                        tickets=ticket,
                        status="completado",
                    )
                    created_orders.append(order)

                    if seat_ids:
                        reserved_seats.update(status='sold', reserved_by=None)

                    location.stock -= requested_qty
                    location.save()

        except Exception as exc:
            messages.error(request, f"No se pudo completar la compra: {exc}")
            return redirect("cart_detail")

        cart.clear()
        messages.success(request, "Compra realizada correctamente.")
        order = created_orders[0] if created_orders else None
        return render(request, "store/checkout_done.html", {"order": order, "orders": created_orders})

    context = {
        'cart': cart,
        'total': format_price(total),
    }
    return render(request, "store/checkout.html", context)

