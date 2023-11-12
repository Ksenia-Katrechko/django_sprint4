from django.core.paginator import Paginator
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.timezone import now
from django.views.generic import (CreateView, DeleteView, DetailView, ListView,
                                  UpdateView)

from .constants import PAGINATE_BY
from .forms import CommentForm, PostForm, ProfileForm
from .models import Category, Comment, Post, User


def annotate_comment_count(posts):
    return posts.select_related(
        'author',
        'category',
        'location'
    ).annotate(comment_count=Count('comment')).order_by('-pub_date')


def pagination(queryset, page_by, page_number):
    paginator = Paginator(queryset, page_by)
    page_obj = paginator.get_page(page_number)
    return page_obj


def filter_posts(posts):
    return posts.filter(is_published=True,
                        category__is_published=True,
                        pub_date__lte=timezone.now())


class PostListView(ListView):
    template_name = 'blog/index.html'
    model = Post
    ordering = '-pub_date'
    paginate_by = PAGINATE_BY

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = filter_posts(queryset)
        queryset = annotate_comment_count(queryset)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        page_number = self.request.GET.get('page')
        page_obj = pagination(self.object_list, self.paginate_by, page_number)

        context['page_obj'] = page_obj
        return context


class CategoryPostsView(ListView):
    template_name = 'blog/category.html'
    context_object_name = 'page_obj'
    paginate_by = PAGINATE_BY
    model = Post

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category_slug = self.kwargs['category_slug']
        category = get_object_or_404(
            Category,
            is_published=True,
            slug=category_slug
        )
        post_list = category.posts.filter(
            is_published=True,
            pub_date__lte=now()
        )

        post_list = annotate_comment_count(post_list)

        page_number = self.request.GET.get('page')
        page_obj = pagination(post_list, self.paginate_by, page_number)

        context['category'] = category
        context['page_obj'] = page_obj

        return context


class PostDetailView(DetailView):

    model = Post
    template_name = 'blog/detail.html'
    context_object_name = 'post'
    pk_url_kwarg = 'post_id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CommentForm()
        context['comments'] = self.object.comment.select_related('author')

        if not self.object.is_published and (
                self.object.author != self.request.user
        ):
            raise Http404('Этот пост не существует.')

        return context


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        url = reverse(
            'blog:profile',
            args=(self.request.user.get_username(),)
        )
        return url

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class EditPostView(LoginRequiredMixin, UpdateView):
    model = Post
    pk_url_kwarg = 'post_id'
    form_class = PostForm
    template_name = 'blog/create.html'

    def get_success_url(self):
        return reverse(
            'blog:post_detail',
            args=(self.kwargs['post_id'],)
        )

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.author != self.request.user:
            return redirect('blog:post_detail', self.kwargs['post_id'])
        return super().dispatch(request, *args, **kwargs)


class PostUpdateView(LoginRequiredMixin, UpdateView):

    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'
    pk_url_kwarg = 'post_id'
    query_pk_and_slug = False

    def dispatch(self, request, *args, **kwargs):
        self.post_id = kwargs['post_id']
        instance = get_object_or_404(Post, id=self.post_id)
        if instance.author != request.user:
            return redirect('blog:post_detail', post_id=self.post_id)
        self.kwargs[self.pk_url_kwarg] = instance.pk
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('blog:post_detail', kwargs={'post_id': self.object.pk})


class DeletePostView(LoginRequiredMixin, DeleteView):
    model = Post
    pk_url_kwarg = 'post_id'
    template_name = 'blog/create.html'
    success_url = reverse_lazy('blog:index')

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(author=self.request.user)


class EditProfileView(LoginRequiredMixin, UpdateView):
    model = User
    template_name = 'blog/user.html'
    form_class = ProfileForm
    slug_url_kwarg = 'name'
    slug_field = 'username'

    def get_object(self, queryset=None):

        return self.request.user

    def get_success_url(self):
        return reverse_lazy(
            'blog:profile',
            kwargs={'name': self.request.user.username}
        )


class UserProfileView(DetailView):
    model = User
    template_name = 'blog/profile.html'
    context_object_name = 'profile'
    slug_url_kwarg = 'name'
    slug_field = 'username'
    paginate_by = PAGINATE_BY

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile_posts = self.object.posts.all()

        if self.object != self.request.user:
            profile_posts = profile_posts.filter(is_published=True)

        profile_posts = annotate_comment_count(profile_posts)

        page_number = self.request.GET.get('page')
        page_obj = pagination(profile_posts, self.paginate_by, page_number)

        context['page_obj'] = page_obj
        return context


class AddCommentView(LoginRequiredMixin, CreateView):

    model = Comment
    form_class = CommentForm
    template_name = 'blog/comment.html'

    def form_valid(self, form):
        post_id = self.kwargs['post_id']
        post = get_object_or_404(Post, id=post_id)

        if not post.is_published:
            raise Http404('The post has been unpublished.')

        form.instance.author = self.request.user
        form.instance.post = post
        return super().form_valid(form)

    def get_success_url(self):
        post_id = self.kwargs['post_id']
        return reverse('blog:post_detail', kwargs={'post_id': post_id})


class CommentSuccessUrlMixin:
    def get_success_url(self):
        post_id = self.kwargs['post_id']
        return reverse('blog:post_detail', kwargs={'post_id': post_id})


class EditCommentView(LoginRequiredMixin, CommentSuccessUrlMixin, UpdateView):

    model = Comment
    form_class = CommentForm
    template_name = 'blog/comment.html'
    pk_url_kwarg = 'comment_id'
    context_object_name = 'comment'

    def dispatch(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.author != request.user:
            post_id = self.kwargs['post_id']
            return redirect('blog:post_detail', post_id=post_id)
        return super().dispatch(request, *args, **kwargs)


class DeleteCommentView(LoginRequiredMixin, CommentSuccessUrlMixin,
                        DeleteView):

    model = Comment
    template_name = 'blog/comment.html'
    pk_url_kwarg = 'comment_id'
    context_object_name = 'comment'

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.author != request.user:
            return redirect('blog:post_detail', post_id=self.kwargs['post_id'])
        instance.delete()
        return redirect(self.get_success_url())
