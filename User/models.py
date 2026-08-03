from django.db import models
from Provider.models import Category
from Authentication.models import User

class Post(models.Model):
    URGENCY_LEVEL_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='posts')
    title = models.CharField(max_length=100)
    description = models.TextField()
    urgency_Level = models.CharField(max_length=20, choices=URGENCY_LEVEL_CHOICES)
    day_price = models.DecimalField(max_digits=10, decimal_places=2,blank=True, null=True)
    hours_price = models.DecimalField(max_digits=10, decimal_places=2,blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title