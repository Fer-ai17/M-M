from core.models import Events
from decimal import Decimal


class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get("cart")
        if not cart:
            cart = self.session["cart"] = {}
        self.cart = cart

    def add(self, events, quantity=1, update_quantity=False, seat_ids=None):
        """
        Añadir un evento al carrito o actualizar su cantidad
        """
        events_id = str(events.id)
        
        if events_id not in self.cart:
            # Convertir el Decimal a string para que sea serializable
            price = str(events.location.price)
            self.cart[events_id] = {
                'quantity': 0,
                'price': price,
            }
        
        if update_quantity:
            self.cart[events_id]['quantity'] = quantity
        else:
            self.cart[events_id]['quantity'] += quantity
        
        # Si hay seat_ids, guardarlos en el carrito
        if seat_ids:
            self.cart[events_id]['seat_ids'] = seat_ids
        
        self.save()

    def remove(self, events):
        events_id = str(events.id)
        if events_id in self.cart:
            del self.cart[events_id]
            self.save()

    def clear(self):
        self.session["cart"] = {}
        self.session.modified = True

    def save(self):
        # Asegurarse de que todos los valores son serializables
        cart_copy = self.cart.copy()
        for key, item in cart_copy.items():
            if 'price' in item and isinstance(item['price'], Decimal):
                item['price'] = str(item['price'])
            if 'total_price' in item and isinstance(item['total_price'], Decimal):
                item['total_price'] = str(item['total_price'])
        
        # Guardar en la sesión con la clave correcta
        self.session["cart"] = cart_copy
        self.session.modified = True

    def __iter__(self):
        """
        Iterar sobre los elementos del carrito y obtener los eventos de la base de datos
        """
        events_ids = self.cart.keys()
        # Obtener los eventos y añadirlos al carrito
        events_db = Events.objects.filter(id__in=events_ids)
        
        # Crear una copia temporal para la iteración
        temp_cart = {}
        for events_id, item in self.cart.items():
            temp_cart[events_id] = item.copy()
        
        # Añadir los objetos Events a la copia temporal
        for events in events_db:
            events_id = str(events.id)
            if events_id in temp_cart:
                temp_cart[events_id]['events'] = events
    
        # Iterar sobre la copia temporal
        for item in temp_cart.values():
            if 'price' in item:
                item['price'] = Decimal(item['price'])
            item['total_price'] = item['price'] * item['quantity']
            yield item

    def total(self):
        return sum(float(item["price"]) * item["quantity"] for item in self.cart.values())
