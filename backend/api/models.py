from django.db import models


class Entity(models.Model):
    ENTITY_TYPE_CHOICES = [
        ('individual', 'Individual'),
        ('company', 'Company'),
        ('LLC', 'LLC'),
        ('trust', 'Trust'),
        ('partnership', 'Partnership'),
        ('other', 'Other'),
    ]

    name = models.CharField(max_length=255)
    entity_type = models.CharField(max_length=50, choices=ENTITY_TYPE_CHOICES)
    description = models.TextField(blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'entities'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.entity_type})"


class Asset(models.Model):
    ASSET_TYPE_CHOICES = [
        ('property', 'Property'),
        ('stock', 'Stock'),
        ('fund', 'Fund'),
        ('bond', 'Bond'),
        ('other', 'Other'),
    ]

    name = models.CharField(max_length=255)
    asset_type = models.CharField(max_length=50, choices=ASSET_TYPE_CHOICES)
    description = models.TextField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    ticker_symbol = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.asset_type})"


class EntityAssetOwnership(models.Model):
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='ownerships')
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='ownerships')
    percentage = models.DecimalField(max_digits=7, decimal_places=4)
    effective_date = models.DateField()
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['asset', 'entity']

    def __str__(self):
        return f"{self.entity.name} owns {self.percentage}% of {self.asset.name}"


class Distribution(models.Model):
    DISTRIBUTION_TYPE_CHOICES = [
        ('regular', 'Regular'),
        ('special', 'Special'),
        ('return_of_capital', 'Return of Capital'),
        ('liquidating', 'Liquidating'),
    ]

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='distributions')
    distribution_date = models.DateField()
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    distribution_type = models.CharField(max_length=50, choices=DISTRIBUTION_TYPE_CHOICES, default='regular')
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-distribution_date']

    def __str__(self):
        return f"{self.asset.name} distribution on {self.distribution_date} (${self.total_amount})"


class DistributionAllocation(models.Model):
    distribution = models.ForeignKey(Distribution, on_delete=models.CASCADE, related_name='allocations')
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='distribution_allocations')
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    percentage = models.DecimalField(max_digits=7, decimal_places=4)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['distribution', 'entity']

    def __str__(self):
        return f"{self.entity.name} receives ${self.amount} from {self.distribution}"
