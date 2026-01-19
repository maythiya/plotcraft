from django.contrib.auth.models import AbstractUser
from django import forms
from .models import (
    CharacterRelationship, User, Profile, Novel, Chapter, Character, Location, Item,
    Scene, Timeline, TimelineEvent
)
from django.contrib.auth.forms import UserCreationForm
from django.forms import inlineformset_factory


# ==================== USER & PROFILE FORMS (from mysite) ====================

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
    #  รวม __init__ ให้เหลือตัวเดียว และรับทั้ง user และ project
    def __init__(self, user, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)

        # 1. กรอง Project ให้เหลือเฉพาะของ User นี้
        self.fields['project'].queryset = Novel.objects.filter(author=user)

        # 2. Logic กรอง Relationships (หัวใจสำคัญ)
        if self.instance.pk:
            # กรณี "แก้ไข" (Edit) -> เลือกตัวละครในเรื่องเดียวกัน แต่ตัดตัวเองออก
            queryset = Character.objects.filter(project=self.instance.project).exclude(id=self.instance.id)
        elif project:
            # กรณี "สร้างใหม่" (Create) โดยมี Project ระบุมา -> เลือกตัวละครในเรื่องนั้น
            queryset = Character.objects.filter(project=project)
        else:
            # กรณีอื่นๆ (Safety) -> ไม่แสดงอะไรเลย หรือจะแสดงทั้งหมดของ User ก็ได้ (เลือกเอา)
            # queryset = Character.objects.filter(created_by=user) # ถ้าอยากให้เห็นทั้งหมด
            queryset = Character.objects.none() # ปลอดภัยสุด

        self.fields['relationships'].queryset = queryset

        # ====================== ส่วนตกแต่ง WIDGETS & CSS ======================

        base_input = 'w-full px-4 py-2 bg-white border border-[#FAEBD7] rounded-lg focus:ring-2 focus:ring-[#DAA520] focus:border-[#DAA520] outline-none transition'
        textarea = base_input + ' min-h-[120px]'
        select = base_input

        # วนลูปตั้งค่า Default Style ให้ทุก Field ก่อน
        for field in self.fields:
            # ตรวจดูว่าเป็น Checkbox หรือไม่ (บางที Style นี้อาจไม่เหมาะกับ Checkbox)
            self.fields[field].widget.attrs.update({'class': base_input})

        # --- ปรับแต่งราย Field ---
        
        # Project
        self.fields['project'].widget.attrs.update({'class': select})
        
        # ข้อมูลพื้นฐาน
        self.fields['name'].widget.attrs.update({'placeholder': 'ชื่อตัวละคร (จำเป็น)'})
        self.fields['alias'].widget.attrs.update({'placeholder': 'ฉายา / ชื่อเรียก'})
        
        # วันเกิด (ต้องแก้ Type เป็น date)
        self.fields['birth_date'].widget = forms.DateInput(
            format='%Y-%m-%d',
            attrs={
                'type': 'date', 
                'class': base_input
            }
        )
        
        # Select Boxes
        self.fields['gender'].widget.attrs.update({'class': select})
        
        # ข้อมูลย่อย
        self.fields['species'].widget.attrs.update({'placeholder': 'มนุษย์ / เอลฟ์ / แวมไพร์ ฯลฯ'})
        self.fields['role'].widget.attrs.update({'placeholder': 'ตัวเอก / ตัวร้าย / ตัวประกอบ'})
        self.fields['status'].widget.attrs.update({'placeholder': 'มีชีวิต / เสียชีวิต / หายตัว'})

        # Textarea Guides (คำแนะนำ)
        guides = {
            'appearance': 'เช่น สีผม, สีตา, ส่วนสูง, รูปร่าง, การแต่งกาย, แผลเป็น หรือจุดเด่นที่เห็นได้ชัด...',
            'personality': 'นิสัยใจคอ, ความชอบ/ไม่ชอบ, Introvert/Extrovert, การตอบสนองต่อความเครียด, ท่าทางติดตัว...',
            'background': 'ภูมิหลัง, บ้านเกิด, ครอบครัว, เหตุการณ์สำคัญในวัยเด็ก หรือจุดเปลี่ยนของชีวิต...',
            'goals': 'สิ่งที่ตัวละครต้องการมากที่สุด (ทั้งระยะสั้นและระยะยาว), แรงจูงใจในการกระทำ...',
            'strengths': 'จุดแข็ง, ความสามารถพิเศษ, ข้อดีทางนิสัย, หรือสิ่งที่ถนัด...',
            'weaknesses': 'จุดอ่อน, ความกลัว, ข้อเสีย, โรคประจำตัว, หรือสิ่งที่ทำได้ไม่ดี...',
            'skills': 'ทักษะเฉพาะตัว เช่น การต่อสู้, การทำอาหาร, เวทมนตร์, การเจรจา...',
            'notes': 'เกร็ดเล็กเกร็ดน้อย, วันเกิด, ของกินที่ชอบ, ธีมสี, หรือข้อมูลอื่นๆ...'
        }

        # วนลูปใส่ class และ placeholder
        for field, text in guides.items():
            if field in self.fields:
                self.fields[field].widget.attrs.update({
                    'class': textarea,
                    'placeholder': text
                })

        # ความสัมพันธ์
        self.fields['relationships'].widget = forms.SelectMultiple(
            attrs={
                'class': select,
                'size': 6
            }
        )

        # รูป
        self.fields['portrait'].widget.attrs.update({
            'class': 'hidden',
            'accept': 'image/*',
            'id': 'id_portrait'
        })

    class Meta:
        model = Character
        fields = [
            'project', 'name', 'alias', 'age', 'birth_date', 'gender', 'species',
            'role', 'status', 'occupation',
            'appearance', 'personality', 'background',
            'goals', 'strengths', 'weaknesses', 'skills',
            'location', 'relationships', 'notes', 'portrait' 
        ]


class CharacterRelationshipForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        project = kwargs.pop('project', None)
        current_char = kwargs.pop('current_char', None)
        
        super().__init__(*args, **kwargs)
        
        # แต่งหน้าตา
        self.fields['to_character'].widget.attrs.update({'class': 'border rounded p-2 w-full'})
        self.fields['status'].widget.attrs.update({'class': 'border rounded p-2 w-full'})
        self.fields['note'].widget.attrs.update({'class': 'border rounded p-2 w-full'})

        # ================= LOGIC แบบ PYTHON ล้วน =================
        # เริ่มต้นให้ว่างไว้ก่อน (กันแสดงข้อมูลมั่ว)
        self.fields['to_character'].queryset = Character.objects.none()

        if user:
            # กรณี 1: ถ้ามี Project ส่งเข้ามา (จากการรีโหลดหน้า)
            if project:
                 self.fields['to_character'].queryset = Character.objects.filter(
                     created_by=user, 
                     project=project
                 )
            
            # กรณี 2: ถ้าเป็นการแก้ไข (Edit) ให้ดึงจาก Project ของตัวละครนั้น
            elif current_char and current_char.project:
                 self.fields['to_character'].queryset = Character.objects.filter(
                     created_by=user, 
                     project=current_char.project
                 )

            # ตัดตัวเองทิ้ง (ถ้ามี)
            if current_char and current_char.pk:
                self.fields['to_character'].queryset = self.fields['to_character'].queryset.exclude(pk=current_char.pk)
        # ========================================================

    class Meta:
        model = CharacterRelationship
        fields = ['to_character', 'status', 'note']

# FormSet (เหมือนเดิม ไม่ต้องแก้)
RelationshipFormSet = inlineformset_factory(
    Character, 
    CharacterRelationship,
    form=CharacterRelationshipForm,
    fk_name='from_character',
    extra=1,
    can_delete=True
)


class LocationForm(forms.ModelForm):
    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['project'].queryset = Novel.objects.filter(author=user)
        self.fields['residents'].queryset = Character.objects.filter(created_by=user)

        base = (
            "w-full px-4 py-2 bg-white border border-[#FAEBD7] "
            "rounded-lg focus:ring-2 focus:ring-[#DAA520] focus:border-[#DAA520] "
            "outline-none transition"
        )
        textarea = base + " min-h-[120px]"
        select = base

        self.fields['project'].widget.attrs.update({'class': select})
        self.fields['name'].widget.attrs.update({'class': base})
        self.fields['world_type'].widget.attrs.update({
            'class': base,
            'placeholder': 'Fantasy / Sci-Fi / Omegaverse'
        })

        self.fields['residents'].widget = forms.SelectMultiple(
            attrs={'class': select, 'size': 6}
        )

        guides = {
            'terrain': 'เช่น ภูเขา, ป่าทึบ, ทะเลทราย, ที่ราบลุ่ม, ลักษณะเด่นทางธรณีวิทยา...',
            'climate': 'สภาพอากาศ, ฤดูกาล, อุณหภูมิเฉลี่ย, ปรากฏการณ์ธรรมชาติพิเศษ...',
            'ecosystem': 'พืชพรรณ, สัตว์ป่า, สัตว์ประหลาด, ทรัพยากรธรรมชาติที่หาได้...',
            'history': 'ประวัติการก่อตั้ง, สงครามในอดีต, เหตุการณ์สำคัญ, หรือซากปรักหักพัง...',
            'myths': 'ตำนานพื้นบ้าน, เรื่องเล่าสยองขวัญ, ความเชื่อ, เทพเจ้าประจำถิ่น...',
            'politics': 'ระบบการปกครอง, ผู้นำ, กฎหมาย, ความขัดแย้งทางการเมือง, กลุ่มอำนาจ...',
            'economy': 'สินค้าส่งออก/นำเข้า, สกุลเงิน, อาชีพหลักของชาวบ้าน, ความยากจน/ร่ำรวย...',
            'culture': 'ประเพณี, เทศกาล, การแต่งกาย, อาหารการกิน, วิถีชีวิตประจำวัน...',
            'language': 'ภาษาที่ใช้, สำเนียงท้องถิ่น, คำแสลง, หรือภาษาโบราณ...'
        }

        # วนลูปใส่ class และ placeholder
        for field, text in guides.items():
            if field in self.fields:
                self.fields[field].widget.attrs.update({
                    'class': textarea,
                    'placeholder': text
                })

        # ใช้ Django field ตัวเดียว (เหมือน Character / Item)
        self.fields['map_image'].widget.attrs.update({
            'class': 'hidden',
            'accept': 'image/*',
        })

    class Meta:
        model = Location
        fields = [
            'project', 'name', 'world_type', 'map_image',
            'residents',
            'terrain', 'climate', 'ecosystem',
            'history', 'myths',
            'politics', 'economy', 'culture', 'language'
        ]


class ItemForm(forms.ModelForm):
    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['project'].queryset = Novel.objects.filter(author=user)
        self.fields['owner'].queryset = Character.objects.filter(created_by=user)
        self.fields['location'].queryset = Location.objects.filter(created_by=user)

        base_input = 'w-full px-4 py-2 bg-white border border-[#FAEBD7] rounded-lg focus:ring-2 focus:ring-[#DAA520] focus:border-[#DAA520] outline-none transition'
        textarea = base_input + ' min-h-[120px]'
        select = base_input

        # Basic
        self.fields['project'].widget.attrs.update({'class': select})
        self.fields['name'].widget.attrs.update({
            'class': base_input,
            'placeholder': 'ชื่อไอเทม เช่น ดาบแห่งรัตติกาล'
        })
        self.fields['category'].widget.attrs.update({
            'class': base_input,
            'placeholder': 'อาวุธ / เครื่องราง / วัตถุโบราณ'
        })

        # Textarea
        guides = {
            'appearance': 'เช่น วัสดุที่ใช้, สี, ขนาด, น้ำหนัก, แสงออร่า, สภาพความเก่า/ใหม่...',
            'abilities': 'ไอเทมนี้ทำอะไรได้บ้าง? (เช่น เพิ่มพลังโจมตี, รักษาบาดแผล, เปิดประตูมิติ)...',
            'limitations': 'ข้อจำกัด, เงื่อนไขการใช้, คูลดาวน์, ผลข้างเคียง, หรือสิ่งที่แพ้ทาง...',
            'history': 'ใครเป็นคนสร้าง?, ผู้ครอบครองคนก่อน, ตำนานที่เกี่ยวข้อง, วิธีการได้มา...'
        }

        # วนลูปใส่ class และ placeholder
        for field, text in guides.items():
            if field in self.fields:
                self.fields[field].widget.attrs.update({
                    'class': textarea,
                    'placeholder': text
                })

        # Relations
        self.fields['owner'].widget.attrs.update({
            'class': select
        })
        self.fields['location'].widget.attrs.update({
            'class': select
        })

        # Image
        self.fields['image'].widget.attrs.update({
            'class': 'hidden',
            'accept': 'image/*'
        })

    class Meta:
        model = Item
        fields = [
            'project', 'name', 'category', 'image',
            'appearance', 'abilities', 'limitations',
            'history', 'owner', 'location'
        ]


# ==================== SCENE FORM (from scenes) ====================

# forms.py

class SceneForm(forms.ModelForm):
    def __init__(self, user, *args, **kwargs):
        # รับค่า project_id ที่ส่งมาจาก View
        project_id = kwargs.pop('project_id', None)
        super().__init__(*args, **kwargs)

        # 1. ตั้งค่า QuerySet เริ่มต้น: เอาเฉพาะข้อมูลของ User คนนี้เท่านั้น
        self.fields['project'].queryset = Novel.objects.filter(author=user)
        self.fields['location'].queryset = Location.objects.filter(created_by=user)
        self.fields['pov_character'].queryset = Character.objects.filter(created_by=user)
        self.fields['characters'].queryset = Character.objects.filter(created_by=user)
        self.fields['items'].queryset = Item.objects.filter(created_by=user)

        # 2. เพิ่ม Event onchange ให้กับ Project Dropdown
        # เพื่อให้เมื่อเลือก Project แล้วหน้าเว็บรีโหลดส่งค่า project กลับมา
        self.fields['project'].widget.attrs.update({
            'onchange': "if(this.value) window.location.href='?project=' + this.value"
        })

        # 3. Logic หา Project ที่กำลังทำงานอยู่ เพื่อกรองตัวเลือกย่อย
        selected_project = None

        # กรณี A: มีการ Submit Form (POST) -> ดึงจาก data ที่ส่งมา
        if self.data and 'project' in self.data:
            try:
                project_id_post = int(self.data.get('project'))
                selected_project = Novel.objects.get(id=project_id_post)
            except (ValueError, TypeError, Novel.DoesNotExist):
                pass

        # กรณี B: สร้างใหม่ (Create) -> ดึง Project จาก URL (project_id)
        elif project_id:
            try:
                selected_project = Novel.objects.get(id=project_id, author=user)
                self.fields['project'].initial = selected_project
            except Novel.DoesNotExist:
                pass
        
        # กรณี C: กำลังแก้ไข (Edit) -> ดึง Project จากข้อมูลเดิมในฐานข้อมูล
        elif self.instance.pk and self.instance.project:
            selected_project = self.instance.project

        # 4. กรองตัวเลือกทั้งหมดให้เหลือแค่ใน Project นั้น
        if selected_project:
            self.fields['location'].queryset = self.fields['location'].queryset.filter(project=selected_project)
            self.fields['pov_character'].queryset = self.fields['pov_character'].queryset.filter(project=selected_project)
            self.fields['characters'].queryset = self.fields['characters'].queryset.filter(project=selected_project)
            self.fields['items'].queryset = self.fields['items'].queryset.filter(project=selected_project)
        
        # กรณี Safety: ถ้ายังไม่เลือก Project เลย -> ปิดการแสดงผลตัวเลือกย่อยไปก่อน
        elif self.instance.pk is None:
             self.fields['location'].queryset = Location.objects.none()
             self.fields['pov_character'].queryset = Character.objects.none()
             self.fields['characters'].queryset = Character.objects.none()
             self.fields['items'].queryset = Item.objects.none()

        # ====================== ส่วนตกแต่ง WIDGETS & CSS ======================
        base = 'w-full px-4 py-2 bg-white border border-[#FAEBD7] rounded-lg focus:ring-2 focus:ring-[#DAA520] outline-none transition'
        textarea = base + ' min-h-[120px]'
        select = base

        # Core
        # project widget อัปเดต class ทับ onchange ที่ใส่ไว้ข้างบน ต้องระวัง
        # ดังนั้น update ทีเดียว หรือ update แยกส่วน
        self.fields['project'].widget.attrs.update({'class': select}) 
        
        self.fields['title'].widget.attrs.update({
            'class': base,
            'placeholder': 'เช่น บทที่ 5: การเผชิญหน้า'
        })
        self.fields['order'].widget.attrs.update({'class': base})
        self.fields['status'].widget.attrs.update({'class': select})

        # World
        self.fields['location'].widget.attrs.update({'class': select})
        self.fields['pov_character'].widget.attrs.update({'class': select})

        self.fields['characters'].widget = forms.SelectMultiple(
            attrs={'class': select, 'size': 6}
        )
        self.fields['items'].widget = forms.SelectMultiple(
            attrs={'class': select, 'size': 6}
        )

        # Story beat
        for field in ['goal', 'conflict', 'outcome']:
            self.fields[field].widget.attrs.update({
                'class': textarea,
                'placeholder': self.fields[field].help_text
            })

        # Writing
        self.fields['content'].widget.attrs.update({
            'class': textarea + ' min-h-[300px]',
            'placeholder': 'เริ่มเขียนฉากตรงนี้...'
        })

    class Meta:
        model = Scene
        fields = [
            'project', 'title', 'order', 'status',
            'location', 'pov_character', 'characters', 'items',
            'goal', 'conflict', 'outcome',
            'content'
        ]


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
