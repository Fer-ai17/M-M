from django import forms
from .models import Events, Artist

class EventsForm(forms.ModelForm):
    class Meta:
        model = Events
        fields = [
            "name",
            "start",   
            "end",    
            "price",
            "stock",
            "location",  
            "artists",   
        ]
        widgets = {
            "start": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "end": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "price": forms.NumberInput(attrs={"type": "number", "step": "0.01"}),
            "stock": forms.NumberInput(attrs={"min": 0}),
            "artists": forms.SelectMultiple(attrs={"class": "form-select"}),
            "location": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        # asegurar formato correcto para datetime-local cuando hay instancias
        super().__init__(*args, **kwargs)
        for f in ("start", "end"):
            if self.instance and getattr(self.instance, f):
                self.fields[f].initial = getattr(self.instance, f).strftime("%Y-%m-%dT%H:%M")

class ArtistForm(forms.ModelForm):
    events = forms.ModelChoiceField(queryset=Events.objects.all(), required=False, widget=forms.CheckboxSelectMultiple)
    
    class Meta:
        model = Artist
        fields = ["name", "birth_city", "musical_gender"]