from django.db import models
from django.utils.text import slugify
import re


class AssetTag(models.Model):
    """Reusable tag for classifying assets."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    color = models.CharField(max_length=7, default='#6B7280')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def clean(self):
        from django.core.exceptions import ValidationError
        # Case-insensitive unique name
        qs = AssetTag.objects.filter(name__iexact=self.name)
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        if qs.exists():
            raise ValidationError({'name': 'A tag with this name already exists.'})
        # Validate hex color
        if not re.match(r'^#[0-9A-Fa-f]{6}$', self.color):
            raise ValidationError({'color': 'Color must be a valid hex color (e.g., #6B7280).'})

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        self.full_clean()
        super().save(*args, **kwargs)


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
        ('real_estate', 'Real Estate'),
        ('public_equity', 'Public Equity'),
        ('private_equity', 'Private Equity'),
        ('fixed_income', 'Fixed Income'),
        ('cash', 'Cash & Equivalents'),
        ('hedge_fund', 'Hedge Fund'),
        ('crypto', 'Cryptocurrency'),
        ('collectible', 'Collectible'),
        ('other', 'Other'),
    ]

    name = models.CharField(max_length=255)
    asset_type = models.CharField(max_length=50, choices=ASSET_TYPE_CHOICES)
    description = models.TextField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    ticker_symbol = models.CharField(max_length=20, blank=True, null=True)
    tags = models.ManyToManyField(AssetTag, blank=True, related_name='assets')
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


class Budget(models.Model):
    PERIOD_TYPE_CHOICES = [
        ('yearly', 'Yearly'),
        ('quarterly', 'Quarterly'),
        ('monthly', 'Monthly'),
    ]

    name = models.CharField(max_length=255)
    year = models.IntegerField()
    period_type = models.CharField(max_length=20, choices=PERIOD_TYPE_CHOICES, default='yearly')
    quarter = models.IntegerField(blank=True, null=True)
    month = models.IntegerField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-year', 'name']

    def __str__(self):
        return f"{self.name} ({self.year})"


class BudgetLineItem(models.Model):
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name='line_items')
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='budget_line_items')
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='budget_line_items', blank=True, null=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['budget', 'asset', 'entity']

    def __str__(self):
        entity_str = f" → {self.entity.name}" if self.entity else ""
        return f"{self.budget.name}: {self.asset.name}{entity_str} = ${self.amount}"


class FMVSnapshot(models.Model):
    """Point-in-time fair market value record for an asset."""
    SOURCE_CHOICES = [
        ('manual', 'Manual'),
        ('plaid', 'Plaid'),
    ]

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='fmv_snapshots')
    snapshot_date = models.DateField()
    value = models.DecimalField(max_digits=15, decimal_places=2)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='manual')
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('asset', 'snapshot_date')]
        ordering = ['-snapshot_date']

    def __str__(self):
        return f"{self.asset.name} FMV ${self.value} on {self.snapshot_date}"

    def clean(self):
        from django.core.exceptions import ValidationError
        from datetime import date as date_cls
        if self.value is not None and self.value < 0:
            raise ValidationError({'value': 'FMV value must be >= 0.'})
        if self.snapshot_date and self.snapshot_date > date_cls.today():
            raise ValidationError({'snapshot_date': 'Snapshot date cannot be in the future.'})


class Commitment(models.Model):
    """One commitment per entity-asset pair tracking PE/VC fund commitments."""
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='commitments')
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='commitments')
    commitment_date = models.DateField()
    original_amount = models.DecimalField(max_digits=15, decimal_places=2)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('entity', 'asset')]
        ordering = ['entity', 'asset']

    def __str__(self):
        return f"{self.entity.name} → {self.asset.name} (${self.original_amount})"


class CapitalCall(models.Model):
    """Capital call (draw-down) against a Commitment."""
    commitment = models.ForeignKey(Commitment, on_delete=models.CASCADE, related_name='capital_calls')
    call_date = models.DateField()
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['call_date']

    def __str__(self):
        return f"Call ${self.amount} on {self.call_date} for {self.commitment}"
