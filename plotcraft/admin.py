from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import (
    User, Profile, Novel, Chapter, Character, Location, Item,
    Scene, Timeline, TimelineEvent, Bookmark
)

# ============================================
# 1. Utility
# ============================================
def show_image_preview(obj, field_name):
    if hasattr(obj, field_name):
        image_field = getattr(obj, field_name)
        if image_field:
            return format_html('<img src="{}" style="width: 50px; height:auto; border-radius: 5px;" />', image_field.url)
    return "-"

# ============================================
# 2. Inlines
# ============================================
class ChapterInline(admin.TabularInline):
    model = Chapter
    extra = 0
    # ตัด created_at ออกจาก Inline เพราะบางที Model อาจจะไม่มี หรือไม่ได้โชว์ใน Inline
    fields = ('order', 'title', 'is_draft', 'is_finished')
    ordering = ('order',)
    show_change_link = True

class TimelineEventInline(admin.StackedInline):
    model = TimelineEvent
    extra = 0
    fields = ('order', 'time_label', 'title', 'description', 'image')
    ordering = ('order',)

# ============================================
# 3. Model Admins
# ============================================

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('PlotCraft Custom Fields', {'fields': ('display_name', 'phone', 'birthdate', 'user_status', 'role')}),
    )
    list_display = ('username', 'email', 'display_name', 'role', 'user_status', 'is_staff', 'created_at')
    list_filter = ('role', 'user_status', 'is_staff', 'is_superuser', 'created_at')
    search_fields = ('username', 'email', 'display_name', 'phone')

@admin.register(Novel)
class NovelAdmin(admin.ModelAdmin):
    list_display = ('title_preview', 'author', 'category', 'rating', 'status', 'created_at', 'updated_at')
    list_filter = ('status', 'category', 'rating', 'created_at')
    search_fields = ('title', 'synopsis', 'author__username')
    inlines = [ChapterInline]
    readonly_fields = ('created_at', 'updated_at')
    
    def title_preview(self, obj):
        img_html = show_image_preview(obj, 'cover_image')
        return format_html('{} <b>{}</b>', img_html, obj.title)
    title_preview.short_description = "Novel"

@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    # Model Character ปกติจะมี created_by/created_at ถ้าไม่มีให้ลบออก
    list_display = ('name_preview', 'project', 'created_by', 'role', 'occupation', 'species', 'created_at')
    list_filter = ('project', 'gender', 'role', 'created_at')
    search_fields = ('name', 'alias', 'occupation')

    def name_preview(self, obj):
        img_html = show_image_preview(obj, 'portrait')
        return format_html('{} {}', img_html, obj.name)
    name_preview.short_description = "Character"

@admin.register(Scene)
class SceneAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'created_by', 'order', 'status', 'created_at')
    list_filter = ('project', 'status', 'created_at')
    search_fields = ('title', 'goal', 'conflict')
    ordering = ('project', 'order')

@admin.register(Timeline)
class TimelineAdmin(admin.ModelAdmin):
    # แก้ไข: ตัด created_at ออก (ตาม Error Log)
    list_display = ('title', 'related_project', 'description')
    list_filter = ('related_project',) 
    inlines = [TimelineEventInline]

# ============================================
# 4. New Registered Admins
# ============================================

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    # แก้ไข: เหลือเฉพาะฟิลด์พื้นฐานเพื่อป้องกัน Error
    list_display = ('name', 'project', 'created_by') 
    list_filter = ('project',)
    search_fields = ('name', 'description')

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    # แก้ไข: เหลือเฉพาะฟิลด์พื้นฐาน
    list_display = ('name', 'project', 'created_by')
    list_filter = ('project',)
    search_fields = ('name', 'description')

@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    # Bookmark มักจะมี created_at แต่ถ้า error ให้ลบออก
    list_display = ('user', 'content_object', 'content_type')
    # list_filter = ('created_at',) 

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    # แก้ไข: ตัด pen_name และ created_at ออก (ตาม Error Log)
    # Profile มักจะลิงก์กับ User โดยตรง ให้โชว์แค่ User ก็พอ
    list_display = ('user',) 
    search_fields = ('user__username', 'user__email')