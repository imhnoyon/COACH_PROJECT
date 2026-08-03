from django.db import models
from Provider.models import Category
from Authentication.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

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
    
    
    
class CoachRating(models.Model):
    coach = models.ForeignKey(User, on_delete=models.CASCADE, related_name='coach_ratings')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_ratings')
    rating = models.PositiveSmallIntegerField(default=0, validators=[MinValueValidator(1), MaxValueValidator(5)])
    review = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('coach', 'user')  
        
    def average_rating(self):
        ratings = CoachRating.objects.filter(coach=self.coach)
        if ratings.exists():
            return sum(r.rating for r in ratings) / ratings.count()
        return 0

    def __str__(self):
        return f"Rating by {self.user.full_name} for {self.coach.full_name}: {self.rating}"
    
    
    
class AppRating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='app_ratings')
    rating = models.PositiveSmallIntegerField(default=0,validators=[MinValueValidator(1), MaxValueValidator(5)])
    review = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    
    def average_rating(self):
        ratings = AppRating.objects.all()
        if ratings.exists():
            return sum(r.rating for r in ratings) / ratings.count()
        return 0

    def __str__(self):
        return f"App Rating by {self.user.full_name}: {self.rating}"