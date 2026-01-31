from rest_framework import serializers
from .models import CustomUser, Page
from django.contrib.auth.password_validation import validate_password
from django.core.validators import EmailValidator
from .models import Project, Alumni, TeamMember, Blog, Resource, Event, SuccessStory,FAQs

class PageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Page
        fields = ['id', 'name']

# class CustomUserSerializer(serializers.ModelSerializer):
#     assigned_pages = serializers.PrimaryKeyRelatedField(many=True, queryset=Page.objects.all(), required=False)
#     password = serializers.CharField(write_only=True, required=True, validators=[validate_password])

#     class Meta:
#         model = CustomUser
#         fields = ['id', 'name', 'email', 'photo', 'role', 'assigned_pages', 'password', ]
#         read_only_fields = ['id','date_joined']
#     def get_role(self, obj):
#         if obj.is_superuser:
#             return "Super Admin"
#         if obj.is_staff:
#             return "Admin"
#         return "Layered Admin"  
#     def validate_email(self, value):
#         if not value.endswith('@cseku.ac.bd'):
#             raise serializers.ValidationError("Email must end with @cseku.ac.bd")
#         return value

#     def create(self, validated_data):
#         assigned_pages = validated_data.pop('assigned_pages', [])
#         user = CustomUser.objects.create_user(**validated_data)
#         user.assigned_pages.set(assigned_pages)
#         return user

#     def update(self, instance, validated_data):
#         assigned_pages = validated_data.pop('assigned_pages', None)
#         password = validated_data.pop('password', None)
#         if password:
#             instance.set_password(password)
#         instance = super().update(instance, validated_data)
#         if assigned_pages is not None:
#             instance.assigned_pages.set(assigned_pages)
#         return instance

class CustomUserSerializer(serializers.ModelSerializer):
    # For read-only display
    assigned_pages = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Page.objects.all(),
        required=False,
        allow_empty=True
    )
    
    # Optional: show page names in GET responses
    assigned_pages_details = PageSerializer(
        source='assigned_pages',
        many=True,
        read_only=True
    )

    role = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CustomUser
        fields = [
            'id',
            'email',
            'name',
            'photo',
            'password',             # write-only
            'role',
            'assigned_pages',
            'assigned_pages_details',  # optional - nicer output
            'is_active',
            'is_staff',
            'is_superuser',
            'date_joined',
        ]
        read_only_fields = ['id', 'date_joined', 'role', 'assigned_pages_details']
        extra_kwargs = {
            'password': {'write_only': True, 'required': False},  # required only on create
        }

    def get_role(self, obj):
        if obj.is_superuser:
            return "Super Admin"
        if obj.is_staff:
            return "Admin"
        return "Layered Admin"

    
    def create(self, validated_data):
    # Extract fields we handle specially
        password = validated_data.pop('password', None)
        assigned_pages = validated_data.pop('assigned_pages', [])

        # Create user – pass only what create_user expects as explicit kwargs
        # Do NOT use **validated_data here to avoid duplicates
        user = CustomUser.objects.create_user(
            email=validated_data.pop('email'),          # pop to remove it
            name=validated_data.pop('name', ''),
            photo=validated_data.pop('photo', None),
            password=password,
            **validated_data                            # now safe – only remaining fields (role, is_active, etc.)
        )

        # Assign pages if provided
        if assigned_pages:
            user.assigned_pages.set(assigned_pages)

        return user

        # Assign pages (ManyToMany)
        if assigned_pages:
            user.assigned_pages.set(assigned_pages)

        return user

    
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        assigned_pages = validated_data.pop('assigned_pages', None)

        # Update regular fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password is not None:
            instance.set_password(password)

        if assigned_pages is not None:
            instance.assigned_pages.set(assigned_pages)

        instance.save()
        return instance

class ProfileSerializer(CustomUserSerializer):
    class Meta(CustomUserSerializer.Meta):
        fields = ['id', 'name', 'email', 'photo', 'role', 'assigned_pages', 'assignedAt']
        read_only_fields = ['email', 'role', 'assigned_pages', 'assignedAt']
class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
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

class BlogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Blog
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at', 'updated_at']

class ResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resource
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at', 'updated_at']

class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at', 'updated_at']

class SuccessStorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SuccessStory
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at', 'updated_at']           

class FAQsSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQs
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at', 'updated_at']    
        
            