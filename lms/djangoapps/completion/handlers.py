"""
Signal handlers to trigger completion updates.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

from django.contrib.auth.models import User
from django.dispatch import receiver

from opaque_keys.edx.keys import CourseKey, UsageKey
from lms.djangoapps.grades.signals.signals import PROBLEM_WEIGHTED_SCORE_CHANGED
from xmodule.modulestore.django import modulestore

from .models import BlockCompletion
from . import waffle


@receiver(PROBLEM_WEIGHTED_SCORE_CHANGED)
def scorable_block_completion(sender, **kwargs):  # pylint: disable=unused-argument
    """
    When a problem is scored, submit a new BlockCompletion for that block.
    """
    course_key = CourseKey.from_string(kwargs['course_id'])
    block_key = UsageKey.from_string(kwargs['usage_id'])
    if not waffle.waffle().is_enabled(waffle.ENABLE_COMPLETION_TRACKING):
        return
    store = modulestore()
    block = store.get_item(block_key)
    if getattr(block, 'completion_method', 'scorable') != 'scorable':
        return
    if getattr(block, 'has_custom_completion', False):
        return
    user = User.objects.get(id=kwargs['user_id'])
    if kwargs.get('score_deleted'):
        completion = 0.0
    else:
        completion = 1.0
    BlockCompletion.objects.submit_completion(
        user=user,
        course_key=course_key,
        block_key=block_key,
        completion=completion,
    )