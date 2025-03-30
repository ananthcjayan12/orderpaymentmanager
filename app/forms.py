from django import forms
from django.forms import inlineformset_factory
from .models import Order, OrderItem, Payment, Item, OrderTemplate, OrderTemplateItem, Customer

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['customer', 'order_date', 'remarks']
        widgets = {
            'order_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company:
            self.fields['customer'].queryset = Customer.objects.filter(company=company)
        if 'initial' in kwargs and 'customer' in kwargs['initial']:
            self.fields['customer'].widget.attrs['readonly'] = True
            self.fields['customer'].disabled = True

class OrderItemForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ['item', 'item_name', 'quantity', 'price', 'remarks']
        widgets = {
            'item': forms.HiddenInput(),
            'item_name': forms.TextInput(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'remarks': forms.TextInput(attrs={'class': 'form-control'}),
        }

# Create the formset with more configuration
OrderItemFormSet = inlineformset_factory(
    Order, 
    OrderItem,
    form=OrderItemForm,
    extra=1,
    min_num=1,
    validate_min=True,
    can_delete=True,
    fields=['item', 'item_name', 'quantity', 'price', 'remarks'],
)

class BulkOrderForm(forms.Form):
    customer = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    order_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    remarks = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )
    items_data = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Customer
        self.fields['customer'].queryset = Customer.objects.filter(company=company)

class OrderTemplateForm(forms.ModelForm):
    class Meta:
        model = OrderTemplate
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Template Name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Template Description'}),
        }

OrderTemplateItemFormSet = inlineformset_factory(
    OrderTemplate,
    OrderTemplateItem,
    fields=('item', 'quantity', 'default_price', 'remarks'),
    extra=1,
    can_delete=True,
    widgets={
        'item': forms.Select(attrs={'class': 'form-control item-select'}),
        'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
        'default_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
        'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
    }
)

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['customer', 'amount_received', 'notes']
        widgets = {
            'amount_received': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company:
            self.fields['customer'].queryset = Customer.objects.filter(company=company)
        if 'initial' in kwargs and 'customer' in kwargs['initial']:
            self.fields['customer'].widget.attrs['readonly'] = True
            self.fields['customer'].disabled = True 

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = [
            'name', 'address', 'mobile1', 'mobile2', 'location', 'id_number', 
            'customer_type', 'collection_frequency', 'collection_day_of_week', 
            'collection_day_of_month', 'initial_balance'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Customer Name'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Address'}),
            'mobile1': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Primary Mobile'}),
            'mobile2': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Secondary Mobile (Optional)'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Location'}),
            'id_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ID Number (Optional)'}),
            'customer_type': forms.Select(attrs={'class': 'form-select'}),
            'collection_frequency': forms.Select(attrs={'class': 'form-select'}),
            'collection_day_of_week': forms.Select(attrs={'class': 'form-select', 'data-frequency': 'WEEKLY'}),
            'collection_day_of_month': forms.NumberInput(attrs={
                'class': 'form-control', 
                'min': '1', 
                'max': '31',
                'data-frequency': 'MONTHLY'
            }),
            'initial_balance': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Initial Outstanding Balance'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['initial_balance'].help_text = 'Enter any existing balance the customer owes from before using this system.'
        self.fields['initial_balance'].label = 'Initial Outstanding Balance'
        self.fields['customer_type'].help_text = 'Select the type of customer relationship'
        self.fields['collection_frequency'].help_text = 'Set a regular collection schedule if applicable'
        self.fields['collection_day_of_week'].help_text = 'Select the day of the week for weekly collections'
        self.fields['collection_day_of_month'].help_text = 'Enter the day of month (1-31) for monthly collections'

class CustomerCSVUploadForm(forms.Form):
    csv_file = forms.FileField(
        label='Upload CSV File',
        help_text='CSV file should contain columns: name, address, mobile1, mobile2, location, id_number, initial_balance',
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.csv'})
    ) 