from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin
from django.contrib.auth.models import User
from .models import Profile, Role, TypeDocument, Events, Venue, Section, Seat

class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = "Profile"
    fk_name = "user"
    extra = 0

class CustomUserAdmin(DefaultUserAdmin):
    inlines = (ProfileInline,)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Ensure profile exists
        profile, created = Profile.objects.get_or_create(user=obj)
        # If profile role is admin, mark user as staff
        if profile.role and profile.role.name.lower() == "admin":
            if not obj.is_staff:
                obj.is_staff = True
                obj.save()

# Replace default User admin with custom that includes Profile inline
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# Register role and type document for management
admin.site.register(Role)
admin.site.register(TypeDocument)
# Optional: allow direct Profile management too
admin.site.register(Profile)

admin.site.register(Events)

class SectionInline(admin.TabularInline):
    model = Section
    extra = 1

@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ('name', 'address')
    inlines = [SectionInline]

class SeatInline(admin.TabularInline):
    model = Seat
    extra = 0

@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'venue', 'price')
    list_filter = ('venue',)
    inlines = [SeatInline]

@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ('section', 'row', 'number', 'status')
    list_filter = ('section__venue', 'section', 'status')
    search_fields = ('row', 'number')
