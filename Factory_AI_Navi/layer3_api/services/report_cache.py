"""
layer3_api/services/report_cache.py
=====================================
진단 결과 인메모리 캐시 (PDF 다운로드용)

프로덕션에서는 Redis로 교체 예정.
"""

from collections import OrderedDict

_MAX_SIZE = 100

class _LRUCache(OrderedDict):
    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        if len(self) > _MAX_SIZE:
            self.popitem(last=False)

report_cache: dict[str, dict] = _LRUCache()
