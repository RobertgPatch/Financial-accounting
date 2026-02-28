"""Add FMVSnapshot model with unique_together constraint."""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0003_assettag_expand_asset_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='FMVSnapshot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('snapshot_date', models.DateField()),
                ('value', models.DecimalField(decimal_places=2, max_digits=15)),
                ('source', models.CharField(choices=[('manual', 'Manual'), ('plaid', 'Plaid')], default='manual', max_length=20)),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('asset', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fmv_snapshots', to='api.asset')),
            ],
            options={
                'ordering': ['-snapshot_date'],
                'unique_together': {('asset', 'snapshot_date')},
            },
        ),
    ]
