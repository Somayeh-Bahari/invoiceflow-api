from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from .models import Customer, Invoice, InvoiceHistory


class InvoicePermissionTests(APITestCase):

    def setUp(self):
        self.employee1 = User.objects.create_user(
            username="employee_test_1",
            password="testpass123",
            role="EMPLOYEE",
        )

        self.employee2 = User.objects.create_user(
            username="employee_test_2",
            password="testpass123",
            role="EMPLOYEE",
        )

        self.customer = Customer.objects.create(
            name="Test Customer GmbH",
            email="test@example.com",
        )

        self.invoice1 = Invoice.objects.create(
            customer=self.customer,
            created_by=self.employee1,
            invoice_number="TEST-INV-001",
            issue_date="2026-09-08",
            due_date="2026-09-20",
            amount="100.00",
            status=Invoice.Status.DRAFT,
        )

        self.invoice2 = Invoice.objects.create(
            customer=self.customer,
            created_by=self.employee2,
            invoice_number="TEST-INV-002",
            issue_date="2026-09-08",
            due_date="2026-09-20",
            amount="200.00",
            status=Invoice.Status.DRAFT,
        )

    def test_employee_only_sees_own_invoices(self):
        self.client.force_authenticate(user=self.employee1)

        url = reverse("invoice-list")
        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        invoice_numbers = [
            item["invoice_number"]
            for item in response.data["results"]
        ]

        self.assertIn("TEST-INV-001", invoice_numbers)
        self.assertNotIn("TEST-INV-002", invoice_numbers)

    def test_manager_only_sees_submitted_invoices(self):
        manager = User.objects.create_user(
            username="manager_test",
            password="testpass123",
            role="MANAGER",
        )

        Invoice.objects.create(
            customer=self.customer,
            created_by=self.employee1,
            invoice_number="TEST-INV-003",
            issue_date="2026-09-08",
            due_date="2026-09-20",
            amount="300.00",
            status=Invoice.Status.SUBMITTED,
        )

        Invoice.objects.create(
            customer=self.customer,
            created_by=self.employee1,
            invoice_number="TEST-INV-004",
            issue_date="2026-09-08",
            due_date="2026-09-20",
            amount="400.00",
            status=Invoice.Status.DRAFT,
        )

        self.client.force_authenticate(user=manager)

        url = reverse("invoice-list")
        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        invoice_numbers = [
            item["invoice_number"]
            for item in response.data["results"]
        ]

        self.assertIn("TEST-INV-003", invoice_numbers)
        self.assertNotIn("TEST-INV-004", invoice_numbers)

    def test_employee_cannot_approve_invoice(self):
        invoice = Invoice.objects.create(
            customer=self.customer,
            created_by=self.employee1,
            invoice_number="TEST-INV-005",
            issue_date="2026-09-08",
            due_date="2026-09-20",
            amount="500.00",
            status=Invoice.Status.SUBMITTED,
        )

        self.client.force_authenticate(user=self.employee1)

        url = reverse(
            "invoice-approve",
            args=[invoice.id],
        )

        response = self.client.post(
            url,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        invoice.refresh_from_db()

        self.assertEqual(
            invoice.status,
            Invoice.Status.SUBMITTED,
        )

    def test_manager_can_approve_invoice_and_history_is_created(self):
        manager = User.objects.create_user(
            username="manager_approve_test",
            password="testpass123",
            role="MANAGER",
        )

        invoice = Invoice.objects.create(
            customer=self.customer,
            created_by=self.employee1,
            invoice_number="TEST-INV-006",
            issue_date="2026-09-08",
            due_date="2026-09-20",
            amount="600.00",
            status=Invoice.Status.SUBMITTED,
        )

        self.client.force_authenticate(user=manager)

        url = reverse(
            "invoice-approve",
            args=[invoice.id],
        )

        response = self.client.post(
            url,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        invoice.refresh_from_db()

        self.assertEqual(
            invoice.status,
            Invoice.Status.APPROVED,
        )

        history = InvoiceHistory.objects.filter(
            invoice=invoice,
            action=InvoiceHistory.Action.APPROVED,
            performed_by=manager,
        )

        self.assertTrue(history.exists())

    def test_manager_reject_requires_comment_and_saves_history(self):
        manager = User.objects.create_user(
            username="manager_reject_test",
            password="testpass123",
            role="MANAGER",
        )

        invoice = Invoice.objects.create(
            customer=self.customer,
            created_by=self.employee1,
            invoice_number="TEST-INV-007",
            issue_date="2026-09-08",
            due_date="2026-09-20",
            amount="700.00",
            status=Invoice.Status.SUBMITTED,
        )

        self.client.force_authenticate(user=manager)

        url = reverse(
            "invoice-reject",
            args=[invoice.id],
        )

        response_without_comment = self.client.post(
            url,
            {},
            format="json",
        )

        self.assertEqual(
            response_without_comment.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        invoice.refresh_from_db()

        self.assertEqual(
            invoice.status,
            Invoice.Status.SUBMITTED,
        )

        response_with_comment = self.client.post(
            url,
            {
                "comment": "Invoice amount needs correction."
            },
            format="json",
        )

        self.assertEqual(
            response_with_comment.status_code,
            status.HTTP_200_OK,
        )

        invoice.refresh_from_db()

        self.assertEqual(
            invoice.status,
            Invoice.Status.REJECTED,
        )

        history = InvoiceHistory.objects.filter(
            invoice=invoice,
            action=InvoiceHistory.Action.REJECTED,
            performed_by=manager,
            comment="Invoice amount needs correction.",
        )

        self.assertTrue(history.exists())

    def test_accountant_can_mark_approved_invoice_as_paid(self):
        accountant = User.objects.create_user(
            username="accountant_test",
            password="testpass123",
            role="ACCOUNTANT",
        )

        approved_invoice = Invoice.objects.create(
            customer=self.customer,
            created_by=self.employee1,
            invoice_number="TEST-INV-008",
            issue_date="2026-09-08",
            due_date="2026-09-20",
            amount="800.00",
            status=Invoice.Status.APPROVED,
        )

        draft_invoice = Invoice.objects.create(
            customer=self.customer,
            created_by=self.employee1,
            invoice_number="TEST-INV-009",
            issue_date="2026-09-08",
            due_date="2026-09-20",
            amount="900.00",
            status=Invoice.Status.DRAFT,
        )

        self.client.force_authenticate(user=accountant)

        list_url = reverse("invoice-list")
        list_response = self.client.get(list_url)

        self.assertEqual(
            list_response.status_code,
            status.HTTP_200_OK,
        )

        invoice_numbers = [
            item["invoice_number"]
            for item in list_response.data["results"]
        ]

        self.assertIn("TEST-INV-008", invoice_numbers)
        self.assertNotIn("TEST-INV-009", invoice_numbers)

        mark_paid_url = reverse(
            "invoice-mark-paid",
            args=[approved_invoice.id],
        )

        response = self.client.post(
            mark_paid_url,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        approved_invoice.refresh_from_db()

        self.assertEqual(
            approved_invoice.status,
            Invoice.Status.PAID,
        )

        history = InvoiceHistory.objects.filter(
            invoice=approved_invoice,
            action=InvoiceHistory.Action.PAID,
            performed_by=accountant,
        )

        self.assertTrue(history.exists())

    def test_invoice_amount_must_be_greater_than_zero(self):
        self.client.force_authenticate(user=self.employee1)

        url = reverse("invoice-list")

        data = {
            "invoice_number": "TEST-INV-010",
            "customer": self.customer.id,
            "issue_date": "2026-09-08",
            "due_date": "2026-09-20",
            "amount": "0.00",
            "status": Invoice.Status.DRAFT,
            "notes": "",
        }

        response = self.client.post(
            url,
            data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "amount",
            response.data,
        )

        self.assertEqual(
            Invoice.objects.filter(
                invoice_number="TEST-INV-010"
            ).count(),
            0,
        )

    def test_due_date_cannot_be_before_issue_date(self):
        self.client.force_authenticate(
            user=self.employee1
        )

        url = reverse("invoice-list")

        data = {
            "invoice_number": "TEST-INV-011",
            "customer": self.customer.id,
            "issue_date": "2026-09-20",
            "due_date": "2026-09-10",
            "amount": "1000.00",
            "status": Invoice.Status.DRAFT,
            "notes": "",
        }

        response = self.client.post(
            url,
            data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "due_date",
            response.data,
        )

        self.assertEqual(
            Invoice.objects.filter(
                invoice_number="TEST-INV-011"
            ).count(),
            0,
        )