from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from ..models import User
from ..serializers import RegisterSerializer, MeSerializer


class LoginView(TokenObtainPairView):
    """Simple JWT login. Deactivated users are rejected automatically."""
    permission_classes = [AllowAny]


class RegisterView(generics.CreateAPIView):
    """Public self-registration (always creates an EMPLOYEE). Off unless ALLOW_PUBLIC_REGISTRATION=True."""
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        if not getattr(settings, 'ALLOW_PUBLIC_REGISTRATION', False):
            return Response({'detail': 'Self-registration is disabled. Ask an administrator for an account.'}, status=403)
        return super().create(request, *args, **kwargs)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=MeSerializer)
    def get(self, request):
        return Response(MeSerializer(request.user).data)
