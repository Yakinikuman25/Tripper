from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import *


admin.site.register(User, UserAdmin)
admin.site.register(Profile)

admin.site.register(Trip)
admin.site.register(Category)
admin.site.register(TripHashtag)
admin.site.register(Hashtag)
admin.site.register(Location)
admin.site.register(Day)
admin.site.register(Spot)

admin.site.register(TripExpense)
admin.site.register(DayExpense)