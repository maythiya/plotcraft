from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import (
	User,
	Profile,
	Project,
	Novel,
	Chapter,
	Character,
	Location,
	Item,
	Scene,
	Timeline,
	TimelineEvent,
)


class ProfileInline(admin.StackedInline):
	model = Profile
	can_delete = False
	verbose_name_plural = 'profiles'


class UserAdmin(BaseUserAdmin):
	inlines = (ProfileInline,)
	list_display = ('username', 'email', 'display_name', 'is_staff', 'is_active')
	search_fields = ('username', 'email', 'display_name')


class ProjectAdmin(admin.ModelAdmin):
	list_display = ('name', 'owner', 'created_at')
	search_fields = ('name', 'owner__username')


class NovelAdmin(admin.ModelAdmin):
	list_display = ('title', 'author', 'category', 'rating', 'status', 'created_at')
	search_fields = ('title', 'author__username')
	list_filter = ('category', 'rating', 'status')


class ChapterAdmin(admin.ModelAdmin):
	list_display = ('title', 'novel', 'order', 'created_at')
	list_filter = ('novel',)


class CharacterAdmin(admin.ModelAdmin):
	list_display = ('name', 'alias', 'project', 'created_by')
	search_fields = ('name', 'alias')


class LocationAdmin(admin.ModelAdmin):
	list_display = ('name', 'project', 'created_by')
	search_fields = ('name',)


class ItemAdmin(admin.ModelAdmin):
	list_display = ('name', 'category', 'project', 'created_by')
	search_fields = ('name',)
	list_filter = ('category',)


class SceneAdmin(admin.ModelAdmin):
	list_display = ('title', 'project', 'order', 'status', 'created_by')
	list_filter = ('status', 'project')
	search_fields = ('title', 'content')


class TimelineAdmin(admin.ModelAdmin):
	list_display = ('title', 'related_project', 'created_by')
	search_fields = ('title',)


class TimelineEventAdmin(admin.ModelAdmin):
	list_display = ('time_label', 'title', 'timeline', 'order')
	list_filter = ('timeline',)
	search_fields = ('title', 'time_label')


# Register models
admin.site.register(User, UserAdmin)
admin.site.register(Profile)
admin.site.register(Project, ProjectAdmin)
admin.site.register(Novel, NovelAdmin)
admin.site.register(Chapter, ChapterAdmin)
admin.site.register(Character, CharacterAdmin)
admin.site.register(Location, LocationAdmin)
admin.site.register(Item, ItemAdmin)
admin.site.register(Scene, SceneAdmin)
admin.site.register(Timeline, TimelineAdmin)
admin.site.register(TimelineEvent, TimelineEventAdmin)

