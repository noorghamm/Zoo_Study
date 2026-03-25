from django.db import models
from django.contrib.auth.models import User
from django.template.defaultfilters import slugify
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum

# ============================================================
# Game Mechanic Constants
# Adjust these after team discussion — all conversion logic
# reads from here so changes only need to happen in one place.
# ============================================================
COINS_PER_MINUTE = 10          # 1 minute of study = 10 coins
STREAK_MINIMUM_MINUTES = 15    # Must study at least 15 min to keep streak


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    currency = models.IntegerField(default=0)
    streak = models.IntegerField(default=0)
    last_study_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.user.username

    def add_currency(self, minutes):
        """Convert study minutes to coins and add to balance."""
        earned = minutes * COINS_PER_MINUTE
        self.currency += earned
        self.save()
        return earned

    def update_streak(self):
        """Update streak based on today's date vs last study date.
        Call this after each study session is logged.
        """
        today = timezone.now().date()

        if self.last_study_date is None:
            # First ever study session
            self.streak = 1
        elif self.last_study_date == today:
            # Already studied today — streak unchanged
            pass
        elif self.last_study_date == today - timedelta(days=1):
            # Studied yesterday — streak continues
            self.streak += 1
        else:
            # Missed a day — streak resets
            self.streak = 1

        self.last_study_date = today
        self.save()

    def buy_animal(self, animal):
        """Attempt to purchase an animal. Returns (success, message)."""
        if self.currency < animal.cost:
            deficit = animal.cost - self.currency
            return False, f"Not enough coins. You need {deficit} more."

        if UserZoo.objects.filter(user=self.user, animal=animal).exists():
            return False, f"You already own {animal.name}."

        self.currency -= animal.cost
        self.save()
        UserZoo.objects.create(user=self.user, animal=animal)
        return True, f"Welcome {animal.name} to your zoo!"

    def owns_animal(self, animal):
        """Check if this user already owns a specific animal."""
        return UserZoo.objects.filter(user=self.user, animal=animal).exists()

    def total_study_minutes(self):
        """Get total minutes studied across all sessions."""
        from django.db.models import Sum
        result = StudySession.objects.filter(user=self.user).aggregate(
            total=Sum('duration_minutes')
        )
        return result['total'] or 0

    def total_study_hours(self):
        """Get total hours studied, rounded to 1 decimal."""
        return round(self.total_study_minutes() / 60, 1)

    def zoo_animal_count(self):
        """Get the number of animals this user owns."""
        return UserZoo.objects.filter(user=self.user).count()

    def today_study_minutes(self):
        """Return total minutes studied today."""
        today = timezone.now().date()
        result = StudySession.objects.filter(user=self.user, date=today).aggregate(
            total=Sum('duration_minutes')
        )
        return result['total'] or 0

    def today_study_time_display(self):
        """Return today's study time in hours and minutes, e.g., '2h 15m'."""
        minutes = self.today_study_minutes()
        hours = minutes // 60
        mins = minutes % 60
        if hours > 0:
            return f"{hours}h {mins}m"
        return f"{mins}m"

    def weekly_study_minutes(self):
        """Return total minutes studied in the last 7 days (including today)."""
        today = timezone.now().date()
        week_ago = today - timedelta(days=6)  # last 7 days including today
        result = StudySession.objects.filter(
            user=self.user,
            date__gte=week_ago
        ).aggregate(total=Sum('duration_minutes'))
        return result['total'] or 0

    @property
    def weekly_study_display(self):
        """Return last 7 days of study in hours and minutes."""
        minutes = self.weekly_study_minutes()
        hours = minutes // 60
        mins = minutes % 60
        if hours > 0:
            return f"{hours}h {mins}m"
        return f"{mins}m"

    @property
    def daily_average_minutes(self):
        """Return average minutes studied per day (based on days with study sessions)."""
        # Count distinct days user has studied
        sessions = StudySession.objects.filter(user=self.user)
        if not sessions.exists():
            return 0

        total_minutes = sessions.aggregate(total=Sum('duration_minutes'))['total'] or 0
        days_with_sessions = sessions.values('date').distinct().count()
        return total_minutes // days_with_sessions  # integer division

    @property
    def daily_average_display(self):
        """Return daily average as hours and minutes."""
        minutes = self.daily_average_minutes
        hours = minutes // 60
        mins = minutes % 60
        if hours > 0:
            return f"{hours}h {mins}m"
        return f"{mins}m"


class Task(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=200)
    deadline = models.DateTimeField()
    completed = models.BooleanField(default=False)

    def __str__(self):
        return self.title

    @property
    def is_overdue(self):
        """Check if the deadline has passed and task is not completed."""
        return not self.completed and timezone.now() > self.deadline

    @property
    def time_remaining(self):
        """Return time remaining until deadline, or None if overdue."""
        if self.is_overdue:
            return None
        return self.deadline - timezone.now()

    @property
    def time_remaining_display(self):
        """Human-readable string for time remaining."""
        remaining = self.time_remaining
        if remaining is None:
            return "Overdue"

        days = remaining.days
        hours = remaining.seconds // 3600

        if days > 0:
            return f"{days}d {hours}h"
        elif hours > 0:
            minutes = (remaining.seconds % 3600) // 60
            return f"{hours}h {minutes}m"
        else:
            minutes = remaining.seconds // 60
            return f"{minutes}m"


class StudySession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='study_sessions')
    duration_minutes = models.IntegerField()
    date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.duration_minutes} mins on {self.date}"

    @property
    def coins_earned(self):
        """How many coins this session was worth."""
        return self.duration_minutes * COINS_PER_MINUTE

    @property
    def duration_display(self):
        """Human-readable duration string."""
        hours = self.duration_minutes // 60
        mins = self.duration_minutes % 60
        if hours > 0:
            return f"{hours}h {mins}m"
        return f"{mins}m"

    @staticmethod
    def log_session(user, duration_minutes):
        """Create a study session and handle all side effects:
        currency reward, streak update. Returns (session, coins_earned).
        """
        if duration_minutes <= 0:
            return None, 0

        session = StudySession.objects.create(
            user=user,
            duration_minutes=duration_minutes
        )

        profile = user.userprofile
        coins = profile.add_currency(duration_minutes)

        # Only update streak if studied enough
        if duration_minutes >= STREAK_MINIMUM_MINUTES:
            profile.update_streak()

        return session, coins


class Animal(models.Model):
    CATEGORY_CHOICES = [
        ('desert', 'Desert'),
        ('aquatic', 'Aquatic'),
        ('forest', 'Forest'),
        ('polar', 'Polar'),
    ]

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    cost = models.IntegerField()
    image = models.ImageField(upload_to='animals/', blank=True)

    class Meta:
        ordering = ['cost']

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def study_hours_required(self):
        """How many hours of study are needed to afford this animal."""
        minutes_needed = self.cost / COINS_PER_MINUTE
        return round(minutes_needed / 60, 1)


class UserZoo(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='zoo_animals')
    animal = models.ForeignKey(Animal, on_delete=models.CASCADE)
    date_acquired = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'animal')

    def __str__(self):
        return f"{self.user.username} owns {self.animal.name}"


class Resource(models.Model):
    TYPE_CHOICES = [
        ('note', 'Note'),
        ('resource', 'Resource'),
    ]

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='resources')
    title = models.CharField(max_length=200)
    content = models.TextField(blank=True)
    url = models.URLField(blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='note')

    def __str__(self):
        return self.title