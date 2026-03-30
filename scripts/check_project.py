import os
import sys
import json

# ensure project root is on sys.path (script lives in scripts/)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
import django

django.setup()

from plotcraft.models import Novel, Character, Item

def main():
    pid = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    try:
        p = Novel.objects.get(id=pid)
    except Novel.DoesNotExist:
        print(json.dumps({"error": "Novel.DoesNotExist", "id": pid}))
        return

    chars_qs = Character.objects.filter(project=p)
    items_qs = Item.objects.filter(project=p)

    chars = list(chars_qs.values('id', 'name', 'created_by_id'))
    items = list(items_qs.values('id', 'name', 'created_by_id'))

    out = {
        'project_id': pid,
        'project_title': p.title,
        'characters_count': chars_qs.count(),
        'characters': chars,
        'items_count': items_qs.count(),
        'items': items,
    }

    print(json.dumps(out, ensure_ascii=False))

if __name__ == '__main__':
    main()
