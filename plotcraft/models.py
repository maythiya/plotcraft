from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


# ==================== USER & PROFILE (from myapp) ====================
class User(AbstractUser):
    phone = models.CharField(max_length=20, blank=True, null=True)
    birthdate = models.DateField(blank=True, null=True)
    user_status = models.CharField(max_length=50, blank=True, null=True)
    role = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    display_name = models.CharField(max_length=50, blank=True, null=True, verbose_name="ชื่อที่ใช้แสดง")
    
    groups = models.ManyToManyField(
        Group,
        related_name='plotcraft_user_set',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups'
    )

    user_permissions = models.ManyToManyField(
        Permission,
        related_name='plotcraft_user_set_permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions'
    )


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    image = models.ImageField(default='default.jpg', upload_to='profile_pics', blank=True, null=True)
    bio = models.TextField(default='', blank=True)

    def __str__(self):
        return f'{self.user.username} Profile'


# Signal: Auto-create Profile when User is created
@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    if not hasattr(instance, 'profile'):
        Profile.objects.create(user=instance)
    instance.profile.save()


class Project(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='projects')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# ==================== NOVEL & CHAPTER (from notes) ====================
class Novel(models.Model):
    CATEGORY_CHOICES = [
        ('FANTASY', 'แฟนตาซี (Fantasy)'),
        ('BL', 'วาย (Boy Love)'),
        ('GL', 'ยูริ (Girl Love)'),
        ('ROMANCE', 'รักโรแมนติก'),
        ('SCIFI', 'ไซไฟ/อนาคต'),
        ('ACTION', 'แอคชั่น/กำลังภายใน'),
        ('HORROR', 'สยองขวัญ/ลึกลับ'),
        ('FANFIC', 'แฟนฟิคชั่น'),
        ('OTHER', 'อื่นๆ'),
    ]

    RATING_CHOICES = [
        ('G', 'ทั่วไป (General)'),
        ('PG', 'PG-13 (13+)'),
        ('R18', 'NC-18 (18+)'),
        ('R20', 'ฉ20 (20+)'),
    ]
    
    STATUS_CHOICES = [
        ('ONGOING', 'ยังไม่จบ'),
        ('COMPLETED', 'จบแล้ว'),
    ]

    title = models.CharField(max_length=200, verbose_name="ชื่อเรื่อง")
    synopsis = models.TextField(blank=True, verbose_name="คำโปรย/เรื่องย่อ")
    cover_image = models.ImageField(upload_to='novel_covers/', blank=True, null=True, verbose_name="รูปปก")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='OTHER', verbose_name="หมวดหมู่")
    rating = models.CharField(max_length=5, choices=RATING_CHOICES, default='G', verbose_name="ระดับเนื้อหา")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ONGOING', verbose_name="สถานะเรื่อง")
    
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='novels')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class Chapter(models.Model):
    novel = models.ForeignKey(Novel, on_delete=models.CASCADE, related_name='chapters')
    title = models.CharField(max_length=200, verbose_name="ชื่อตอน")
    content = models.TextField(blank=True, verbose_name="เนื้อหา")
    order = models.IntegerField(default=1, verbose_name="ลำดับตอน")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    is_draft = models.BooleanField(default=True, verbose_name="ฉบับร่าง (ไม่ส่งออก)")
    is_finished = models.BooleanField(default=False, verbose_name="เสร็จสมบูรณ์ (พร้อมส่งออก)")

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return f"{self.novel.title} - {self.title}"


# ==================== WORLDBUILDING (Character, Location, Item) ====================
class Character(models.Model):
    project = models.ForeignKey(Novel, on_delete=models.CASCADE, related_name='characters', null=True, blank=True)

    # Basic identity
    name = models.CharField(max_length=200)
    alias = models.CharField(max_length=200, blank=True)

    # Demographics
    age = models.IntegerField(null=True, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    GENDER_CHOICES = [
        ('M', 'ชาย'),
        ('F', 'หญิง'),
        ('O', 'อื่นๆ'),
    ]
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    species = models.CharField(max_length=200, blank=True)
    role = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=100, blank=True)

    # Physical
    occupation = models.CharField(max_length=200, blank=True)
    height = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    weight = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    appearance = models.TextField(blank=True)

    # Personality & background
    personality = models.TextField(blank=True)
    background = models.TextField(blank=True)
    goals = models.TextField(blank=True)

    # Skills/stats
    strengths = models.TextField(blank=True)
    weaknesses = models.TextField(blank=True)
    skills = models.TextField(blank=True)

    # Location & relationships
    location = models.ForeignKey('Location', null=True, blank=True, on_delete=models.CASCADE)
    relationships = models.ManyToManyField('self', blank=True, symmetrical=False, related_name='related_to')

    # Extra
    notes = models.TextField(blank=True)
    portrait = models.ImageField(upload_to='portraits/', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='created_characters'
    )

    def __str__(self):
        return self.name


class Location(models.Model):
    project = models.ForeignKey(Novel, on_delete=models.SET_NULL, null=True, blank=True, related_name='locations')
    
    # ข้อมูลพื้นฐาน
    name = models.CharField(max_length=200)
    world_type = models.CharField(max_length=100, blank=True, help_text="Ex: Fantasy, Sci-Fi, Omegaverse")
    map_image = models.ImageField(upload_to='location_maps/', null=True, blank=True)
    
    # ความสัมพันธ์
    residents = models.ManyToManyField(Character, blank=True, related_name='resides_in')
    
    # ภูมิประเทศ
    terrain = models.TextField(blank=True, help_text="ลักษณะภูมิประเทศ")
    climate = models.TextField(blank=True, help_text="สภาพอากาศ")
    ecosystem = models.TextField(blank=True, help_text="ระบบนิเวศ")
    
    # ประวัติศาสตร์
    history = models.TextField(blank=True, help_text="ประวัติศาสตร์ความเป็นมา")
    myths = models.TextField(blank=True, help_text="ตำนานและเรื่องเล่า")
    
    # สังคม
    politics = models.TextField(blank=True, help_text="การปกครอง")
    economy = models.TextField(blank=True, help_text="ระบบเศรษฐกิจ")
    culture = models.TextField(blank=True, help_text="วัฒนธรรม ความเชื่อ ศาสนา")
    language = models.TextField(blank=True, help_text="ภาษาที่ใช้")
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Item(models.Model):
    CATEGORY_CHOICES = [
        ('weapon', 'Weapon (อาวุธ)'),
        ('apparel', 'Apparel/Clothing (เครื่องแต่งกาย)'),
        ('item', 'Item/Consumable (ไอเทม/ยา)'),
        ('key_item', 'Key Item/Artifact (วัตถุสำคัญ/อาร์ติแฟกต์)'),
        ('technology', 'Technology (เทคโนโลยี)'),
        ('vehicle', 'Vehicle (ยานพาหนะ)'),
        ('other', 'Other (อื่นๆ)'),
    ]

    project = models.ForeignKey(Novel, on_delete=models.SET_NULL, null=True, blank=True, related_name='items')
    
    # Basic Info
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='item')
    image = models.ImageField(upload_to='items/', null=True, blank=True)
    
    # Mechanics
    abilities = models.TextField(blank=True, help_text="ความสามารถพิเศษ หรือผลของไอเทม")
    limitations = models.TextField(blank=True, help_text="เงื่อนไข ข้อจำกัด หรือผลข้างเคียง")
    
    # Lore & Description
    appearance = models.TextField(blank=True, help_text="ลักษณะภายนอก วัสดุ สี")
    history = models.TextField(blank=True, help_text="ประวัติความเป็นมา ตำนาน")
    
    # Connections
    owner = models.ForeignKey(Character, on_delete=models.SET_NULL, null=True, blank=True, related_name='inventory', help_text="ผู้ครอบครองปัจจุบัน")
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True, related_name='items', help_text="สถานที่ที่เก็บซ่อนอยู่ (ถ้าไม่มีเจ้าของ)")

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


# ==================== SCENE (from scenes) ====================
class Scene(models.Model):
    STATUS_CHOICES = [
        ('idea', 'Idea (ไอเดียร่าง)'),
        ('draft', 'Drafting (กำลังเขียน)'),
        ('finished', 'Finished (เสร็จสมบูรณ์)'),
    ]

    # 1. ความเชื่อมโยงหลัก
    project = models.ForeignKey(Novel, on_delete=models.CASCADE, related_name='scenes', help_text="ฉากนี้อยู่ในนิยายเรื่องไหน")
    title = models.CharField(max_length=200, verbose_name="ชื่อฉาก")
    order = models.IntegerField(default=0, verbose_name="ลำดับฉาก")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='idea')

    # 2. องค์ประกอบฉาก (Worldbuilding Elements)
    pov_character = models.ForeignKey(Character, on_delete=models.SET_NULL, null=True, blank=True, related_name='pov_scenes')
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True, related_name='scenes')
    characters = models.ManyToManyField(Character, blank=True, related_name='appeared_in_scenes')
    items = models.ManyToManyField(Item, blank=True, related_name='used_in_scenes')

    # 3. โครงสร้างการเล่าเรื่อง (Story Structure)
    goal = models.TextField(blank=True, help_text="ตัวละครต้องการอะไรในฉากนี้?")
    conflict = models.TextField(blank=True, help_text="อุปสรรคคืออะไร?")
    outcome = models.TextField(blank=True, help_text="ผลลัพธ์เป็นอย่างไร? (ได้/ไม่ได้)")
    
    # 4. เนื้อหา
    content = models.TextField(blank=True, help_text="เนื้อหาฉาก หรือบทร่าง")

    # System fields
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return f"{self.order}. {self.title}"


# ==================== TIMELINE & TIMELINE EVENT (from timeline) ====================
class Timeline(models.Model):
    title = models.CharField(max_length=200, default="New Timeline")
    description = models.TextField(blank=True, null=True)
    related_project = models.ForeignKey(Novel, on_delete=models.SET_NULL, null=True, blank=True, related_name='timelines')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class TimelineEvent(models.Model):
    timeline = models.ForeignKey(Timeline, on_delete=models.CASCADE, related_name='events')
    
    # ข้อมูลเวลา
    time_label = models.CharField(max_length=100, default="", verbose_name="ช่วงเวลา/ปี")
    order = models.IntegerField(default=0, verbose_name="ลำดับ")
    
    # เนื้อหา
    title = models.CharField(max_length=200, default="", verbose_name="ชื่อเหตุการณ์")
    description = models.TextField(blank=True, default="", verbose_name="รายละเอียดเหตุการณ์")
    image = models.ImageField(upload_to='timeline_events/', blank=True, null=True, verbose_name="รูปภาพเหตุการณ์")
    
    # เชื่อมกับฉาก
    related_scene = models.ForeignKey(Scene, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="ตรงกับฉาก")
    
    # ตัวละคร
    characters = models.ManyToManyField(Character, blank=True, related_name='timeline_events')

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.time_label}: {self.title}"
    
# ==================== Bookmark ====================
class Bookmark(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmarks')
    
    # 3 บรรทัดนี้คือหัวใจของการเก็บ "อะไรก็ได้"
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        # ห้าม User คนเดิม Bookmark ของชิ้นเดิมซ้ำ
        unique_together = ('user', 'content_type', 'object_id')
