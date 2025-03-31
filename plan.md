# Plan for Resolving Upcoming Payments Due Date Issue

## Overview

The upcoming payments view is intended to display EMI orders with their next due installment dates. However, currently the due date is showing as `None` for orders where we expect a valid due date. This plan outlines the investigation, proposed changes, and the overall user flow.

## Issues Identified

1. **Next Payment Date Calculation:**
   - The `Order` model has a computed method `get_next_payment_date()` which is supposed to return the due date of the earliest unpaid installment from its associated `OrderPayment` entries.
   - Currently, the upcoming payments view and its query rely on the static field `next_payment_date`, which may not be updated properly, instead of consistently using the computed method.

2. **EMI Schedule Generation:**
   - When an EMI order is created, the `Order.save()` method generates a complete payment schedule (i.e., creates `OrderPayment` entries) based on the order details.
   - Once payments are made, the computed next due date should reflect the earliest unpaid installment.

3. **View & Template Usage:**
   - The Upcoming Payments view groups orders by customer and displays the due date using `order_info.next_payment_date` (which is derived from calling `order.get_next_payment_date()`).
   - The query in the view filters orders based on the static field `next_payment_date` being non-null, which might be conflicting with the computed value.

## Proposed Changes

1. **Use Computed Next Payment Date:**
   - Update the Upcoming Payments view and its template to rely on the computed `get_next_payment_date()` method for determining the due date of an order, rather than the stored `next_payment_date` field.

2. **Ensure Correct EMI Schedule Generation:**
   - Confirm that the EMI schedule is generated properly in the `Order.save()` method when an EMI order is created.
   - Verify that when payments are recorded, the corresponding `OrderPayment` entries are updated, so that the computed `get_next_payment_date()` returns the correct upcoming installment due date.

3. **Review Filtering in Upcoming Payments View:**
   - Review and possibly modify the filtering criteria in the Upcoming Payments view to use the computed due date.

## Current User Flow

1. **EMI Order Creation:**
   - A user creates an EMI order via the "Create Order" page.
   - The user fills in details such as the order date, EMI amount, and collection frequency/days.

2. **EMI Schedule Generation:**
   - Upon saving the order, the overridden `Order.save()` method is triggered.
   - The method calls `get_payment_schedule()` to generate a complete schedule of installments.
   - For each installment, an `OrderPayment` entry is created with a due date calculated based on the provided collection frequency.

3. **Displaying Upcoming Payments:**
   - The Upcoming Payments view groups orders by customer and displays each order along with its next due installment.
   - The due date shown is obtained by calling `order.get_next_payment_date()`, which scans for the earliest unpaid installment.

4. **Recording Payments:**
   - The user records a payment through the Payment Create view.
   - The corresponding `OrderPayment` entries are updated to link to the new payment.
   - As installments are paid off, subsequent unpaid installments become the "next due date." 

5. **Dashboard Update:**
   - The home/dashboard view and Upcoming Payments view are updated to reflect the current status of orders, including overdue and due soon notifications based on the computed next payment dates.

## Next Steps

- **Review:** Please review this plan.md. Confirm if the plan meets your expectations.
- **Approval:** Once approved, we will proceed with implementing the changes as described.

This plan is designed to ensure that EMI orders correctly display the upcoming due installment dates and that the overall user experience remains consistent and intuitive. 