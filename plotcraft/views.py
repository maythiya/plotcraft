import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse
from django.views.decorators.http import require_POST
from django.conf import settings
from django.conf.urls.static import static
from django.urls import reverse
import json

import io
from django.template.loader import render_to_string
from django.utils.encoding import escape_uri_path

# Library สำหรับ Export (ต้องติดตั้งก่อน)
from ebooklib import epub
from weasyprint import HTML, CSS
from django.utils.encoding import escape_uri_path

from .models import (
    Novel, Chapter, Character, Location, Item,
    Scene, Timeline, TimelineEvent, Bookmark
)
from .forms import (
    UserForm, RegisterForm, ProfileForm, NovelForm, ChapterForm,
    CharacterForm, LocationForm, ItemForm, SceneForm, TimelineForm, EventForm
)

from .rag_service import rag_service

# ==================== AUTHENTICATION & PROFILE (from myapp) ====================

def landing(request):
    return render(request, 'landing.html')


def home(request):
    max_items = 3
    if request.user.is_authenticated:
        characters = Character.objects.filter(created_by=request.user).order_by('-created_at')[:max_items]
        novels = Novel.objects.filter(author=request.user).order_by('-updated_at')[:max_items]
        locations = Location.objects.filter(created_by=request.user).order_by('-created_at')[:max_items]
    else:
        characters = Character.objects.all().order_by('-created_at')[:max_items]
        novels = Novel.objects.all().order_by('-updated_at')[:max_items]
        locations = Location.objects.all().order_by('-created_at')[:max_items]

    return render(request, 'home.html', {
        'characters': characters,
        'novels': novels,
        'locations': locations,
    })


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful.")
            return redirect('plotcraft:home')
        else:
            messages.error(request, "Unsuccessful registration. Invalid information.")
    else:
        form = RegisterForm()

    return render(request, 'registration/register.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('plotcraft:landing')

def login_view(request):
    return render(request, 'registration/login.html')

@login_required
def profile(request):
    if request.method == 'POST':
        if 'delete_account' in request.POST:
            user = request.user
            logout(request)
            user.delete()
            return redirect('plotcraft:landing')

        u_form = UserForm(request.POST, instance=request.user)
        p_form = ProfileForm(request.POST, request.FILES, instance=request.user.profile)

        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, 'บันทึกข้อมูลสำเร็จ')
            return redirect('plotcraft:profile')
    else:
        u_form = UserForm(instance=request.user)
        p_form = ProfileForm(instance=request.user.profile)

    return render(request, 'profile.html', {'u_form': u_form, 'p_form': p_form})


@login_required
def global_search(request):
    query = request.GET.get('q', '')
    results = {}
    
    if query:
        results['projects'] = Novel.objects.filter(
            Q(title__icontains=query) | Q(synopsis__icontains=query),
            author=request.user
        )

        results['characters'] = Character.objects.filter(
            Q(name__icontains=query) | 
            Q(background__icontains=query) | 
            Q(personality__icontains=query) |
            Q(appearance__icontains=query) |
            Q(alias__icontains=query),
            created_by=request.user
        )

        results['scenes'] = Scene.objects.filter(
            Q(title__icontains=query) | 
            Q(content__icontains=query),
            created_by=request.user
        )

        results['timeline_events'] = TimelineEvent.objects.filter(
            Q(title__icontains=query) | 
            Q(description__icontains=query),
            timeline__created_by=request.user
        )

        results['locations'] = Location.objects.filter(
            Q(name__icontains=query) |
            Q(history__icontains=query) |
            Q(terrain__icontains=query) |
            Q(climate__icontains=query) |
            Q(ecosystem__icontains=query) |
            Q(myths__icontains=query) |
            Q(culture__icontains=query) |
            Q(politics__icontains=query) |
            Q(economy__icontains=query) |
            Q(language__icontains=query),
            created_by=request.user
        )

        results['items'] = Item.objects.filter(
            Q(name__icontains=query) |
            Q(appearance__icontains=query) |
            Q(history__icontains=query) |
            Q(abilities__icontains=query) |
            Q(limitations__icontains=query),
            created_by=request.user
        )

    return render(request, 'search_results.html', {'query': query, 'results': results})


# ==================== NOVEL & CHAPTER ====================

@login_required
def novel_list(request):
    novels = Novel.objects.filter(author=request.user).order_by('-updated_at')

    #ดึง ID ของนิยายที่ Bookmark ไว้
    bookmarked_ids = Bookmark.objects.filter(
        user=request.user,
        content_type__model='novel' # ระบุชื่อ Model (ตัวเล็ก)
    ).values_list('object_id', flat=True)

    return render(request, 'notes/novel_list.html', {
        'novels': novels,
        'bookmarked_ids': bookmarked_ids, # ส่งไปที่ Template
    })


@login_required
def novel_create(request):
    if request.method == 'POST':
        form = NovelForm(request.POST, request.FILES)
        if form.is_valid():
            novel = form.save(commit=False)
            novel.author = request.user
            novel.save()
            return redirect('plotcraft:novel_detail', pk=novel.id)
    else:
        form = NovelForm()
    return render(request, 'notes/novel_create.html', {'form': form})


@login_required
def novel_edit(request, pk):
    novel = get_object_or_404(Novel, pk=pk, author=request.user)
    if request.method == 'POST':
        form = NovelForm(request.POST, request.FILES, instance=novel)
        if form.is_valid():
            form.save()
            return redirect('plotcraft:novel_detail', pk=novel.id)
    else:
        form = NovelForm(instance=novel)
    return render(request, 'notes/novel_create.html', {'form': form, 'is_edit': True})


@login_required
def novel_detail(request, pk):
    novel = get_object_or_404(Novel, pk=pk, author=request.user)
    chapters = novel.chapters.all().order_by('order')
    return render(request, 'notes/novel_detail.html', {'novel': novel, 'chapters': chapters})


@login_required
def novel_delete(request, pk):
    novel = get_object_or_404(Novel, pk=pk, author=request.user)
    if request.method == 'POST':
        novel.delete()
        return redirect('plotcraft:novel_list')
    return render(request, 'notes/novel_confirm_delete.html', {'novel': novel})


@login_required
def chapter_create(request, novel_id):
    novel = get_object_or_404(Novel, pk=novel_id, author=request.user)
    
    if request.method == 'POST':
        form = ChapterForm(request.POST)
        if form.is_valid():
            chapter = form.save(commit=False)
            chapter.novel = novel
            chapter.save()
            return redirect('plotcraft:chapter_edit', novel_id=novel.id, chapter_id=chapter.id)
    else:
        next_order = novel.chapters.count() + 1
        form = ChapterForm(initial={'order': next_order})
    
    return render(request, 'notes/chapter_create.html', {'form': form, 'novel': novel})


@login_required
def chapter_edit(request, novel_id, chapter_id):
    novel = get_object_or_404(Novel, pk=novel_id, author=request.user)
    chapter = get_object_or_404(Chapter, pk=chapter_id, novel=novel)

    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        
        # รับค่า is_draft จาก Form (ส่งมาเป็น String 'true' หรือ 'false')
        is_draft_str = request.POST.get('is_draft') 
        
        chapter.title = title
        chapter.content = content
        
        # ตรวจสอบถ้ามีการส่งสถานะมาให้บันทึกด้วย
        if is_draft_str:
            chapter.is_draft = True if is_draft_str == 'true' else False
            
        chapter.save()
        
        return redirect('plotcraft:novel_detail', pk=novel.id)

    return render(request, 'notes/chapter_write.html', {'novel': novel, 'chapter': chapter})


@login_required
def chapter_delete(request, pk):
    chapter = get_object_or_404(Chapter, pk=pk, novel__author=request.user)
    novel_id = chapter.novel.id
    if request.method == 'POST':
        chapter.delete()
    return redirect('plotcraft:novel_detail', pk=novel_id)

@login_required
def change_chapter_status(request, chapter_id, status):
    # ฟังก์ชันสำหรับเปลี่ยนสถานะ Draft/finish แบบไม่ต้องรีโหลดหน้า
    chapter = get_object_or_404(Chapter, id=chapter_id)
    
    # ตรวจสอบสิทธิ์ความเป็นเจ้าของก่อนบันทึก (กันคนอื่นมาแก้)
    # if chapter.novel.author != request.user:
    #    return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    if status == 'finish':
        chapter.is_draft = False
    elif status == 'draft':
        chapter.is_draft = True
        
    chapter.save()
    
    # ส่งค่ากลับไปบอกหน้าเว็บว่าทำสำเร็จแล้ว
    return JsonResponse({'success': True, 'is_draft': chapter.is_draft})

@login_required
def chapter_preview(request, pk):
    chapter = get_object_or_404(Chapter, id=pk)
    
    if chapter.novel.author != request.user:
         return HttpResponseForbidden("คุณไม่มีสิทธิ์ดูตัวอย่างตอนนี้")

    # หาตอนที่มี order น้อยกว่าปัจจุบัน (ตอนก่อนหน้า)
    previous_chapter = Chapter.objects.filter(
        novel=chapter.novel, 
        order__lt=chapter.order
    ).order_by('-order').first()
    
    # หาตอนที่มี order มากกว่าปัจจุบัน (ตอนถัดไป)
    next_chapter = Chapter.objects.filter(
        novel=chapter.novel, 
        order__gt=chapter.order
    ).order_by('order').first()

    # ส่งตัวแปรเพิ่มเข้าไปใน template
    return render(request, 'notes/chapter_preview.html', {
        'chapter': chapter,
        'previous_chapter': previous_chapter,
        'next_chapter': next_chapter,
    })



# ==================== WORLDBUILDING (Characters, Locations, Items) ====================

def worldbuilding_overview(request):
    return render(request, "worldbuilding/overview.html")


@login_required
def character_list(request):
    base_characters = Character.objects.filter(created_by=request.user)
    
    project_id = request.GET.get('project')
    if project_id:
        project = get_object_or_404(Novel, id=project_id)
        characters = base_characters.filter(project=project)
    else:
        characters = base_characters.order_by('-created_at')

    #ดึง ID ของตัวละครที่ Bookmark ไว้
    bookmarked_ids = Bookmark.objects.filter(
        user=request.user,
        content_type__model='character'
    ).values_list('object_id', flat=True)

    return render(request, 'worldbuilding/character_list.html', {
        'characters': characters,
        'bookmarked_ids': bookmarked_ids, # ส่งไปที่ Template
    })


@login_required
def character_create(request):
    if request.method == 'POST':
        form = CharacterForm(request.user, request.POST, request.FILES)
        if form.is_valid():
            character = form.save(commit=False)
            if request.user.is_authenticated:
                character.created_by = request.user
            character.save()
            form.save_m2m()
            return redirect('plotcraft:character_detail', pk=character.id)
    else:
        initial = {}
        project_id = request.GET.get('project')
        if project_id:
            try:
                initial['project'] = Novel.objects.get(id=project_id, author=request.user)
            except Novel.DoesNotExist:
                pass
        form = CharacterForm(request.user, initial=initial)
    return render(request, 'worldbuilding/character_form.html', {'form': form})


@login_required
def character_edit(request, pk):
    character = get_object_or_404(Character, id=pk) 
    
    if character.created_by != request.user:
        messages.error(request, "คุณไม่มีสิทธิ์แก้ไข/ลบตัวละครนี้")
        return redirect('plotcraft:character_detail', pk=pk)

    if request.method == 'POST':
        
        if "character_delete" in request.POST:
            character_name = character.name
            character.delete()
            messages.success(request, f"ลบตัวละคร '{character_name}' เรียบร้อยแล้ว")
            return redirect('plotcraft:character_list')
        
        form = CharacterForm(request.user, request.POST, request.FILES, instance=character)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.created_by = request.user
            obj.save()
            form.save_m2m()
            messages.success(request, f"บันทึกตัวละคร '{obj.name}' เรียบร้อยแล้ว")
            return redirect('plotcraft:character_detail', pk=obj.id)
        
    else:
        form = CharacterForm(request.user, instance=character)

    return render(request, 'worldbuilding/character_form.html', {
        'form': form,
        'character': character,
    })


@login_required
def character_detail(request, pk):
    character = get_object_or_404(Character, id=pk)
    return render(request, 'worldbuilding/character_detail.html', {'character': character})


@login_required
def location_create(request):
    if request.method == 'POST':
        form = LocationForm(request.user, request.POST, request.FILES)
        if form.is_valid():
            location = form.save(commit=False)
            location.created_by = request.user
            location.save()
            form.save_m2m()
            messages.success(request, f"สร้างสถานที่ '{location.name}' เรียบร้อยแล้ว")
            return redirect('plotcraft:location_detail', pk=location.id)
    else:
        initial = {}
        project_id = request.GET.get('project')
        if project_id:
            try:
                initial['project'] = Novel.objects.get(id=project_id, author=request.user)
            except Novel.DoesNotExist:
                pass
        form = LocationForm(request.user, initial=initial)
    return render(request, 'worldbuilding/location_form.html', {'form': form})


@login_required
def location_list(request):
    locations = Location.objects.filter(created_by=request.user).order_by('-created_at')

    #ดึง ID ของสถานที่ที่ Bookmark ไว้
    bookmarked_ids = Bookmark.objects.filter(
        user=request.user,
        content_type__model='location'
    ).values_list('object_id', flat=True)

    return render(request, 'worldbuilding/location_list.html', {
        'locations': locations,
        'bookmarked_ids': bookmarked_ids, # ส่งไปที่ Template
    })


@login_required
def location_detail(request, pk):
    location = get_object_or_404(Location, id=pk)
    return render(request, 'worldbuilding/location_detail.html', {'location': location})


@login_required
def location_edit(request, pk):
    location = get_object_or_404(Location, id=pk)
    
    if location.created_by != request.user:
        messages.error(request, "คุณไม่มีสิทธิ์แก้ไข/ลบสถานที่นี้")
        return redirect('plotcraft:location_detail', pk=pk)

    if request.method == 'POST':
        if "location_delete" in request.POST:
            location_name = location.name
            location.delete()
            messages.success(request, f"ลบสถานที่ '{location_name}' เรียบร้อยแล้ว")
            return redirect('plotcraft:location_list')
        
        form = LocationForm(request.user, request.POST, request.FILES, instance=location)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.created_by = request.user
            obj.save()
            form.save_m2m()
            messages.success(request, f"บันทึกสถานที่ '{obj.name}' เรียบร้อยแล้ว")
            return redirect('plotcraft:location_detail', pk=obj.id)
    else:
        form = LocationForm(request.user, instance=location)

    return render(request, 'worldbuilding/location_form.html', {
        'form': form,
        'location': location,
    })


@login_required
def item_create(request):
    if request.method == 'POST':
        form = ItemForm(request.user, request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.created_by = request.user
            item.save()
            form.save_m2m()
            messages.success(request, f"สร้างไอเท็ม '{item.name}' เรียบร้อยแล้ว")
            return redirect('plotcraft:item_detail', pk=item.id)
    else:
        initial = {}
        project_id = request.GET.get('project')
        if project_id:
            try:
                initial['project'] = Novel.objects.get(id=project_id, author=request.user)
            except Novel.DoesNotExist:
                pass
        form = ItemForm(request.user, initial=initial)
    return render(request, 'worldbuilding/item_form.html', {'form': form})


@login_required
def item_list(request):
    items = Item.objects.filter(created_by=request.user).order_by('-created_at')

    #ดึง ID ของไอเท็มที่ Bookmark ไว้
    bookmarked_ids = Bookmark.objects.filter(
        user=request.user,
        content_type__model='item'
    ).values_list('object_id', flat=True)

    return render(request, 'worldbuilding/item_list.html', {
        'items': items,
        'bookmarked_ids': bookmarked_ids, # ส่งไปที่ Template
    })


@login_required
def item_detail(request, pk):
    item = get_object_or_404(Item, id=pk)
    return render(request, 'worldbuilding/item_detail.html', {'item': item})


@login_required
def item_edit(request, pk):
    item = get_object_or_404(Item, id=pk)
    
    if item.created_by != request.user:
        messages.error(request, "คุณไม่มีสิทธิ์แก้ไข/ลบไอเท็มนี้")
        return redirect('plotcraft:item_detail', pk=pk)

    if request.method == 'POST':
        if "item_delete" in request.POST:
            item_name = item.name
            item.delete()
            messages.success(request, f"ลบไอเท็ม '{item_name}' เรียบร้อยแล้ว")
            return redirect('plotcraft:item_list')
        
        form = ItemForm(request.user, request.POST, request.FILES, instance=item)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.created_by = request.user
            obj.save()
            form.save_m2m()
            messages.success(request, f"บันทึกไอเท็ม '{obj.name}' เรียบร้อยแล้ว")
            return redirect('plotcraft:item_detail', pk=obj.id)
    else:
        form = ItemForm(request.user, instance=item)

    return render(request, 'worldbuilding/item_form.html', {
        'form': form,
        'item': item,
    })


# ==================== SCENES ====================

@login_required
def scene_list(request):
    projects = Novel.objects.filter(author=request.user)
    scenes = Scene.objects.filter(created_by=request.user).order_by('order')
    
    selected_project_id = request.GET.get('project')
    selected_project = None

    if selected_project_id:
        scenes = scenes.filter(project_id=selected_project_id)
        if projects.filter(id=selected_project_id).exists():
            selected_project = projects.get(id=selected_project_id)

    #ดึง ID ของฉากที่ Bookmark ไว้
    bookmarked_ids = Bookmark.objects.filter(
        user=request.user,
        content_type__model='scene'
    ).values_list('object_id', flat=True)

    context = {
        'scenes': scenes,
        'projects': projects,
        'selected_project': selected_project,
        'bookmarked_ids': bookmarked_ids, # ส่งไปที่ Template
    }
    return render(request, 'scenes/scene_list.html', context)


@login_required
def scene_create(request):
    if request.method == 'POST':
        form = SceneForm(request.user, request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.created_by = request.user
            obj.save()
            form.save_m2m()

            messages.success(request, f"สร้างฉาก '{obj.title}' เรียบร้อย")

            url = reverse('plotcraft:scene_list')
            return redirect(f"{url}?project={obj.project.id}")

    else:
        form = SceneForm(request.user)

    return render(request, 'scenes/scene_form.html', {'form': form})


@login_required
def scene_edit(request, pk):
    scene = get_object_or_404(Scene, pk=pk)

    if scene.created_by != request.user:
        messages.error(request, "ไม่มีสิทธิ์แก้ไข")
        return redirect('plotcraft:scene_list')

    if request.method == 'POST':
        if "scene_delete" in request.POST:
            project_id = scene.project.id
            scene.delete()
            messages.success(request, "ลบฉากเรียบร้อย")

            url = reverse('plotcraft:scene_list')
            return redirect(f"{url}?project={project_id}")

        form = SceneForm(request.user, request.POST, instance=scene)
        if form.is_valid():
            form.save()
            messages.success(request, "บันทึกฉากเรียบร้อย")

            url = reverse('plotcraft:scene_list')
            return redirect(f"{url}?project={scene.project.id}")

    else:
        form = SceneForm(request.user, instance=scene)

    return render(request, 'scenes/scene_form.html', {'form': form, 'scene': scene})

@login_required
def scene_delete(request, pk):
    scene = get_object_or_404(Scene, pk=pk)

    if scene.created_by != request.user:
        messages.error(request, "ไม่มีสิทธิ์ลบ")
        return redirect('plotcraft:scene_list')

    if request.method == 'POST':
        project_id = scene.project.id
        scene.delete()
        messages.success(request, "ลบฉากเรียบร้อย")

        url = reverse('plotcraft:scene_list')
        return redirect(f"{url}?project={project_id}")

    return render(request, 'scenes/scene_confirm_delete.html', {'scene': scene})

@login_required
def scene_detail(request, pk):
    scene = get_object_or_404(Scene, id=pk)
    # เช็คสิทธิ์ (optional: ป้องกันไม่ให้ดูของคนอื่นถ้าต้องการ)
    if scene.created_by != request.user:
         return HttpResponseForbidden()
         
    return render(request, 'scenes/scene_detail.html', {'scene': scene}) 


# ==================== TIMELINE ====================

def timeline_list(request):

    # เตรียมตัวแปร bookmarked_ids ไว้ก่อน (เผื่อกรณีไม่ได้ login)
    bookmarked_ids = []

    if request.user.is_authenticated:
        timelines = Timeline.objects.filter(created_by=request.user).order_by('-updated_at')

        bookmarked_ids = Bookmark.objects.filter(
            user=request.user,
            content_type__model='timeline'
        ).values_list('object_id', flat=True)
    else:
        timelines = Timeline.objects.all().order_by('-updated_at')

    return render(request, 'timeline/timeline_list.html', {
        'timelines': timelines,
        'bookmarked_ids': bookmarked_ids, # ส่งไปที่ Template
    })


@login_required
def timeline_create(request):
    if request.method == 'POST':
        form = TimelineForm(request.POST, user=request.user) 
        
        if form.is_valid():
            timeline = form.save(commit=False)
            timeline.created_by = request.user
            timeline.save()
            return redirect('plotcraft:timeline_detail', pk=timeline.id)
    else:
        form = TimelineForm(user=request.user)
    
    return render(request, 'timeline/timeline_form.html', {'form': form})


def timeline_detail(request, pk):
    timeline = get_object_or_404(Timeline, id=pk)
    events = timeline.events.all().order_by('order')

    if request.user.is_authenticated:
        event_form = EventForm(user=request.user, timeline=timeline)
    else:
        event_form = EventForm()

    return render(request, 'timeline/timeline_detail.html', {
        'timeline': timeline,
        'events': events,
        'event_form': event_form,
    })


@login_required
def timeline_delete(request, pk):
    timeline = get_object_or_404(Timeline, id=pk)
    if timeline.created_by != request.user and not request.user.is_staff:
        return HttpResponseForbidden()
    if request.method == 'POST':
        timeline.delete()
        return redirect('plotcraft:timeline_list')
    return render(request, 'timeline/timeline_confirm_delete.html', {'timeline': timeline})


@require_POST
def update_event_order(request):
    try:
        data = json.loads(request.body)
        event_ids = data.get('ids', [])
        for index, event_id in enumerate(event_ids):
            TimelineEvent.objects.filter(
                id=event_id, 
                timeline__created_by=request.user
            ).update(order=index)
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error'}, status=400)

    
@login_required
def timeline_event_create(request, pk):
    timeline = get_object_or_404(Timeline, id=pk)
    
    if timeline.created_by != request.user and not request.user.is_staff:
        return HttpResponseForbidden()

    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES, user=request.user, timeline=timeline)
        
        if form.is_valid():
            ev = form.save(commit=False)
            ev.timeline = timeline
            ev.save()
            form.save_m2m()
            return redirect('plotcraft:timeline_detail', pk=timeline.id)
    else:
        form = EventForm(user=request.user, timeline=timeline)
    
    return render(request, 'timeline/event_form.html', {'form': form, 'timeline': timeline})


@login_required
def timeline_event_update(request, pk):
    event = get_object_or_404(TimelineEvent, id=pk)
    
    if event.timeline.created_by != request.user and not request.user.is_staff:
        return HttpResponseForbidden()

    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES, user=request.user, instance=event)
        if form.is_valid():
            form.save()
            return redirect('plotcraft:timeline_detail', pk=event.timeline.id)
    else:
        form = EventForm(user=request.user, instance=event)
    
    return render(request, 'timeline/event_form.html', {'form': form, 'event': event})


@login_required
def timeline_event_delete(request, pk):
    event = get_object_or_404(TimelineEvent, id=pk)
    
    if event.timeline.created_by != request.user and not request.user.is_staff:
        return HttpResponseForbidden()
    
    timeline_id = event.timeline.id
    if request.method == 'POST':
        event.delete()
        messages.success(request, "ลบเหตุการณ์เรียบร้อย")
        return redirect('plotcraft:timeline_detail', pk=timeline_id)
    
    return render(request, 'timeline/event_confirm_delete.html', {'event': event})

# ==================== EXPORT FUNCTIONALITY ====================

def get_font_path():
 # ฟังก์ชันช่วยหำ path ของไฟล์ฟอนต์
 return os.path.join(settings.BASE_DIR, 'static/fonts/THSarabunNew.ttf')

@login_required
def export_novel_pdf(request, pk):
    novel = get_object_or_404(Novel, pk=pk, author=request.user)
    chapters = novel.chapters.filter(is_draft=False).order_by('order')
    
    font_path = get_font_path()

    css_string = f'''
        @font-face {{
            font-family: 'THSarabunNew';
            src: url('file://{font_path}');
        }}
        
        /* ตั้งค่าหน้ากระดาษ A5 มาตรฐาน */
        @page {{
            size: A5;
            margin: 2cm 1.5cm; /* บนล่าง 2cm, ซ้ายขวา 1.5cm */
            
            @top-right {{
                content: counter(page);
                font-family: 'THSarabunNew';
                font-size: 12pt;
                color: #888;
                vertical-align: bottom;
                padding-bottom: 10px;
            }}
        }}

        /* === แก้ไข 1: หน้าปก (หน้าแรก) ต้องไม่มีขอบขาวเลย === */
        @page :first {{
            margin: 0cm; /* ลบขอบกระดาษออกทั้งหมด */
            @top-right {{ content: none; }} /* ไม่เอาเลขหน้า */
        }}

        body {{
            font-family: 'THSarabunNew', serif;
            font-size: 14pt;
            line-height: 1.4;
            text-align: justify;
        }}

        /* สไตล์สำหรับรูปปกแบบเต็มจอ */
        .cover-wrapper {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: -1;
            overflow: hidden;
        }}

        .cover-wrapper img {{
            width: 100%;
            height: 100%;
            object-fit: cover; /* ขยายรูปให้เต็มพื้นที่ (อาจโดนตัดขอบบ้างเพื่อรักษาสัดส่วน) */
            /* หรือใช้ object-fit: fill; ถ้าอยากให้ยืดเต็มโดยไม่ตัดขอบ (แต่รูปอาจเบี้ยว) */
        }}

        /* สไตล์หน้ารองปก */
        .title-page {{
            page-break-before: always; /* ขึ้นหน้าใหม่หลังจากปก */
            page-break-after: always;
            text-align: center;
            padding-top: 30%;
            padding-left: 1cm;  /* เพิ่มระยะกันตก */
            padding-right: 1cm; /* เพิ่มระยะกันตก */
        }}

        h1 {{ font-size: 24pt; font-weight: bold; margin-bottom: 0.5cm; line-height: 1.2; }}
        h2 {{ font-size: 18pt; font-weight: bold; margin-top: 1cm; }}
        
        /* เนื้อหา */
        .chapter-content p {{
            margin: 0;
            text-indent: 2.5em;
            padding-bottom: 0.5em; /* เว้นบรรทัดนิดหน่อยให้อ่านง่าย */
        }}
        
        /* รูปภาพแทรกในเนื้อหา */
        .chapter-content img {{
            max-width: 100%;
            height: auto;
            display: block;
            margin: 0.5cm auto;
        }}
    '''

    html_string = render_to_string('notes/export_pdf.html', {
        'novel': novel,
        'chapters': chapters,
    })

    # base_url สำคัญมากสำหรับการดึงรูป
    pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf(stylesheets=[CSS(string=css_string)])

    response = HttpResponse(pdf_file, content_type='application/pdf')
    filename = f"{novel.title}.pdf"
    response['Content-Disposition'] = f"attachment; filename*=UTF-8''{escape_uri_path(filename)}"
    return response

@login_required
def export_novel_epub(request, pk):
    novel = get_object_or_404(Novel, pk=pk, author=request.user)
    chapters = novel.chapters.filter(is_draft=False).order_by('order')

    # 1. ตั้งค่าหนังสือ
    book = epub.EpubBook()
    book.set_identifier(f'id_novel_{novel.id}') 
    book.set_title(novel.title)
    book.set_language('th')
    book.add_author(novel.author.get_full_name() or novel.author.username)

    # ==========================================
    # 2. จัดการรูปปก (Cover Image)
    # ==========================================
    has_cover = False
    cover_filename = "cover.jpg"
    
    if novel.cover_image:
        try:
            image_path = novel.cover_image.path
            file_ext = os.path.splitext(image_path)[1].lower()
            if file_ext:
                cover_filename = f"cover{file_ext}"

            with open(image_path, 'rb') as f:
                cover_content = f.read()
            
            if len(cover_content) > 0:
                book.set_cover(cover_filename, cover_content, create_page=False)
                has_cover = True
        except Exception as e:
            print(f"Error adding cover: {e}")

    # ==========================================
    # 3. CSS Style
    # ==========================================
    style_css = '''
    @font-face { font-family: 'THSarabunNew'; src: url('fonts/THSarabunNew.ttf'); }
    body { font-family: 'THSarabunNew', sans-serif; font-size: 1.2em; line-height: 1.6; margin: 0; padding: 0; }
    
    /* ปกเต็มจอ */
    .cover-container {
        height: 100vh; width: 100vw;
        display: flex; justify-content: center; align-items: center;
        background-color: #ffffff;
    }
    .cover-img { max-width: 100%; max-height: 100%; object-fit: contain; }

    /* หน้ารองปก */
    .title-page-container {
        height: 90vh;
        display: flex; flex-direction: column;
        justify-content: center; align-items: center; text-align: center;
        padding: 20px;
    }
    .novel-title { font-size: 2.5em; font-weight: bold; margin-bottom: 0.5em; }
    .author-name { font-size: 1.5em; color: #555; }
    
    /* เนื้อหา & เรื่องย่อ */
    .chapter-content { margin: 5%; }
    h1 { text-align: center; margin-bottom: 1em; border-bottom: 1px solid #ccc; padding-bottom: 0.5em;}
    p { text-indent: 1.5em; margin-bottom: 1em; text-align: justify; }
    '''
    
    nav_css = epub.EpubItem(uid="style_nav", file_name="nav.css", media_type="text/css", content=style_css)
    book.add_item(nav_css)

    # ฝังฟอนต์
    font_path = get_font_path()
    try:
        with open(font_path, 'rb') as f:
            font_data = f.read()
            font_item = epub.EpubItem(uid="THSarabunNew", file_name="fonts/THSarabunNew.ttf", media_type="application/x-font-ttf", content=font_data)
            book.add_item(font_item)
    except Exception:
        pass

    # ==========================================
    # 4. สร้างหน้าต่างๆ (Spine Items)
    # ==========================================
    spine_items = []

    # --- 4.1 หน้าปก (Cover) ---
    if has_cover:
        cover_page = epub.EpubHtml(title="Cover", file_name="cover.xhtml", lang='th')
        cover_page.add_item(nav_css)
        cover_page.content = f'''<!DOCTYPE html>
<html lang="th"><head><title>Cover</title><link rel="stylesheet" type="text/css" href="nav.css"/></head>
<body>
    <div class="cover-container"><img src="{cover_filename}" alt="Cover" class="cover-img"/></div>
</body></html>'''
        book.add_item(cover_page)
        spine_items.append(cover_page)

    # --- 4.2 หน้ารองปก (Title) ---
    title_page = epub.EpubHtml(title="Title Page", file_name="title.xhtml", lang='th')
    title_page.add_item(nav_css)
    title_page.content = f'''<!DOCTYPE html>
<html lang="th"><head><title>{novel.title}</title><link rel="stylesheet" type="text/css" href="nav.css"/></head>
<body>
    <div class="title-page-container">
        <div class="novel-title">{novel.title}</div>
        <div class="author-name">โดย {novel.author.get_full_name() or novel.author.username}</div>
    </div>
</body></html>'''
    book.add_item(title_page)
    spine_items.append(title_page)

    # --- 4.3 หน้าเรื่องย่อ (Synopsis) ---
    # แก้ไขตรงนี้: ใช้ novel.synopsis ตามใน Models.py
    synopsis_page = None
    if novel.synopsis: 
        synopsis_page = epub.EpubHtml(title="เรื่องย่อ", file_name="synopsis.xhtml", lang='th')
        synopsis_page.add_item(nav_css)
        
        # แปลง \n เป็น <br> เพื่อให้ขึ้นบรรทัดใหม่สวยงาม
        desc_text = novel.synopsis.replace('\n', '<br/>')
        
        synopsis_page.content = f'''<!DOCTYPE html>
<html lang="th"><head><title>เรื่องย่อ</title><link rel="stylesheet" type="text/css" href="nav.css"/></head>
<body>
    <div class="chapter-content">
        <h1>เรื่องย่อ</h1>
        <div>{desc_text}</div>
    </div>
</body></html>'''
        book.add_item(synopsis_page)

    # --- 4.4 เนื้อหา (Chapters) ---
    chapters_list = []
    for chapter in chapters:
        c = epub.EpubHtml(title=chapter.title, file_name=f"chap_{chapter.id}.xhtml", lang='th')
        c.add_item(nav_css)
        safe_content = chapter.content if chapter.content else ""
        c.content = f'''<!DOCTYPE html>
<html lang="th"><head><title>{chapter.title}</title><link rel="stylesheet" type="text/css" href="nav.css"/></head>
<body>
    <div class="chapter-content">
        <h1>{chapter.title}</h1>
        <div>{safe_content}</div>
    </div>
</body></html>'''
        book.add_item(c)
        chapters_list.append(c)

    # ==========================================
    # 5. รวมเล่ม (TOC & Spine)
    # ==========================================
    
    # TOC (สารบัญ): รองปก -> เรื่องย่อ -> บทต่างๆ
    toc_list = [title_page]
    if synopsis_page:
        toc_list.append(synopsis_page)
    toc_list.extend(chapters_list)
    
    book.toc = toc_list

    # สร้างไฟล์ Nav
    book.add_item(epub.EpubNcx())
    nav_item = epub.EpubNav()
    book.add_item(nav_item)

    # Spine (ลำดับการเปิดอ่าน): ปก -> รองปก -> Nav -> เรื่องย่อ -> เนื้อหา
    final_spine = []
    if has_cover:
        final_spine.append(spine_items[0]) # ปก
    
    final_spine.append(title_page) # รองปก
    final_spine.append(nav_item)   # Nav (หน้าสารบัญ)
    
    if synopsis_page:
        final_spine.append(synopsis_page) # เรื่องย่อ (อยู่หลังสารบัญ)

    final_spine.extend(chapters_list) # เนื้อหา
    
    book.spine = final_spine

    # ==========================================
    # 6. Export
    # ==========================================
    epub_buffer = io.BytesIO()
    epub.write_epub(epub_buffer, book, {})
    epub_buffer.seek(0)

    response = HttpResponse(epub_buffer, content_type='application/epub+zip')
    filename = f"{novel.title}.epub"
    # ใช้ escape_uri_path เพื่อรองรับชื่อไฟล์ภาษาไทย
    response['Content-Disposition'] = f"attachment; filename*=UTF-8''{escape_uri_path(filename)}"
    return response

# ==================== Bookmark ====================

# 1. ฟังก์ชันสำหรับกดปุ่ม Bookmark (Toggle: กดครั้งแรกเก็บ กดอีกทีลบ)
@login_required
def toggle_bookmark(request, model_name, pk):
    # หา Model จากชื่อ (เช่น 'character', 'scene')
    try:
        content_type = ContentType.objects.get(model=model_name.lower())
    except ContentType.DoesNotExist:
        return redirect('plotcraft:home')

    # เช็คว่ามีอยู่แล้วไหม
    bookmark, created = Bookmark.objects.get_or_create(
        user=request.user,
        content_type=content_type,
        object_id=pk
    )

    if not created:
        # ถ้ามีอยู่แล้ว แปลว่า user กดซ้ำเพื่อ "ยกเลิก"
        bookmark.delete()
        messages.info(request, f'นำ {model_name} ออกจากรายการโปรดแล้ว')
    else:
        messages.success(request, f'บันทึก {model_name} ลงรายการโปรดแล้ว')

    # เด้งกลับไปหน้าเดิมที่ user กดมา
    return redirect(request.META.get('HTTP_REFERER', 'plotcraft:home'))

# 2. หน้าแสดงรายการ Bookmark ทั้งหมด
@login_required
def bookmark_list(request):
    # รับค่า type จาก URL (ถ้าไม่มีให้เป็น 'all')
    filter_type = request.GET.get('type', 'all')
    
    # ดึงข้อมูลพื้นฐาน
    bookmarks = Bookmark.objects.filter(user=request.user).select_related('content_type').order_by('-created_at')

    # ถ้ามีการเลือก type ให้กรองตาม content_type model
    if filter_type != 'all':
        bookmarks = bookmarks.filter(content_type__model=filter_type)

    return render(request, 'bookmark_list.html', {
        'bookmarks': bookmarks,
        'current_type': filter_type, # ส่งค่าปัจจุบันไปเพื่อทำ Highlight ปุ่มที่เลือกอยู่
    })

# ==================== RAG SERVICE INTEGRATION ====================

@csrf_exempt
@login_required
def ai_generate_scene(request, scene_id):
    """ API สำหรับกดปุ่ม 'Generate Draft' """
    if request.method == "POST":
        # 1. ดึงข้อมูล Scene มา (ต้องเป็นเจ้าของเท่านั้น)
        # หมายเหตุ: ใน models.py ของคุณ Scene ไม่ได้ผูกกับ User โดยตรง แต่ผูกผ่าน Project -> Owner
        # ดังนั้นต้องเช็คผ่าน project__owner
        scene = get_object_or_404(Scene, pk=scene_id, project__author=request.user)
        
        # 2. เรียก AI ให้ร่างให้
        draft_content = rag_service.generate_scene_draft(scene)
        
        # 3. ส่งเนื้อหากลับไป
        try:
             draft_content = rag_service.generate_scene_draft(scene)
             return JsonResponse({'draft': draft_content})
        except Exception as e:
             return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid method'}, status=405)

@csrf_exempt
@login_required
def ai_chat_general(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '')
            novel_id = data.get('novel_id')
            
            reply = rag_service.chat_with_editor(
                user_message, 
                novel_id=novel_id, 
                user_id=request.user.id
            )
            
            return JsonResponse({'reply': reply})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@csrf_exempt
@login_required
def ai_generate_character(request):
    """ API สำหรับ Gen ข้อมูลตัวละคร """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            concept = data.get('concept', '')
            
            # เรียก AI
            char_data = rag_service.generate_character_data(concept)
            
            if char_data:
                return JsonResponse({'success': True, 'data': char_data})
            else:
                return JsonResponse({'success': False, 'error': 'AI นึกไม่ออก ลองเปลี่ยนคำสั่งดูครับ'})
                
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)