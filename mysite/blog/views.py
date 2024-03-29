from django.contrib.postgres.search import TrigramSimilarity
from django.db.models.functions import Greatest
from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView
from django.core.mail import send_mail
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from taggit.models import Tag
from .models import Post, Comment
from .forms import EmailPostForm, CommentForm, SearchForm

class PostListView(ListView):
    queryset = Post.published.all()
    context_object_name = 'posts'
    paginate_by = 3
    template_name = 'blog/post/list.html'

def post_list(request, tag_slug=None):
    object_list = Post.published.all()
    tag = None

    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        object_list = object_list.filter(tags__in=[tag])

    paginator = Paginator(object_list, 3)
    page = request.GET.get('page')

    try:
        posts = paginator.page(page)
    except PageNotAnInteger:
        posts = paginator.page(1)
    except EmptyPage:
        posts = paginator.page(paginator.num_pages)

    return render(request, 'blog/post/list.html', {'page': page, 'posts': posts, 'tag': tag})

def post_detail(request, year, month, day, post):
    post = get_object_or_404(Post, slug=post, status='published',       
                            publish__year=year, publish__month=month, publish__day=day)
    
    # Список активных комментариев для этой статьи.
    comments = post.comments.filter(active=True)
    new_comment = None
    if request.method == 'POST':
        # Пользователь отправил комментарий.
        comment_form = CommentForm(data=request.POST)
        if comment_form.is_valid():
            # Создаем комментарий, но пока не сохраняем в базе данных.
            new_comment = comment_form.save(commit=False)
            # Привязываем комментарий к текущей статье.
            new_comment.post = post
            # Сохраняем комментарий в базе данных.
            new_comment.save() 
    else:
        comment_form = CommentForm()
    
    return render(request, 'blog/post/detail.html', {'post': post, 
                                                    'comments': comments,
                                                    'new_comment': new_comment,
                                                    'comment_form': comment_form})

def post_share(request, post_id):
    post = get_object_or_404(Post, id=post_id,status='published')
    sent = False
    
    if request.method == 'POST':
        form = EmailPostForm(request.POST)

        if form.is_valid():
            cd = form.cleaned_data
            post_url = request.build_absolute_uri(post.get_absolute_url())
            subject = '{} рекомендует вам прочесть.'.format(cd['name'], post.title)
            message = 'Пост "{}" доступен по ссылке: {}\n\n{} пишет:\n\n{}'.format(post.title, post_url, cd['name'], cd['comments'])
            send_mail(subject, message, 'admin@myblog.com', [cd['to']])
            sent = True
            return render(request, 'blog/post/share.html',
                        {'post': post, 'form': form, 'sent': sent, 'post_url': post_url})
    else:
        form = EmailPostForm()
        return render(request, 'blog/post/share.html',
                        {'post': post, 'form': form, 'sent': sent})

def post_search(request):
    form = SearchForm()
    query = None
    results = []
    if 'query' in request.GET:
        form = SearchForm(request.GET)
    if form.is_valid():
        query = form.cleaned_data['query']
        results = Post.objects.annotate(        
            similarity=Greatest(
                TrigramSimilarity('title', query),
                TrigramSimilarity('body', query),
            )
        ).filter(similarity__gt=0.3).order_by('-similarity')
        
    return render(request, 'blog/post/search.html', {'form': form,      
                                                     'query': query,
                                                     'results': results})
