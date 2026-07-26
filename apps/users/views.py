"""Vues auth — délégation minimale, pas de logique métier."""
import json
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView, LogoutView
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.http import require_POST
from django.views.generic import CreateView

from apps.couples.services import CoupleService
from .forms import LoginForm, SignUpForm
from .models import User
from .services import UserService


class SignUpView(CreateView):
    model = User
    form_class = SignUpForm
    template_name = "users/signup.html"
    success_url = reverse_lazy("couples:dashboard")

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response


class UserLoginView(LoginView):
    form_class = LoginForm
    template_name = "users/login.html"


class UserLogoutView(View):
    """Déconnexion — accepte GET et redirige vers welcome."""
    def get(self, request):
        logout(request)
        return HttpResponseRedirect('/')


class OnboardingView(View):
    """Vue pour l'onboarding conversationnel."""
    
    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        """Affiche le template d'onboarding."""
        return self.render_onboarding(request)
    
    @method_decorator(csrf_protect)
    def post(self, request):
        """Traite les étapes de l'onboarding via AJAX."""
        try:
            data = json.loads(request.body)
            step = data.get('step')

            if step == 'user_profile':
                return self.handle_user_profile(request, data)
            elif step == 'couple_profile':
                return self.handle_couple_profile(request, data)
            elif step == 'join_room':
                return self.handle_join_room(request, data)
            else:
                return JsonResponse({'success': False, 'error': 'Étape invalide'}, status=400)
                
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Données invalides'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    def handle_user_profile(self, request, data):
        """Traite la création de l'utilisateur."""
        display_name = data.get('display_name', '')
        phone_number = data.get('phone_number', '')
        password = data.get('password', '')
        
        try:
            user = UserService.register_user_conversational(
                display_name=display_name,
                phone_number=phone_number,
                password=password,
            )
            UserService.login_user(request, user)
            
            return JsonResponse({'success': True})
        except ValueError as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    
    def handle_couple_profile(self, request, data):
        """Traite la création de la room avec le profil du couple."""
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Utilisateur non connecté'}, status=401)

        relationship_duration = data.get('relationship_duration', 'less_than_1_year')
        residence_continent = data.get('residence_continent', 'africa')
        is_long_distance = data.get('is_long_distance', False)

        try:
            couple = CoupleService.create_room(
                user=request.user,
                relationship_duration=relationship_duration,
                residence_continent=residence_continent,
                is_long_distance=is_long_distance,
            )

            return JsonResponse({
                'success': True,
                'redirect_url': reverse_lazy('couples:waiting', kwargs={'code': couple.room_code})
            })
        except ValueError as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

    def handle_join_room(self, request, data):
        """Traite le rejoindre d'une room existante avec un code."""
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Utilisateur non connecté'}, status=401)

        room_code = data.get('room_code', '').strip().upper()

        if not room_code:
            return JsonResponse({'success': False, 'error': 'Code d\'invitation requis'}, status=400)

        try:
            couple = CoupleService.join_room(
                user=request.user,
                room_code=room_code,
            )

            return JsonResponse({
                'success': True,
                'redirect_url': reverse_lazy('couples:waiting', kwargs={'code': couple.room_code})
            })
        except ValueError as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    
    def render_onboarding(self, request):
        """Rend le template d'onboarding."""
        from django.shortcuts import render
        return render(request, 'users/onboarding.html')
