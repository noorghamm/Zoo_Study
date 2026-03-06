from django.contrib import admin
from zoo_app.models import UserProfile, Task, StudySession, Animal, UserZoo, Resource


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'currency', 'streak', 'last_study_date', 'zoo_animal_count')
    search_fields = ('user__username',)
    list_filter = ('streak',)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'deadline', 'completed', 'is_overdue')
    search_fields = ('title', 'user__username')
    list_filter = ('completed', 'deadline')
    list_editable = ('completed',)


@admin.register(StudySession)
class StudySessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'duration_minutes', 'coins_earned', 'date')
    search_fields = ('user__username',)
    list_filter = ('date',)


@admin.register(Animal)
class AnimalAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'cost', 'study_hours_required')
    search_fields = ('name',)
    list_filter = ('category',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(UserZoo)
class UserZooAdmin(admin.ModelAdmin):
    list_display = ('user', 'animal', 'date_acquired')
    search_fields = ('user__username', 'animal__name')
    list_filter = ('animal__category', 'date_acquired')


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ('title', 'task', 'type', 'created_date')
    search_fields = ('title', 'task__title')
    list_filter = ('type', 'created_date')