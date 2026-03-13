from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db import transaction
from .models import Profile, Role, TypeDocument, Events, Artist, Venue


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    name = forms.CharField(required=False)
    lastname = forms.CharField(required=False)
    document = forms.CharField(required=False)
    typedocument = forms.ModelChoiceField(queryset=TypeDocument.objects.all(), required=False)
    cellphone = forms.CharField(required=False)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2", "name", "lastname", "document", "typedocument", "cellphone")

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data.get("email", "")
        if commit:
            user.save()
            role = Role.objects.filter(name__iexact="comprador").first()
            if not role:
                role = Role.objects.create(name="COMPRADOR")
            Profile.objects.create(
                user=user,
                name=self.cleaned_data.get("name", ""),
                lastname=self.cleaned_data.get("lastname", ""),
                role=role,
                document=self.cleaned_data.get("document", ""),
                typedocument=self.cleaned_data.get("typedocument"),
                cellphone=self.cleaned_data.get("cellphone", ""),
                email=user.email,
            )
        return user

class EditForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["name", "lastname", "document", "typedocument", "cellphone", "email"]
        
class EventsForm(forms.ModelForm):
    venue = forms.ModelChoiceField(
        queryset=Venue.objects.all().order_by("name"),
        required=True,
        label="Recinto",
    )

    class Meta:
        model = Events
        fields = ["name", "description", "start_date", "end_date", "venue", "artist", "place", "label"]

        widgets = {
            # si quieres fecha+hora:
            "start_date": forms.DateTimeInput(format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local"}),
            "end_date": forms.DateTimeInput(format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local"}),
            # si sólo fecha (sin hora) usa:
            # "start_date": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            # "end_date": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # input_formats para que Django acepte el valor enviado por el widget
        self.fields["start_date"].input_formats = ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S")
        self.fields["end_date"].input_formats = ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S")

        if self.instance and self.instance.pk and self.instance.venue_id:
            self.fields["venue"].initial = self.instance.venue

class ArtistForm(forms.ModelForm):
    events = forms.ModelChoiceField(queryset=Events.objects.all(), required=False, widget=forms.CheckboxSelectMultiple)
    
    class Meta:
        model = Artist
        fields = ["name", "birth_city", "musical_gender"]


class VenueForm(forms.ModelForm):
    class Meta:
        model = Venue
        fields = ["name", "address"]