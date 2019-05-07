"""
Unit tests for completing program course enrollments
once a social auth entry for the user is created.
"""
from django.test import TestCase
import mock
from opaque_keys.edx.keys import CourseKey
from social_django.models import UserSocialAuth
from testfixtures import LogCapture

from lms.djangoapps.program_enrollments.signals import logger
from lms.djangoapps.program_enrollments.tests.factories import ProgramCourseEnrollmentFactory, ProgramEnrollmentFactory
from organizations.tests.factories import OrganizationFactory
from openedx.core.djangoapps.content.course_overviews.tests.factories import CourseOverviewFactory
from student.models import CourseEnrollmentException
from student.tests.factories import UserFactory
from third_party_auth.tests.factories import SAMLProviderConfigFactory


class SocialAuthEnrollmentCompletionSignalTest(TestCase):
    """
    Test post-save handler on UserSocialAuth
    """

    def setUp(self):
        super(SocialAuthEnrollmentCompletionSignalTest, self).setUp()

        self.external_id = '0000'
        self.provider_slug = 'uox'
        self.course_keys = [
            CourseKey.from_string('course-v1:edX+DemoX+Test_Course'),
            CourseKey.from_string('course-v1:edX+DemoX+Another_Test_Course'),
        ]
        self.organization = OrganizationFactory.create()
        self.user = UserFactory.create()

        for course_key in self.course_keys:
            CourseOverviewFactory(id=course_key)
        SAMLProviderConfigFactory.create(organization=self.organization, slug=self.provider_slug)

    def _create_waiting_program_enrollment(self):
        return ProgramEnrollmentFactory.create(
            user=None,
            external_user_key=self.external_id
        )

    def _create_waiting_course_enrollments(self, program_enrollment):
        return [
            ProgramCourseEnrollmentFactory(
                program_enrollment=program_enrollment,
                course_enrollment=None,
                course_key=course_key
            )
            for course_key in self.course_keys
        ]

    def test_waiting_course_enrollments_completed(self):
        program_enrollment = self._create_waiting_program_enrollment()
        program_course_enrollments = self._create_waiting_course_enrollments(program_enrollment)

        UserSocialAuth.objects.create(
            user=self.user,
            uid='{0}:{1}'.format(self.provider_slug, self.external_id)
        )

        program_enrollment.refresh_from_db()
        self.assertEqual(program_enrollment.user, self.user)

        for program_course_enrollment in program_course_enrollments:
            program_course_enrollment.refresh_from_db()
            student_course_enrollment = program_course_enrollment.course_enrollment
            self.assertEqual(student_course_enrollment.user, self.user)
            self.assertEqual(student_course_enrollment.course.id, program_course_enrollment.course_key)

    def test_enrolled_with_no_course_enrollments(self):
        program_enrollment = self._create_waiting_program_enrollment()

        UserSocialAuth.objects.create(
            user=self.user,
            uid='{0}:{1}'.format(self.provider_slug, self.external_id)
        )

        program_enrollment.refresh_from_db()
        self.assertEqual(program_enrollment.user, self.user)

    def test_create_social_auth_with_no_waiting_enrollments(self):
        """
        No exceptions should be raised if there are no enrollments to update
        """
        UserSocialAuth.objects.create(
            user=self.user,
            uid='{0}:{1}'.format(self.provider_slug, self.external_id)
        )

    def test_create_social_auth_provider_has_no_organization(self):
        """
        No exceptions should be raised if provider is not linked to an organization
        """
        provider = SAMLProviderConfigFactory.create()
        UserSocialAuth.objects.create(
            user=self.user,
            uid='{0}:{1}'.format(provider.slug, self.external_id)
        )

    def test_create_social_auth_non_saml_provider(self):
        """
        No exceptions should be raised for a non-SAML uid or if a SAML provider cannot be found
        """
        UserSocialAuth.objects.create(
            user=self.user,
            uid='google-oauth-user@gmail.com'
        )
        UserSocialAuth.objects.create(
            user=self.user,
            uid='123:123:123'
        )

    def test_log_on_enrollment_failure(self):
        program_enrollment = self._create_waiting_program_enrollment()
        program_course_enrollments = self._create_waiting_course_enrollments(program_enrollment)

        with mock.patch('student.models.CourseEnrollment.enroll') as enrollMock:
            enrollMock.side_effect = CourseEnrollmentException('something has gone wrong')
            with LogCapture(logger.name) as log:
                UserSocialAuth.objects.create(
                    user=self.user,
                    uid='{0}:{1}'.format(self.provider_slug, self.external_id)
                )
                error_tmpl = u'Failed to enroll waiting program_course_enrollment={}: {}'
                log.check_present(
                    (
                        logger.name,
                        'CRITICAL',
                        error_tmpl.format(program_course_enrollments[0].id, 'something has gone wrong')
                    )
                )
