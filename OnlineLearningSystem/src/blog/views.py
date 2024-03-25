from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.http import HttpResponse
from blog.models import BlogPost, Comment
from blog.forms import CreateBlogPostForm, UpdateBlogPostForm, CommentForm
from account.models import Account
from quizzes.models import Quiz, Attempt
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
import spacy

# spaCy's English language model
nlp = spacy.load("en_core_web_sm")



def generate_tags(text):
    doc = nlp(text)
    tags = set([token.text.lower() for token in doc if token.pos_ in ["NOUN", "PROPN", "ADJ", "VERB"]])
    return list(tags)

def create_blog_view(request):
    context = {}
    user = request.user
    if not user.is_authenticated:
        return redirect('must_authenticate')

    if request.method == 'POST':
        form = CreateBlogPostForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.author = request.user
            combined_text = obj.title + ' ' + obj.body
            obj.tags = ', '.join(generate_tags(combined_text))  # Automatically generate tags
            obj.save()
            return redirect('blog:detail', slug=obj.slug)  # Adjust the redirect as needed
    else:
        form = CreateBlogPostForm()

    context['form'] = form
    return render(request, "blog/create_blog.html", context)


def detail_blog_view(request, slug):
    context = {}
    blog_post = get_object_or_404(BlogPost, slug=slug)
    comments = blog_post.comments.all()

    if request.method == 'POST':
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            new_comment = comment_form.save(commit=False)
            new_comment.blog_post = blog_post
            new_comment.author = request.user
            new_comment.save()
            return redirect('blog:detail', slug=slug)
    else:
        comment_form = CommentForm()

    context['blog_post'] = blog_post
    context['comments'] = comments
    context['comment_form'] = comment_form

    return render(request, 'blog/detail_blog.html', context)

def edit_blog_view(request, slug):
    context = {}
    user = request.user
    if not user.is_authenticated:
        return redirect("must_authenticated")

    blog_post = get_object_or_404(BlogPost, slug=slug)

    if blog_post.author != user:
        return HttpResponse("You cannot edit another user's post")

    if request.POST:
        form = UpdateBlogPostForm(request.POST or None, request.FILES or None, instance=blog_post)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.save()
            context['success_message'] = 'Post updated!!!!!'
            blog_post = obj

    form = UpdateBlogPostForm(
        initial={
            "title": blog_post.title,
            "body": blog_post.body,
            "image": blog_post.image,
        }
    )

    context['form'] = form
    return render(request, 'blog/edit_blog.html', context)

def get_blog_queryset(query=None):
    queryset = []
    queries = query.split(" ")
    for q in queries:
        posts = BlogPost.objects.filter(
            Q(title__icontains=q) |
            Q(body__icontains=q)
        ).distinct()
        for post in posts:
            queryset.append(post)
    return list(set(queryset))







