from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

CREATE_USER_URL = reverse('user:create')
TOKEN_URL = reverse('user:token')
ME_URL = reverse('user:me')


def create_user(**param):
    return get_user_model().objects.create_user(**param)


class PublicUserApiTests(TestCase):
    '''Test the users API (public)'''

    def setUp(self):
        self.client = APIClient()

    def test_create_valid_user_success(self):
        '''Test creating user with valid user successful'''
        payload = {
            'email': 'test@baus.com',
            'password': 'test123',
            'name': 'Test name'
        }
        result = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(result.status_code, status.HTTP_201_CREATED)
        user = get_user_model().objects.get(**result.data)
        self.assertTrue(user.check_password(payload['password']))
        self.assertNotIn('password', result.data)

    def test_user_exists(self):
        '''Test creating the user that already exists fails'''
        payload = {
            'email': 'test@baus.com',
            'password': 'test123',
            'name': 'Test',
        }
        create_user(**payload)

        result = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(result.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_too_short(self):
        '''Test that the password must be more then 5 characters'''
        payload = {
            'email': 'test@baus.com',
            'password': 'py',
            'name': 'Test',
        }
        result = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(result.status_code, status.HTTP_400_BAD_REQUEST)
        user_exists = get_user_model().objects.filter(
            email=payload['email']
        ).exists()
        self.assertFalse(user_exists)

    def test_create_token_for_user(self):
        '''Test that the token is created for user'''
        payload = {'email': 'test@baus.com', "password": 'TestPass123'}
        create_user(**payload)
        response = self.client.post(TOKEN_URL, payload)

        self.assertIn('token', response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_token_invalid_credentials(self):
        '''Test that token is not created that invalid token is created'''
        payload = {'email': 'test@baus.com', "password": 'TestPass123'}
        create_user(**payload)
        wrong_payload = {'email': 'test@baus.com', "password": 'TestPass1234'}
        response = self.client.post(TOKEN_URL, wrong_payload)

        self.assertNotIn('token', response.data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_token_no_user(self):
        '''Test that token is not created for user that doesn't exists'''
        payload = {'email': 'test@baus.com', "password": 'TestPass123'}
        response = self.client.post(TOKEN_URL, payload)

        self.assertNotIn('token', response.data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_token_missing_field(self):
        '''Test that email and password are pased'''
        payload = {'email': 'test@baus.com', "password": ''}
        res = self.client.post(TOKEN_URL, payload)

        self.assertNotIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_user_unauthorized(self):
        '''Test that authentication is requeired for users'''
        res = self.client.get(ME_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateUserApiTests(TestCase):
    '''Test API requests that require authentication'''

    def setUp(self):
        self.user = create_user(
            email='test@baus.com',
            password='testpass123',
            name='Name'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_retrieve_profile_success(self):
        '''Test retrieving profile for logged in user'''
        result = self.client.get(ME_URL)

        self.assertEqual(result.status_code, status.HTTP_200_OK)
        self.assertEqual(result.data, {
            'email': self.user.email,
            'name': self.user.name
        })

    def test_post_me_not_allowed(self):
        '''Test that post is not allowed on the me url'''
        res = self.client.post(ME_URL, {})

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_user_profile(self):
        '''Test updating the user profile for authenticated user'''
        # This should be different than
        # values from setUp / create_user
        payload = {'name': 'new_name', 'password': 'newpass123'}

        result = self.client.patch(ME_URL, payload)

        # updating data in db
        self.user.refresh_from_db()

        self.assertEqual(self.user.name, payload['name'])
        self.assertTrue(self.user.check_password(payload['password']))
        self.assertEqual(result.status_code, status.HTTP_200_OK)
