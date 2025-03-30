# Order Payment Manager - Proposed Changes

## Overview
Based on the analysis of the current codebase, we need to make the following changes to improve the order payment management system:

1. Move customer type from Customer model to Order model
2. Move collection frequency settings from Customer model to Order model
3. Identify and show upcoming payments for customers
4. Add functionality to show defaulters

## Detailed Plan

### 1. Model Changes

#### Order Model
- Add `order_type` field to Order model with the same choices that were previously in Customer model
- Add `collection_frequency` field to Order model
- Add `collection_day_of_week` field to Order model
- Add `collection_day_of_month` field to Order model
- Add `next_payment_date` field to Order model (to be calculated based on collection frequency)

#### Customer Model
- Completely remove `customer_type` field from Customer model
- Completely remove `collection_frequency`, `collection_day_of_week`, and `collection_day_of_month` fields from Customer model
- Since there are very few orders, we don't need to worry about backward compatibility

### 2. Form Changes

#### OrderForm
- Update to include new fields (`order_type`, `collection_frequency`, etc.)
- Add JavaScript to show/hide relevant fields based on collection frequency

#### PaymentForm
- No significant changes needed

### 3. View Changes

#### Order Views
- Update views to handle new fields
- Add logic to calculate `next_payment_date` based on collection frequency

#### Payment Views
- Add functionality to identify the next upcoming payment for a customer
- Add ability to pay that specific payment

#### New Defaulters View
- Create a new view to show customers with pending payments
- Filter and sort by overdue status, collection frequency, etc.

### 4. Template Changes

#### Order Templates
- Update order creation and detail pages to include new fields
- Add conditional display based on order type and collection frequency

#### Dashboard
- Add a defaulters section showing customers with pending payments
- Show upcoming payments

### 5. Migration Strategy
- Create migrations for model changes
- Set default values for new fields in the Order model
- No need for migrations to preserve data since we're dropping the fields completely

## Implementation Timeline

1. Model Changes - First priority
2. Form and View Updates - Second priority
3. Templates and UI - Third priority
4. Testing - Final step

## Benefits

The proposed changes will:
- Allow tracking payment schedules per order rather than per customer
- Enable more flexible payment tracking
- Make it easier to identify defaulters
- Improve collection processes 