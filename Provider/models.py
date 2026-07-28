from django.db import models
from Administration.models import Category
from Authentication.models import User

class CoachProfile(models.Model):
    user = models.OneToOneField(User,on_delete=models.CASCADE,related_name="coach_profile")
    categories = models.ManyToManyField(Category,related_name="coaches")
    profile_photo = models.ImageField(upload_to="coach/profile/")
    introduction_video = models.FileField(upload_to="coach/videos/",blank=True,null=True)
    about = models.TextField()
    expertises = models.JSONField(default=list, blank=True)
    is_completed = models.BooleanField(default=False)

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