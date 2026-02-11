


"""
Views for the CLUSTER admin backend API.
Handles authentication, user management, content CRUD with approval workflows,
and yearly team committee import/transition features.
"""
from io import StringIO
import csv

from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, SAFE_METHODS
from rest_framework_simplejwt.tokens import RefreshToken
from django.db import transaction
from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from rest_framework.request import Request
from .models import (
    CustomUser, Page, PendingRegistration, Project, Blog, Resource, Event,
    Alumni, TeamMember, SuccessStory, FAQs, Post, Role, CommitteeMembership,
    SystemSetting
)
from .serializers import (
    PendingRegistrationSerializer, CustomUserSerializer, ProfileSerializer,
    PageSerializer, ProjectSerializer, AlumniSerializer, TeamMemberSerializer,
    BlogSerializer, ResourceSerializer, EventSerializer,
    SuccessStorySerializer, FAQsSerializer, PostSerializer,
    RoleSerializer, CommitteeMembershipSerializer
)
from .permissions import (
    IsCurrentPresident,
    IsPresidentOrAdmin,
    HasPagePermission,
    CanModifyCurrentYearContent,
)


# ────────────────────────────────────────────────
# Helper functions
# ────────────────────────────────────────────────

def get_current_year():
    return SystemSetting.get_current_year()

# views.py
class CurrentYearView(APIView):
    """
    Returns the current committee/academic year.
    """
    permission_classes = [AllowAny]  # or [IsAuthenticated] if you prefer

    def get(self, request):
        current_year = SystemSetting.get_current_year()
        return Response({"current_year": current_year})

# ────────────────────────────────────────────────
# Authentication Views
# ────────────────────────────────────────────────

class RegistrationView(APIView):
    """Register a new user → sends OTP to email."""
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")

        if CustomUser.objects.filter(email=email).exists():
            return Response({"error": "Email already registered."}, status=status.HTTP_400_BAD_REQUEST)

        PendingRegistration.objects.filter(email=email).delete()

        serializer = PendingRegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        pending = serializer.save()
        otp = get_random_string(length=6, allowed_chars="0123456789")
        pending.otp = otp
        pending.save()

        send_mail(
            subject="CLUSTER Registration OTP",
            message=f"Your OTP: {otp}\nValid for 10 minutes.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )

        return Response({
            "message": "OTP sent. Verify to complete registration.",
            "pending_id": pending.id,
        }, status=status.HTTP_200_OK)


class VerifyOTPView(APIView):
    """Verify OTP and complete registration."""
    permission_classes = [AllowAny]

    def post(self, request):
        pending_id = request.data.get('pending_id')
        otp = request.data.get('otp')

        try:
            pending = PendingRegistration.objects.get(id=pending_id, otp=otp)
            if not pending.is_valid():
                pending.delete()
                return Response({'error': 'OTP expired.'}, status=status.HTTP_400_BAD_REQUEST)

            user = CustomUser.objects.create(
                name=pending.name,
                email=pending.email,
                student_id=pending.student_id,
                phone_number=pending.phone_number,
                is_active=True,
            )
            user.password = pending.hashed_password
            user.save()

            pending.delete()

            refresh = RefreshToken.for_user(user)
            return Response({
                'message': 'Registration complete.',
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            })

        except PendingRegistration.DoesNotExist:
            return Response({'error': 'Invalid OTP or registration session.'}, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    """Logout by blacklisting refresh token."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"message": "Logout successful."})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ────────────────────────────────────────────────
# User & Profile Management
# ────────────────────────────────────────────────

class CustomUserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'me']:
            return [IsAuthenticated()]
        return [IsCurrentPresident()]

    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        serializer = CustomUserSerializer(request.user)
        return Response(serializer.data)


# ────────────────────────────────────────────────
# Role & Membership Management
# ────────────────────────────────────────────────

class PageViewSet(viewsets.ModelViewSet):
    queryset = Page.objects.all()
    serializer_class = PageSerializer
    permission_classes = [IsCurrentPresident]


class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsCurrentPresident]


class CommitteeMembershipViewSet(viewsets.ModelViewSet):
    queryset = CommitteeMembership.objects.all()
    serializer_class = CommitteeMembershipSerializer
    permission_classes = [IsCurrentPresident]

    def get_queryset(self):
        year = self.request.query_params.get('year')
        qs = self.queryset
        if year:
            qs = qs.filter(year=year)
        return qs


# ────────────────────────────────────────────────
# Handover Endpoint
# ────────────────────────────────────────────────

class HandoverView(APIView):
    permission_classes = [IsCurrentPresident]

    def post(self, request):
        new_year = request.data.get('new_year')
        new_president_id = request.data.get('new_president_id')
        archive_old = request.data.get('archive_old', False)  # New: optional archiving

        if not new_year or not new_president_id:
            return Response({"error": "new_year and new_president_id required"}, status=400)

        try:
            with transaction.atomic():
                if archive_old:
                    prev_year = SystemSetting.get_current_year()
                    old_memberships = CommitteeMembership.objects.filter(year=prev_year)
                    for m in old_memberships:
                        Alumni.objects.create(
                            name=m.user.name,
                            batch=f"{prev_year} Committee",  # Example archiving
                            role=m.role.name,
                            email=m.user.email,
                            year=prev_year,
                            created_by=request.user,
                        )
                    old_memberships.delete()  

                SystemSetting.set_current_year(new_year)

                new_president = CustomUser.objects.get(id=new_president_id)
                president_role = Role.objects.filter(is_president=True).first()
                if not president_role:
                    return Response({"error": "No president role defined"}, status=400)

                CommitteeMembership.objects.create(
                    user=new_president,
                    role=president_role,
                    year=new_year
                )

                return Response({"message": f"Handover to {new_year} complete. New president: {new_president.email}"})

        except Exception as e:
            return Response({"error": str(e)}, status=400)


# ────────────────────────────────────────────────
# Content ViewSets
# ────────────────────────────────────────────────

class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [AllowAny()]
        return [HasPagePermission(), CanModifyCurrentYearContent()]

    def get_queryset(self):
        
        """
        IMPORTANT FIX:
        - On LIST → filter by year (good for dashboard)
        - On DETAIL actions (update, delete, approve, etc.) → return full queryset
        """
        if self.action in ['retrieve', 'update', 'partial_update', 'destroy', 'approve', 'reject']:
            return self.queryset   # ← Critical: No year filter here

        # Only filter by year on list view
        year = self.request.query_params.get('year')
        qs = self.queryset
        if year:
            qs = qs.filter(year=year)
        return qs.order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(
            created_by=self.request.user,
            year=get_current_year()
        )

    @action(detail=True, methods=['post'], permission_classes=[IsPresidentOrAdmin])
    def approve(self, request, pk=None):
        obj = self.get_object()
        obj.approval_status = 'APPROVED'
        obj.save()
        return Response({'message': 'Project Approved Successfully'})

    @action(detail=True, methods=['post'], permission_classes=[IsPresidentOrAdmin])
    def reject(self, request, pk=None):
        obj = self.get_object()
        obj.approval_status = 'REJECTED'
        obj.save()
        return Response({'message': 'Project Rejected'})


class BlogViewSet(viewsets.ModelViewSet):
    queryset = Blog.objects.all().order_by('-created_at')
    serializer_class = BlogSerializer

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [AllowAny()]
        return [HasPagePermission(), CanModifyCurrentYearContent()]

    def get_queryset(self):
        """
        IMPORTANT FIX:
        - On LIST → filter by year (good for dashboard)
        - On DETAIL actions (update, delete, approve, etc.) → return full queryset
        """
        if self.action in ['retrieve', 'update', 'partial_update', 'destroy', 'approve', 'reject']:
            return self.queryset   # ← Critical: No year filter here

        # Only filter by year on list view
        year = self.request.query_params.get('year')
        qs = self.queryset
        if year:
            qs = qs.filter(year=year)
        return qs.order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(
            created_by=self.request.user,
            year=get_current_year()
        )

    @action(detail=True, methods=['post'], permission_classes=[IsPresidentOrAdmin])
    def approve(self, request, pk=None):
        obj = self.get_object()
        obj.approval_status = 'APPROVED'
        obj.save()
        return Response({'message': 'Approved'})

    @action(detail=True, methods=['post'], permission_classes=[IsPresidentOrAdmin])
    def reject(self, request, pk=None):
        obj = self.get_object()
        obj.approval_status = 'REJECTED'
        obj.save()
        return Response({'message': 'Rejected'})


class ResourceViewSet(viewsets.ModelViewSet):
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [AllowAny()]
        return [HasPagePermission(), CanModifyCurrentYearContent()]

    def get_queryset(self):
        if self.action in ['retrieve', 'update', 'partial_update', 'destroy', 'approve', 'reject']:
            return self.queryset
        year = self.request.query_params.get('year')
        qs = self.queryset
        if year:
            qs = qs.filter(year=year)
        return qs.order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(
            created_by=self.request.user,
            year=get_current_year()
        )

    @action(detail=True, methods=['post'], permission_classes=[IsPresidentOrAdmin])
    def approve(self, request, pk=None):
        obj = self.get_object()
        obj.approval_status = 'APPROVED'
        obj.save()
        return Response({'message': 'Resource Approved Successfully'})

    @action(detail=True, methods=['post'], permission_classes=[IsPresidentOrAdmin])
    def reject(self, request, pk=None):
        obj = self.get_object()
        obj.approval_status = 'REJECTED'
        obj.save()
        return Response({'message': 'Resource Rejected'})


class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all()
    serializer_class = EventSerializer

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [AllowAny()]
        return [HasPagePermission(), CanModifyCurrentYearContent()]

    def get_queryset(self):
        if self.action in ['retrieve', 'update', 'partial_update', 'destroy', 'approve', 'reject']:
            return self.queryset 
        if self.action in ['retrieve','update', 'partial_update', 'destroy']:
            return self.queryset  
        
        # Only apply year filter on list
        year = self.request.query_params.get('year')
        qs = self.queryset
        if year:
            qs = qs.filter(year=year)
        return qs.order_by('-date')

    def perform_create(self, serializer):
        serializer.save(
            created_by=self.request.user,
            year=get_current_year()
        )


class SuccessStoryViewSet(viewsets.ModelViewSet):
    queryset = SuccessStory.objects.all()
    serializer_class = SuccessStorySerializer

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [AllowAny()]
        return [HasPagePermission(), CanModifyCurrentYearContent()]

    def get_queryset(self):
        if self.action in ['retrieve', 'update', 'partial_update', 'destroy', 'approve', 'reject']:
            return self.queryset 
        if self.action in ['retrieve', 'update', 'partial_update', 'destroy']:
            return self.queryset
        year = self.request.query_params.get('year')
        qs = self.queryset
        if year:
            qs = qs.filter(year=year)
        return qs

    def perform_create(self, serializer):
        serializer.save(
            created_by=self.request.user,
            year=get_current_year()
        )


class FAQsViewSet(viewsets.ModelViewSet):
    queryset = FAQs.objects.all()
    serializer_class = FAQsSerializer

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [AllowAny()]
        return [HasPagePermission(), CanModifyCurrentYearContent()]

    def get_queryset(self):
        if self.action in ['retrieve', 'update', 'partial_update', 'destroy', 'approve', 'reject']:
            return self.queryset 
        if self.action in ['retrieve', 'update', 'partial_update', 'destroy']:
            return self.queryset
        year = self.request.query_params.get('year')
        qs = self.queryset
        if year:
            qs = qs.filter(year=year)
        return qs

    def perform_create(self, serializer):
        serializer.save(
            created_by=self.request.user,
            year=get_current_year()
        )


class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    pagination_class = None
    
    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [AllowAny()]
        return [HasPagePermission(), CanModifyCurrentYearContent()]

    def get_queryset(self):
        if self.action in ['retrieve', 'update', 'partial_update', 'destroy']:
            return self.queryset
        year = self.request.query_params.get('year')
        qs = self.queryset
        if year:
            qs = qs.filter(year=year)
        # Optional: order by newest first
        return qs.order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(
            author=self.request.user,
            year=SystemSetting.get_current_year()
        )

    


# ────────────────────────────────────────────────
# Archive / Read-only Models
# ────────────────────────────────────────────────

class AlumniViewSet(viewsets.ModelViewSet):
    queryset = Alumni.objects.all()
    serializer_class = AlumniSerializer
    permission_classes = [IsAuthenticated, HasPagePermission, CanModifyCurrentYearContent]
    page_name = 'alumni'

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'create']:
            return [AllowAny()]  # Public can see approved & submit new
        return super().get_permissions()

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_authenticated:
            qs = qs.filter(approval_status='approved')
        return qs.order_by('-created_at')

    @action(detail=True, methods=['post'], permission_classes=[IsCurrentPresident])
    def approve(self, request, pk=None):
        obj = self.get_object()
        obj.approval_status = 'approved'
        obj.approved_by = request.user
        obj.save()
        return Response({'status': 'approved'})

    @action(detail=True, methods=['post'], permission_classes=[IsCurrentPresident])
    def reject(self, request, pk=None):
        obj = self.get_object()
        obj.approval_status = 'rejected'
        obj.save()
        return Response({'status': 'rejected'})


class TeamMemberViewSet(viewsets.ModelViewSet):
    queryset = TeamMember.objects.all()
    serializer_class = TeamMemberSerializer
    permission_classes = [IsPresidentOrAdmin, CanModifyCurrentYearContent]

    def get_queryset(self):
        year = self.request.query_params.get('year')
        qs = self.queryset
        if year:
            qs = qs.filter(year=year)
        return qs


# ────────────────────────────────────────────────
# Yearly Committee CSV Import
# ────────────────────────────────────────────────

# class ImportTeamMembersView(APIView):
#     """
#     President-only endpoint.
#     Imports committee from CSV → creates/updates users, roles, memberships, TeamMember entries.
#     Optionally archives previous year's committee to Alumni.
#     """
#     permission_classes = [IsCurrentPresident]

#     def post(self, request):
#         archive_old = request.data.get("archive_old", False)
#         file = request.FILES.get("file")
#         target_year = int(request.data.get('year', get_current_year()))

#         if not file:
#             return Response({"error": "CSV file is required"}, status=400)

#         try:
#             if archive_old:
#                 prev_year = target_year - 1
#                 old_memberships = CommitteeMembership.objects.filter(year=prev_year)
#                 for m in old_memberships:
#                     Alumni.objects.create(
#                         name=m.user.name,
#                         role=m.role.name,
#                         email=m.user.email,
#                         # image_url=... (you may want to copy from TeamMember if exists)
#                         year=prev_year,
#                         created_by=request.user,
#                     )
#                 old_memberships.delete()

#             content = file.read().decode("utf-8-sig")
#             reader = csv.DictReader(StringIO(content))

#             count = 0

#             for row in reader:
#                 role_name = row.get("Designation", "").strip()
#                 name = row.get("Name", "").strip()
#                 email = row.get("Email", "").strip()

#                 if not role_name or not email or not name:
#                     continue

#                 user, _ = CustomUser.objects.update_or_create(
#                     email=email,
#                     defaults={
#                         "name": name,
#                         "password": make_password(f"committee{target_year}!"),
#                         "is_active": True,
#                         "is_staff": True,
#                         "student_id": row.get("Student ID", ""),
#                         "photo": row.get("Image URL", ""),
#                     }
#                 )

#                 role, _ = Role.objects.get_or_create(
#                     name=role_name,
#                     defaults={"created_by": request.user}
#                 )

#                 CommitteeMembership.objects.update_or_create(
#                     user=user,
#                     year=target_year,
#                     defaults={"role": role}
#                 )

#                 TeamMember.objects.update_or_create(
#                     email=email,
#                     defaults={
#                         "designation": role_name,
#                         "name": name,
#                         "student_id": row.get("Student ID", ""),
#                         "image_url": row.get("Image URL", ""),
#                         "facebook_url": row.get("Facebook URL", ""),
#                         "linkedin_url": row.get("LinkedIn URL", ""),
#                         "quote": row.get("Quote", ""),
#                         "created_by": request.user,
#                         "year": target_year,
#                     }
#                 )

#                 count += 1

#             msg = f"Processed {count} committee members for year {target_year}."
#             if archive_old:
#                 msg += f" Previous year ({target_year-1}) archived."

#             return Response({"message": msg}, status=200)

#         except Exception as e:
#             return Response({"error": f"Import failed: {str(e)}"}, status=400)

# ... (rest of the file unchanged)

class ImportTeamMembersView(APIView):
    """
    President-only endpoint.
    Imports committee from CSV → creates/updates users, roles, memberships, TeamMember entries.
    Optionally archives previous year's committee (memberships preserved - no Alumni creation).
    """
    permission_classes = [IsCurrentPresident]

    def post(self, request):
        archive_old = request.data.get("archive_old", False)
        file = request.FILES.get("file")
        target_year = int(request.data.get('year', get_current_year()))

        if not file:
            return Response({"error": "CSV file is required"}, status=400)

        try:
            if archive_old:
                prev_year = target_year - 1
                # Old memberships remain for history (no deletion, no Alumni creation)
                pass

            content = file.read().decode("utf-8-sig")
            reader = csv.DictReader(StringIO(content))

            count = 0

            for row in reader:
                role_name = row.get("Designation", "").strip()
                name = row.get("Name", "").strip()
                email = row.get("Email", "").strip()

                if not role_name or not email or not name:
                    continue

                user, _ = CustomUser.objects.update_or_create(
                    email=email,
                    defaults={
                        "name": name,
                        "password": make_password(f"committee{target_year}!"),
                        "is_active": True,
                        "is_staff": True,
                        "student_id": row.get("Student ID", ""),
                        "photo": row.get("Image URL", ""),
                    }
                )

                role, _ = Role.objects.get_or_create(
                    name=role_name,
                    defaults={"created_by": request.user}
                )

                CommitteeMembership.objects.update_or_create(
                    user=user,
                    year=target_year,
                    defaults={"role": role}
                )

                TeamMember.objects.update_or_create(
                    email=email,
                    defaults={
                        "designation": role_name,
                        "name": name,
                        "student_id": row.get("Student ID", ""),
                        "image_url": row.get("Image URL", ""),
                        "facebook_url": row.get("Facebook URL", ""),
                        "linkedin_url": row.get("LinkedIn URL", ""),
                        "quote": row.get("Quote", ""),
                        "created_by": request.user,
                        "year": target_year,
                    }
                )

                count += 1

            msg = f"Processed {count} committee members for year {target_year}."
            if archive_old:
                msg += f" Previous year ({target_year-1}) archived (memberships preserved)."

            return Response({"message": msg}, status=200)

        except Exception as e:
            return Response({"error": f"Import failed: {str(e)}"}, status=400)

# ... (HandoverView unchanged - it should just update current_year and new president)