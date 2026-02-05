# admins/serializers.py
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.hashers import make_password
from .models import (
    CustomUser, Page, PendingRegistration,
    Project, Alumni, TeamMember, Blog, Resource, Event,
    SuccessStory, FAQs,Post
)


class PageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Page
        fields = ['id', 'name','description']




class CustomUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    role_display = serializers.SerializerMethodField(read_only=True)
    assigned_pages = serializers.PrimaryKeyRelatedField(
        queryset=Page.objects.all(),
        many=True,
        required=False
    )   
    class Meta:
        model = CustomUser
        fields = [
            'id', 'name', 'email', 'password', 'role', 'role_display',
            'student_id', 'phone_number', 'photo', 'assigned_pages',
            'is_active', 'date_joined'
        ]
        read_only_fields = ['id', 'date_joined', 'is_active']

    def get_role_display(self, obj):
        return obj.get_role_display()

    def validate_email(self, value):
        if not value.lower().endswith('@cseku.ac.bd'):
            raise serializers.ValidationError("Email must end with @cseku.ac.bd")
        return value

    def validate(self, data):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("Authentication required.")

        current_user = request.user
        is_create = self.instance is None

        new_role = data.get('role', self.instance.role if self.instance else 'STUDENT')

        # Role change restrictions
        if new_role == 'SUPER_ADMIN' and current_user.role != 'SUPER_ADMIN':
            raise serializers.ValidationError({"role": "Only Super Admin can assign Super Admin role."})

        if new_role == 'ADMIN' and current_user.role != 'SUPER_ADMIN':
            raise serializers.ValidationError({"role": "Only Super Admin can assign Admin role."})

        # Page assignment only by SUPER_ADMIN
        if 'assigned_pages' in data or (self.instance and self.instance.assigned_pages.exists()):
            if current_user.role != 'SUPER_ADMIN':
                raise serializers.ValidationError({"assigned_pages": "Only Super Admin can assign or change pages."})

        if new_role == 'LAYERED_ADMIN' and not data.get('assigned_pages') and is_create:
            raise serializers.ValidationError({"assigned_pages": "Layered Admin must be assigned at least one page."})

        return data

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        assigned_pages = validated_data.pop('assigned_pages', [])
        user = CustomUser.objects.create(**validated_data)
        if password:
            user.set_password(password)
        user.assigned_pages.set(assigned_pages)
        user.save()
        return user
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        assigned_pages = validated_data.pop('assigned_pages', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        if assigned_pages is not None:
            instance.assigned_pages.set(assigned_pages)

        instance.save()
        return instance
    
class PendingRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])

    class Meta:
        model = PendingRegistration
        fields = ['name', 'email', 'student_id', 'phone_number', 'password']

    def validate_email(self, value):
        if not value.lower().endswith('@cseku.ac.bd'):
            raise serializers.ValidationError("Email must end with @cseku.ac.bd")
        if CustomUser.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("This email is already registered.")
        return value

    def create(self, validated_data):
        # Hash password before saving to pending table
        validated_data['hashed_password'] = make_password(validated_data.pop('password'))
        return super().create(validated_data)  
    
      

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'name', 'email', 'photo', 'role', 'student_id', 'phone_number']
        read_only_fields = ['id', 'name', 'email', 'photo', 'role', 'student_id']


# Other serializers remain mostly unchanged — just showing key ones

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at', 'updated_at', 'approval_status']


class BlogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Blog
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at', 'updated_at', 'approval_status']


class ResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resource
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at', 'updated_at', 'approval_status']


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at', 'updated_at']


class AlumniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alumni
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at', 'updated_at']


class TeamMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeamMember
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at', 'updated_at']


class SuccessStorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SuccessStory
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at', 'updated_at']



class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = [
            'id', 'title', 'slug', 'content',
            'images', 'videos',
            'author', 'created_at', 'updated_at'
        ]
        read_only_fields = ['author', 'created_at', 'updated_at']

    def validate_images(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("images must be a list")
        for url in value:
            if not isinstance(url, str):
                raise serializers.ValidationError("Each image must be a string URL")
            if not url.startswith(('http://', 'https://')):
                raise serializers.ValidationError("Image URLs must start with http/https")
        return value

    def validate_videos(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("videos must be a list")
        for url in value:
            if not isinstance(url, str):
                raise serializers.ValidationError("Each video must be a string URL")
            if not url.startswith(('http://', 'https://')):
                raise serializers.ValidationError("Video URLs must start with http/https")
        return value

# ... (rest of file unchanged)
class FAQsSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQs
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at', 'updated_at']