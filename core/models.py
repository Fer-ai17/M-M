from django.db import models
from django.core.exceptions import ValidationError

from blogsite import settings


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
<<<<<<< HEAD
    label = models.CharField(max_length=20, choices=[
        ("nuevo", "Nuevo"),
        ("preventa", "Preventa"),
        ("ninguno", "Ninguno"),
    ], default="ninguno")
=======
>>>>>>> 3db138f7f4e8dc02d1a8ce67eff56da0e85d5050
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
class Tickets(models.Model):
    quantity = models.PositiveIntegerField()
    events = models.ForeignKey("Events", on_delete=models.CASCADE)
    purchase_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.events.name} - {self.quantity}"

#Compras
class Bought(models.Model):
    STATUS_CHOICES = [
        ("pendiente", "Pendiente"),
        ("enviado", "Enviado"),
        ("completado", "Completado"),
    ]

    profile = models.ForeignKey("Profile", on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pendiente")
    tickets = models.ForeignKey("Tickets", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pedido #{self.id} - {self.customer_name}"

    def total(self):
        return sum(item.total_price() for item in self.items.all())
    

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

#Eventos
class Events(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    start_date = models.DateTimeField(blank=True, null=True)
    end_date = models.DateTimeField(blank=True, null=True)
    location = models.ForeignKey("Location", on_delete=models.CASCADE)
    artist = models.ForeignKey("Artist", on_delete=models.CASCADE)
<<<<<<< HEAD
=======
    place = models.ForeignKey("Municipality", on_delete=models.CASCADE, blank=True, null=True)
>>>>>>> 3db138f7f4e8dc02d1a8ce67eff56da0e85d5050
    label = models.CharField(max_length=20, choices=[
        ("proximamente", "Próximamente"),
        ("preventa", "Preventa"),
        ("ninguno", "Ninguno"),
    ], default="ninguno")

    def __str__(self):
        return f"{self.name} - {self.start_date} to {self.end_date}"

    

    def total_price(self):
        return self.quantity * self.product.price

#Eventos con artistas
class EventArtist(models.Model):
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE)
    event = models.ForeignKey("Events", on_delete=models.CASCADE)

    class Meta:
        unique_together = ('artist', 'event')

    def clean(self):
        # validar que no existan eventos con la misma fecha para el artista
        overlapping = Events.objects.filter(
            artist=self.artist
        ).exclude(pk=self.event.pk).filter(
            start_date__lt=self.event.end_date,
            end_date__gt=self.event.start_date
        )
        if overlapping.exists():
            first = overlapping.first()
            raise ValidationError(
                f"El artista '{self.artist}' ya participa en '{first.name}' "
                f"({first.start_date} — {first.end_date}) que se solapa con este evento."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
