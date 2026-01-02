from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from .serializers import UserSerializer

User = get_user_model()

class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_staff

class AdminUserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        user = self.get_object()
        user.is_approved = True
        user.save()
        
        # Ensure wallet exists
        from wallet.models import Wallet
        Wallet.objects.get_or_create(user=user)
        
        return Response({'message': 'User approved successfully'})
    
    @action(detail=True, methods=['post'])
    def toggle_status(self, request, pk=None):
        user = self.get_object()
        user.is_active = not user.is_active
        user.save()
        return Response({'message': f'User {"activated" if user.is_active else "deactivated"}'})

    # Override destroy to just deactivate
    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()

# Admin Password Verification
from rest_framework import views
from django.contrib.auth import authenticate

class VerifyAdminPasswordView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        password = request.data.get('password')
        
        if not password:
            return Response({'error': 'Password is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if user is admin
        if not (request.user.is_staff or request.user.is_superuser):
            return Response({'error': 'Access denied. Admin privileges required.'}, status=status.HTTP_403_FORBIDDEN)
        
        # Verify password
        user = authenticate(username=request.user.email, password=password)
        
        if user is None:
            return Response({'error': 'Invalid password'}, status=status.HTTP_401_UNAUTHORIZED)
        
        return Response({
            'message': 'Password verified successfully',
            'is_admin': True
        }, status=status.HTTP_200_OK)
