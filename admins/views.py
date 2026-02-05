# admins/views.py           
from rest_framework.views import APIView
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, SAFE_METHODS
from rest_framework_simplejwt.tokens import RefreshToken

from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string
from django.utils import timezone

from .models import CustomUser, Page, PendingRegistration, Project, Blog, Resource, Event, OTP,Alumni, TeamMember, SuccessStory, FAQs,Post
from .serializers import (
    PendingRegistrationSerializer, CustomUserSerializer, ProfileSerializer, PageSerializer,
    ProjectSerializer, AlumniSerializer, TeamMemberSerializer,
    BlogSerializer, ResourceSerializer, EventSerializer,
    SuccessStorySerializer, FAQsSerializer,PostSerializer
)
from .permissions import IsSuperAdmin, IsAdminOrSuperAdmin,IsStudent


class RegistrationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')

        # Check if already verified user exists
        if CustomUser.objects.filter(email=email).exists():
            return Response(
                {"error": "This email is already registered and verified."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Delete any old pending record for this email
        PendingRegistration.objects.filter(email=email).delete()

        serializer = PendingRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            pending = serializer.save()  # hashed_password set in serializer

            # Generate new OTP
            otp_code = get_random_string(length=6, allowed_chars='0123456789')
            pending.otp = otp_code
            pending.save()

            # Send email
            send_mail(
                subject='Your CLUSTER Registration OTP',
                message=f'Your OTP is: {otp_code}\nIt expires in 10 minutes.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[pending.email],
                fail_silently=False,
            )

            return Response({
                'message': 'OTP sent to your email. Please verify to complete registration.',
                'pending_id': pending.id
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class ResendOTPView(APIView):
    """
    Resend OTP for an existing pending registration
    """
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')

        if not email:
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            pending = PendingRegistration.objects.get(email=email)

            # Optional: check if too many resends (rate limiting)
            if timezone.now() - pending.created_at > timezone.timedelta(hours=1):
                pending.delete()
                return Response({"error": "Session expired. Please register again."}, status=status.HTTP_400_BAD_REQUEST)

            # Generate new OTP
            otp_code = get_random_string(length=6, allowed_chars='0123456789')
            pending.otp = otp_code
            pending.save()

            # Re-send email
            send_mail(
                subject='Your CLUSTER Registration OTP (Resent)',
                message=f'Your new OTP is: {otp_code}\nIt expires in 10 minutes.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[pending.email],
                fail_silently=False,
            )

            return Response({
                'message': 'New OTP sent to your email.',
                'pending_id': pending.id
            }, status=status.HTTP_200_OK)

        except PendingRegistration.DoesNotExist:
            return Response({"error": "No pending registration found for this email. Please register first."}, status=status.HTTP_404_NOT_FOUND)
        
        
class VerifyOTPView(APIView):
    """
    Verify OTP → create real CustomUser if valid → delete pending record
    """
    permission_classes = [AllowAny]

    def post(self, request):
        pending_id = request.data.get('pending_id')
        otp_input = request.data.get('otp')

        try:
            pending = PendingRegistration.objects.get(id=pending_id)

            if pending.otp != otp_input:
                return Response({'error': 'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)

            if not pending.is_valid():
                pending.delete()
                return Response({'error': 'OTP expired. Please register again.'}, status=status.HTTP_400_BAD_REQUEST)

            # Create real user
            user = CustomUser.objects.create(
                name=pending.name,
                email=pending.email,
                student_id=pending.student_id,
                phone_number=pending.phone_number,
                role='STUDENT',
                is_active=True
            )
            user.password = pending.hashed_password  # already hashed
            user.save()

            # Clean up
            pending.delete()

            # Issue JWT tokens
            refresh = RefreshToken.for_user(user)
            return Response({
                'message': 'Account verified and activated!',
                'access': str(refresh.access_token),
                'refresh': str(refresh)
            }, status=status.HTTP_200_OK)

        except PendingRegistration.DoesNotExist:
            return Response({'error': 'Invalid registration session'}, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh = RefreshToken(request.data.get('refresh'))
            refresh.blacklist()
            return Response({"message": "Logout successful"}, status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ────────────────────────────────────────────────
# User & Profile Management
# ────────────────────────────────────────────────
class CustomUserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAdminOrSuperAdmin()]
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsSuperAdmin()]
        return [IsAuthenticated()]

    @action(detail=False, methods=['get', 'patch'], permission_classes=[IsAuthenticated])
    def profile(self, request):
        user = request.user
        if request.method == 'GET':
            serializer = ProfileSerializer(user)
            return Response(serializer.data)
        
        serializer = ProfileSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class PageViewSet(viewsets.ModelViewSet):
    queryset = Page.objects.all()
    serializer_class = PageSerializer
    permission_classes = [IsAdminOrSuperAdmin]


# ────────────────────────────────────────────────
# Content ViewSets
# ────────────────────────────────────────────────

class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [AllowAny()]
        if self.action == 'create':
            return [IsAuthenticated()]
        return [IsAdminOrSuperAdmin()]

    def get_queryset(self):
        if self.request.user.is_authenticated and self.request.user.role in ['LAYERED_ADMIN', 'SUPER_ADMIN']:
            return Project.objects.all()
        return Project.objects.filter(approval_status='approved')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrSuperAdmin])
    def approve(self, request, pk=None):
        obj = self.get_object()
        obj.approval_status = 'approved'
        obj.save()
        return Response(ProjectSerializer(obj).data)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrSuperAdmin])
    def reject(self, request, pk=None):
        obj = self.get_object()
        obj.approval_status = 'rejected'
        obj.save()
        return Response(ProjectSerializer(obj).data)


# Similar pattern for Blog & Resource (omitted for brevity — same as Project)

class BlogViewSet(viewsets.ModelViewSet):
    queryset = Blog.objects.all()
    serializer_class = BlogSerializer

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [AllowAny()]
        if self.action == 'create':
            return [IsAuthenticated()]
        return [IsAdminOrSuperAdmin()]

    def get_queryset(self):
        if self.request.user.is_authenticated and self.request.user.role in ['LAYERED_ADMIN', 'SUPER_ADMIN']:
            return Blog.objects.all()
        return Blog.objects.filter(approval_status='approved')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrSuperAdmin])
    def approve(self, request, pk=None):
        obj = self.get_object()
        obj.approval_status = 'approved'
        obj.save()
        return Response(BlogSerializer(obj).data)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrSuperAdmin])
    def reject(self, request, pk=None):
        obj = self.get_object()
        obj.approval_status = 'rejected'
        obj.save()
        return Response(BlogSerializer(obj).data)


class ResourceViewSet(viewsets.ModelViewSet):
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [AllowAny()]
        if self.action == 'create':
            return [IsAuthenticated()]
        return [IsAdminOrSuperAdmin()]

    def get_queryset(self):
        if self.request.user.is_authenticated and self.request.user.role in ['LAYERED_ADMIN', 'SUPER_ADMIN']:
            return Resource.objects.all()
        return Resource.objects.filter(approval_status='approved')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrSuperAdmin])
    def approve(self, request, pk=None):
        obj = self.get_object()
        obj.approval_status = 'approved'
        obj.save()
        return Response(ResourceSerializer(obj).data)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrSuperAdmin])
    def reject(self, request, pk=None):
        obj = self.get_object()
        obj.approval_status = 'rejected'
        obj.save()
        return Response(ResourceSerializer(obj).data)


class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all()
    serializer_class = EventSerializer

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [AllowAny()]
        if self.action == 'create':
            return [IsAuthenticated()]
        return [IsAdminOrSuperAdmin()]

    def get_queryset(self):
        # Everyone sees all events (no approval for events yet)
        return Event.objects.all()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


# Admin-only content
class AlumniViewSet(viewsets.ModelViewSet):
    queryset = Alumni.objects.all()
    serializer_class = AlumniSerializer
    permission_classes = [IsAdminOrSuperAdmin]


class TeamMemberViewSet(viewsets.ModelViewSet):
    queryset = TeamMember.objects.all()
    serializer_class = TeamMemberSerializer
    permission_classes = [IsAdminOrSuperAdmin]


class SuccessStoryViewSet(viewsets.ModelViewSet):
    queryset = SuccessStory.objects.all()
    serializer_class = SuccessStorySerializer
    permission_classes = [IsAdminOrSuperAdmin]
# admins/views.py (add at the end)
# admins/views.py
# ... (other imports and views unchanged)

class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all()
    serializer_class = PostSerializer

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [AllowAny()]
        return [IsAdminOrSuperAdmin()]  # Restrict create/update/delete to admins (including create)

    def get_queryset(self):
        if self.request.user.is_authenticated and self.request.user.role in ['ADMIN', 'SUPER_ADMIN', 'LAYERED_ADMIN']:
            return Post.objects.all()
        # return Post.objects.filter(approval_status='approved')  # Remove this line if no approval_status
        return Post.objects.all()

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)  # Use 'author' (no created_by)

    # @action(detail=True, methods=['post'], permission_classes=[IsAdminOrSuperAdmin])
    # def approve(self, request, pk=None):
    #     obj = self.get_object()
    #     obj.approval_status = 'approved'
    #     obj.save()
    #     return Response(PostSerializer(obj).data)

    # @action(detail=True, methods=['post'], permission_classes=[IsAdminOrSuperAdmin])
    # def reject(self, request, pk=None):
    #     obj = self.get_object()
    #     obj.approval_status = 'rejected'
    #     obj.save()
    #     return Response(PostSerializer(obj).data)  # Fixed typo (was ResourceSerializer)


class FAQsViewSet(viewsets.ModelViewSet):
    queryset = FAQs.objects.all()
    serializer_class = FAQsSerializer
    permission_classes = [IsAdminOrSuperAdmin]