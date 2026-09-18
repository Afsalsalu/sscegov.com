from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image
from io import BytesIO

from .banner_forms import BannerForm
from .models import (
    AddState,
    Banner,
    CentreUserAccount,
    DownloadForm,
    LatestNewsCentre,
    OnlineClass,
    StateService,
    StateServiceDetailImage,
)
from .service_forms import StateServiceForm, validate_detail_image
from .forms import DownloadFormForm, OnlineClassForm


def image_file(name="banner.png", fmt="PNG"):
    stream = BytesIO()
    Image.new("RGB", (20, 10), "red").save(stream, format=fmt)
    return SimpleUploadedFile(name, stream.getvalue(), content_type="image/png")


def pdf_file(name="form.pdf"):
    return SimpleUploadedFile(name, b"%PDF-1.4 test", content_type="application/pdf")


def video_file(name="class.mp4", content_type="video/mp4", content=b"video-data"):
    return SimpleUploadedFile(name, content, content_type=content_type)


class BannerTests(TestCase):
    def test_valid_image_is_accepted(self):
        form = BannerForm(files={"image": image_file()}, data={"display_order": 1, "is_enabled": True})
        self.assertTrue(form.is_valid(), form.errors)

    def test_invalid_extension_is_rejected(self):
        form = BannerForm(files={"image": SimpleUploadedFile("banner.txt", b"not image", content_type="text/plain")}, data={"display_order": 1})
        self.assertFalse(form.is_valid())

    def test_franchise_queryset_ordering_and_enabled_filter(self):
        Banner.objects.create(image=image_file("one.png"), display_order=2, is_enabled=True)
        Banner.objects.create(image=image_file("two.png"), display_order=1, is_enabled=False)
        enabled = Banner.objects.filter(is_enabled=True)
        self.assertEqual(list(enabled.values_list("display_order", flat=True)), [2])


class ServiceDetailsTests(TestCase):
    def setUp(self):
        self.state = AddState.objects.create(state_name="Kerala")
        self.other_state = AddState.objects.create(state_name="Tamil Nadu")
        self.user = get_user_model().objects.create_user(
            username="centre-details-test", password="test-password", usertype="centre"
        )
        self.service = StateService.objects.create(
            state=self.state,
            service_name="Kerala Service",
            service_logo=image_file("logo.png"),
            service_link="https://example.com/service",
            service_details="First paragraph.\n\nSecond paragraph.",
            is_active=True,
        )
        StateService.objects.create(
            state=self.other_state,
            service_name="Other State Service",
            service_logo=image_file("other.png"),
            service_details="Must not be shown.",
            is_active=True,
        )

    def test_detail_page_is_state_scoped_and_renders_saved_content(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse(
                "web:service_detail",
                kwargs={"state_slug": self.state.slug, "pk": self.service.pk},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kerala Service")
        self.assertContains(response, "First paragraph.")
        self.assertNotContains(response, "Must not be shown.")

    def test_detail_content_is_escaped_as_plain_text(self):
        self.service.service_details = "<script>alert('x')</script>\nSafe text"
        self.service.save(update_fields=["service_details"])
        self.client.force_login(self.user)
        response = self.client.get(
            reverse(
                "web:service_detail",
                kwargs={"state_slug": self.state.slug, "pk": self.service.pk},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "&lt;script&gt;")
        self.assertNotContains(response, "<script>alert")

    def test_detail_page_rejects_service_from_another_state(self):
        other_service = StateService.objects.get(service_name="Other State Service")
        self.client.force_login(self.user)
        response = self.client.get(
            reverse(
                "web:service_detail",
                kwargs={"state_slug": self.state.slug, "pk": other_service.pk},
            )
        )
        self.assertEqual(response.status_code, 404)

    def test_detail_image_is_saved_and_rendered(self):
        detail_image = StateServiceDetailImage.objects.create(
            service=self.service, image=image_file("detail.png")
        )
        self.client.force_login(self.user)
        response = self.client.get(
            reverse(
                "web:service_detail",
                kwargs={"state_slug": self.state.slug, "pk": self.service.pk},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, detail_image.image.url)

    def test_invalid_detail_image_is_rejected(self):
        invalid = SimpleUploadedFile(
            "not-an-image.txt", b"not an image", content_type="text/plain"
        )
        with self.assertRaises(Exception):
            validate_detail_image(invalid)

    def test_oversized_detail_image_is_rejected(self):
        oversized = SimpleUploadedFile(
            "large.png", b"x" * (5 * 1024 * 1024 + 1), content_type="image/png"
        )
        with self.assertRaises(Exception):
            validate_detail_image(oversized)

    def test_franchise_user_can_view_but_cannot_edit(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("web:stateservice_update", kwargs={"pk": self.service.pk})
        )
        self.assertEqual(response.status_code, 302)

    def test_detail_buttons_are_present_and_open_keeps_stored_link(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("web:state_detail", kwargs={"slug": self.state.slug})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Detail")
        self.assertContains(response, "Open")
        self.assertContains(response, self.service.service_link)

    def test_state_services_page_has_other_states_navigation(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("web:state_detail", kwargs={"slug": self.state.slug})
        )
        self.assertContains(response, "Other States")
        self.assertContains(response, 'href="/franchise-dashboard/all-states/"')

    def test_head_office_can_create_service_with_details_and_images(self):
        admin = get_user_model().objects.create_user(
            username="head-office-details-test",
            password="test-password",
            usertype="HeadOffice",
        )
        self.client.force_login(admin)
        response = self.client.post(
            reverse(
                "web:add_service_for_state", kwargs={"state_slug": self.state.slug}
            ),
            data={
                "service_name": "New Detailed Service",
                "service_link": "https://example.com/new-service",
                "service_logo": image_file("new-logo.png"),
                "service_details": "Heading\n\nA detailed paragraph.",
                "is_active": "on",
                "is_popular": "on",
                "detail_images": [image_file("detail-one.png"), image_file("detail-two.png")],
            },
        )
        self.assertEqual(response.status_code, 302)
        created = StateService.objects.get(service_name="New Detailed Service")
        self.assertEqual(created.service_details, "Heading\n\nA detailed paragraph.")
        self.assertEqual(created.detail_images.count(), 2)

    def test_head_office_can_add_multiple_images_without_replacing_existing_images(self):
        admin = get_user_model().objects.create_user(
            username="head-office-gallery-edit-test",
            password="test-password",
            usertype="HeadOffice",
        )
        existing = StateServiceDetailImage.objects.create(
            service=self.service, image=image_file("existing.png")
        )
        self.client.force_login(admin)
        response = self.client.post(
            reverse("web:stateservice_update", kwargs={"pk": self.service.pk}),
            data={
                "service_name": self.service.service_name,
                "service_link": self.service.service_link,
                "service_details": self.service.service_details,
                "is_active": "on",
                "detail_images": [image_file("new-one.png"), image_file("new-two.png")],
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(StateServiceDetailImage.objects.filter(pk=existing.pk).exists())
        self.assertEqual(self.service.detail_images.count(), 3)

    def test_head_office_service_form_renders_details_section(self):
        admin = get_user_model().objects.create_user(
            username="head-office-form-test",
            password="test-password",
            usertype="HeadOffice",
        )
        self.client.force_login(admin)
        response = self.client.get(
            reverse(
                "web:add_service_for_state", kwargs={"state_slug": self.state.slug}
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Service Details")
        self.assertContains(response, "detail_images")
        self.assertContains(response, 'accept="image/jpeg,image/png,image/webp"')
        self.assertContains(response, "selectedDetailFiles")
        self.assertContains(response, "newlyChosen.forEach")
        self.assertContains(response, "DataTransfer")

    def test_logo_and_gallery_inputs_are_separate(self):
        form = StateServiceForm()
        logo_html = str(form["service_logo"])
        self.assertIn('name="service_logo"', logo_html)
        self.assertNotIn("multiple", logo_html)
        admin = get_user_model().objects.create_user(
            username="head-office-input-separation-test",
            password="test-password",
            usertype="HeadOffice",
        )
        self.client.force_login(admin)
        response = self.client.get(
            reverse(
                "web:add_service_for_state", kwargs={"state_slug": self.state.slug}
            )
        )
        self.assertContains(response, 'name="detail_images"')
        self.assertContains(response, 'id="detail-preview"')
        self.assertContains(response, 'id="logo-preview"')
        self.assertNotContains(response, 'id="id_service_logo" multiple')

    def test_detail_page_renders_all_gallery_images_and_action_links(self):
        images = [
            StateServiceDetailImage.objects.create(
                service=self.service, image=image_file("gallery-one.png")
            ),
            StateServiceDetailImage.objects.create(
                service=self.service, image=image_file("gallery-two.png")
            ),
        ]
        self.client.force_login(self.user)
        response = self.client.get(
            reverse(
                "web:service_detail",
                kwargs={"state_slug": self.state.slug, "pk": self.service.pk},
            )
        )
        self.assertEqual(response.status_code, 200)
        for gallery_image in images:
            self.assertContains(response, gallery_image.image.url)
        self.assertContains(response, "service-lightbox")
        self.assertContains(response, "Previous image")
        self.assertContains(response, self.service.service_link)

    def test_edit_preserves_existing_logo_and_details_without_new_upload(self):
        admin = get_user_model().objects.create_user(
            username="head-office-edit-test",
            password="test-password",
            usertype="HeadOffice",
        )
        original_logo = self.service.service_logo.name
        self.client.force_login(admin)
        response = self.client.post(
            reverse("web:stateservice_update", kwargs={"pk": self.service.pk}),
            data={
                "service_name": "Edited Service",
                "service_link": self.service.service_link,
                "service_details": "Updated details",
                "is_active": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.service.refresh_from_db()
        self.assertEqual(self.service.service_logo.name, original_logo)
        self.assertEqual(self.service.service_details, "Updated details")


class DownloadFormFilteringTests(TestCase):
    def setUp(self):
        self.kerala = AddState.objects.create(state_name="Kerala")
        self.tamil_nadu = AddState.objects.create(state_name="Tamil Nadu")
        self.kerala_service = StateService.objects.create(
            state=self.kerala,
            service_name="Kerala Certificate",
            service_logo=image_file("kerala-logo.png"),
        )
        self.tamil_service = StateService.objects.create(
            state=self.tamil_nadu,
            service_name="Tamil Certificate",
            service_logo=image_file("tamil-logo.png"),
        )
        self.admin = get_user_model().objects.create_user(
            username="download-form-admin", password="test-password", usertype="HeadOffice"
        )
        self.franchise_user = get_user_model().objects.create_user(
            username="download-form-franchise", password="test-password", usertype="centre"
        )

    def test_download_form_form_rejects_mismatched_service(self):
        form = DownloadFormForm(
            data={
                "title": "Wrong assignment",
                "state": self.kerala.pk,
                "service": self.tamil_service.pk,
            },
            files={"pdf": pdf_file()},
        )
        self.assertFalse(form.is_valid())
        self.assertIn("service", form.errors)

    def test_download_form_state_and_service_are_independently_optional(self):
        for state, service in (
            (self.kerala, None),
            (None, self.kerala_service),
            (None, None),
        ):
            form = DownloadFormForm(
                data={
                    "title": "Optional assignment",
                    "state": state.pk if state else "",
                    "service": service.pk if service else "",
                },
                files={"pdf": pdf_file()},
            )
            self.assertTrue(form.is_valid(), form.errors)

    def test_admin_can_create_download_form_with_state_and_service(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("web:add_downloadform"),
            data={
                "title": "Kerala Certificate Form",
                "state": self.kerala.pk,
                "service": self.kerala_service.pk,
                "pdf": pdf_file(),
            },
        )
        self.assertEqual(response.status_code, 302)
        created = DownloadForm.objects.get(title="Kerala Certificate Form")
        self.assertEqual(created.state_id, self.kerala.pk)
        self.assertEqual(created.service_id, self.kerala_service.pk)

    def test_franchise_state_service_and_combined_filters_are_queryset_filters(self):
        kerala_form = DownloadForm.objects.create(
            title="Kerala Form", pdf=pdf_file("kerala.pdf"), state=self.kerala, service=self.kerala_service
        )
        DownloadForm.objects.create(
            title="Tamil Form", pdf=pdf_file("tamil.pdf"), state=self.tamil_nadu, service=self.tamil_service
        )
        self.client.force_login(self.franchise_user)
        state_response = self.client.get(reverse("web:download_form_list"), {"state": self.kerala.pk})
        self.assertEqual(list(state_response.context["download_forms"]), [kerala_form])
        service_response = self.client.get(
            reverse("web:download_form_list"), {"state": self.kerala.pk, "service": self.kerala_service.pk}
        )
        self.assertEqual(list(service_response.context["download_forms"]), [kerala_form])
        service_only_response = self.client.get(
            reverse("web:download_form_list"), {"service": self.kerala_service.pk}
        )
        self.assertEqual(list(service_only_response.context["download_forms"]), [kerala_form])
        self.assertContains(service_response, "Clear Filters")
        self.assertContains(service_response, "Download")

    def test_edit_form_loads_existing_state_and_service(self):
        download_form = DownloadForm.objects.create(
            title="Existing Form", pdf=pdf_file("existing.pdf"), state=self.kerala, service=self.kerala_service
        )
        self.client.force_login(self.admin)
        response = self.client.get(reverse("web:edit_downloadform", kwargs={"pk": download_form.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["form"].initial["state"], self.kerala.pk)
        self.assertEqual(response.context["form"].initial["service"], self.kerala_service.pk)


class LatestNewsTests(TestCase):
    def make_franchise_user(self):
        user = get_user_model().objects.create_user(
            username="latest-news-franchise", password="test-password", usertype="centre"
        )
        CentreUserAccount.objects.create(
            user=user,
            owner_centre="Latest News Centre",
            mobile=9999999999,
            aadhaar_number=999999999999,
            email="latest-news-franchise@example.com",
            centre_phone_number=9999999999,
            state="",
            location="",
        )
        return user

    def test_admin_list_uses_compact_cards_search_and_safe_image_fallback(self):
        admin = get_user_model().objects.create_user(
            username="latest-news-admin", password="test-password", usertype="HeadOffice"
        )
        news = LatestNewsCentre.objects.create(
            image=image_file("latest-news.png"),
            title="Important update",
            content="A useful description for franchise users.",
        )
        missing = LatestNewsCentre.objects.create(
            image="media/news/missing-latest-news.png",
            title="Missing image update",
            content="This item should use the built-in fallback.",
        )
        self.client.force_login(admin)
        response = self.client.get(reverse("web:latest_news_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Latest News")
        self.assertContains(response, "Search news by title or description")
        self.assertContains(response, "group-data-[sidebar-size=lg]:ltr:md:ml-vertical-menu")
        self.assertContains(response, "news-management-header-actions")
        self.assertContains(response, '<article class="news-management-card" data-news-card>', count=2)
        self.assertContains(response, "Edit")
        self.assertContains(response, "Delete")
        self.assertContains(response, news.image.url)
        self.assertContains(response, "No image available")
        self.assertNotContains(response, 'src=""')
        self.assertContains(response, f'data-edit-url="{reverse("web:latest_news_edit", kwargs={"pk": news.pk})}"')
        self.assertContains(response, f'data-delete-url="{reverse("web:latest_news_delete", kwargs={"pk": missing.pk})}"')

    def test_dashboard_latest_news_uses_compact_safe_cards(self):
        LatestNewsCentre.objects.create(
            image=image_file("dashboard-news.png"),
            title="Dashboard update",
            content="A compact dashboard news preview.",
        )
        LatestNewsCentre.objects.create(
            image="media/news/missing-dashboard-news.png",
            title="Fallback update",
            content="Fallback preview.",
        )
        self.client.force_login(self.make_franchise_user())
        response = self.client.get(reverse("web:centre_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<article class="dashboard-news-card">', count=2)
        self.assertContains(response, "dashboard-news-grid")
        self.assertContains(response, "Dashboard update")
        self.assertContains(response, "No image available")
        self.assertNotContains(response, 'src=""')


class StateSmartDashboardTests(TestCase):
    def make_franchise_user(self, state_value):
        user = get_user_model().objects.create_user(
            username=f"dashboard-{state_value or 'unassigned'}",
            password="test-password",
            usertype="centre",
        )
        CentreUserAccount.objects.create(
            user=user,
            owner_centre="Dashboard Centre",
            mobile=9999999999,
            aadhaar_number=999999999999,
            email=f"{user.username}@example.com",
            centre_phone_number=9999999999,
            state=state_value,
            location="",
        )
        return user

    def make_state(self, name):
        return AddState.objects.create(state_name=name, logo=image_file(f"{name}.png"))

    def make_service(self, state, name):
        return StateService.objects.create(
            state=state,
            service_name=name,
            service_logo=image_file(f"{name}.png"),
            service_link="https://example.com/service",
            is_popular=True,
            is_active=True,
        )

    def test_state_services_are_prioritized_without_duplicates(self):
        kerala = self.make_state("Kerala")
        other_state = self.make_state("Tamil Nadu")
        priority = self.make_service(kerala, "Kerala Priority")
        general = self.make_service(other_state, "General Service")
        user = self.make_franchise_user(kerala.slug)

        self.client.force_login(user)
        response = self.client.get(reverse("web:centre_dashboard"))

        self.assertEqual(
            list(response.context["priority_services"]), [priority]
        )
        self.assertEqual(list(response.context["other_services"]), [general])
        self.assertContains(response, "Showing priority content for")
        self.assertContains(response, "More Services")
        self.assertEqual(response.content.decode().count('class="popular-service-card"'), 2)

    def test_user_without_state_keeps_global_dashboard_content(self):
        kerala = self.make_state("Kerala")
        service = self.make_service(kerala, "Global Service")
        user = self.make_franchise_user("")

        self.client.force_login(user)
        response = self.client.get(reverse("web:centre_dashboard"))

        self.assertEqual(list(response.context["popular_services"]), [service])
        self.assertNotContains(response, "Showing priority content for")
        self.assertContains(response, "Global Service")

    def test_state_without_content_falls_back_to_global_services(self):
        assigned_state = self.make_state("Kerala")
        other_state = self.make_state("Tamil Nadu")
        general = self.make_service(other_state, "General Service")
        user = self.make_franchise_user(assigned_state.slug)

        self.client.force_login(user)
        response = self.client.get(reverse("web:centre_dashboard"))

        self.assertFalse(response.context["priority_services"])
        self.assertEqual(list(response.context["other_services"]), [general])
        self.assertContains(response, "General Service")


class FranchiseSidebarNavigationTests(TestCase):
    def make_franchise_user(self, state_value):
        user = get_user_model().objects.create_user(
            username=f"sidebar-{state_value or 'unassigned'}",
            password="test-password",
            usertype="centre",
        )
        CentreUserAccount.objects.create(
            user=user,
            owner_centre="Sidebar Centre",
            mobile=9999999999,
            aadhaar_number=999999999999,
            email=f"{user.username}@example.com",
            centre_phone_number=9999999999,
            state=state_value,
            location="",
        )
        return user

    def test_state_user_gets_state_service_sidebar_destination(self):
        state = AddState.objects.create(
            state_name="Kerala", logo=image_file("sidebar-kerala.png")
        )
        user = self.make_franchise_user(state.slug)
        self.client.force_login(user)

        response = self.client.get(reverse("web:centre_dashboard"))

        self.assertContains(response, 'href="/franchise-dashboard/services/kerala/"')
        self.assertNotContains(response, 'href="/franchise-dashboard/all-states/"')

    def test_user_without_state_keeps_all_states_sidebar_destination(self):
        user = self.make_franchise_user("")
        self.client.force_login(user)

        response = self.client.get(reverse("web:centre_dashboard"))

        self.assertContains(response, 'href="/franchise-dashboard/all-states/"')

    def test_direct_all_states_route_remains_available(self):
        user = self.make_franchise_user("kerala")
        self.client.force_login(user)

        response = self.client.get(reverse("web:state_list"))

        self.assertEqual(response.status_code, 200)


class OnlineClassTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(
            username="online-class-admin", password="test-password", usertype="HeadOffice"
        )
        self.franchise_user = get_user_model().objects.create_user(
            username="online-class-franchise", password="test-password", usertype="centre"
        )

    def test_uploaded_video_is_saved_with_a_stable_slug(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("web:add_online_class"),
            data={
                "title": "Uploaded Training Class",
                "description": "A complete uploaded class.",
                "video_file": video_file(),
            },
        )
        self.assertEqual(response.status_code, 302)
        online_class = OnlineClass.objects.get(title="Uploaded Training Class")
        self.assertEqual(online_class.slug, "uploaded-training-class")
        self.assertTrue(online_class.video_file.name.startswith("online_classes/videos/"))

    def test_existing_video_link_remains_valid_without_upload(self):
        form = OnlineClassForm(
            data={
                "title": "Hosted Class",
                "class_video_link": "https://example.com/class",
                "description": "Hosted content.",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_requires_a_video_upload_or_link(self):
        form = OnlineClassForm(
            data={"title": "Unavailable Class", "description": "No video yet."}
        )
        self.assertFalse(form.is_valid())
        self.assertTrue(form.non_field_errors())

    def test_invalid_video_extension_and_mime_are_rejected(self):
        form = OnlineClassForm(
            data={"title": "Invalid Class"},
            files={
                "video_file": video_file(
                    "class.txt", content_type="text/plain", content=b"not-video"
                )
            },
        )
        self.assertFalse(form.is_valid())
        self.assertIn("video_file", form.errors)

    @override_settings(ONLINE_CLASS_MAX_VIDEO_SIZE=4)
    def test_oversized_video_is_rejected(self):
        form = OnlineClassForm(
            data={"title": "Large Class"},
            files={"video_file": video_file(content=b"12345")},
        )
        self.assertFalse(form.is_valid())
        self.assertIn("video_file", form.errors)

    def test_detail_page_renders_uploaded_video_and_full_description(self):
        online_class = OnlineClass.objects.create(
            title="Detail Class",
            description="First paragraph.\n\nSecond paragraph.",
            video_file=video_file("detail.mp4"),
        )
        self.client.force_login(self.franchise_user)
        response = self.client.get(
            reverse("web:online_class_detail", kwargs={"slug": online_class.slug})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, online_class.video_file.url)
        self.assertContains(response, "controls")
        self.assertContains(response, "preload=\"metadata\"")
        self.assertContains(response, "First paragraph.")
        self.assertContains(response, "Second paragraph.")

    def test_link_only_class_keeps_link_playback_fallback(self):
        online_class = OnlineClass.objects.create(
            title="Link Class",
            class_video_link="https://example.com/hosted-class",
            description="Hosted class.",
        )
        self.client.force_login(self.franchise_user)
        response = self.client.get(
            reverse("web:online_class_detail", kwargs={"slug": online_class.slug})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, online_class.class_video_link)
        self.assertContains(response, "Open class video")

    def test_edit_without_new_upload_preserves_existing_video(self):
        online_class = OnlineClass.objects.create(
            title="Editable Class",
            description="Before edit.",
            video_file=video_file("editable.mp4"),
        )
        existing_name = online_class.video_file.name
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("web:edit_onlineclass", kwargs={"pk": online_class.pk}),
            data={"title": "Edited Class", "description": "After edit."},
        )
        self.assertEqual(response.status_code, 302)
        online_class.refresh_from_db()
        self.assertEqual(online_class.video_file.name, existing_name)
        self.assertEqual(online_class.title, "Edited Class")

    def test_admin_list_uses_thumbnail_and_visible_management_actions(self):
        online_class = OnlineClass.objects.create(
            title="Thumbnail Class",
            description="A class with a thumbnail.",
            thumbnail=image_file("thumbnail.png"),
            class_video_link="https://example.com/thumbnail-class",
        )
        self.client.force_login(self.admin)
        response = self.client.get(reverse("web:onlineclass_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, online_class.thumbnail.url)
        self.assertContains(response, "Thumbnail Class")
        self.assertContains(response, "Edit")
        self.assertContains(response, "Delete")
        self.assertNotContains(response, "<iframe")

    def test_admin_list_uses_placeholder_for_missing_thumbnail(self):
        OnlineClass.objects.create(
            title="Missing Thumbnail Class",
            description="A class whose old thumbnail is unavailable.",
            thumbnail="media/missing-thumbnail.png",
            class_video_link="https://example.com/missing-thumbnail-class",
        )
        self.client.force_login(self.admin)
        response = self.client.get(reverse("web:onlineclass_list"))
        self.assertContains(response, "No thumbnail")
        self.assertContains(response, "Video class")
        self.assertNotContains(response, '<img src=""')

    def test_admin_list_search_matches_title_and_description(self):
        matching = OnlineClass.objects.create(
            title="Safety Basics",
            description="A lesson about workplace safety.",
            class_video_link="https://example.com/safety",
        )
        OnlineClass.objects.create(
            title="Unrelated Lesson",
            description="A lesson about another topic.",
            class_video_link="https://example.com/other",
        )
        self.client.force_login(self.admin)

        title_response = self.client.get(reverse("web:onlineclass_list"), {"q": "safety"})
        self.assertEqual(list(title_response.context["onlineclass"]), [matching])

        description_response = self.client.get(
            reverse("web:onlineclass_list"), {"q": "workplace"}
        )
        self.assertEqual(list(description_response.context["onlineclass"]), [matching])

# Create your tests here.
