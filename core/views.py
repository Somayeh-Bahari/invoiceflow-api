from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django_filters.rest_framework import DjangoFilterBackend

from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiResponse,
    extend_schema,
    inline_serializer,
)

from .models import Customer, Invoice, InvoiceHistory
from .serializers import (
    CustomerSerializer,
    InvoiceSerializer,
    RejectInvoiceRequestSerializer,
)
from .permissions import (
    IsManagerOrAdminForApproval,
    IsAccountantOrAdmin,
)


DetailResponseSerializer = inline_serializer(
    name="DetailResponse",
    fields={
        "detail": serializers.CharField(),
    },
)


RejectSuccessResponseSerializer = inline_serializer(
    name="RejectSuccessResponse",
    fields={
        "detail": serializers.CharField(),
        "comment": serializers.CharField(),
    },
)


RejectErrorResponseSerializer = inline_serializer(
    name="RejectErrorResponse",
    fields={
        "detail": serializers.CharField(required=False),
        "comment": serializers.CharField(required=False),
    },
)


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer


class InvoiceViewSet(viewsets.ModelViewSet):
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]

    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter,
    ]

    filterset_fields = [
        "status",
        "customer",
    ]

    search_fields = [
        "invoice_number",
        "customer__name",
    ]

    ordering_fields = [
        "issue_date",
        "due_date",
        "amount",
        "created_at",
    ]

    ordering = [
        "-created_at",
    ]

    def get_queryset(self):
        user = self.request.user

        if user.is_superuser or getattr(user, "role", None) == "ADMIN":
            return Invoice.objects.all()

        if getattr(user, "role", None) == "MANAGER":
            return Invoice.objects.filter(
                status=Invoice.Status.SUBMITTED
            )

        if getattr(user, "role", None) == "ACCOUNTANT":
            return Invoice.objects.filter(
                status=Invoice.Status.APPROVED
            )

        return Invoice.objects.filter(
            created_by=user
        )

    def perform_create(self, serializer):
        invoice = serializer.save(
            created_by=self.request.user
        )

        InvoiceHistory.objects.create(
            invoice=invoice,
            action=InvoiceHistory.Action.CREATED,
            performed_by=self.request.user,
        )

    @extend_schema(
        summary="Submit invoice",
        description=(
            "Allows the invoice owner to submit a draft invoice "
            "for manager review."
        ),
        request=None,
        responses={
            200: OpenApiResponse(
                response=DetailResponseSerializer,
                description="Invoice submitted successfully.",
                examples=[
                    OpenApiExample(
                        "Success",
                        value={
                            "detail": "Invoice submitted successfully."
                        },
                    ),
                ],
            ),
            400: OpenApiResponse(
                response=DetailResponseSerializer,
                description="Invoice is not in draft status.",
                examples=[
                    OpenApiExample(
                        "Invalid status",
                        value={
                            "detail": (
                                "Only draft invoices can be submitted."
                            )
                        },
                    ),
                ],
            ),
            403: OpenApiResponse(
                response=DetailResponseSerializer,
                description="User is not the owner of the invoice.",
                examples=[
                    OpenApiExample(
                        "Forbidden",
                        value={
                            "detail": (
                                "You can only submit your own invoices."
                            )
                        },
                    ),
                ],
            ),
        },
    )
    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated],
    )
    def submit(self, request, pk=None):
        invoice = self.get_object()

        if invoice.created_by != request.user:
            return Response(
                {
                    "detail": "You can only submit your own invoices."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if invoice.status != Invoice.Status.DRAFT:
            return Response(
                {
                    "detail": "Only draft invoices can be submitted."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        invoice.status = Invoice.Status.SUBMITTED
        invoice.save(
            update_fields=["status", "updated_at"]
        )

        InvoiceHistory.objects.create(
            invoice=invoice,
            action=InvoiceHistory.Action.SUBMITTED,
            performed_by=request.user,
        )

        return Response(
            {
                "detail": "Invoice submitted successfully."
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Approve invoice",
        description=(
            "Allows a manager or admin to approve a submitted invoice."
        ),
        request=None,
        responses={
            200: OpenApiResponse(
                response=DetailResponseSerializer,
                description="Invoice approved successfully.",
                examples=[
                    OpenApiExample(
                        "Success",
                        value={
                            "detail": "Invoice approved successfully."
                        },
                    ),
                ],
            ),
            400: OpenApiResponse(
                response=DetailResponseSerializer,
                description="Invoice is not in submitted status.",
                examples=[
                    OpenApiExample(
                        "Invalid status",
                        value={
                            "detail": (
                                "Only submitted invoices can be approved."
                            )
                        },
                    ),
                ],
            ),
            403: OpenApiResponse(
                response=DetailResponseSerializer,
                description="User does not have permission to approve.",
                examples=[
                    OpenApiExample(
                        "Forbidden",
                        value={
                            "detail": (
                                "You do not have permission "
                                "to perform this action."
                            )
                        },
                    ),
                ],
            ),
        },
    )
    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsManagerOrAdminForApproval],
    )
    def approve(self, request, pk=None):
        invoice = self.get_object()

        if invoice.status != Invoice.Status.SUBMITTED:
            return Response(
                {
                    "detail": "Only submitted invoices can be approved."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        invoice.status = Invoice.Status.APPROVED
        invoice.save(
            update_fields=["status", "updated_at"]
        )

        InvoiceHistory.objects.create(
            invoice=invoice,
            action=InvoiceHistory.Action.APPROVED,
            performed_by=request.user,
        )

        return Response(
            {
                "detail": "Invoice approved successfully."
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Reject invoice",
        description=(
            "Allows a manager or admin to reject a submitted invoice. "
            "A rejection comment is required."
        ),
        request=RejectInvoiceRequestSerializer,
        responses={
            200: OpenApiResponse(
                response=RejectSuccessResponseSerializer,
                description="Invoice rejected successfully.",
                examples=[
                    OpenApiExample(
                        "Success",
                        value={
                            "detail": "Invoice rejected successfully.",
                            "comment": (
                                "Invoice amount needs to be corrected."
                            ),
                        },
                    ),
                ],
            ),
            400: OpenApiResponse(
                response=RejectErrorResponseSerializer,
                description=(
                    "Invoice is not submitted or rejection "
                    "comment is missing."
                ),
                examples=[
                    OpenApiExample(
                        "Missing comment",
                        value={
                            "comment": (
                                "A rejection reason is required."
                            )
                        },
                    ),
                    OpenApiExample(
                        "Invalid status",
                        value={
                            "detail": (
                                "Only submitted invoices can be rejected."
                            )
                        },
                    ),
                ],
            ),
            403: OpenApiResponse(
                response=DetailResponseSerializer,
                description="User does not have permission to reject.",
                examples=[
                    OpenApiExample(
                        "Forbidden",
                        value={
                            "detail": (
                                "You do not have permission "
                                "to perform this action."
                            )
                        },
                    ),
                ],
            ),
        },
    )
    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsManagerOrAdminForApproval],
    )
    def reject(self, request, pk=None):
        invoice = self.get_object()

        if invoice.status != Invoice.Status.SUBMITTED:
            return Response(
                {
                    "detail": "Only submitted invoices can be rejected."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        comment = request.data.get("comment", "").strip()

        if not comment:
            return Response(
                {
                    "comment": "A rejection reason is required."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        invoice.status = Invoice.Status.REJECTED
        invoice.save(
            update_fields=["status", "updated_at"]
        )

        InvoiceHistory.objects.create(
            invoice=invoice,
            action=InvoiceHistory.Action.REJECTED,
            performed_by=request.user,
            comment=comment,
        )

        return Response(
            {
                "detail": "Invoice rejected successfully.",
                "comment": comment,
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Mark invoice as paid",
        description=(
            "Allows an accountant or admin to mark "
            "an approved invoice as paid."
        ),
        request=None,
        responses={
            200: OpenApiResponse(
                response=DetailResponseSerializer,
                description="Invoice marked as paid successfully.",
                examples=[
                    OpenApiExample(
                        "Success",
                        value={
                            "detail": (
                                "Invoice marked as paid successfully."
                            )
                        },
                    ),
                ],
            ),
            400: OpenApiResponse(
                response=DetailResponseSerializer,
                description="Invoice is not approved.",
                examples=[
                    OpenApiExample(
                        "Invalid status",
                        value={
                            "detail": (
                                "Only approved invoices can be "
                                "marked as paid."
                            )
                        },
                    ),
                ],
            ),
            403: OpenApiResponse(
                response=DetailResponseSerializer,
                description=(
                    "User does not have permission "
                    "to mark the invoice as paid."
                ),
                examples=[
                    OpenApiExample(
                        "Forbidden",
                        value={
                            "detail": (
                                "You do not have permission "
                                "to perform this action."
                            )
                        },
                    ),
                ],
            ),
        },
    )
    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAccountantOrAdmin],
    )
    def mark_paid(self, request, pk=None):
        invoice = self.get_object()

        if invoice.status != Invoice.Status.APPROVED:
            return Response(
                {
                    "detail": (
                        "Only approved invoices can be marked as paid."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        invoice.status = Invoice.Status.PAID
        invoice.save(
            update_fields=["status", "updated_at"]
        )

        InvoiceHistory.objects.create(
            invoice=invoice,
            action=InvoiceHistory.Action.PAID,
            performed_by=request.user,
        )

        return Response(
            {
                "detail": "Invoice marked as paid successfully."
            },
            status=status.HTTP_200_OK,
        )