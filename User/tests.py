from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from Authentication.models import User
from Provider.models import CoachProfile, Service, Blog, Product
from Payments.models import ServiceBooking
from User.models import CoachRating, AppRating

class CoachRatingAPITests(APITestCase):

    def setUp(self):
        # Create user / customer
        self.customer = User.objects.create_user(
            email="customer@example.com",
            password="password123",
            full_name="John Customer",
            role="User"
        )
        # Create coach / provider user
        self.provider_user = User.objects.create_user(
            email="provider@example.com",
            password="password123",
            full_name="Jane Coach",
            role="Provider"
        )
        # Create Coach Profile
        self.coach_profile = CoachProfile.objects.create(
            user=self.provider_user,
            about="Fitness Coach",
            is_completed=True,
            status="approved"
        )
        # Rating data
        self.rating_data = {
            "rating": 5,
            "review": "Excellent guidance!"
        }

    def test_review_fails_for_non_existent_coach(self):
        self.client.force_authenticate(user=self.customer)
        url = reverse('coach-profile-review', kwargs={'coach_id': 9999})
        response = self.client.post(url, self.rating_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(response.data['success'])
        self.assertEqual(response.data['message'], "Coach profile not found.")

    def test_review_fails_when_no_booking_exists(self):
        self.client.force_authenticate(user=self.customer)
        url = reverse('coach-profile-review', kwargs={'coach_id': self.coach_profile.id})
        response = self.client.post(url, self.rating_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertEqual(response.data['message'], "You can only review this coach after completing a booking with them.")

    def test_review_fails_when_booking_not_completed(self):
        # Create a pending booking
        ServiceBooking.objects.create(
            user=self.customer,
            coach=self.provider_user,
            amount=Decimal("100.00"),
            currency="USD",
            status="pending",
            payment_status="paid"
        )
        
        self.client.force_authenticate(user=self.customer)
        url = reverse('coach-profile-review', kwargs={'coach_id': self.coach_profile.id})
        response = self.client.post(url, self.rating_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertEqual(response.data['message'], "You can only review this coach after completing a booking with them.")

    def test_review_succeeds_when_booking_completed(self):
        # Create a completed booking
        ServiceBooking.objects.create(
            user=self.customer,
            coach=self.provider_user,
            amount=Decimal("100.00"),
            currency="USD",
            status="completed",
            payment_status="paid"
        )
        
        self.client.force_authenticate(user=self.customer)
        url = reverse('coach-profile-review', kwargs={'coach_id': self.coach_profile.id})
        response = self.client.post(url, self.rating_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['message'], "Rating submitted successfully.")
        
        # Verify database record
        rating_obj = CoachRating.objects.filter(coach=self.coach_profile, user=self.customer).first()
        self.assertIsNotNone(rating_obj)
        self.assertEqual(rating_obj.rating, 5)
        self.assertEqual(rating_obj.review, "Excellent guidance!")

    def test_duplicate_review_fails(self):
        # Create a completed booking
        ServiceBooking.objects.create(
            user=self.customer,
            coach=self.provider_user,
            amount=Decimal("100.00"),
            currency="USD",
            status="completed",
            payment_status="paid"
        )
        # Create existing rating
        CoachRating.objects.create(
            coach=self.coach_profile,
            user=self.customer,
            rating=3,
            review="Average service"
        )
        
        self.client.force_authenticate(user=self.customer)
        url = reverse('coach-profile-review', kwargs={'coach_id': self.coach_profile.id})
        response = self.client.post(url, self.rating_data, format='json')
        
        # Verify it fails because user has already reviewed this coach
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertEqual(response.data['message'], "You have already submitted a review for this coach.")


class AppRatingAPITests(APITestCase):

    def setUp(self):
        # Create users
        self.user1 = User.objects.create_user(
            email="user1@example.com",
            password="password123",
            full_name="User One",
            role="User"
        )
        self.user2 = User.objects.create_user(
            email="user2@example.com",
            password="password123",
            full_name="User Two",
            role="User"
        )
        self.rating_url = reverse('app-rating')

    def test_submit_rating_succeeds(self):
        self.client.force_authenticate(user=self.user1)
        data = {"rating": 5, "review": "Awesome app!"}
        response = self.client.post(self.rating_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['message'], "App rating submitted successfully.")

        # Verify in database
        rating = AppRating.objects.filter(user=self.user1).first()
        self.assertIsNotNone(rating)
        self.assertEqual(rating.rating, 5)
        self.assertEqual(rating.review, "Awesome app!")

    def test_submit_duplicate_rating_fails(self):
        # Create an initial rating
        AppRating.objects.create(user=self.user1, rating=4, review="Good app.")

        self.client.force_authenticate(user=self.user1)
        data = {"rating": 5, "review": "Trying to rate again"}
        response = self.client.post(self.rating_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertEqual(response.data['message'], "You have already submitted a rating for this app.")

    def test_get_rating_stats(self):
        # Initial stats check when no ratings exist
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.rating_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['average_rating'], 0)
        self.assertEqual(response.data['data']['total_ratings'], 0)
        self.assertEqual(response.data['data']['has_rated'], False)
        self.assertIsNone(response.data['data']['user_rating'])

        # Create ratings
        AppRating.objects.create(user=self.user1, rating=5, review="Excellent!")
        AppRating.objects.create(user=self.user2, rating=3, review="Okay.")

        # Get stats for user1 (has rated)
        response = self.client.get(self.rating_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['average_rating'], 4.0)
        self.assertEqual(response.data['data']['total_ratings'], 2)
        self.assertEqual(response.data['data']['has_rated'], True)
        self.assertEqual(response.data['data']['user_rating']['rating'], 5)

        # Get stats for a guest or user who hasn't rated
        user3 = User.objects.create_user(
            email="user3@example.com",
            password="password123",
            full_name="User Three",
            role="User"
        )
        self.client.force_authenticate(user=user3)
        response = self.client.get(self.rating_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['average_rating'], 4.0)
        self.assertEqual(response.data['data']['total_ratings'], 2)
        self.assertEqual(response.data['data']['has_rated'], False)
        self.assertIsNone(response.data['data']['user_rating'])


class CoachProfileOrderingTests(APITestCase):

    def setUp(self):
        # Create a user to authenticate
        self.customer = User.objects.create_user(
            email="customer_test@example.com",
            password="password123",
            full_name="John Customer",
            role="User"
        )
        # Create coach 1 (average rating: 5)
        self.user_coach1 = User.objects.create_user(
            email="coach1@example.com",
            password="password123",
            full_name="Coach One",
            role="Provider"
        )
        self.profile_coach1 = CoachProfile.objects.create(
            user=self.user_coach1,
            about="Fitness Coach 1",
            is_completed=True,
            status="approved"
        )
        # Create coach 2 (average rating: 3)
        self.user_coach2 = User.objects.create_user(
            email="coach2@example.com",
            password="password123",
            full_name="Coach Two",
            role="Provider"
        )
        self.profile_coach2 = CoachProfile.objects.create(
            user=self.user_coach2,
            about="Fitness Coach 2",
            is_completed=True,
            status="approved"
        )
        # Create coach 3 (average rating: 0)
        self.user_coach3 = User.objects.create_user(
            email="coach3@example.com",
            password="password123",
            full_name="Coach Three",
            role="Provider"
        )
        self.profile_coach3 = CoachProfile.objects.create(
            user=self.user_coach3,
            about="Fitness Coach 3",
            is_completed=True,
            status="approved"
        )

        # Submit reviews for coach 1
        CoachRating.objects.create(coach=self.profile_coach1, user=self.customer, rating=5, review="Great!")
        # Submit reviews for coach 2
        CoachRating.objects.create(coach=self.profile_coach2, user=self.customer, rating=3, review="Okay.")

    def test_coach_list_ordered_by_rating_descending(self):
        self.client.force_authenticate(user=self.customer)
        url = reverse('coach-profile')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        coaches = response.data['data']
        self.assertEqual(len(coaches), 3)

        # Assert correct ordering: coach1 (5.0), coach2 (3.0), coach3 (0.0)
        self.assertEqual(coaches[0]['id'], self.profile_coach1.id)
        self.assertEqual(coaches[0]['avg_rating'], 5.0)

        self.assertEqual(coaches[1]['id'], self.profile_coach2.id)
        self.assertEqual(coaches[1]['avg_rating'], 3.0)

        self.assertEqual(coaches[2]['id'], self.profile_coach3.id)
        self.assertEqual(coaches[2]['avg_rating'], 0.0)


class CoachProfileDetailAPITests(APITestCase):

    def setUp(self):
        # Create categories
        self.category = Category.objects.create(name="Business", description="Business coaching")
        
        # Create user / customer
        self.customer = User.objects.create_user(
            email="customer@example.com",
            password="password123",
            full_name="John Customer",
            role="User"
        )
        
        # Create coach / provider user
        self.provider_user = User.objects.create_user(
            email="provider@example.com",
            password="password123",
            full_name="Sarah Chen",
            role="Provider"
        )
        
        # Create Coach Profile
        self.coach_profile = CoachProfile.objects.create(
            user=self.provider_user,
            about="Executive Business Coach",
            is_completed=True,
            status="approved"
        )
        self.coach_profile.categories.add(self.category)

        # Create published service (session)
        self.service_published = Service.objects.create(
            coach=self.provider_user,
            title="Strategy Session",
            category=self.category,
            description="Deep-dive strategic planning...",
            service_type="one_time",
            session_format="video",
            session_duration=60,
            price=Decimal("150.00"),
            status="published"
        )

        # Create draft service (session) - should not be visible in profile detail
        self.service_draft = Service.objects.create(
            coach=self.provider_user,
            title="Draft Session",
            category=self.category,
            description="Should not see this...",
            service_type="one_time",
            session_format="video",
            session_duration=30,
            price=Decimal("50.00"),
            status="draft"
        )

    def test_coach_profile_detail_succeeds(self):
        self.client.force_authenticate(user=self.customer)
        url = reverse('coach-profile-detail', kwargs={'coach_id': self.coach_profile.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        data = response.data['data']
        self.assertEqual(data['id'], self.coach_profile.id)
        self.assertEqual(data['user']['full_name'], "Sarah Chen")
        
        # Verify services (sessions) list
        services = data['services']
        self.assertEqual(len(services), 1)  # Only the published service
        self.assertEqual(services[0]['title'], "Strategy Session")
        self.assertEqual(services[0]['price'], "150.00")
        self.assertEqual(services[0]['session_duration'], 60)
        self.assertEqual(services[0]['category_name'], "Business")

    def test_coach_profile_detail_not_found(self):
        self.client.force_authenticate(user=self.customer)
        url = reverse('coach-profile-detail', kwargs={'coach_id': 9999})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(response.data['success'])
        self.assertEqual(response.data['message'], "Coach profile not found.")


class RecommendedCoachOrderingTests(APITestCase):

    def setUp(self):
        # Create a user to authenticate
        self.customer = User.objects.create_user(
            email="customer_test_rec@example.com",
            password="password123",
            full_name="John Customer",
            role="User"
        )
        
        # Coach A: avg_rating = 5.0, completed_bookings = 1
        self.user_a = User.objects.create_user(email="coach_a@example.com", password="password123", role="Provider")
        self.profile_a = CoachProfile.objects.create(user=self.user_a, about="Coach A", is_completed=True, status="approved")
        
        # Coach B: avg_rating = 4.0, completed_bookings = 5
        self.user_b = User.objects.create_user(email="coach_b@example.com", password="password123", role="Provider")
        self.profile_b = CoachProfile.objects.create(user=self.user_b, about="Coach B", is_completed=True, status="approved")
        
        # Coach C: avg_rating = 4.0, completed_bookings = 2
        self.user_c = User.objects.create_user(email="coach_c@example.com", password="password123", role="Provider")
        self.profile_c = CoachProfile.objects.create(user=self.user_c, about="Coach C", is_completed=True, status="approved")

        # Ratings
        CoachRating.objects.create(coach=self.profile_a, user=self.customer, rating=5, review="Excellent")
        CoachRating.objects.create(coach=self.profile_b, user=self.customer, rating=4, review="Good")
        CoachRating.objects.create(coach=self.profile_c, user=self.customer, rating=4, review="Good")

        # Bookings for Coach A (1 completed)
        ServiceBooking.objects.create(user=self.customer, coach=self.user_a, amount=Decimal("100"), status="completed", payment_status="paid")
        
        # Bookings for Coach B (5 completed)
        for _ in range(5):
            ServiceBooking.objects.create(user=self.customer, coach=self.user_b, amount=Decimal("100"), status="completed", payment_status="paid")
            
        # Bookings for Coach C (2 completed)
        for _ in range(2):
            ServiceBooking.objects.create(user=self.customer, coach=self.user_c, amount=Decimal("100"), status="completed", payment_status="paid")

        self.url = reverse('recommended-coach-profile')

    def test_recommendation_ordering(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        coaches = response.data['data']
        self.assertEqual(len(coaches), 3)

        # First should be Coach A (highest average rating: 5.0)
        self.assertEqual(coaches[0]['id'], self.profile_a.id)
        self.assertEqual(coaches[0]['avg_rating'], 5.0)
        self.assertEqual(coaches[0]['completed_sessions_count'], 1)

        # Second should be Coach B (rating: 4.0, 5 completed bookings)
        self.assertEqual(coaches[1]['id'], self.profile_b.id)
        self.assertEqual(coaches[1]['avg_rating'], 4.0)
        self.assertEqual(coaches[1]['completed_sessions_count'], 5)

        self.assertEqual(coaches[2]['id'], self.profile_c.id)
        self.assertEqual(coaches[2]['avg_rating'], 4.0)
        self.assertEqual(coaches[2]['completed_sessions_count'], 2)


class UserBlogListTests(APITestCase):

    def setUp(self):
        # Create category
        self.category = Category.objects.create(name="Health", description="Health coaching")
        
        # Create user / customer
        self.customer = User.objects.create_user(
            email="customer_blog@example.com",
            password="password123",
            full_name="John Customer",
            role="User"
        )
        
        # Create coach / provider user
        self.provider_user = User.objects.create_user(
            email="provider_blog@example.com",
            password="password123",
            full_name="Sarah Chen",
            role="Provider"
        )
        
        # Create Coach Profile
        self.coach_profile = CoachProfile.objects.create(
            user=self.provider_user,
            about="Executive Business Coach",
            is_completed=True,
            status="approved"
        )
        
        # Create a blog post
        self.blog = Blog.objects.create(
            coach=self.provider_user,
            category=self.category,
            title="My First Blog Post",
            content="This is the content of the blog post.",
            status="published"
        )

        self.url = reverse('blog-list')

    def test_blog_list_returns_coach_details(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        blogs = response.data['data']
        self.assertEqual(len(blogs), 1)
        
        blog_data = blogs[0]
        self.assertEqual(blog_data['title'], "My First Blog Post")
        
        # Check nested coach details
        coach_details = blog_data['coach']
        self.assertIsNotNone(coach_details)
        self.assertEqual(coach_details['id'], self.provider_user.id)
        self.assertEqual(coach_details['full_name'], "Sarah Chen")
        self.assertEqual(coach_details['email'], "provider_blog@example.com")
        self.assertEqual(coach_details['about'], "Executive Business Coach")

    def test_blog_list_filtering_by_category_name(self):
        self.client.force_authenticate(user=self.customer)
        
        # Query with correct category name (case-insensitive)
        response = self.client.get(self.url + "?category=Health")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        blogs = response.data['data']
        self.assertEqual(len(blogs), 1)
        self.assertEqual(blogs[0]['title'], "My First Blog Post")

        # Query with non-matching category name
        response = self.client.get(self.url + "?category=Business")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        blogs = response.data['data']
        self.assertEqual(len(blogs), 0)


class DigitalProductListTests(APITestCase):

    def setUp(self):
        # Create category
        self.category = Category.objects.create(name="Design", description="Design coaching")
        
        # Create user / customer
        self.customer = User.objects.create_user(
            email="customer_prod@example.com",
            password="password123",
            full_name="John Customer",
            role="User"
        )
        
        # Create coach / provider user
        self.provider_user = User.objects.create_user(
            email="provider_prod@example.com",
            password="password123",
            full_name="Sarah Chen",
            role="Provider"
        )
        
        # Create Coach Profile
        self.coach_profile = CoachProfile.objects.create(
            user=self.provider_user,
            about="Expert UI/UX Designer",
            is_completed=True,
            status="approved"
        )
        
        # Create a product post
        self.product = Product.objects.create(
            coach=self.provider_user,
            category=self.category,
            title="UI/UX Design Book",
            description="Learn how to design amazing products.",
            price=Decimal("29.99"),
            status="published"
        )

        self.url = reverse('digital-product-list')

    def test_digital_product_list_returns_coach_details(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        products = response.data['data']
        self.assertEqual(len(products), 1)
        
        product_data = products[0]
        self.assertEqual(product_data['title'], "UI/UX Design Book")
        self.assertEqual(product_data['price'], "29.99")
        
        # Check nested coach details
        coach_details = product_data['coach']
        self.assertIsNotNone(coach_details)
        self.assertEqual(coach_details['id'], self.provider_user.id)
        self.assertEqual(coach_details['full_name'], "Sarah Chen")
        self.assertEqual(coach_details['email'], "provider_prod@example.com")
        self.assertEqual(coach_details['about'], "Expert UI/UX Designer")







