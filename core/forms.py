from django import forms
from .models import Events, Artist

class EventsForm(forms.ModelForm):
    class Meta:
        model = Events
        fields = ["name", "description", "start_date", "end_date", "location", "artist", "label"]
        widgets = {
            # si quieres fecha+hora:
            "start_date": forms.DateTimeInput(format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local"}),
            "end_date": forms.DateTimeInput(format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # input_formats para que Django acepte el valor enviado por el widget
        self.fields["start_date"].input_formats = ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S")
        self.fields["end_date"].input_formats = ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S")

class ArtistForm(forms.ModelForm):
    class Meta:
        model = Artist
        fields = ["name", "birth_city", "musical_gender"]