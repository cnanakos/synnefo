from django.contrib import admin
from django import forms
from django.db import models
from django.utils.encoding import iri_to_uri
from django.utils.translation import gettext_lazy as _
from models import  *

class LimitForm(forms.ModelForm):
    class Meta:
        model = Limit

class LimitAdmin(admin.ModelAdmin):
    ""    

    form = LimitForm

class UserForm(forms.ModelForm):
    class Meta:
        model = OceanUser

class UserAdmin(admin.ModelAdmin):
    ""    
    form = UserForm


class UserLimitForm(forms.ModelForm):
    class Meta:
        model = UserLimit

class UserLimitAdmin(admin.ModelAdmin):
    ""    

    form = UserLimitForm

class FlavorForm(forms.ModelForm):
    class Meta:
        model = Flavor

class FlavorAdmin(admin.ModelAdmin):
    ""    

    form = FlavorForm


class VirtualMachineForm(forms.ModelForm):
    class Meta:
        model = VirtualMachine

class VirtualMachineAdmin(admin.ModelAdmin):
    ""    

    form = VirtualMachineForm


class ChargingLogForm(forms.ModelForm):
    class Meta:
        model = ChargingLog

class ChargingLogAdmin(admin.ModelAdmin):
    ""    

    form = ChargingLogForm

admin.site.register(Limit, LimitAdmin)
admin.site.register(OceanUser, UserAdmin)
admin.site.register(UserLimit, UserLimitAdmin)
admin.site.register(Flavor, FlavorAdmin)
admin.site.register(VirtualMachine, VirtualMachineAdmin)
admin.site.register(ChargingLog, ChargingLogAdmin)

