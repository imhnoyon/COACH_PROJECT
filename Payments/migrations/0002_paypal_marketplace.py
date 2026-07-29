# Generated for PayPal Marketplace Payment Integration

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Payments', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='servicebooking',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('confirmed', 'Confirmed'), ('completed', 'Completed'), ('cancelled', 'Cancelled'), ('refunded', 'Refunded')], default='pending', max_length=20),
        ),
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('total_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('platform_commission', models.DecimalField(decimal_places=2, max_digits=10)),
                ('provider_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('paypal_order_id', models.CharField(db_index=True, max_length=255, unique=True)),
                ('paypal_capture_id', models.CharField(blank=True, db_index=True, max_length=255, null=True, unique=True)),
                ('payment_status', models.CharField(choices=[('created', 'Created'), ('captured', 'Captured'), ('completed', 'Completed'), ('refunded', 'Refunded'), ('failed', 'Failed')], default='created', max_length=20)),
                ('payment_method', models.CharField(default='paypal', max_length=50)),
                ('captured_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='customer_payments', to=settings.AUTH_USER_MODEL)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payments', to='Payments.servicebooking')),
                ('provider', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='provider_payments', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PaymentLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_type', models.CharField(max_length=100)),
                ('payload', models.JSONField(default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('payment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='logs', to='Payments.payment')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ProviderWallet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('available_balance', models.DecimalField(decimal_places=2, default=0.0, max_digits=12)),
                ('pending_balance', models.DecimalField(decimal_places=2, default=0.0, max_digits=12)),
                ('total_earned', models.DecimalField(decimal_places=2, default=0.0, max_digits=12)),
                ('total_withdrawn', models.DecimalField(decimal_places=2, default=0.0, max_digits=12)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('provider', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='wallet', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Refund',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('refund_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('paypal_refund_id', models.CharField(max_length=255)),
                ('refunded_at', models.DateTimeField(auto_now_add=True)),
                ('reason', models.TextField(blank=True, null=True)),
                ('payment', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='refund', to='Payments.payment')),
                ('refunded_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='WithdrawalRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('paypal_email', models.EmailField(max_length=254)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('paid', 'Paid')], default='pending', max_length=20)),
                ('paypal_payout_batch_id', models.CharField(blank=True, max_length=255, null=True)),
                ('paypal_payout_item_id', models.CharField(blank=True, max_length=255, null=True)),
                ('approved_at', models.DateTimeField(blank=True, null=True)),
                ('paid_at', models.DateTimeField(blank=True, null=True)),
                ('rejection_reason', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('approved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approved_withdrawals', to=settings.AUTH_USER_MODEL)),
                ('provider', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='withdrawals', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
