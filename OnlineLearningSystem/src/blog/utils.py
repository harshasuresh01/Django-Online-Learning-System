# blog/utils.py

# from django.db.models import Q
# from .models import BlogPost

# def get_blog_queryset(query=None):
#     queryset = []
#     queries = query.split(" ")
#     for q in queries:
#         posts = BlogPost.objects.filter(
#             Q(title__icontains=q) |
#             Q(body__icontains=q)
#         ).distinct()
#         for post in posts:
#             queryset.append(post)
#     return list(set(queryset))
