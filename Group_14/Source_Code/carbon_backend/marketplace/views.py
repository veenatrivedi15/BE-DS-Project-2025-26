from django.shortcuts import render

# Create your views here.

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Sum, Avg, Count, F, Q

from .models import MarketOffer, MarketplaceTransaction
from users.models import EmployerProfile
from .serializers import (
    MarketOfferSerializer, MarketOfferCreateSerializer,
    TransactionSerializer, TransactionCreateSerializer,
    TransactionApprovalSerializer, MarketStatsSerializer
)
from .permissions import IsEmployerOrAdmin, IsOfferParticipantOrAdmin, IsOfferSellerOrAdmin
from users.permissions import IsApprovedUser


class MarketOfferListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsApprovedUser, IsEmployerOrAdmin]
    
    def get(self, request):
        """List all active market offers"""
        offers = MarketOffer.objects.filter(status='active').order_by('-created_at')
        serializer = MarketOfferSerializer(offers, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        """Create a new market offer"""
        # Permission already checked by IsEmployerOrAdmin
        employer = request.user.employer_profile
        
        serializer = MarketOfferCreateSerializer(data=request.data)
        if serializer.is_valid():
            # Check if seller has enough credits
            # This would require integration with a credit balance system
            # For now, we'll assume they have enough
            
            # Create the offer
            offer = serializer.save(seller=employer)
            return Response(
                MarketOfferSerializer(offer).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MarketOfferDetailView(APIView):
    permission_classes = [IsAuthenticated, IsApprovedUser]
    
    def get(self, request, pk):
        """Get detailed information about a specific offer"""
        offer = get_object_or_404(MarketOffer, pk=pk)
        serializer = MarketOfferSerializer(offer)
        return Response(serializer.data)


class MarketOfferCancelView(APIView):
    permission_classes = [IsAuthenticated, IsApprovedUser, IsOfferSellerOrAdmin]
    
    def post(self, request, pk):
        """Cancel a market offer"""
        offer = get_object_or_404(MarketOffer, pk=pk)
        
        # Permission check
        self.check_object_permissions(request, offer)
            
        # Check if the offer can be cancelled
        if offer.status != 'active':
            return Response(
                {"error": "Only active offers can be cancelled"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Cancel the offer
        offer.status = 'cancelled'
        offer.save()
        
        # Cancel any pending transactions
        MarketplaceTransaction.objects.filter(
            offer=offer,
            status='pending'
        ).update(status='cancelled')
        
        serializer = MarketOfferSerializer(offer)
        return Response(serializer.data)


class TransactionListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsApprovedUser, IsEmployerOrAdmin]
    
    def get(self, request):
        """List all transactions for the current user"""
        # Permission already checked by IsEmployerOrAdmin
        employer = request.user.employer_profile
        
        # Get transactions where user is either buyer or seller
        transactions = MarketplaceTransaction.objects.filter(
            Q(buyer=employer) | Q(seller=employer)
        ).order_by('-created_at')
        
        serializer = TransactionSerializer(transactions, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        """Create a new transaction (purchase credits)"""
        # Permission already checked by IsEmployerOrAdmin
        employer = request.user.employer_profile
        
        # Add buyer to serializer context for validation
        serializer = TransactionCreateSerializer(
            data=request.data,
            context={'buyer': employer}
        )
        
        if serializer.is_valid():
            offer_id = serializer.validated_data.get('offer')
            credit_amount = serializer.validated_data.get('credit_amount')
            
            # Get the offer
            offer = get_object_or_404(MarketOffer, pk=offer_id)
            
            # Check if offer is active
            if offer.status != 'active':
                return Response(
                    {"error": "This offer is no longer active"},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Check if trying to buy from self
            if offer.seller == employer:
                return Response(
                    {"error": "You cannot buy your own credits"},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Check if enough credits available
            if credit_amount > offer.credit_amount:
                return Response(
                    {"error": "Not enough credits available in this offer"},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Check if buyer has enough funds (would integrate with payment system)
            # For now, assume they do
            
            # Create the transaction
            transaction = MarketplaceTransaction.objects.create(
                offer=offer,
                seller=offer.seller,
                buyer=employer,
                credit_amount=credit_amount,
                total_price=credit_amount * offer.price_per_credit,
                status='pending'
            )
            
            # If this purchase uses all remaining credits, mark offer as completed
            if credit_amount == offer.credit_amount:
                offer.status = 'completed'
                offer.save()
            # Otherwise, reduce the available credits
            else:
                offer.credit_amount -= credit_amount
                offer.total_price = offer.credit_amount * offer.price_per_credit
                offer.save()
                
            return Response(
                TransactionSerializer(transaction).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TransactionDetailView(APIView):
    permission_classes = [IsAuthenticated, IsApprovedUser, IsOfferParticipantOrAdmin]
    
    def get(self, request, pk):
        """Get details of a specific transaction"""
        transaction = get_object_or_404(MarketplaceTransaction, pk=pk)
        
        # Permission check
        self.check_object_permissions(request, transaction)
        
        serializer = TransactionSerializer(transaction)
        return Response(serializer.data)


class TransactionApprovalView(APIView):
    permission_classes = [IsAuthenticated, IsApprovedUser, IsOfferSellerOrAdmin]
    
    def post(self, request, pk):
        """Approve a transaction as the seller"""
        transaction = get_object_or_404(MarketplaceTransaction, pk=pk)
        
        # Permission check
        self.check_object_permissions(request, transaction)
        
        # Check transaction status
        if transaction.status != 'pending':
            return Response(
                {"error": "Only pending transactions can be approved"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update transaction status
        transaction.status = 'approved'
        transaction.completed_at = timezone.now()
        transaction.save()
        
        # If this transaction was for all credits in the offer, mark offer as completed
        if transaction.offer.status == 'active' and transaction.credit_amount == transaction.offer.credit_amount:
            transaction.offer.status = 'completed'
            transaction.offer.save()
        
        # Transfer the credits to the buyer
        # This would be where you'd call a function to actually transfer credits
        # For now, we'll assume the transfer happens automatically
        
        serializer = TransactionSerializer(transaction)
        return Response(serializer.data)


class TransactionRejectView(APIView):
    permission_classes = [IsAuthenticated, IsApprovedUser, IsOfferSellerOrAdmin]
    
    def post(self, request, pk):
        """Reject a transaction as the seller"""
        transaction = get_object_or_404(MarketplaceTransaction, pk=pk)
        
        # Permission check
        self.check_object_permissions(request, transaction)
        
        # Check transaction status
        if transaction.status != 'pending':
            return Response(
                {"error": "Only pending transactions can be rejected"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update transaction status
        transaction.status = 'rejected'
        transaction.save()
        
        # Return the credits to the offer
        offer = transaction.offer
        if offer.status == 'active' or offer.status == 'completed':
            offer.credit_amount += transaction.credit_amount
            offer.total_price = offer.credit_amount * offer.price_per_credit
            
            # If offer was marked as completed but we're rejecting the transaction,
            # reactivate the offer
            if offer.status == 'completed':
                offer.status = 'active'
                
            offer.save()
        
        serializer = TransactionSerializer(transaction)
        return Response(serializer.data)


class MarketStatsView(APIView):
    permission_classes = [IsAuthenticated, IsApprovedUser, IsEmployerOrAdmin]
    
    def get(self, request):
        """Get market statistics"""
        # Overall market stats
        active_offers = MarketOffer.objects.filter(status='active')
        completed_transactions = MarketplaceTransaction.objects.filter(status__in=['approved', 'completed'])
        
        stats = {
            'total_active_offers': active_offers.count(),
            'total_credits_available': active_offers.aggregate(Sum('credit_amount'))['credit_amount__sum'] or 0,
            'average_price_per_credit': active_offers.aggregate(Avg('price_per_credit'))['price_per_credit__avg'] or 0,
            'total_transactions_completed': completed_transactions.count(),
            'total_credits_traded': completed_transactions.aggregate(Sum('credit_amount'))['credit_amount__sum'] or 0,
            'total_transaction_value': completed_transactions.aggregate(Sum('total_price'))['total_price__sum'] or 0,
        }
        
        # User-specific stats if user is an employer
        try:
            employer = request.user.employer_profile
            
            user_stats = {
                'my_active_offers': MarketOffer.objects.filter(seller=employer, status='active').count(),
                'my_credits_for_sale': MarketOffer.objects.filter(seller=employer, status='active').aggregate(Sum('credit_amount'))['credit_amount__sum'] or 0,
                'my_completed_sales': MarketplaceTransaction.objects.filter(seller=employer, status__in=['approved', 'completed']).count(),
                'my_completed_purchases': MarketplaceTransaction.objects.filter(buyer=employer, status__in=['approved', 'completed']).count(),
                'credits_sold': MarketplaceTransaction.objects.filter(seller=employer, status__in=['approved', 'completed']).aggregate(Sum('credit_amount'))['credit_amount__sum'] or 0,
                'credits_purchased': MarketplaceTransaction.objects.filter(buyer=employer, status__in=['approved', 'completed']).aggregate(Sum('credit_amount'))['credit_amount__sum'] or 0,
            }
            
            stats.update(user_stats)
        except EmployerProfile.DoesNotExist:
            # User is not an employer, don't add user-specific stats
            pass
        
        serializer = MarketStatsSerializer(stats)
        return Response(serializer.data)
