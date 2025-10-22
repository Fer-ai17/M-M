from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User


class Role(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

class TypeDocument(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

class Profile(models.Model):
    user = models.OneToOneField("auth.User", on_delete=models.CASCADE, related_name="profile", null=True, blank=True)
    name = models.CharField(max_length=100, blank=True)
    lastname = models.CharField(max_length=100, blank=True)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, null=True, blank=True)
    document = models.CharField(max_length=10, blank=True)
    typedocument = models.ForeignKey("TypeDocument", on_delete=models.CASCADE, null=True, blank=True)
    email = models.EmailField(blank=True)
    cellphone = models.CharField(max_length=15, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.name or self.lastname:
            return f"{self.name} {self.lastname}".strip()
        return f"Profile #{self.pk}"


class Location(models.Model):
    name = models.CharField(max_length=200)
    loc_code = models.CharField(max_length=50, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Events(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    start_date = models.DateTimeField(blank=True, null=True)
    end_date = models.DateTimeField(blank=True, null=True)
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    artist = models.ForeignKey("Artist", on_delete=models.CASCADE)
    place = models.ForeignKey("Municipality", on_delete=models.CASCADE, blank=True, null=True)
    label = models.CharField(
        max_length=20,
        choices=[
            ("proximamente", "Próximamente"),
            ("preventa", "Preventa"),
            ("ninguno", "Ninguno"),
        ],
        default="ninguno",
    )
    venue = models.ForeignKey("Venue", on_delete=models.SET_NULL, null=True, blank=True, related_name='events')
    has_seat_map = models.BooleanField(default=False, help_text="¿Este evento usa mapa de asientos?")

    def __str__(self):
        return self.name

    def total_price(self):
        try:
            return Decimal(self.location.price)
        except Exception:
            return Decimal("0.00")


class Tickets(models.Model):
    quantity = models.PositiveIntegerField()
    events = models.ForeignKey(Events, on_delete=models.CASCADE)
    purchase_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.events.name} - {self.quantity}"


class Bought(models.Model):
    STATUS_CHOICES = [
        ("pendiente", "Pendiente"),
        ("enviado", "Enviado"),
        ("completado", "Completado"),
    ]

    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Completado")
    tickets = models.ForeignKey(Tickets, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        name = f"{self.profile.name} {self.profile.lastname}".strip() if self.profile else "Anónimo"
        return f"Pedido #{self.pk} - {name}"

    def total(self):
        try:
            unit_price = self.tickets.events.location.price
            return Decimal(self.tickets.quantity) * Decimal(unit_price)
        except Exception:
            return Decimal("0.00")


class MusicalGender(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Artist(models.Model):
    name = models.CharField(max_length=100)
    birth_city = models.CharField(max_length=100)
    musical_gender = models.ForeignKey(MusicalGender, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Department(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Municipality(models.Model):
    name = models.CharField(max_length=100)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


# Mapa Interactivo
class Venue(models.Model):
    """Representa un recinto/lugar donde se realizan eventos"""
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=200, blank=True)
    
    def __str__(self):
        return self.name

class Section(models.Model):
    """Representa una sección del venue (Ej: Platea, VIP, General)"""
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name='sections')
    name = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    color = models.CharField(max_length=7, help_text="Color en formato HEX (#RRGGBB)", default="#CCCCCC")
    
    def __str__(self):
        return f"{self.venue.name} - {self.name}"

class Seat(models.Model):
    """Representa un asiento individual"""
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='seats')
    row = models.CharField(max_length=10)  # Ej: A, B, C o 1, 2, 3
    number = models.CharField(max_length=10)  # Ej: 1, 2, 3...
    x_position = models.IntegerField(help_text="Posición X en el mapa")
    y_position = models.IntegerField(help_text="Posición Y en el mapa")
    status = models.CharField(max_length=20, choices=[
        ('available', 'Disponible'),
        ('reserved', 'Reservado'),
        ('sold', 'Vendido'),
        ('blocked', 'Bloqueado'),
    ], default='available')
    
    def __str__(self):
        return f"{self.section.name} Fila {self.row} Asiento {self.number}"