from django.contrib import admin

from .models import Invitation, Store, User

admin.site.register(User)
admin.site.register(Invitation)
admin.site.register(Store)
from .models import Invitation, User

admin.site.register(User)
admin.site.register(Invitation)
