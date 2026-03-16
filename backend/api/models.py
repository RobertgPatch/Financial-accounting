from decimal import Decimal

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
        ('venture_capital', 'Venture Capital'),
        ('private_equity', 'Private Equity'),
        ('hedge_fund', 'Hedge Fund'),
        ('credit', 'Credit'),
        ('co_investment', 'Co-Investment'),
        ('infrastructure', 'Infrastructure'),
        ('natural_resources', 'Natural Resources'),
        ('public_equity', 'Public Equity'),
        ('fixed_income', 'Fixed Income'),
        ('cash', 'Cash & Equivalents'),
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
    source_k1_document = models.ForeignKey('K1Document', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_distributions')
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


# ---------------------------------------------------------------------------
# K-1 PDF Ingestion Models
# ---------------------------------------------------------------------------

def k1_upload_path(instance, filename):
    """Upload K-1 PDFs to k1_documents/{tax_year}/{filename}."""
    return f"k1_documents/{instance.tax_year}/{filename}"


class K1Document(models.Model):
    """Root model for an ingested Schedule K-1 (Form 1065) PDF."""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
    ]
    EXTRACTION_METHOD_CHOICES = [
        ('text', 'Text'),
        ('ocr', 'OCR'),
    ]

    entity = models.ForeignKey(Entity, on_delete=models.SET_NULL, null=True, blank=True, related_name='k1_documents')
    asset = models.ForeignKey(Asset, on_delete=models.SET_NULL, null=True, blank=True, related_name='k1_documents')
    tax_year = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    asset_type_classification = models.CharField(max_length=50, choices=Asset.ASSET_TYPE_CHOICES, null=True, blank=True)
    is_final = models.BooleanField(default=False)
    is_amended = models.BooleanField(default=False)
    document = models.FileField(upload_to=k1_upload_path, validators=[])
    original_filename = models.CharField(max_length=255)
    extraction_method = models.CharField(max_length=10, choices=EXTRACTION_METHOD_CHOICES, default='text')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"K-1 {self.tax_year} - {self.original_filename} ({self.status})"

    def save(self, *args, **kwargs):
        # Attach PDF validator at runtime to avoid circular import
        from .validators import validate_pdf_file
        if validate_pdf_file not in self.document.field.validators:
            self.document.field.validators.append(validate_pdf_file)
        super().save(*args, **kwargs)


class K1PartnershipInfo(models.Model):
    """Part I: Information About the Partnership."""
    document = models.OneToOneField(K1Document, on_delete=models.CASCADE, related_name='partnership_info')
    ein = models.CharField(max_length=20, blank=True, default='')
    name = models.CharField(max_length=255, blank=True, default='')
    address = models.TextField(blank=True, default='')
    city = models.CharField(max_length=100, blank=True, default='')
    state = models.CharField(max_length=50, blank=True, default='')
    zip_code = models.CharField(max_length=20, blank=True, default='')
    irs_center = models.CharField(max_length=100, blank=True, default='')
    is_ptp = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'K-1 Partnership Info'
        verbose_name_plural = 'K-1 Partnership Info'

    def __str__(self):
        return f"Partnership: {self.name} (EIN: {self.ein})"


class K1PartnerInfo(models.Model):
    """Part II: Information About the Partner."""
    document = models.OneToOneField(K1Document, on_delete=models.CASCADE, related_name='partner_info')
    tin = models.CharField(max_length=20, blank=True, default='')
    name = models.CharField(max_length=255, blank=True, default='')
    address = models.TextField(blank=True, default='')
    city = models.CharField(max_length=100, blank=True, default='')
    state = models.CharField(max_length=50, blank=True, default='')
    zip_code = models.CharField(max_length=20, blank=True, default='')
    is_general_partner = models.BooleanField(default=False)
    is_domestic = models.BooleanField(default=True)
    entity_type = models.CharField(max_length=100, blank=True, default='')
    is_retirement_plan = models.BooleanField(default=False)
    # J: Profit/Loss/Capital percentages
    profit_beginning_pct = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    profit_ending_pct = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    loss_beginning_pct = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    loss_ending_pct = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    capital_beginning_pct = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    capital_ending_pct = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    # K: Partner's share of liabilities
    nonrecourse_beginning = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    nonrecourse_ending = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    qualified_nonrecourse_beginning = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    qualified_nonrecourse_ending = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    recourse_beginning = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    recourse_ending = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    has_lower_tier_liabilities = models.BooleanField(default=False)
    has_guarantee_obligations = models.BooleanField(default=False)
    # N: Section 704(c)
    section_704c_beginning = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    section_704c_ending = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    built_in_gain = models.BooleanField(null=True, blank=True)

    class Meta:
        verbose_name = 'K-1 Partner Info'
        verbose_name_plural = 'K-1 Partner Info'

    def __str__(self):
        return f"Partner: {self.name} (TIN: {self.tin})"


class K1IncomeItem(models.Model):
    """Part III: Partner's Share of Current Year Income — one row per line/code."""
    document = models.ForeignKey(K1Document, on_delete=models.CASCADE, related_name='income_items')
    line_number = models.CharField(max_length=10)
    code = models.CharField(max_length=10, blank=True, null=True)
    description = models.CharField(max_length=255, blank=True, default='')
    amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    raw_text = models.CharField(max_length=500, blank=True, default='')
    is_supplemental = models.BooleanField(default=False)

    class Meta:
        ordering = ['line_number', 'code']

    def __str__(self):
        code_str = f" {self.code}" if self.code else ""
        return f"Line {self.line_number}{code_str}: {self.amount or self.raw_text}"


class K1CapitalAccount(models.Model):
    """Section L: Partner's Capital Account Analysis."""
    document = models.OneToOneField(K1Document, on_delete=models.CASCADE, related_name='capital_account')
    beginning_balance = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    capital_contributed = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    net_income = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    other_increase_decrease = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    withdrawals = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    ending_balance = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    tax_basis_method = models.CharField(max_length=50, blank=True, default='')

    class Meta:
        verbose_name = 'K-1 Capital Account'
        verbose_name_plural = 'K-1 Capital Accounts'

    def __str__(self):
        return f"Capital Account: {self.beginning_balance} → {self.ending_balance}"


# ---------------------------------------------------------------------------
# Activity Ledger
# ---------------------------------------------------------------------------

class Activity(models.Model):
    """Yearly tax-basis activity record per Entity + Partnership (Asset).

    This is the central ledger that feeds all report views.  Rows are
    auto-created from confirmed K-1 documents or entered manually.
    """

    year = models.IntegerField()
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='activities')
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='activities')

    # Tax basis start
    beginning_basis = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    # Capital in
    contributions = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    # Income line items (K-1 references)
    interest = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                   help_text='K-1 Line 5')
    dividends = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                    help_text='K-1 Line 6')
    capital_gains = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                        help_text='K-1 Lines 8/9/10')
    remaining_k1_income = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                              help_text='Remaining K-1 income/deductions')
    total_income = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                       help_text='Sum of income components')

    # Outflows
    distributions = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    other_adjustments = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                            help_text='K-1 Line 18-c')

    # Ending values
    ending_tax_basis = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    ending_gl_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                            help_text='Ending GL Balance Per Books')
    book_to_tax_adj = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                          help_text='GL Ending - Tax Basis')
    ending_k1_capital = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                            help_text='Ending K-1 Capital Account')
    k1_capital_vs_tax_diff = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                                  help_text='K-1 Capital vs Tax Basis Difference')

    # Flags & derived
    excess_distribution = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    negative_basis = models.BooleanField(default=False)
    basis_change = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                       help_text='Δ Ending Basis vs Prior Year')

    notes = models.TextField(blank=True, default='')

    # Source tracking
    source_k1_document = models.ForeignKey(
        K1Document, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='activity_records',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'activities'
        unique_together = [('year', 'entity', 'asset')]
        ordering = ['entity', 'asset', 'year']

    def __str__(self):
        return f"{self.entity.name} | {self.asset.name} | {self.year}"

    # ------------------------------------------------------------------
    # Auto-computed fields
    # ------------------------------------------------------------------

    def compute_derived(self):
        """Recompute all auto-calculated fields from flow inputs."""
        Z = Decimal('0')
        self.total_income = (
            (self.interest or Z) + (self.dividends or Z)
            + (self.capital_gains or Z) + (self.remaining_k1_income or Z)
        )
        bb = self.beginning_basis or Z
        self.ending_tax_basis = (
            bb + (self.contributions or Z) + self.total_income
            - (self.distributions or Z) + (self.other_adjustments or Z)
        )
        self.book_to_tax_adj = (self.ending_gl_balance or Z) - self.ending_tax_basis
        self.k1_capital_vs_tax_diff = (self.ending_k1_capital or Z) - self.ending_tax_basis
        self.negative_basis = self.ending_tax_basis < Z
        self.excess_distribution = max(Z, -self.ending_tax_basis) if self.negative_basis else Z
        self.basis_change = self.ending_tax_basis - bb

    def save(self, *args, **kwargs):
        Z = Decimal('0')
        # Auto-populate beginning_basis from prior year's ending_tax_basis
        prior_ending = (
            Activity.objects.filter(
                year=self.year - 1,
                entity_id=self.entity_id,
                asset_id=self.asset_id,
            )
            .values_list('ending_tax_basis', flat=True)
            .first()
        )
        self.beginning_basis = prior_ending if prior_ending is not None else Z

        self.compute_derived()

        # Ensure computed fields are persisted when update_fields is set
        # (e.g. from update_or_create)
        update_fields = kwargs.get('update_fields')
        if update_fields is not None:
            kwargs['update_fields'] = frozenset(update_fields) | frozenset({
                'beginning_basis', 'total_income', 'ending_tax_basis',
                'book_to_tax_adj', 'k1_capital_vs_tax_diff',
                'excess_distribution', 'negative_basis', 'basis_change',
            })

        super().save(*args, **kwargs)

        # Cascade: propagate ending_tax_basis to the next year's beginning_basis
        try:
            nxt = Activity.objects.get(
                year=self.year + 1,
                entity_id=self.entity_id,
                asset_id=self.asset_id,
            )
            if nxt.beginning_basis != self.ending_tax_basis:
                nxt.save()  # recursive — bounded by the year range
        except Activity.DoesNotExist:
            pass
