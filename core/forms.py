from django import forms
from .models import Events, Artist

class EventsForm(forms.ModelForm):
    class Meta:
        model = Events
<<<<<<< HEAD
        fields = ["name", "description", "start_date", "end_date", "location", "artist"]
        fields = ["name", "description", "start_date", "end_date", "location", "artist", "label"]
=======
        fields = ["name", "description", "start_date", "end_date", "location", "artist", "place", "label"]

>>>>>>> 3db138f7f4e8dc02d1a8ce67eff56da0e85d5050
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

class ArtistForm(forms.ModelForm):
    events = forms.ModelChoiceField(queryset=Events.objects.all(), required=False, widget=forms.CheckboxSelectMultiple)
    
    class Meta:
        model = Artist
        fields = ["name", "birth_city", "musical_gender"]