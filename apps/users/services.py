from django.contrib.auth import login
from django.db import transaction

from apps.users.models import User


class UserService:
    """Service pour la gestion des utilisateurs."""

    @staticmethod
    @transaction.atomic
    def register_user_conversational(
        display_name: str,
        phone_number: str,
        password: str,
    ) -> User:
        """
        Crée un utilisateur de manière atomique à partir des données récoltées
        lors de l'onboarding conversationnel.
        
        Args:
            display_name: Prénom ou surnom de l'utilisateur
            phone_number: Numéro de téléphone de l'utilisateur (utilisé comme username)
            password: Mot de passe de l'utilisateur
            
        Returns:
            User: L'utilisateur créé
            
        Raises:
            ValueError: Si le numéro existe déjà ou si les données sont invalides
        """
        if not display_name or not display_name.strip():
            raise ValueError("Le prénom est requis")
        
        if not phone_number or not phone_number.strip():
            raise ValueError("Le numéro de téléphone est requis")
            
        if not password or len(password) < 8:
            raise ValueError("Le mot de passe doit contenir au moins 8 caractères")
        
        # Nettoyer le numéro de téléphone (enlever espaces, tirets, etc.)
        clean_phone = ''.join(c for c in phone_number if c.isdigit())
        
        # Vérifier si le numéro existe déjà
        if User.objects.filter(username=clean_phone).exists():
            raise ValueError("Ce numéro de téléphone est déjà utilisé")
        
        # Utiliser le numéro de téléphone comme username
        username = clean_phone
        
        # Créer l'utilisateur
        user = User.objects.create_user(
            username=username,
            password=password,
            display_name=display_name.strip(),
            email=None,  # Email optionnel
        )
        
        return user

    @staticmethod
    @transaction.atomic
    def login_user(request, user: User) -> None:
        """
        Connecte l'utilisateur.
        
        Args:
            request: La requête HTTP
            user: L'utilisateur à connecter
        """
        login(request, user)
