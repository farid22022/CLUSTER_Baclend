from admins.models import Page

def run():
    pages = [
        'home', 'events', 'projects', 'blogs', 'resources', 'alumni', 'contact', 'email'
    ]
    for p in pages:
        Page.objects.get_or_create(name=p)