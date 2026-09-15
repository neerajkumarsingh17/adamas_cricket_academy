"""Only used via @pytest.mark.urls(...) in test_module_scoped_viewset.py —
DRF's @action(verb=...) override is only ever applied by a real router, not
by a bare ViewSet.as_view({...}) call.
"""

from rest_framework.routers import SimpleRouter

from .module_scoped_viewset_support import EnquiryStandInViewSet

router = SimpleRouter()
router.register("stand-in", EnquiryStandInViewSet, basename="stand-in")

urlpatterns = router.urls
