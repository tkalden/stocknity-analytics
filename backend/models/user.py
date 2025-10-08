"""
User Model for Stocknity Platform

This module defines the User model with methods for managing user profiles,
experience levels, and graduation eligibility from beginner to advanced mode.
"""

from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import UUID


@dataclass
class User:
    """
    Represents a user in the Stocknity platform.
    
    This model corresponds to the 'users' table in Supabase and includes
    methods for checking advanced mode access and graduation eligibility.
    
    Attributes:
        id: Unique user identifier (UUID)
        email: User's email address
        name: User's full name
        password_hash: Hashed password (stored in Supabase)
        experience_level: Investment experience ('beginner', 'intermediate', 'advanced')
        selected_guru: Preferred investment guru ('buffett', 'lynch', 'graham', 'dalio')
        investment_goal: Primary goal ('retirement', 'wealth', 'income')
        risk_tolerance: Risk preference ('low', 'medium', 'high')
        age: User's age (18-120)
        investment_timeline: Investment timeline in years
        learning_progress: Progress through educational content (0-100)
        onboarding_completed: Whether user has completed onboarding
        preferred_mode: UI mode preference ('beginner' or 'advanced')
        created_at: Account creation timestamp
        updated_at: Last update timestamp
    """
    
    id: UUID
    email: str
    name: str
    password_hash: str
    experience_level: str = 'beginner'
    selected_guru: Optional[str] = None
    investment_goal: Optional[str] = None
    risk_tolerance: str = 'medium'
    age: Optional[int] = None
    investment_timeline: Optional[int] = None
    learning_progress: int = 0
    onboarding_completed: bool = False
    preferred_mode: str = 'beginner'
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @classmethod
    def from_supabase_dict(cls, data: Dict[str, Any]) -> 'User':
        """
        Create a User instance from a Supabase response dictionary.
        
        Args:
            data: Dictionary from Supabase query result
            
        Returns:
            User instance with all fields populated
            
        Example:
            >>> supabase_response = supabase.table('users').select('*').eq('id', user_id).execute()
            >>> user = User.from_supabase_dict(supabase_response.data[0])
        """
        # Convert string UUID to UUID object if needed
        user_id = data.get('id')
        if isinstance(user_id, str):
            user_id = UUID(user_id)
        
        # Parse datetime strings if they're strings
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        
        updated_at = data.get('updated_at')
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
        
        return cls(
            id=user_id,
            email=data.get('email', ''),
            name=data.get('name', ''),
            password_hash=data.get('password_hash', ''),
            experience_level=data.get('experience_level', 'beginner'),
            selected_guru=data.get('selected_guru'),
            investment_goal=data.get('investment_goal'),
            risk_tolerance=data.get('risk_tolerance', 'medium'),
            age=data.get('age'),
            investment_timeline=data.get('investment_timeline'),
            learning_progress=data.get('learning_progress', 0),
            onboarding_completed=data.get('onboarding_completed', False),
            preferred_mode=data.get('preferred_mode', 'beginner'),
            created_at=created_at or datetime.now(timezone.utc),
            updated_at=updated_at or datetime.now(timezone.utc)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert User instance to a dictionary.
        
        Returns:
            Dictionary representation of the user with serialized UUID and datetime
            
        Example:
            >>> user.to_dict()
            {'id': 'abc123...', 'email': 'user@example.com', ...}
        """
        user_dict = asdict(self)
        
        # Convert UUID to string for JSON serialization
        user_dict['id'] = str(self.id)
        
        # Convert datetime to ISO format strings
        user_dict['created_at'] = self.created_at.isoformat()
        user_dict['updated_at'] = self.updated_at.isoformat()
        
        return user_dict
    
    def can_access_advanced(self) -> bool:
        """
        Check if user can access advanced mode features.
        
        Users can access advanced mode if their experience level is
        'intermediate' or 'advanced' (i.e., not 'beginner').
        
        Returns:
            True if user can access advanced features, False otherwise
            
        Example:
            >>> user = User(...)
            >>> if user.can_access_advanced():
            ...     # Show advanced portfolio optimization
        """
        return self.experience_level != 'beginner'
    
    def calculate_graduation_eligibility(
        self, 
        portfolio_count: int = 0
    ) -> Dict[str, Any]:
        """
        Calculate if user is eligible to graduate from beginner to advanced mode.
        
        Graduation criteria:
        1. Learning progress >= 70%
        2. At least 3 portfolios created
        3. Account age >= 30 days
        
        Args:
            portfolio_count: Number of portfolios user has created
            
        Returns:
            Dictionary with eligibility status and progress metrics:
            {
                'eligible': bool,
                'progress': {
                    'learning': int (0-100),
                    'portfolios': int,
                    'days': int
                },
                'requirements_met': {
                    'learning': bool,
                    'portfolios': bool,
                    'account_age': bool
                }
            }
            
        Example:
            >>> # In your route, fetch portfolio count from Supabase
            >>> portfolios = supabase.table('portfolios').select('id').eq('user_id', user.id).execute()
            >>> eligibility = user.calculate_graduation_eligibility(len(portfolios.data))
            >>> if eligibility['eligible']:
            ...     # Show "Graduate to Advanced" button
        """
        # Calculate account age in days
        now = datetime.now(timezone.utc)
        account_age_days = (now - self.created_at).days
        
        # Check each requirement
        learning_met = self.learning_progress >= 70
        portfolios_met = portfolio_count >= 3
        account_age_met = account_age_days >= 30
        
        # User is eligible if ALL criteria are met
        eligible = learning_met and portfolios_met and account_age_met
        
        return {
            'eligible': eligible,
            'progress': {
                'learning': self.learning_progress,
                'portfolios': portfolio_count,
                'days': account_age_days
            },
            'requirements_met': {
                'learning': learning_met,
                'portfolios': portfolios_met,
                'account_age': account_age_met
            }
        }
    
    def __repr__(self) -> str:
        """String representation of User for debugging."""
        return (
            f"User(id={self.id}, email='{self.email}', "
            f"experience_level='{self.experience_level}', "
            f"preferred_mode='{self.preferred_mode}')"
        )

