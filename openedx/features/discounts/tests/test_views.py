"""Tests of openedx.features.discounts.views"""
# -*- coding: utf-8 -*-
import jwt

from django.test.client import Client
from django.urls import reverse

from xmodule.modulestore.tests.factories import CourseFactory
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from student.tests.factories import UserFactory, TEST_PASSWORD
from rest_framework.test import APIRequestFactory

from openedx.features.discounts.views import CourseUserDiscount


class TestCourseUserDiscount(ModuleStoreTestCase):
    """
    CourseUserDiscount should return a jwt with the information if this combination of user and
    course can receive a discount, and how much that discount should be.
    """

    def setUp(self):
        super(TestCourseUserDiscount, self).setUp()
        self.user = UserFactory.create()
        self.course = CourseFactory.create(run='test', display_name='test')
        self.client = Client()

    def test_url(self):
        """
        Test that the url hasn't changed
        """

        url = reverse('api_discounts:course_user_discount', kwargs={'course_key_string': unicode(self.course.id)})
        assert url == ('/api/discounts/course/' + unicode(self.course.id))

    def test_course_user_discount(self):
        """
        Test that the api returns a jwt with the discount information
        """
        self.client.login(username=self.user.username, password=TEST_PASSWORD)
        url = reverse('api_discounts:course_user_discount', kwargs={'course_key_string': unicode(self.course.id)})

        # the endpoint should return a 200 if all goes well
        response = self.client.get(reverse(
            'api_discounts:course_user_discount',
            kwargs={'course_key_string': unicode(self.course.id)}))
        assert response.status_code == 200

        # for now, it should always return false
        expected_payload = {'discount_applicable': False, 'discount_percent': 15}
        assert expected_payload['discount_applicable'] == response.data['discount_applicable']

        # make sure that the response matches the expected response
        response_payload = jwt.decode(response.data['jwt'], verify=False)
        assert all(item in response_payload.items() for item in expected_payload.items())

    def test_course_user_discount_no_user(self):
        """
        Test that the endpoint returns a 401 if there is no user signed in
        """
        url = reverse('api_discounts:course_user_discount', kwargs={'course_key_string': unicode(self.course.id)})

        # the endpoint should return a 401 because the user is not logged in
        response = self.client.get(reverse(
            'api_discounts:course_user_discount',
            kwargs={'course_key_string': unicode(self.course.id)}))
        assert response.status_code == 401
