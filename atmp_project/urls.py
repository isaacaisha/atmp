# /home/siisi/atmp/atmp_project/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.views.generic import RedirectView
from two_factor.urls import urlpatterns as tf_urls
from django.conf.urls.static import static

urlpatterns = [
    # 1) Root URL (“/”) → redirect to the dashboard URL by its name
    path(
        '',
        RedirectView.as_view(pattern_name='atmp_app:dashboard', permanent=False),
        name='root-redirect'
    ),

    # 2) Admin site
    path('admin/', admin.site.urls),

    # 3) Built‑in auth views (login, logout, password reset at /accounts/…)
    path('accounts/', include(('django.contrib.auth.urls', 'accounts'), namespace='accounts')),
    # 2FA default URLs (login, setup, backup tokens, QR, etc.)
    #path('account/', include('two_factor.urls', namespace='two_factor')),
    path('', include(tf_urls)),  # Include 2FA URLs

    # 4) Your custom user URLs (register, etc.); still lives under /register/, /login/, etc.
    path('users/', include('users.urls', namespace='users')),

    # 5) Dashboard pages under /dashboard/
    path('dashboard/', include('dashboard.urls', namespace='dashboard')),

    # 6) ATMP API
    path('api/atmp/', include(('atmp_app.urls','atmp_app'), namespace='atmp_app')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
