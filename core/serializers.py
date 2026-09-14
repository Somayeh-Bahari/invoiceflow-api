from rest_framework import serializers

from .models import Customer, Invoice, InvoiceHistory


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = "__all__"


class InvoiceHistorySerializer(serializers.ModelSerializer):
    performed_by_username = serializers.CharField(
        source="performed_by.username",
        read_only=True,
    )

    class Meta:
        model = InvoiceHistory
        fields = [
            "id",
            "action",
            "performed_by",
            "performed_by_username",
            "comment",
            "created_at",
        ]

        read_only_fields = [
            "performed_by",
            "created_at",
        ]


class RejectInvoiceRequestSerializer(serializers.Serializer):
    comment = serializers.CharField(
        required=True,
        allow_blank=False,
        max_length=500,
    )


class InvoiceSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(
        source="customer.name",
        read_only=True,
    )

    created_by_username = serializers.CharField(
        source="created_by.username",
        read_only=True,
    )

    history = InvoiceHistorySerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = Invoice
        fields = [
            "id",
            "invoice_number",
            "customer",
            "customer_name",
            "created_by",
            "created_by_username",
            "issue_date",
            "due_date",
            "amount",
            "status",
            "notes",
            "created_at",
            "updated_at",
            "history",
        ]

        read_only_fields = [
            "created_by",
        ]

    def validate(self, data):
        issue_date = data.get(
            "issue_date",
            getattr(self.instance, "issue_date", None),
        )

        due_date = data.get(
            "due_date",
            getattr(self.instance, "due_date", None),
        )

        amount = data.get(
            "amount",
            getattr(self.instance, "amount", None),
        )

        new_status = data.get("status")

        if amount is not None and amount <= 0:
            raise serializers.ValidationError({
                "amount": "Amount must be greater than zero."
            })

        if issue_date and due_date and due_date < issue_date:
            raise serializers.ValidationError({
                "due_date": "Due date cannot be before issue date."
            })

        request = self.context.get("request")

        if request and self.instance and new_status:
            user = request.user

            if (
                getattr(user, "role", None) == "EMPLOYEE"
                and new_status != Invoice.Status.DRAFT
            ):
                raise serializers.ValidationError({
                    "status": (
                        "Employees must use the submit action "
                        "to change invoice status."
                    )
                })

        return data