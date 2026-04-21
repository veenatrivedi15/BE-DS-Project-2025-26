from rest_framework import serializers
from .models import MarketOffer, MarketplaceTransaction
from users.models import EmployerProfile


class EmployerProfileSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(read_only=True)
    
    class Meta:
        model = EmployerProfile
        fields = ['id', 'company_name']


class MarketOfferSerializer(serializers.ModelSerializer):
    seller = EmployerProfileSerializer(read_only=True)
    
    class Meta:
        model = MarketOffer
        fields = [
            'id', 'seller', 'credit_amount', 'price_per_credit',
            'total_price', 'status', 'expiry_date', 'created_at'
        ]
        read_only_fields = ['id', 'seller', 'status', 'created_at']


class MarketOfferCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketOffer
        fields = ['credit_amount', 'price_per_credit', 'expiry_date']
        
    def validate(self, data):
        # Ensure credit amount is positive
        if data.get('credit_amount', 0) <= 0:
            raise serializers.ValidationError({"credit_amount": "Credit amount must be positive"})
            
        # Ensure price is positive
        if data.get('price_per_credit', 0) <= 0:
            raise serializers.ValidationError({"price_per_credit": "Price per credit must be positive"})
            
        return data
        
    def create(self, validated_data):
        # Calculate total price
        credit_amount = validated_data.get('credit_amount')
        price_per_credit = validated_data.get('price_per_credit')
        total_price = credit_amount * price_per_credit
        
        # Create the offer
        offer = MarketOffer.objects.create(
            seller=validated_data.get('seller'),
            credit_amount=credit_amount,
            price_per_credit=price_per_credit,
            total_price=total_price,
            expiry_date=validated_data.get('expiry_date'),
            status='active'
        )
        
        return offer


class TransactionSerializer(serializers.ModelSerializer):
    seller = EmployerProfileSerializer(read_only=True)
    buyer = EmployerProfileSerializer(read_only=True)
    offer_details = MarketOfferSerializer(source='offer', read_only=True)
    
    class Meta:
        model = MarketplaceTransaction
        fields = [
            'id', 'offer', 'offer_details', 'seller', 'buyer',
            'credit_amount', 'total_price', 'status',
            'admin_approval_required', 'created_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'seller', 'buyer', 'total_price', 'status',
            'admin_approval_required', 'created_at', 'completed_at'
        ]


class TransactionCreateSerializer(serializers.Serializer):
    offer = serializers.IntegerField()
    credit_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    def validate(self, data):
        # Ensure credit amount is positive
        if data.get('credit_amount', 0) <= 0:
            raise serializers.ValidationError({"credit_amount": "Credit amount must be positive"})
            
        return data


class TransactionApprovalSerializer(serializers.Serializer):
    approved = serializers.BooleanField()
    rejection_reason = serializers.CharField(required=False, allow_blank=True)


class MarketStatsSerializer(serializers.Serializer):
    total_active_offers = serializers.IntegerField()
    total_credits_available = serializers.DecimalField(max_digits=12, decimal_places=2)
    average_price_per_credit = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_transactions_completed = serializers.IntegerField()
    total_credits_traded = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_transaction_value = serializers.DecimalField(max_digits=14, decimal_places=2)
    
    # User-specific fields (optional)
    my_active_offers = serializers.IntegerField(required=False)
    my_credits_for_sale = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    my_completed_sales = serializers.IntegerField(required=False)
    my_completed_purchases = serializers.IntegerField(required=False)
    credits_sold = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    credits_purchased = serializers.DecimalField(max_digits=12, decimal_places=2, required=False) 