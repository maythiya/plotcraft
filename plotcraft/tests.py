from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse

from .models import Bookmark, Chapter, Character, Item, Location, Novel, Timeline, User


class OwnershipAndRouteTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='owner', password='test-password')
        self.other = User.objects.create_user(username='other', password='test-password')
        self.novel = Novel.objects.create(title='Owner novel', author=self.owner)
        self.other_novel = Novel.objects.create(title='Other novel', author=self.other)
        self.chapter = Chapter.objects.create(novel=self.novel, title='Chapter one', order=1)
        self.other_chapter = Chapter.objects.create(novel=self.other_novel, title='Private chapter', order=1)
        self.character = Character.objects.create(name='Owner character', created_by=self.owner, project=self.novel)
        self.other_character = Character.objects.create(name='Private character', created_by=self.other, project=self.other_novel)
        self.location = Location.objects.create(name='Owner location', created_by=self.owner, project=self.novel)
        self.other_location = Location.objects.create(name='Private location', created_by=self.other, project=self.other_novel)
        self.item = Item.objects.create(name='Owner item', created_by=self.owner, project=self.novel)
        self.other_item = Item.objects.create(name='Private item', created_by=self.other, project=self.other_novel)
        self.timeline = Timeline.objects.create(title='Owner timeline', created_by=self.owner)
        self.other_timeline = Timeline.objects.create(title='Private timeline', created_by=self.other)

    def test_private_pages_require_login(self):
        protected_urls = [
            reverse('plotcraft:home'),
            reverse('plotcraft:worldbuilding_overview'),
            reverse('plotcraft:timeline_list'),
            reverse('plotcraft:timeline_detail', args=[self.timeline.id]),
        ]
        for url in protected_urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)

    def test_logout_redirects_to_landing_page(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse('plotcraft:logout'))
        self.assertRedirects(response, reverse('plotcraft:landing'))

    def test_worldbuilding_overview_renders_for_owner(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse('plotcraft:worldbuilding_overview'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Story universe')
        self.assertEqual(response.context['character_count'], 1)

    def test_worldbuilding_details_do_not_expose_other_users_objects(self):
        self.client.force_login(self.owner)
        private_urls = [
            reverse('plotcraft:character_detail', args=[self.other_character.id]),
            reverse('plotcraft:location_detail', args=[self.other_location.id]),
            reverse('plotcraft:item_detail', args=[self.other_item.id]),
            reverse('plotcraft:timeline_detail', args=[self.other_timeline.id]),
        ]
        for url in private_urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)

    def test_chapter_status_only_changes_owned_chapter(self):
        self.client.force_login(self.owner)
        denied = self.client.post(reverse('plotcraft:change_chapter_status', args=[self.other_chapter.id, 'finish']))
        self.assertEqual(denied.status_code, 404)
        invalid = self.client.post(reverse('plotcraft:change_chapter_status', args=[self.chapter.id, 'unknown']))
        self.assertEqual(invalid.status_code, 400)
        allowed = self.client.post(reverse('plotcraft:change_chapter_status', args=[self.chapter.id, 'finish']))
        self.assertEqual(allowed.status_code, 200)
        self.chapter.refresh_from_db()
        self.assertFalse(self.chapter.is_draft)

    def test_bookmark_requires_post_and_owned_object(self):
        self.client.force_login(self.owner)
        url = reverse('plotcraft:toggle_bookmark', args=['novel', self.novel.id])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url).status_code, 302)
        content_type = ContentType.objects.get_for_model(Novel)
        self.assertTrue(Bookmark.objects.filter(user=self.owner, content_type=content_type, object_id=self.novel.id).exists())

        other_url = reverse('plotcraft:toggle_bookmark', args=['novel', self.other_novel.id])
        self.assertEqual(self.client.post(other_url).status_code, 404)
