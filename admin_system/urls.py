from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from admins.views import CustomUserViewSet, PageViewSet
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from admins.views import (
    ProjectViewSet, AlumniViewSet, TeamMemberViewSet,
    BlogViewSet, ResourceViewSet, EventViewSet, SuccessStoryViewSet,FAQsViewSet
)
from django.http import HttpResponse
from admins.views import LogoutView
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

router = DefaultRouter()
router.register(r'users', CustomUserViewSet)
router.register(r'pages', PageViewSet)
router.register(r'projects', ProjectViewSet)
router.register(r'alumni', AlumniViewSet)
router.register(r'team-members', TeamMemberViewSet)
router.register(r'blogs', BlogViewSet)
router.register(r'resources', ResourceViewSet)
router.register(r'events', EventViewSet)
router.register(r'success-stories', SuccessStoryViewSet)
router.register(r'faqs', FAQsViewSet)

urlpatterns = [
    path('', home, name='home'),
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/logout/', LogoutView.as_view(), name='logout'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)