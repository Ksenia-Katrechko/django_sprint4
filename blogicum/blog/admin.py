from django.contrib import admin
from django.contrib.admin.decorators import register

from blog.models import Category, Location, Post


class ModelAdmin(admin.ModelAdmin):
    pass


register(Category, Location, Post)(ModelAdmin)
