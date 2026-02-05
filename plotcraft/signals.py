# plotcraft/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Character, Chapter, Scene, Novel, Location, Item # Import Scene เพิ่มเผื่ออนาคต
from .rag_service import rag_service

# ==================== NOVEL (นิยาย) ====================
@receiver(post_save, sender=Novel)
def update_novel_rag(sender, instance, created, **kwargs):
    """ เมื่อสร้างหรือแก้ไขนิยาย -> ให้ AI จำชื่อเรื่อง/คำโปรยใหม่ """
    rag_service.add_novel_summary_to_rag(instance)
    print(f"🔄 RAG Updated: Novel Summary '{instance.title}'")

@receiver(post_delete, sender=Novel)
def delete_novel_rag(sender, instance, **kwargs):
    """ เมื่อลบนิยาย -> ลบออกจากสมอง AI """
    rag_service.delete_data_from_rag(f"novel_{instance.id}")
    print(f"🗑️ RAG Deleted: Novel '{instance.title}'")

# ==================== CHARACTER (ตัวละคร) ====================
@receiver(post_save, sender=Character)
def update_character_rag(sender, instance, created, **kwargs):
    rag_service.add_character_to_rag(instance)
    """ เมื่อสร้างหรือแก้ตัวละคร -> ให้จำข้อมูลตัวละคร """
    print(f"🔄 RAG Updated: Character '{instance.name}'")

@receiver(post_delete, sender=Character)
def delete_character_rag(sender, instance, **kwargs):
    """ เมื่อลบตัวละคร -> ให้ลืม """
    rag_service.delete_data_from_rag(f"char_{instance.id}")
    print(f"🗑️ RAG Deleted: Character '{instance.name}'")


# ==================== CHAPTER (เนื้อหาตอน) ====================
@receiver(post_save, sender=Chapter)
def update_chapter_rag(sender, instance, created, **kwargs):
    if instance.content: 
        """ เมื่อสร้างหรือแก้ตอน -> ให้จำข้อมูลตอน """
        rag_service.add_chapter_to_rag(instance)
        print(f"🔄 RAG Updated: Chapter '{instance.title}'")

# เพิ่มฟังก์ชันลบตอน
@receiver(post_delete, sender=Chapter)
def delete_chapter_rag(sender, instance, **kwargs):
    """ เมื่อลบตอน -> ให้ลืม """
    rag_service.delete_data_from_rag(f"chap_{instance.id}")
    print(f"🗑️ RAG Deleted: Chapter '{instance.title}'")

# ==================== SCENE (ฉาก) ====================
@receiver(post_save, sender=Scene)
def update_scene_rag(sender, instance, **kwargs):
    """ เมื่อสร้างหรือแก้ฉาก -> ให้จำข้อมูลฉาก (Goal/Conflict) """
    rag_service.add_scene_to_rag(instance) 
    print(f"🔄 RAG Updated: Scene '{instance.title}'")

@receiver(post_delete, sender=Scene)
def delete_scene_rag(sender, instance, **kwargs):
    """ เมื่อลบฉาก -> ให้ลืม """
    rag_service.delete_data_from_rag(f"scene_{instance.id}")
    print(f"🗑️ RAG Deleted: Scene '{instance.title}'")

# =================== LOCATION & ITEM ====================
@receiver(post_delete, sender=Location)
@receiver(post_delete, sender=Item)
def delete_location_item_rag(sender, instance, **kwargs):
    """ เมื่อลบ Location หรือ Item -> ให้ลืม """
    model_name = sender.__name__.lower()
    if model_name == 'location':
        rag_service.delete_data_from_rag(f"loc_{instance.id}")
        print(f"🗑️ RAG Deleted: Location '{instance.name}'")
    elif model_name == 'item':
        rag_service.delete_data_from_rag(f"item_{instance.id}")
        print(f"🗑️ RAG Deleted: Item '{instance.name}'")

@receiver(post_save, sender=Location)
@receiver(post_save, sender=Item)
def update_location_item_rag(sender, instance, created, **kwargs):
    """ เมื่อสร้างหรือแก้ Location หรือ Item -> ให้จำข้อมูล """
    model_name = sender.__name__.lower()
    if model_name == 'location':
        rag_service.add_location_to_rag(instance)
        print(f"🔄 RAG Updated: Location '{instance.name}'")
    elif model_name == 'item':
        rag_service.add_item_to_rag(instance)
        print(f"🔄 RAG Updated: Item '{instance.name}'")