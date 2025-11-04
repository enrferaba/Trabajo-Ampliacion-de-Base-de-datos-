from rest_framework.throttling import SimpleRateThrottle

from .services.redis_service import rate_limit_hit


class UserIPRateThrottle(SimpleRateThrottle):
    scope = "user"

    def get_cache_key(self, request, view):
        ident = request.user.id if request.user and request.user.is_authenticated else self.get_ident(request)
        return f"throttle:{self.scope}:{ident}"

    def allow_request(self, request, view):
        cache_key = self.get_cache_key(request, view)
        hit_limit = rate_limit_hit(self.scope, cache_key)
        if hit_limit:
            return False
        return super().allow_request(request, view)
