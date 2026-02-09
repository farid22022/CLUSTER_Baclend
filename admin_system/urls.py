

# from django.contrib import admin
# from django.urls import path, include
# from django.conf import settings
# from django.conf.urls.static import static
# from django.http import HttpResponse

# from rest_framework.routers import DefaultRouter
# from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

# from admins.views import (
#     # Viewsets
#     CustomUserViewSet, PageViewSet, PostViewSet,
#     ProjectViewSet, AlumniViewSet, TeamMemberViewSet,
#     BlogViewSet, ResourceViewSet, EventViewSet,
#     SuccessStoryViewSet, FAQsViewSet,
#     RoleViewSet, CommitteeMembershipViewSet,
#     # Custom views
#     RegistrationView, VerifyOTPView, LogoutView, ImportTeamMembersView,
#     HandoverView,  # Add this import
# )


# def home(request):
#     return HttpResponse("""
#         <h1 style="text-align:center; margin-top:100px; color:#4f46e5;">
#             CLUSTER Admin Backend is running!
#         </h1>
#         <p style="text-align:center; font-size:1.2em;">
#             API is available at <a href="/api/">/api/</a><br>
#             Admin panel: <a href="/admin/">/admin/</a>
#         </p>
#     """)


# # ────────────────────────────────────────────────
# # DRF Router - registers all viewsets
# # ────────────────────────────────────────────────
# router = DefaultRouter()
# router.register(r'users', CustomUserViewSet, basename='user')
# router.register(r'pages', PageViewSet, basename='page')
# router.register(r'projects', ProjectViewSet, basename='project')
# router.register(r'alumni', AlumniViewSet, basename='alumni')
# router.register(r'team-members', TeamMemberViewSet, basename='team-member')
# router.register(r'blogs', BlogViewSet, basename='blog')
# router.register(r'resources', ResourceViewSet, basename='resource')
# router.register(r'events', EventViewSet, basename='event')
# router.register(r'success-stories', SuccessStoryViewSet, basename='success-story')
# router.register(r'faqs', FAQsViewSet, basename='faq')
# router.register(r'posts', PostViewSet, basename='post')
# router.register(r'roles', RoleViewSet, basename='role')
# router.register(r'memberships', CommitteeMembershipViewSet, basename='membership')  # Add this line


# # ────────────────────────────────────────────────
# # Main URL patterns
# # ────────────────────────────────────────────────
# urlpatterns = [
#     # Home page
#     path('', home, name='home'),

#     # Django admin
#     path('admin/', admin.site.urls),

#     # API root + all router-registered viewsets (/api/users/, /api/roles/, etc.)
#     path('api/', include(router.urls)),

#     # Custom non-router endpoints
#     path('api/team-members/import/', ImportTeamMembersView.as_view(), name='import-team'),
#     path('api/handover/', HandoverView.as_view(), name='handover'),  # Add this line

#     # Custom authentication endpoints
#     path('api/auth/register/', RegistrationView.as_view(), name='register'),
#     path('api/auth/verify-otp/', VerifyOTPView.as_view(), name='verify_otp'),

#     # JWT authentication
#     path('api/auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
#     path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
#     path('api/auth/logout/', LogoutView.as_view(), name='logout'),
# ]

# # Serve media files in development
# if settings.DEBUG:
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse

from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from admins.views import (
    # Viewsets
    CustomUserViewSet, PageViewSet, PostViewSet,
    ProjectViewSet, AlumniViewSet, TeamMemberViewSet,
    BlogViewSet, ResourceViewSet, EventViewSet,
    SuccessStoryViewSet, FAQsViewSet,
    RoleViewSet, CommitteeMembershipViewSet,
    # Custom views
    RegistrationView, VerifyOTPView, LogoutView, ImportTeamMembersView,
    HandoverView,
)


def home(request):
    return HttpResponse("""
        <h1 style="text-align:center; margin-top:100px; color:#4f46e5;">
            CLUSTER Admin Backend is running!
        </h1>
        <p style="text-align:center; font-size:1.2em;">
            API is available at <a href="/api/">/api/</a><br>
            Admin panel: <a href="/admin/">/admin/</a>
        </p>
    """)


# ────────────────────────────────────────────────
# DRF Router - registers all viewsets
# ────────────────────────────────────────────────
router = DefaultRouter()
router.register(r'users', CustomUserViewSet, basename='user')
router.register(r'pages', PageViewSet, basename='page')
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'alumni', AlumniViewSet, basename='alumni')
router.register(r'team-members', TeamMemberViewSet, basename='team-member')
router.register(r'blogs', BlogViewSet, basename='blog')
router.register(r'resources', ResourceViewSet, basename='resource')
router.register(r'events', EventViewSet, basename='event')
router.register(r'success-stories', SuccessStoryViewSet, basename='success-story')
router.register(r'faqs', FAQsViewSet, basename='faq')
router.register(r'posts', PostViewSet, basename='post')  # Make sure this is included
router.register(r'roles', RoleViewSet, basename='role')
router.register(r'memberships', CommitteeMembershipViewSet, basename='membership')


# ────────────────────────────────────────────────
# Main URL patterns
# ────────────────────────────────────────────────
urlpatterns = [
    # Home page
    path('', home, name='home'),

    # Django admin
    path('admin/', admin.site.urls),

    # API root + all router-registered viewsets (/api/users/, /api/roles/, etc.)
    path('api/', include(router.urls)),

    # Custom non-router endpoints
    path('api/team-members/import/', ImportTeamMembersView.as_view(), name='import-team'),
    path('api/handover/', HandoverView.as_view(), name='handover'),

    # Custom authentication endpoints
    path('api/auth/register/', RegistrationView.as_view(), name='register'),
    path('api/auth/verify-otp/', VerifyOTPView.as_view(), name='verify_otp'),

    # JWT authentication
    path('api/auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/logout/', LogoutView.as_view(), name='logout'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)