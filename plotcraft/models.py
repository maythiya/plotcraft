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
    display_name = models.CharField(max_length=50, blank=True, null=True, verbose_name="Display name")
    
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
        ('FANTASY', 'Fantasy'),
        ('BL', 'Boy Love'),
        ('GL', 'Girl Love'),
        ('ROMANCE', 'Romance'),
        ('SCIFI', 'Science Fiction'),
        ('ACTION', 'Action'),
        ('HORROR', 'Horror / Mystery'),
        ('FANFIC', 'Fan Fiction'),
        ('OTHER', 'Other'),
    ]

    RATING_CHOICES = [
        ('G', 'General'),
        ('PG', 'PG-13 (13+)'),
        ('R18', 'NC-18 (18+)'),
        ('R20', 'Adults only (20+)'),
    ]
    
    STATUS_CHOICES = [
        ('ONGOING', 'Ongoing'),
        ('COMPLETED', 'Completed'),
    ]

    title = models.CharField(max_length=200, verbose_name="Title")
    synopsis = models.TextField(blank=True, verbose_name="Synopsis")
    cover_image = models.ImageField(upload_to='novel_covers/', blank=True, null=True, verbose_name="Cover image")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='OTHER', verbose_name="Category")
    rating = models.CharField(max_length=5, choices=RATING_CHOICES, default='G', verbose_name="Content rating")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ONGOING', verbose_name="Status")
    
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='novels')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class Chapter(models.Model):
    novel = models.ForeignKey(Novel, on_delete=models.CASCADE, related_name='chapters')
    title = models.CharField(max_length=200, verbose_name="Chapter title")
    content = models.TextField(blank=True, verbose_name="Content")
    order = models.IntegerField(default=1, verbose_name="Chapter order")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    is_draft = models.BooleanField(default=True, verbose_name="Draft (excluded from export)")
    is_finished = models.BooleanField(default=False, verbose_name="Finished (ready to export)")

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
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
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

    relationships = models.ManyToManyField(
        'self', 
        blank=True, 
        symmetrical=False, 
        related_name='related_to',  # เพื่อให้ Django ไม่งงเวลาย้อนกลับ
        verbose_name="Relationships"
    )

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
    
class CharacterRelationship(models.Model):
    RELATIONSHIP_TYPES = [
        ('FAMILY', 'Family'),
        ('LOVER', 'Partner / Lover'),
        ('FRIEND', 'Friend / Ally'),
        ('ENEMY', 'Enemy / Rival'),
        ('MASTER_SERVANT', 'Leader / Subordinate'),
        ('OTHER', 'Other'),
    ]

    # ตัวละครหลัก (คนที่เรากำลังระบุความสัมพันธ์)
    from_character = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='relationships_from')
    
    # ตัวละครเป้าหมาย (คนที่เราจะระบุความสัมพันธ์ด้วย)
    to_character = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='relationships_to')
    
    # สถานะ (เป็นอะไรกัน)
    status = models.CharField(max_length=50, choices=RELATIONSHIP_TYPES, default='FRIEND')
    
    # รายละเอียดเพิ่มเติม (เผื่ออยากระบุลึกๆ เช่น "พี่สาวคนโต")
    note = models.CharField(max_length=100, blank=True, null=True, verbose_name="Relationship note")

    def __str__(self):
        return f"{self.from_character.name} -> {self.to_character.name} ({self.get_status_display()})"


class Location(models.Model):
    project = models.ForeignKey(Novel, on_delete=models.SET_NULL, null=True, blank=True, related_name='locations')
    
    # ข้อมูลพื้นฐาน
    name = models.CharField(max_length=200)
    world_type = models.CharField(max_length=100, blank=True, help_text="Ex: Fantasy, Sci-Fi, Omegaverse")
    map_image = models.ImageField(upload_to='location_maps/', null=True, blank=True)
    
    # ความสัมพันธ์
    residents = models.ManyToManyField(Character, blank=True, related_name='resides_in')
    
    # ภูมิประเทศ
    terrain = models.TextField(blank=True, help_text="Terrain and geography")
    climate = models.TextField(blank=True, help_text="Climate and weather")
    ecosystem = models.TextField(blank=True, help_text="Ecosystem")
    
    # ประวัติศาสตร์
    history = models.TextField(blank=True, help_text="History")
    myths = models.TextField(blank=True, help_text="Myths and folklore")
    
    # สังคม
    politics = models.TextField(blank=True, help_text="Politics and government")
    economy = models.TextField(blank=True, help_text="Economy")
    culture = models.TextField(blank=True, help_text="Culture, beliefs, and religion")
    language = models.TextField(blank=True, help_text="Language")
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Item(models.Model):
    CATEGORY_CHOICES = [
        ('weapon', 'Weapon'),
        ('apparel', 'Apparel / Clothing'),
        ('item', 'Item / Consumable'),
        ('key_item', 'Key Item / Artifact'),
        ('technology', 'Technology'),
        ('vehicle', 'Vehicle'),
        ('other', 'Other'),
    ]

    project = models.ForeignKey(Novel, on_delete=models.SET_NULL, null=True, blank=True, related_name='items')
    
    # Basic Info
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='item')
    image = models.ImageField(upload_to='items/', null=True, blank=True)
    
    # Mechanics
    abilities = models.TextField(blank=True, help_text="Special abilities and effects")
    limitations = models.TextField(blank=True, help_text="Conditions, limitations, and side effects")
    
    # Lore & Description
    appearance = models.TextField(blank=True, help_text="Appearance, materials, and color")
    history = models.TextField(blank=True, help_text="History and legends")
    
    # Connections
    owner = models.ForeignKey(Character, on_delete=models.SET_NULL, null=True, blank=True, related_name='inventory', help_text="Current owner")
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True, related_name='items', help_text="Where the item is stored when it has no owner")

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


# ==================== SCENE (from scenes) ====================
class Scene(models.Model):
    STATUS_CHOICES = [
        ('idea', 'Idea'),
        ('draft', 'Drafting'),
        ('finished', 'Finished'),
    ]

    # 1. ความเชื่อมโยงหลัก
    project = models.ForeignKey(Novel, on_delete=models.CASCADE, related_name='scenes', help_text="Novel containing this scene")
    title = models.CharField(max_length=200, verbose_name="Scene title")
    order = models.IntegerField(default=0, verbose_name="Scene order")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='idea')

    # 2. องค์ประกอบฉาก (Worldbuilding Elements)
    pov_character = models.ForeignKey(Character, on_delete=models.SET_NULL, null=True, blank=True, related_name='pov_scenes')
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True, related_name='scenes')
    characters = models.ManyToManyField(Character, blank=True, related_name='appeared_in_scenes')
    items = models.ManyToManyField(Item, blank=True, related_name='used_in_scenes')

    # 3. โครงสร้างการเล่าเรื่อง (Story Structure)
    goal = models.TextField(blank=True, help_text="What does the character want in this scene?")
    conflict = models.TextField(blank=True, help_text="What stands in their way?")
    outcome = models.TextField(blank=True, help_text="What changes by the end of the scene?")
    
    # 4. เนื้อหา
    content = models.TextField(blank=True, help_text="Scene content or draft")

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
    time_label = models.CharField(max_length=100, default="", verbose_name="Time period / Year")
    order = models.IntegerField(default=0, verbose_name="Order")
    
    # เนื้อหา
    title = models.CharField(max_length=200, default="", verbose_name="Event title")
    description = models.TextField(blank=True, default="", verbose_name="Event description")
    image = models.ImageField(upload_to='timeline_events/', blank=True, null=True, verbose_name="Event image")
    
    # เชื่อมกับฉาก
    related_scene = models.ForeignKey(Scene, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Related scene")
    
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
