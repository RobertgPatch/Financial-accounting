from django.contrib import admin
from .models import Entity, Asset, EntityAssetOwnership, Distribution, DistributionAllocation

admin.site.register(Entity)
admin.site.register(Asset)
admin.site.register(EntityAssetOwnership)
admin.site.register(Distribution)
admin.site.register(DistributionAllocation)
