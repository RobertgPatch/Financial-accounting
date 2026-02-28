"""Add AssetTag model, expand Asset.asset_type choices, add tags M2M, data migration."""
from django.db import migrations, models
import django.db.models.deletion


def migrate_asset_types(apps, schema_editor):
    """Map old asset_type values to new expanded values."""
    Asset = apps.get_model('api', 'Asset')
    mapping = {
        'property': 'real_estate',
        'stock': 'public_equity',
        'fund': 'hedge_fund',
        'bond': 'fixed_income',
    }
    for old_value, new_value in mapping.items():
        Asset.objects.filter(asset_type=old_value).update(asset_type=new_value)


def reverse_asset_types(apps, schema_editor):
    """Reverse the asset_type migration."""
    Asset = apps.get_model('api', 'Asset')
    mapping = {
        'real_estate': 'property',
        'public_equity': 'stock',
        'hedge_fund': 'fund',
        'fixed_income': 'bond',
    }
    for old_value, new_value in mapping.items():
        Asset.objects.filter(asset_type=old_value).update(asset_type=new_value)


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0002_budget_budgetlineitem'),
    ]

    operations = [
        # 1. Create AssetTag model
        migrations.CreateModel(
            name='AssetTag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('slug', models.SlugField(max_length=100, unique=True, blank=True)),
                ('color', models.CharField(default='#6B7280', max_length=7)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        # 2. Expand asset_type choices (alter field before data migration)
        migrations.AlterField(
            model_name='asset',
            name='asset_type',
            field=models.CharField(
                choices=[
                    ('real_estate', 'Real Estate'),
                    ('public_equity', 'Public Equity'),
                    ('private_equity', 'Private Equity'),
                    ('fixed_income', 'Fixed Income'),
                    ('cash', 'Cash & Equivalents'),
                    ('hedge_fund', 'Hedge Fund'),
                    ('crypto', 'Cryptocurrency'),
                    ('collectible', 'Collectible'),
                    ('other', 'Other'),
                ],
                max_length=50,
            ),
        ),
        # 3. Data migration — map old values to new
        migrations.RunPython(migrate_asset_types, reverse_asset_types),
        # 4. Add tags M2M field
        migrations.AddField(
            model_name='asset',
            name='tags',
            field=models.ManyToManyField(blank=True, related_name='assets', to='api.assettag'),
        ),
    ]
