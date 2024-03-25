from django.db import models
from django.utils.text import slugify
from django.conf import settings
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from account.models import Account
from django.contrib.auth.models import User

def upload_location(instance, filename, **kwargs):
	file_path = 'blog/{author_id}/{title}-{filename}'.format(
		author_id=str(instance.author.id), title=str(instance.title), filename=filename)
	return file_path

class BlogPost(models.Model):
	title = models.CharField(max_length=50, null=False, blank=False)
	body = models.TextField(max_length=500, null=False, blank=False)
	image = models.ImageField(upload_to=upload_location, null=True, blank=True)
	date_published = models.DateTimeField(auto_now_add=True, verbose_name="date published")
	date_updated = models.DateTimeField(auto_now=True, verbose_name="date updated")
	author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
	slug = models.SlugField(blank=True, unique=True)
	tags = models.TextField(null=True, blank=True)

	def __str__(self):
		return self.title

@receiver(post_delete, sender=BlogPost)
def submission_delete(sender, instance, **kwargs):
	instance.image.delete(False)

def pre_save_blog_post_receiver(sender, instance, *args, **kwargs):
	if not instance.slug:
		instance.slug = slugify(instance.author.username + "-" + instance.title)

pre_save.connect(pre_save_blog_post_receiver, sender=BlogPost)

class Comment(models.Model):
    content = models.TextField()
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='user_comments'  # This related_name is for the reverse relationship from User to Comment
    )
    created_at = models.DateTimeField(auto_now_add=True)
    blog_post = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name='comments', null=True)

    def __str__(self):
        return f'Comment by {self.author.username} on {self.created_at}'




