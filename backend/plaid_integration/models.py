from django.db import models


class PlaidItem(models.Model):
    """Represents a linked financial institution via Plaid."""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('error', 'Error'),
        ('needs_relink', 'Needs Re-link'),
    ]

    item_id = models.CharField(max_length=255, unique=True)
    access_token = models.CharField(max_length=255)
    institution_id = models.CharField(max_length=100, blank=True, null=True)
    institution_name = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    last_synced = models.DateTimeField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.institution_name or self.item_id} ({self.status})"


class PlaidAccount(models.Model):
    """An individual account within a Plaid-linked institution."""
    plaid_item = models.ForeignKey(
        PlaidItem, on_delete=models.CASCADE, related_name='accounts'
    )
    account_id = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    mask = models.CharField(max_length=10, blank=True, null=True)
    type = models.CharField(max_length=50)
    subtype = models.CharField(max_length=50, blank=True, null=True)
    asset = models.ForeignKey(
        'api.Asset', on_delete=models.SET_NULL,
        blank=True, null=True, related_name='plaid_accounts'
    )
    current_balance = models.DecimalField(
        max_digits=15, decimal_places=2, blank=True, null=True
    )
    last_synced = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['plaid_item', 'name']

    def __str__(self):
        return f"{self.name} ({self.mask or 'no mask'})"
