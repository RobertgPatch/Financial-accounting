"""PlaidItem and PlaidAccount models."""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('api', '0004_fmvsnapshot'),
    ]

    operations = [
        migrations.CreateModel(
            name='PlaidItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('item_id', models.CharField(max_length=255, unique=True)),
                ('access_token', models.CharField(max_length=255)),
                ('institution_id', models.CharField(blank=True, max_length=100, null=True)),
                ('institution_name', models.CharField(blank=True, max_length=255, null=True)),
                ('status', models.CharField(choices=[('active', 'Active'), ('error', 'Error'), ('needs_relink', 'Needs Re-link')], default='active', max_length=20)),
                ('last_synced', models.DateTimeField(blank=True, null=True)),
                ('error_message', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PlaidAccount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('account_id', models.CharField(max_length=255, unique=True)),
                ('name', models.CharField(max_length=255)),
                ('mask', models.CharField(blank=True, max_length=10, null=True)),
                ('type', models.CharField(max_length=50)),
                ('subtype', models.CharField(blank=True, max_length=50, null=True)),
                ('current_balance', models.DecimalField(blank=True, decimal_places=2, max_digits=15, null=True)),
                ('last_synced', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('plaid_item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='accounts', to='plaid_integration.plaiditem')),
                ('asset', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='plaid_accounts', to='api.asset')),
            ],
            options={
                'ordering': ['plaid_item', 'name'],
            },
        ),
    ]
