from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.hashers import make_password

from .models import (
    CustomUser, Page, PendingRegistration,
    Project, Alumni, TeamMember, Blog, Resource, Event,
    SuccessStory, FAQs, Post, Role, CommitteeMembership
)


class PageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Page
        fields = ['id', 'name', 'description']


class RoleSerializer(serializers.ModelSerializer):
    permissions = PageSerializer(many=True, read_only=True)
    permissions_ids = serializers.PrimaryKeyRelatedField(
        queryset=Page.objects.all(),
        many=True,
        write_only=True,
        source='permissions'
    )

    class Meta:
        model = Role
        fields = [
            'id', 'name', 'permissions', 'permissions_ids',
            'is_president', 'created_by', 'created_at'
        ]
        read_only_fields = ['created_by', 'created_at']

    def validate(self, data):
        if data.get('is_president') and Role.objects.filter(is_president=True).exclude(id=self.instance.id if self.instance else None).exists():
            raise serializers.ValidationError("Only one President role can exist.")
        return data


class CommitteeMembershipSerializer(serializers.ModelSerializer):
    role = RoleSerializer(read_only=True)
    role_id = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(),
        write_only=True,
        source='role'
    )
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = CommitteeMembership
        fields = ['id', 'user', 'role', 'role_id', 'year', 'assigned_at', 'user_email']
        read_only_fields = ['assigned_at']


class CustomUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, validators=[validate_password])
    current_membership = CommitteeMembershipSerializer(read_only=True)
    memberships = CommitteeMembershipSerializer(many=True, read_only=True)

    class Meta:
        model = CustomUser
        fields = [
            'id', 'name', 'email', 'password', 'photo',
            'student_id', 'phone_number', 'is_active', 'date_joined',
            'current_membership', 'memberships'
        ]
        read_only_fields = ['id', 'date_joined', 'is_active']

    def validate_email(self, value):
        if not value.lower().endswith('@cseku.ac.bd'):
            raise serializers.ValidationError("Email must end with @cseku.ac.bd")
        return value

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = CustomUser.objects.create(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
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
        validated_data['hashed_password'] = make_password(validated_data.pop('password'))
        return super().create(validated_data)


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'name', 'email', 'photo', 'student_id', 'phone_number']
        read_only_fields = ['id', 'name', 'email', 'photo', 'student_id']


# Content serializers (all follow similar pattern)

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at', 'updated_at', 'approval_status', 'year']


class BlogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Blog
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at', 'updated_at', 'approval_status', 'year']


class ResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resource
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at', 'updated_at', 'approval_status', 'year']


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at', 'updated_at', 'year']


class AlumniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alumni
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at', 'updated_at', 'year']


class TeamMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeamMember
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at', 'updated_at', 'year']


class SuccessStorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SuccessStory
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at', 'updated_at', 'year']


class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ['id', 'title', 'slug', 'content', 'images', 'videos', 'author', 'created_at', 'updated_at', 'year']
        read_only_fields = ['author', 'created_at', 'updated_at', 'year']

    def validate_images(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("images must be a list")
        for url in value:
            if not isinstance(url, str) or not url.startswith(('http://', 'https://')):
                raise serializers.ValidationError("Each image must be a valid http(s) URL")
        return value

    def validate_videos(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("videos must be a list")
        for url in value:
            if not isinstance(url, str) or not url.startswith(('http://', 'https://')):
                raise serializers.ValidationError("Each video must be a valid http(s) URL")
        return value


class FAQsSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQs
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at', 'updated_at', 'year']