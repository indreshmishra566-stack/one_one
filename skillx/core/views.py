from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse

from .models import Profile, Match, Message, LiveMessage
from .forms import SignupForm, ProfileForm, MessageForm
from .matching import compute_match


# ── Auth ──────────────────────────────────────────────────────────────────────

def home(request):
    if request.user.is_authenticated:
        return redirect('live_lobby')
    return render(request, 'core/home.html')


def signup_view(request):
    if request.user.is_authenticated:
        return redirect('edit_profile')
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome to SkillX, {user.username}! Set up your skills to go live.')
            return redirect('edit_profile')
    else:
        form = SignupForm()
    return render(request, 'core/signup.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('live_lobby')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('live_lobby')
        messages.error(request, 'Invalid username or password.')
    return render(request, 'core/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


# ── Profile ───────────────────────────────────────────────────────────────────

@login_required
def edit_profile(request):
    profile = request.user.profile
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile saved! Ready to go live.')
            return redirect('live_lobby')
    else:
        form = ProfileForm(instance=profile)
    return render(request, 'core/edit_profile.html', {'form': form, 'profile': profile})


# ── Live System ───────────────────────────────────────────────────────────────

@login_required
def live_lobby(request):
    """Main landing — shows Go Live button and stats."""
    profile = request.user.profile
    has_skills = bool(profile.skills_have and profile.skills_want)

    from .consumers.queue_consumer import LIVE_QUEUE
    queue_size = len(LIVE_QUEUE)

    my_matches = Match.objects.filter(
        Q(user1=request.user) | Q(user2=request.user)
    ).count()

    return render(request, 'core/live_lobby.html', {
        'profile': profile,
        'has_skills': has_skills,
        'queue_size': queue_size,
        'my_matches': my_matches,
    })


@login_required
def live_room(request, room_id):
    """The actual live chat room after matching."""
    messages_qs = LiveMessage.objects.filter(room_id=room_id).select_related('sender')[:100]
    return render(request, 'core/live_room.html', {
        'room_id': room_id,
        'past_messages': messages_qs,
    })


# ── Smart Match (browse) ──────────────────────────────────────────────────────

@login_required
def find_match(request):
    current_user = request.user
    current_profile = current_user.profile

    if not current_profile.skills_have or not current_profile.skills_want:
        messages.warning(request, 'Fill in your skills first.')
        return redirect('edit_profile')

    all_users = User.objects.exclude(id=current_user.id).select_related('profile')
    matched_users = []

    for other_user in all_users:
        try:
            op = other_user.profile
        except Profile.DoesNotExist:
            continue
        if not op.skills_have or not op.skills_want:
            continue

        result = compute_match(
            current_profile.skills_have, current_profile.skills_want,
            op.skills_have, op.skills_want,
        )

        if result['is_match']:
            u1, u2 = sorted([current_user, other_user], key=lambda u: u.id)
            match, _ = Match.objects.get_or_create(
                user1=u1, user2=u2,
                defaults={'score': result['score']}
            )
            # Update score
            if match.score != result['score']:
                match.score = result['score']
                match.save(update_fields=['score'])

            matched_users.append({
                'match': match,
                'other_user': other_user,
                'other_profile': op,
                'result': result,
                'score_pct': int(result['score'] * 100),
            })

    matched_users.sort(key=lambda x: x['result']['score'], reverse=True)

    if matched_users:
        return render(request, 'core/match.html', {
            'matched_users': matched_users,
            'current_profile': current_profile,
        })
    return render(request, 'core/no_match.html', {'current_profile': current_profile})


# ── Persistent Chat ───────────────────────────────────────────────────────────

@login_required
def chat(request, username):
    other_user = get_object_or_404(User, username=username)
    current_user = request.user

    if other_user == current_user:
        return redirect('live_lobby')

    u1, u2 = sorted([current_user, other_user], key=lambda u: u.id)
    match = Match.objects.filter(user1=u1, user2=u2).first()
    if not match:
        messages.error(request, "You can only chat with your matches.")
        return redirect('find_match')

    # POST handled by WebSocket now; keep form for JS-disabled fallback
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if content:
            Message.objects.create(sender=current_user, receiver=other_user, content=content)
        return redirect('chat', username=username)

    conversation = Message.objects.filter(
        Q(sender=current_user, receiver=other_user) |
        Q(sender=other_user, receiver=current_user)
    ).order_by('timestamp')

    form = MessageForm()
    return render(request, 'core/chat.html', {
        'other_user': other_user,
        'other_profile': other_user.profile,
        'conversation': conversation,
        'form': form,
        'match': match,
    })


@login_required
def my_matches(request):
    current_user = request.user
    matches = Match.objects.filter(
        Q(user1=current_user) | Q(user2=current_user)
    ).select_related('user1', 'user2').order_by('-score', '-created_at')

    match_data = []
    for match in matches:
        other = match.user2 if match.user1 == current_user else match.user1
        match_data.append({'match': match, 'other_user': other})

    return render(request, 'core/my_matches.html', {'match_data': match_data})


# ── API ───────────────────────────────────────────────────────────────────────

@login_required
def queue_status(request):
    """JSON endpoint — current queue size for lobby display."""
    from .consumers.queue_consumer import LIVE_QUEUE
    return JsonResponse({'queue_size': len(LIVE_QUEUE)})
