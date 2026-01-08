from django.contrib.auth.models import AbstractUser
from django import forms
from .models import (
    User, Profile, Novel, Chapter, Character, Location, Item,
    Scene, Timeline, TimelineEvent
)
from django.contrib.auth.forms import UserCreationForm


# ==================== USER & PROFILE FORMS (from myapp) ====================

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone = forms.CharField(required=False)
    birthdate = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + (
            "username", "email", "birthdate", "phone", "password1", "password2",
        )


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['display_name', 'email', 'phone']

    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        self.fields['display_name'].widget.attrs.update({
            'class': 'w-full px-4 py-2 bg-white border border-gray-200 rounded-lg focus:ring-2 focus:ring-[#DAA520] focus:border-[#DAA520] outline-none transition',
            'placeholder': 'ชื่อเล่น / นามแฝง'
        })
        self.fields['email'].widget.attrs.update({
            'class': 'w-full px-4 py-2 bg-white border border-gray-200 rounded-lg focus:ring-2 focus:ring-[#DAA520] focus:border-[#DAA520] outline-none transition',
        })
        self.fields['phone'].widget.attrs.update({
            'class': 'w-full px-4 py-2 bg-white border border-gray-200 rounded-lg focus:ring-2 focus:ring-[#DAA520] focus:border-[#DAA520] outline-none transition',
        })


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['image', 'bio']

    def __init__(self, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)
        self.fields['bio'].widget.attrs.update({
            'class': 'w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-[#DAA520]',
            'rows': 3,
            'placeholder': 'แนะนำตัวสั้นๆ...'
        })
        self.fields['image'].widget.attrs.update({
            'class': 'hidden',
            'id': 'id_image',
            'accept': 'image/*'
        })


# ==================== NOVEL & CHAPTER FORMS (from notes) ====================

class NovelForm(forms.ModelForm):
    class Meta:
        model = Novel
        fields = ['title', 'synopsis', 'category', 'rating', 'status', 'cover_image']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'w-full p-3 border rounded-lg focus:ring-[#DAA520] focus:border-[#DAA520]', 'placeholder': 'ชื่อเรื่อง...'}),
            'synopsis': forms.Textarea(attrs={'class': 'w-full p-3 border rounded-lg focus:ring-[#DAA520] focus:border-[#DAA520]', 'rows': 5, 'placeholder': 'เรื่องย่อ...'}),
            'category': forms.Select(attrs={'class': 'w-full p-3 border rounded-lg'}),
            'rating': forms.Select(attrs={'class': 'w-full p-3 border rounded-lg'}),
            'status': forms.Select(attrs={'class': 'w-full p-3 border rounded-lg'}),
            'cover_image': forms.FileInput(attrs={'class': 'w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:bg-[#DAA520]/10 file:text-[#DAA520] hover:file:bg-[#DAA520]/20'}),
        }


class ChapterForm(forms.ModelForm):
    class Meta:
        model = Chapter
        fields = ['title', 'order', 'content']


# ==================== CHARACTER, LOCATION, ITEM FORMS (from worldbuilding) ====================

class CharacterForm(forms.ModelForm):
    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['project'].queryset = Novel.objects.filter(author=user)

    class Meta:
        model = Character
        fields = ['project', 'name', 'alias', 'age', 'birth_date', 'gender', 'species', 
                  'role', 'status', 'occupation', 'height', 'weight', 'appearance',
                  'personality', 'background', 'goals', 'strengths', 'weaknesses',
                  'skills', 'location', 'relationships', 'notes', 'portrait']


class LocationForm(forms.ModelForm):
    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['project'].queryset = Novel.objects.filter(author=user)
        self.fields['residents'].queryset = Character.objects.filter(created_by=user)

    class Meta:
        model = Location
        fields = ['project', 'name', 'world_type', 'map_image', 'residents',
                  'terrain', 'climate', 'ecosystem', 'history', 'myths',
                  'politics', 'economy', 'culture', 'language']


class ItemForm(forms.ModelForm):
    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['project'].queryset = Novel.objects.filter(author=user)
        self.fields['owner'].queryset = Character.objects.filter(created_by=user)
        self.fields['location'].queryset = Location.objects.filter(created_by=user)

    class Meta:
        model = Item
        fields = ['project', 'name', 'category', 'image', 'abilities', 'limitations',
                  'appearance', 'history', 'owner', 'location']


# ==================== SCENE FORM (from scenes) ====================

class SceneForm(forms.ModelForm):
    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['project'].queryset = Novel.objects.filter(author=user)
        self.fields['pov_character'].queryset = Character.objects.filter(created_by=user)
        self.fields['location'].queryset = Location.objects.filter(created_by=user)
        self.fields['characters'].queryset = Character.objects.filter(created_by=user)
        self.fields['items'].queryset = Item.objects.filter(created_by=user)

    class Meta:
        model = Scene
        fields = ['project', 'title', 'order', 'status', 'pov_character', 'location',
                  'characters', 'items', 'goal', 'conflict', 'outcome', 'content']


# ==================== TIMELINE FORMS (from timeline) ====================

class TimelineForm(forms.ModelForm):
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['related_project'].queryset = Novel.objects.filter(author=user)

    class Meta:
        model = Timeline
        fields = ['title', 'description', 'related_project']


class EventForm(forms.ModelForm):
    def __init__(self, *args, user=None, timeline=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['related_scene'].queryset = Scene.objects.filter(created_by=user)
            self.fields['characters'].queryset = Character.objects.filter(created_by=user)

    class Meta:
        model = TimelineEvent
        fields = ['time_label', 'order', 'title', 'description', 'image',
                  'related_scene', 'characters']
