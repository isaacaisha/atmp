# /home/siisi/atmp/atmp_api/auth_views.py

from django.contrib.auth import authenticate, login as django_login, logout as django_logout
from django_otp import devices_for_user
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.reverse import reverse

from .auth_serializers import (
    EmptySerializer,
    RegisterSerializer,
    LoginSerializer,
    ProfileSerializer,
    LogoutSerializer,
)

from users.models import CustomUser


class AuthViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    Authentication & Profile API endpoints.

    Available routes:
    - GET    /atmp/api/auth/           → List all available auth endpoints.
    - GET    /atmp/api/auth/register/  → Get registration schema.
    - POST   /atmp/api/auth/register/  → Register a new user.
    - GET    /atmp/api/auth/login/     → Get login schema.
    - POST   /atmp/api/auth/login/     → Log in a user.
    - GET    /atmp/api/auth/logout/    → Get logout schema.
    - POST   /atmp/api/auth/logout/    → Log out the current user.
    - GET    /atmp/api/auth/profile/   → Get user profile or list all users (if superuser).
    - POST   /atmp/api/auth/profile/   → Update your own profile.
    """

    queryset = CustomUser.objects.all()
    serializer_class = EmptySerializer  # default fallback serializer

    def get_serializer_class(self):
        if self.action == 'register':
            return RegisterSerializer
        if self.action == 'login':
            return LoginSerializer
        if self.action == 'profile':
            return ProfileSerializer
        if self.action == 'logout':
            return LogoutSerializer
        return EmptySerializer

    def list(self, request, *args, **kwargs):
        """
        GET /atmp/api/auth/
        Return reverse links to all available auth-related endpoints.
        """
        return Response({
            'register': reverse('atmp_api:api:auth-register', request=request),
            'login':    reverse('atmp_api:api:auth-login',    request=request),
            'profile':  reverse('atmp_api:api:auth-profile',  request=request),
            'logout':   reverse('atmp_api:api:auth-logout',   request=request),
        })

    @action(detail=False, methods=['get', 'post'], url_path='register', permission_classes=[])
    def register(self, request):
        """
        GET  /register/ → Return registration schema (empty serializer).
        POST /register/ → Register a new user with email, password, name, and role.
        """
        if request.method == 'GET':
            return Response(self.get_serializer().data)
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        # Create user
        CustomUser.objects.create_user(
            email=data['email'],
            password=data['password1'],
            name=data['name'],
            role=data['role']
        )
        return Response({'detail': 'User created'}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get','post'], url_path='login', permission_classes=[])
    def login(self, request):
        """
        GET  /login/ → Return login schema.
        POST /login/ → 
            1) Validate email+password
            2) If user has no confirmed TOTPDevice → log in immediately.
            3) If user has confirmed TOTPDevice → require valid `otp_token` to complete login.
        """
        if request.method == 'GET':
            return Response(self.get_serializer().data)

        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        email = ser.validated_data['username']
        password = ser.validated_data['password']
        otp = ser.validated_data.get('otp_token')

        # Step 1: basic auth
        user = authenticate(request, email=email, password=password)
        if not user:
            return Response({'detail':'Invalid credentials'}, status=400)

        # Step 2: check for any confirmed TOTP devices
        confirmed = list(devices_for_user(user, confirmed=True))
        if not confirmed:
            # no 2FA set up → straight in
            django_login(request, user)
            return Response({'detail':'Logged in (no 2FA)'}, status=200)

        # Step 3: user *does* have TOTP devices → require OTP
        if not otp:
            return Response(
                {'detail':'OTP required', '2fa': True},
                status=400
            )

        # validate the provided token on *any* device
        valid = any(dev.verify_token(otp) for dev in confirmed)
        if not valid:
            return Response({'detail':'Invalid OTP token'}, status=400)

        # OTP is good → complete login
        django_login(request, user)
        return Response({'detail':'Logged in (2FA)'}, status=200)

    @action(detail=False, methods=["get", "post"], url_path="profile", permission_classes=[IsAuthenticated])
    def profile(self, request):
        """
        GET  /profile/
            → Return your own profile if you're a regular user.
            → Return all user profiles if you're a superuser.

        POST /profile/
            → Update your own profile. Field `has_2fa` is excluded from updates.
        """
        if request.method == "GET":
            if request.user.is_superuser:
                qs = CustomUser.objects.all()
                ser = ProfileSerializer(qs, many=True, context={"request": request})
            else:
                ser = ProfileSerializer(request.user, context={"request": request})
            return Response(ser.data, status=200)

        ser = ProfileSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={"request": request}
        )
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data, status=200)

    @action(detail=False, methods=['get', 'post'], url_path='logout', permission_classes=[])
    def logout(self, request):
        """
        GET  /logout/ → Return logout schema (empty serializer).
        POST /logout/
            → Validate credentials and log out the currently authenticated user.
            → Ensures the provided password matches the current session user.
        """
        if request.method == 'GET':
            serializer = LogoutSerializer()
            return Response(serializer.data)

        ser = LogoutSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        user_obj = ser.validated_data['user_obj']
        password = ser.validated_data['password']

        user = authenticate(request, email=user_obj.email, password=password)
        if user is None or user != request.user:
            return Response(
                {'detail': 'Invalid credentials or not logged in as that user.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        django_logout(request)
        return Response({'detail': 'Logged out'}, status=status.HTTP_200_OK)
