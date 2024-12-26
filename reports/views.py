from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, Count, F
from django.db.models.functions import TruncDate, TruncMonth, ExtractMonth
from django.utils import timezone
from app.models import Order, Payment, Customer, OrderItem
from datetime import datetime, timedelta
import calendar

class DailySalesReportView(LoginRequiredMixin, TemplateView):
    template_name = 'reports/daily_sales.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get the date from request or use today
        date_str = self.request.GET.get('date')
        if date_str:
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                target_date = timezone.now().date()
        else:
            target_date = timezone.now().date()

        # Get orders for the day
        daily_orders = Order.objects.filter(order_date=target_date)
        
        # Calculate order totals using F() expressions
        order_items_total = OrderItem.objects.filter(
            order__order_date=target_date
        ).aggregate(
            total_amount=Sum(F('quantity') * F('price'))
        )
        
        order_total = {
            'total_amount': order_items_total['total_amount'],
            'order_count': daily_orders.count()
        }

        # Get payments for the day
        daily_payments = Payment.objects.filter(payment_date=target_date)
        payment_total = daily_payments.aggregate(
            total_received=Sum('amount_received'),
            payment_count=Count('id')
        )

        # Get top selling items using F() expressions
        top_items = OrderItem.objects.filter(
            order__order_date=target_date
        ).values('item_name').annotate(
            total_quantity=Sum('quantity'),
            total_amount=Sum(F('quantity') * F('price'))
        ).order_by('-total_amount')[:5]

        context.update({
            'target_date': target_date,
            'order_total': order_total['total_amount'] or 0,
            'order_count': order_total['order_count'] or 0,
            'payment_total': payment_total['total_received'] or 0,
            'payment_count': payment_total['payment_count'] or 0,
            'top_items': top_items,
            'daily_orders': daily_orders,
            'daily_payments': daily_payments,
        })
        return context

class MonthlyReportView(LoginRequiredMixin, TemplateView):
    template_name = 'reports/monthly_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get current year for the dropdown
        current_year = timezone.now().year
        
        # Get the month and year from request or use current month
        year = self.request.GET.get('year', current_year)
        month = self.request.GET.get('month', timezone.now().month)
        try:
            year = int(year)
            month = int(month)
            start_date = datetime(year, month, 1).date()
            _, last_day = calendar.monthrange(year, month)
            end_date = datetime(year, month, last_day).date()
        except (ValueError, TypeError):
            start_date = timezone.now().replace(day=1).date()
            _, last_day = calendar.monthrange(start_date.year, start_date.month)
            end_date = start_date.replace(day=last_day)
            year = start_date.year
            month = start_date.month

        # Get orders for the month
        monthly_orders = Order.objects.filter(
            order_date__range=[start_date, end_date]
        ).prefetch_related('orderitems')

        # Calculate monthly totals
        total_amount = 0
        total_items = 0
        item_totals = {}  # For tracking item-wise totals

        for order in monthly_orders:
            for item in order.orderitems.all():
                total_amount += item.quantity * item.price
                total_items += item.quantity
                
                # Track item-wise totals
                if item.item_name not in item_totals:
                    item_totals[item.item_name] = {
                        'total_quantity': 0,
                        'total_amount': 0
                    }
                item_totals[item.item_name]['total_quantity'] += item.quantity
                item_totals[item.item_name]['total_amount'] += item.quantity * item.price

        # Convert item totals to sorted list for top items
        top_items = [
            {
                'item_name': k,
                'total_quantity': v['total_quantity'],
                'total_amount': v['total_amount']
            }
            for k, v in item_totals.items()
        ]
        top_items.sort(key=lambda x: x['total_amount'], reverse=True)
        top_items = top_items[:10]

        # Get payments for the month
        monthly_payments = Payment.objects.filter(
            payment_date__range=[start_date, end_date]
        )
        payment_total = monthly_payments.aggregate(
            total_received=Sum('amount_received'),
            payment_count=Count('id')
        )

        # Calculate daily trends
        daily_trends = {}
        for order in monthly_orders:
            date_str = order.order_date.strftime('%Y-%m-%d')
            if date_str not in daily_trends:
                daily_trends[date_str] = {
                    'date': order.order_date,
                    'total_orders': 0,
                    'total_amount': 0
                }
            daily_trends[date_str]['total_orders'] += 1
            order_amount = sum(item.quantity * item.price for item in order.orderitems.all())
            daily_trends[date_str]['total_amount'] += order_amount

        # Convert daily trends to sorted list
        daily_trends = [
            {
                'date': v['date'],
                'total_orders': v['total_orders'],
                'total_amount': v['total_amount']
            }
            for v in daily_trends.values()
        ]
        daily_trends.sort(key=lambda x: x['date'])

        # Get customer payment patterns
        customer_patterns = {}
        for payment in monthly_payments:
            if payment.customer.name not in customer_patterns:
                customer_patterns[payment.customer.name] = {
                    'total_payments': 0,
                    'total_amount': 0
                }
            customer_patterns[payment.customer.name]['total_payments'] += 1
            customer_patterns[payment.customer.name]['total_amount'] += payment.amount_received

        # Convert customer patterns to sorted list
        customer_patterns = [
            {
                'customer__name': k,
                'total_payments': v['total_payments'],
                'total_amount': v['total_amount']
            }
            for k, v in customer_patterns.items()
        ]
        customer_patterns.sort(key=lambda x: x['total_amount'], reverse=True)
        customer_patterns = customer_patterns[:10]

        context.update({
            'current_year': current_year,
            'year': year,
            'month': month,
            'month_name': calendar.month_name[int(month)],
            'start_date': start_date,
            'end_date': end_date,
            'order_count': monthly_orders.count(),
            'order_total': total_amount,
            'total_items_sold': total_items,
            'payment_total': payment_total['total_received'] or 0,
            'payment_count': payment_total['payment_count'] or 0,
            'top_items': top_items,
            'daily_trends': daily_trends,
            'customer_patterns': customer_patterns,
            'monthly_orders': monthly_orders,
            'monthly_payments': monthly_payments,
        })
        return context

class DateRangeReportView(LoginRequiredMixin, TemplateView):
    template_name = 'reports/date_range_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get date range from request or use last 30 days
        try:
            start_date = datetime.strptime(
                self.request.GET.get('start_date'),
                '%Y-%m-%d'
            ).date()
            end_date = datetime.strptime(
                self.request.GET.get('end_date'),
                '%Y-%m-%d'
            ).date()
        except (ValueError, TypeError):
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=30)

        # Get previous period for comparison
        period_length = (end_date - start_date).days + 1
        prev_end_date = start_date - timedelta(days=1)
        prev_start_date = prev_end_date - timedelta(days=period_length-1)

        # Get orders for both periods
        current_orders = Order.objects.filter(
            order_date__range=[start_date, end_date]
        ).prefetch_related('orderitems')
        
        previous_orders = Order.objects.filter(
            order_date__range=[prev_start_date, prev_end_date]
        ).prefetch_related('orderitems')

        # Calculate totals for current period
        current_stats = self._calculate_period_stats(current_orders)
        
        # Calculate totals for previous period
        previous_stats = self._calculate_period_stats(previous_orders)

        # Get payments for both periods
        current_payments = Payment.objects.filter(
            payment_date__range=[start_date, end_date]
        )
        previous_payments = Payment.objects.filter(
            payment_date__range=[prev_start_date, prev_end_date]
        )

        # Calculate payment totals
        current_payment_total = current_payments.aggregate(
            total_received=Sum('amount_received'),
            payment_count=Count('id')
        )
        previous_payment_total = previous_payments.aggregate(
            total_received=Sum('amount_received'),
            payment_count=Count('id')
        )

        # Calculate growth percentages
        growth_stats = self._calculate_growth_stats(
            current_stats, previous_stats,
            current_payment_total, previous_payment_total
        )

        context.update({
            'start_date': start_date,
            'end_date': end_date,
            'prev_start_date': prev_start_date,
            'prev_end_date': prev_end_date,
            'current_stats': current_stats,
            'previous_stats': previous_stats,
            'current_payment_total': current_payment_total,
            'previous_payment_total': previous_payment_total,
            'growth_stats': growth_stats,
            'period_length': period_length,
            'current_orders': current_orders,
            'current_payments': current_payments,
        })
        return context

    def _calculate_period_stats(self, orders):
        """Calculate statistics for a given period."""
        total_amount = 0
        total_items = 0
        item_totals = {}
        daily_totals = {}

        for order in orders:
            order_date = order.order_date
            if order_date not in daily_totals:
                daily_totals[order_date] = {
                    'total_orders': 0,
                    'total_amount': 0
                }
            daily_totals[order_date]['total_orders'] += 1

            order_amount = 0
            for item in order.orderitems.all():
                amount = item.quantity * item.price
                total_amount += amount
                order_amount += amount
                total_items += item.quantity

                if item.item_name not in item_totals:
                    item_totals[item.item_name] = {
                        'total_quantity': 0,
                        'total_amount': 0
                    }
                item_totals[item.item_name]['total_quantity'] += item.quantity
                item_totals[item.item_name]['total_amount'] += amount

            daily_totals[order_date]['total_amount'] += order_amount

        # Convert daily totals to sorted list
        daily_trends = [
            {
                'date': date,
                'total_orders': data['total_orders'],
                'total_amount': data['total_amount']
            }
            for date, data in daily_totals.items()
        ]
        daily_trends.sort(key=lambda x: x['date'])

        # Get top items
        top_items = [
            {
                'item_name': k,
                'total_quantity': v['total_quantity'],
                'total_amount': v['total_amount']
            }
            for k, v in item_totals.items()
        ]
        top_items.sort(key=lambda x: x['total_amount'], reverse=True)
        top_items = top_items[:10]

        return {
            'total_amount': total_amount,
            'total_items': total_items,
            'order_count': orders.count(),
            'daily_trends': daily_trends,
            'top_items': top_items,
            'avg_daily_orders': len(daily_totals) and orders.count() / len(daily_totals) or 0,
            'avg_order_value': orders.count() and total_amount / orders.count() or 0
        }

    def _calculate_growth_stats(self, current_stats, previous_stats,
                              current_payment_total, previous_payment_total):
        """Calculate growth percentages between two periods."""
        def calculate_growth(current, previous):
            if not previous:
                return 100 if current else 0
            return ((current - previous) / previous) * 100

        return {
            'order_count_growth': calculate_growth(
                current_stats['order_count'],
                previous_stats['order_count']
            ),
            'total_amount_growth': calculate_growth(
                current_stats['total_amount'],
                previous_stats['total_amount']
            ),
            'total_items_growth': calculate_growth(
                current_stats['total_items'],
                previous_stats['total_items']
            ),
            'payment_count_growth': calculate_growth(
                current_payment_total['payment_count'] or 0,
                previous_payment_total['payment_count'] or 0
            ),
            'payment_amount_growth': calculate_growth(
                current_payment_total['total_received'] or 0,
                previous_payment_total['total_received'] or 0
            ),
            'avg_order_value_growth': calculate_growth(
                current_stats['avg_order_value'],
                previous_stats['avg_order_value']
            ),
            'avg_daily_orders_growth': calculate_growth(
                current_stats['avg_daily_orders'],
                previous_stats['avg_daily_orders']
            )
        }
