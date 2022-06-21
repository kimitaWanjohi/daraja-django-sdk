from django.db import models

class AccessToken(models.Model):
    token = models.CharField(max_length=30)

    def __str__(self) -> str:
        return self.token

