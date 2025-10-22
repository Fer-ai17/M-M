from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone

from blogsite import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Administrador'),
        ('user', 'Usuario'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')

    def is_admin(self):
        return self.role == 'admin'



#Usuarios - Administrador
class Profile(models.Model):
    name = models.CharField(max_length=100)
    role = models.ForeignKey("Role", on_delete=models.CASCADE)
    document = models.CharField(max_length=10, blank= True),
    type_document = models.CharField(max_length=30, blank=True)
    email = models.TextField(blank=True)
    password = models.ImageField(upload_to="avatars/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Profile de {self.user.username}"

#Roles - Admin, Cliente 
class Role(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


#Localidad - VIP, General, Preferencial
class Location(models.Model):
    name = models.CharField(max_length=200)
    loc_code = models.CharField(max_length=50, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    label = models.CharField(max_length=20, choices=[
        ("nuevo", "Nuevo"),
        ("preventa", "Preventa"),
        ("ninguno", "Ninguno"),
    ], default="ninguno")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
class Events(models.Model):
    name = models.CharField(max_length=200)
    start = models.DateTimeField(null=True, blank=True)
    end = models.DateTimeField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock = models.PositiveIntegerField(default=0)
    label = models.CharField(max_length=20, choices=[
        ("proximamente", "Próximamente"),
        ("preventa", "Preventa"),
        ("ninguno", "Ninguno"),
    ], default="ninguno")
    artists = models.ManyToManyField("Artist", through="EventArtist", related_name="events")
    location = models.ForeignKey("Location", on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.name} - {self.start} to {self.end}"

#Compras
class Bought(models.Model):
    profile = models.ForeignKey("Profile", on_delete=models.SET_NULL, null=True, blank=True)
    total_qty = models.PositiveIntegerField(default=0)
    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Compra #{self.pk} - {self.total_qty} boletas - {self.total_price}"

class Tickets(models.Model):
    bought = models.ForeignKey(Bought, on_delete=models.CASCADE, related_name="tickets", null=True, blank=True)
    events = models.ForeignKey(Events, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)  # unidad en moneda base
    purchase_date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.events.name} x{self.quantity}"

    def clean(self):
        if self.quantity < 1:
            raise ValidationError("La cantidad debe ser al menos 1.")
        if self.events and self.quantity > self.events.stock:
            raise ValidationError(f"Sólo hay {self.events.stock} boletas disponibles para '{self.events.name}'.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

#Genero Musical
class MusicalGender(models.Model):
    name = models.CharField(max_length=100)

#Artistas
class Artist(models.Model):
    name = models.CharField(max_length=200)
    birth_city = models.CharField(max_length=100)
    musical_gender = models.ForeignKey("MusicalGender", on_delete=models.CASCADE)

    def __str__(self):
        return self.name

#Departamento
class Department(models.Model):
    name = models.CharField(max_length=100)

#Municipio
class Municipality(models.Model):
    name = models.CharField(max_length=100)
    department = models.ForeignKey("Department", on_delete=models.CASCADE)

#Eventos con artistas
class EventArtist(models.Model):
    artist = models.ForeignKey("Artist", on_delete=models.CASCADE)
    event = models.ForeignKey("Events", on_delete=models.CASCADE)

    class Meta:
        unique_together = ('artist', 'event')

    def clean(self):
        # Validar que el artista no esté en otro evento con fechas superpuestas
        overlapping = Events.objects.filter(
            artists=self.artist
        ).exclude(pk=self.event.pk).filter(
            start__lt=self.event.end,
            end__gt=self.event.start
        )
        if overlapping.exists():
            first = overlapping.first()
            raise ValidationError(
                f"El artista '{self.artist}' ya participa en '{first.name}' "
                f"({first.start} — {first.end}), que se superpone con este evento."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

