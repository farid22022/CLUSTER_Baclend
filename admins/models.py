# admins/models.py
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
import random
import string
from simple_history.models import HistoricalRecords


def get_current_year_default():
    return SystemSetting.get_current_year()

class CustomUserManager(BaseUserManager):
    def create_user(self, email, name, password=None, **extra_fields):
        if not email:
            raise ValueError(_('The Email must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, name=name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', 'SUPER_ADMIN')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, name, password, **extra_fields)

# new 4.42 PM 09/02/26
class SystemSetting(models.Model):
    """Singleton for system-wide settings like current_year."""
    key = models.CharField(max_length=100, unique=True)
    value = models.CharField(max_length=255)

    @classmethod
    def get_current_year(cls):
        obj, _ = cls.objects.get_or_create(key='current_year', defaults={'value': str(timezone.now().year)})
        return int(obj.value)

    @classmethod
    def set_current_year(cls, year):
        obj, _ = cls.objects.get_or_create(key='current_year')
        obj.value = str(year)
        obj.save()

class Page(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name
    
# new 4.42 PM 09/02/26        
class Role(models.Model):
    name = models.CharField(max_length=100, unique=True)  # e.g., 'Vice President', 'Treasurer'
    permissions = models.ManyToManyField(Page, blank=True, related_name='roles')  # Pages/routes accessible
    is_president = models.BooleanField(default=False)  # Special flag for President (Super Admin)
    created_by = models.ForeignKey('CustomUser', on_delete=models.SET_NULL, null=True, related_name='created_roles')
    created_at = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()  # Audit changes

    def __str__(self):
        return self.name

    class Meta:
        unique_together = ['name']  # Ensure unique roles
        indexes = [models.Index(fields=['name'])]            
# new 4.42 PM 09/02/26    
class CommitteeMembership(models.Model):
    user = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='memberships')
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name='memberships')
    year = models.PositiveIntegerField(default=get_current_year_default)  # e.g., 2026
    assigned_at = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()  # Audit changes

    def __str__(self):
        return f"{self.user} - {self.role} ({self.year})"

    class Meta:
        ordering = ['-year', 'user__name']  # Added for better querying
        unique_together = ['user', 'year']  # Unchanged


class CustomUser(AbstractBaseUser, PermissionsMixin):
    # ... (remove fixed ROLE_CHOICES and assigned_pages; derive from membership)
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    photo = models.URLField(max_length=500, blank=True, null=True)
    student_id = models.CharField(max_length=50, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    history = HistoricalRecords()  

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        if not self.email.lower().endswith('@cseku.ac.bd'):
            raise ValueError('Email must end with @cseku.ac.bd')
        super().save(*args, **kwargs)

    @property
    def current_membership(self):
        current_year = SystemSetting.get_current_year()
        return self.memberships.filter(year=current_year).first()

    @property
    def current_role(self):
        membership = self.current_membership
        return membership.role if membership else None

    @property
    def is_current_president(self):
        role = self.current_role
        return role and role.is_president

    @property
    def current_permissions(self):
        role = self.current_role
        return role.permissions.all() if role else Page.objects.none()
    
    

class PendingRegistration(models.Model):
    """
    Temporary storage for users who have signed up but not yet verified via OTP.
    Deleted after successful verification.
    """
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True, db_index=True)
    student_id = models.CharField(max_length=50)
    phone_number = models.CharField(max_length=20)
    hashed_password = models.CharField(max_length=128)  # Stored hashed
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        """OTP is valid for 10 minutes"""
        return timezone.now() - self.created_at < timezone.timedelta(minutes=10)

    def __str__(self):
        return f"Pending: {self.email}"
    
    class Meta:
        indexes = [
            models.Index(fields=['email']),           # fast lookup
            models.Index(fields=['created_at']),      # for cleanup
        ]
            

class OTP(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        return timezone.now() - self.created_at < timezone.timedelta(minutes=10)

    def __str__(self):
        return f"OTP for {self.user.email}"

# ────────────────────────────────────────────────
# Content Models (with approval workflow where needed)
# ────────────────────────────────────────────────

class Project(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    tech_stack = models.JSONField(default=list)
    status = models.CharField(max_length=20, choices=[('Ongoing', 'Ongoing'), ('Completed', 'Completed')])
    team = models.JSONField(default=list)
    github = models.URLField(
        blank=True,
        null=True,          
        default=''          
    )
    demo = models.URLField(
        blank=True,
        null=True,
        default=''
    )
    year = models.PositiveIntegerField(default=get_current_year_default)
    history = HistoricalRecords()
    domain = models.CharField(max_length=100)
    image = models.CharField(   # or ImageField if using uploads
        max_length=500,
        blank=True,
        null=True,
        default=''
    )
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    student_id = models.CharField(max_length=50, blank=True)
    approval_status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')],
        default='pending'
    )

    def __str__(self):
        return self.title

class Blog(models.Model):
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=50)
    tags = models.JSONField(default=list)
    author = models.CharField(max_length=100)
    date = models.DateField()
    excerpt = models.TextField()
    image = models.CharField(max_length=500, blank=True)
    restricted = models.BooleanField(default=False)
    approval_status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')],
        default='pending'
    )
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    year = models.PositiveIntegerField(default=get_current_year_default)
    history = HistoricalRecords()

    def __str__(self):
        return self.title

class Resource(models.Model):
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=100)
    format = models.CharField(max_length=50)
    difficulty = models.CharField(max_length=50)
    link = models.URLField()
    restricted = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    approval_status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')],
        default='pending'
    )
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    year = models.PositiveIntegerField(default=get_current_year_default)
    history = HistoricalRecords()

    def __str__(self):
        return self.title

class Event(models.Model):
    title = models.CharField(max_length=255)
    date = models.DateField()
    time = models.CharField(max_length=50, blank=True)
    location = models.CharField(max_length=100, blank=True)
    description = models.TextField()
    image = models.CharField(max_length=500, blank=True)
    venue = models.CharField(max_length=100, blank=True)
    tags = models.JSONField(default=list)
    link = models.URLField(blank=True)
    is_upcoming = models.BooleanField(default=True)
    highlights = models.JSONField(default=list, blank=True)
    links = models.JSONField(default=list, blank=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    year = models.PositiveIntegerField(default=get_current_year_default)
    history = HistoricalRecords()

    def __str__(self):
        return self.title

class Alumni(models.Model):
    APPROVAL_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    batch = models.CharField(max_length=100)              # e.g. CSE-17
    session = models.CharField(max_length=100, blank=True)
    passing_year = models.PositiveIntegerField(null=True, blank=True)
    current_role = models.CharField(max_length=100, blank=True)  # ← renamed from 'role'
    company = models.CharField(max_length=200, blank=True)
    location = models.CharField(max_length=100, blank=True)
    image_url = models.CharField(max_length=500, blank=True)
    linkedin_url = models.URLField(blank=True, null=True)
    facebook_url = models.URLField(blank=True, null=True)
    about = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approval_status = models.CharField(max_length=10, choices=APPROVAL_CHOICES, default='pending')
    approved_by = models.ForeignKey('CustomUser', null=True, blank=True, on_delete=models.SET_NULL, related_name='approved_alumni')

    def __str__(self):
        return f"{self.name} ({self.batch})"

    class Meta:
        ordering = ['-created_at']

class TeamMember(models.Model):
    designation = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    student_id = models.CharField(max_length=50, blank=True)
    image_url = models.CharField(max_length=500, blank=True)
    facebook_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    email = models.EmailField(blank=True)
    quote = models.TextField(blank=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    year = models.PositiveIntegerField(default=get_current_year_default)
    history = HistoricalRecords()

    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['-year', 'name']

class SuccessStory(models.Model):
    name = models.CharField(max_length=255)
    position = models.CharField(max_length=100)
    company = models.CharField(max_length=100)
    quote = models.TextField()
    image_url = models.CharField(max_length=500, blank=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    year = models.PositiveIntegerField(default=get_current_year_default)
    history = HistoricalRecords()

    def __str__(self):
        return self.name

class FAQs(models.Model):
    question = models.CharField(max_length=255)
    answer = models.TextField()
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    year = models.PositiveIntegerField(default=get_current_year_default)
    history = HistoricalRecords()

    def __str__(self):
        return self.question


class Post(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True, null=True)
    content = models.TextField()
    images = models.JSONField(
        default=list,
        blank=True,
        help_text="List of image URLs (strings)"
    )
    videos = models.JSONField(
        default=list,
        blank=True,
        help_text="List of video URLs (strings)"
    )
    author = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='posts')
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    year = models.PositiveIntegerField(default=get_current_year_default)
    history = HistoricalRecords()


    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug and self.title:
            from django.utils.text import slugify
            self.slug = slugify(self.title)
            # Ensure uniqueness
            original_slug = self.slug
            counter = 1
            while Post.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

