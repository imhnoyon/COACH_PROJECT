from django.db import models
from Administration.models import Category
from Authentication.models import User

class CoachProfile(models.Model):
    STATUS=(
        ("pending","Pending"),
        ("approved","Approved"),
        ("rejected","Rejected"),
    )
    user = models.OneToOneField(User,on_delete=models.CASCADE,related_name="coach_profile")
    categories = models.ManyToManyField(Category,related_name="coaches")
    profile_photo = models.ImageField(upload_to="coach/profile/")
    introduction_video = models.FileField(upload_to="coach/videos/",blank=True,null=True)
    about = models.TextField()
    expertises = models.JSONField(default=list, blank=True)
    is_completed = models.BooleanField(default=False)
    status = models.CharField(max_length=20,choices=STATUS,default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.full_name
    
    
class Certification(models.Model):
    coach = models.ForeignKey(CoachProfile,on_delete=models.CASCADE,related_name="certifications")
    name = models.CharField(max_length=255)
    document = models.FileField( upload_to="coach/certificates/")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
    
class Qualification(models.Model):
    coach = models.ForeignKey(CoachProfile,on_delete=models.CASCADE,related_name="qualifications")
    name = models.CharField(max_length=255)
    document = models.FileField( upload_to="coach/qualifications/")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
    
    
    
class Service(models.Model):
    SERVICE_TYPE = (
        ("one_time", "One Time Session"),
        ("package", "Session Package"),
        ("monthly", "Monthly Retainer"),
        ("discovery", "Free Discovery Call"),
    )

    SESSION_FORMAT = (
        ("video", "Video Call"),
        ("audio", "Audio Call"),
        ("chat", "Chat Session"),
    )

    BOOKING_TYPE = (
        ("instant", "Instant Booking"),
        ("approval", "Coach Approval Required"),
    )

    CANCELLATION_POLICY = (
        ("flexible", "Flexible"),
        ("standard", "Standard"),
        ("strict", "Strict"),
        ("default", "Platform Default"),
    )
    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("published", "Published"),
        
    )
    coach = models.ForeignKey(User,on_delete=models.CASCADE,related_name="services")
    title = models.CharField(max_length=255)
    category = models.ForeignKey(Category,on_delete=models.CASCADE,related_name="services")
    description = models.TextField()
    service_type = models.CharField(max_length=20,choices=SERVICE_TYPE)
    session_format = models.CharField(max_length=20,choices=SESSION_FORMAT)
    session_duration = models.PositiveIntegerField(help_text="Minutes")
    currency = models.CharField(max_length=10,default="USD")
    price = models.DecimalField(max_digits=10,decimal_places=2)
    booking_type = models.CharField(max_length=20,choices=BOOKING_TYPE,default="instant")
    who_is_this_service_for = models.TextField()
    preparation_instructions = models.TextField(blank=True,null=True)
    session_url = models.URLField(blank=True)
    cancellation_policy = models.CharField(max_length=20,choices=CANCELLATION_POLICY,default="standard")
    status = models.CharField(max_length=20,choices=STATUS_CHOICES,default="published")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
class ClientBenefit(models.Model):
    service = models.ForeignKey(Service,on_delete=models.CASCADE,related_name="benefits")
    outcome = models.CharField(max_length=255)

    def __str__(self):
        return self.outcome
    
    
    
    
class Blog(models.Model):
    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("published", "Published"),
        
    )
    coach = models.ForeignKey(User,on_delete=models.CASCADE,related_name="blogs")
    category = models.ForeignKey(Category,on_delete=models.CASCADE,related_name="blogs")
    title = models.CharField(max_length=255)
    content = models.TextField()
    image = models.ImageField(upload_to="coach/blogs/",blank=True,null=True)
    status = models.CharField(max_length=20,choices=STATUS_CHOICES,default="published")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
    
    
    
    
class Product(models.Model):
    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("published", "Published"),   
    )
    
    coach = models.ForeignKey(User,on_delete=models.CASCADE,related_name="products")
    category = models.ForeignKey(Category,on_delete=models.CASCADE,related_name="products")
    title = models.CharField(max_length=255)
    description = models.TextField()
    Thumbnail = models.ImageField(upload_to="coach/products/",blank=True,null=True)
    book_file = models.FileField(upload_to="coach/products/",blank=True,null=True)
    price = models.DecimalField(max_digits=10,decimal_places=2)
    status = models.CharField(max_length=20,choices=STATUS_CHOICES,default="published")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title