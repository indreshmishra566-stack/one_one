from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    skills_have = models.TextField(blank=True, help_text="Comma-separated skills you can teach")
    skills_want = models.TextField(blank=True, help_text="Comma-separated skills you want to learn")
    bio = models.TextField(blank=True)
    is_live = models.BooleanField(default=False)  # currently in live queue

    def get_skills_have_list(self):
        return [s.strip().lower() for s in self.skills_have.split(',') if s.strip()]

    def get_skills_want_list(self):
        return [s.strip().lower() for s in self.skills_want.split(',') if s.strip()]

    def __str__(self):
        return f"{self.user.username}'s Profile"


class Match(models.Model):
    user1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='matches_as_user1')
    user2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='matches_as_user2')
    score = models.FloatField(default=0.0)   # smart match score
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user1', 'user2')

    def __str__(self):
        return f"{self.user1.username} ↔ {self.user2.username} ({self.score:.2f})"


class Message(models.Model):
    """Persistent messages between matched users."""
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.sender.username} → {self.receiver.username}: {self.content[:40]}"


class LiveMessage(models.Model):
    """Ephemeral messages from a live session room."""
    room_id = models.CharField(max_length=64)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='live_messages')
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"[{self.room_id}] {self.sender.username}: {self.content[:40]}"
