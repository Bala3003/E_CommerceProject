from .utils.invoice import generate_invoice_pdf
from django.db.models import Q
from django.shortcuts import render, get_object_or_404,redirect
from .models import Product, Category,Order,OrderItem,Profile
from django.core.paginator import Paginator
from django.contrib import messages
from decimal import Decimal
from django.http import FileResponse,Http404,HttpResponse

from .forms import UserRegistrationForm, UserUpdateForm, ProfileForm,ProductForm
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required,user_passes_test
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm

def home(request):
    return render(request, 'home.html')

def products(request):
    products = Product.objects.all()
    return render(request, 'products.html', {'products': products})

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug,available=True)
    return render(request, 'product_details.html', {'product': product})

def product_list(request):
    qs = Product.objects.filter(available=True).order_by('-created_at')
    paginator = Paginator(qs, 12)
    page = request.GET.get('page')
    page_obj = paginator.get_page(page)

    categories = Category.objects.all()
    return render(request, 'products.html', {
        'products': page_obj.object_list,
        'page_obj': page_obj,
        'categories': categories,
        'current_category': None,
    })

def product_list_by_category(request, category_slug):
    category = get_object_or_404(Category, slug=category_slug)
    qs = Product.objects.filter(category=category, is_active=True).order_by('-created_at')
    paginator = Paginator(qs, 12)
    page = request.GET.get('page')
    page_obj = paginator.get_page(page)

    categories = Category.objects.all()
    return render(request, 'products.html', {
        'products': page_obj.object_list,
        'page_obj': page_obj,
        'categories': categories,
        'current_category': category,
    })

def categories_list(request):
    categories = Category.objects.all().order_by('name')
    return render(request, 'categories.html', {'categories': categories})

def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    products_qs = category.products.filter(available=True).order_by('-id')  # uses related_name

    paginator = Paginator(products_qs, 8)   # 8 products per page
    page = request.GET.get('page')
    products = paginator.get_page(page)

    return render(request, 'categories_detail.html', {
        'category': category,
        'products': products
    })

def orderitems(request):
    return render(request, 'orderitems.html')

def privacy(request):
    return render(request, 'privacy.html')

def terms(request):
    return render(request, 'terms.html')

def add_to_cart(request, slug):
    product = get_object_or_404(Product, slug=slug)
    if request.method == 'POST' or request.method == 'GET':
        cart = request.session.get('cart', {})
        pid = str(product.id)
        cart[pid] = cart.get(pid, 0) + 1
        request.session['cart'] = cart
        request.session.modified = True
        return redirect('orders')

    return redirect('products')
def cart_view(request):
    cart = request.session.get('cart', [])
    products = Product.objects.filter(id__in=cart)
    return render(request, 'cart.html', {'products': products})

def orders(request):
    cart = request.session.get('cart', {})  # cart is a dict: { '1': 2, '3': 1 }
    items = []
    total = Decimal('0.00')

    if cart:
        product_ids = [int(pid) for pid in cart.keys()]
        products = Product.objects.filter(id__in=product_ids)
        product_map = {p.id: p for p in products}

        for pid_str, qty in cart.items():
            pid = int(pid_str)
            p = product_map.get(pid)
            if not p:
                continue
            quantity = int(qty)
            subtotal = p.price * quantity
            total += subtotal
            items.append({
                'product': p,
                'quantity': quantity,
                'subtotal': subtotal,
            })

    return render(request, 'orders.html', {
        'items': items,
        'total': total,
    })

def update_cart(request):
    if request.method != 'POST':
        return redirect('orders')

    cart = request.session.get('cart', {})
    product_id = str(request.POST.get('product_id'))
    action = request.POST.get('action')
    quantity = request.POST.get('quantity', 1)

    if action == 'update':
        try:
            quantity = int(quantity)
            if quantity < 1:
                quantity = 1
            if product_id in cart:
                cart[product_id] = quantity
                messages.success(request, "Cart updated successfully!")
        except ValueError:
            messages.error(request, "Invalid quantity value.")
    elif action == 'remove':
        if product_id in cart:
            del cart[product_id]
            messages.success(request, "Item removed from cart.")

    request.session['cart'] = cart
    request.session.modified = True
    return redirect('orders')

def checkout(request):
    cart = request.session.get('cart', {})
    if not cart:
        messages.error(request, "Your cart is empty.")
        return redirect('products')

    product_ids = [int(pid) for pid in cart.keys()]
    products = Product.objects.filter(id__in=product_ids)
    product_map = {p.id: p for p in products}

    items = []
    total = Decimal('0.00')
    for pid_str, qty in cart.items():
        pid = int(pid_str)
        p = product_map.get(pid)
        if not p:
            continue
        subtotal = p.price * qty
        total += subtotal
        items.append({'product': p, 'quantity': qty, 'subtotal': subtotal})

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        address_line1 = request.POST.get('address_line1', '').strip()
        city = request.POST.get('city', '').strip()
        state = request.POST.get('state', '').strip()
        postal_code = request.POST.get('postal_code', '').strip()

        if not full_name:
            messages.error(request, "Name is required.")
        elif not phone:
            messages.error(request, "Phone number is required.")
        elif not phone.isdigit() or len(phone) != 10:
            messages.error(request, "Phone number must be 10 digits.")
        elif not address_line1:
            messages.error(request, "Address is required.")
        elif not city:
            messages.error(request, "City is required.")
        elif not state:
            messages.error(request, "State is required.")
        elif not postal_code:
            messages.error(request, "Postal code is required.")
        else:
            order = Order.objects.create(
                full_name=full_name,
                phone=phone,
                address_line1=address_line1,
                city=city,
                state=state,
                postal_code=postal_code,
                total_amount=total,
                details = [{
                'product': it['product'].name,
                'quantity': it['quantity'],
                'price': float(it['product'].price),
                'subtotal': float(it['subtotal']),
            } for it in items]
            )

            for it in items:
                OrderItem.objects.create(
                    order=order,
                    product=it['product'],
                    quantity=it['quantity'],
                    price=it['product'].price,
                    subtotal=it['subtotal']
                )
        pdf_bytes = generate_invoice_pdf(order)
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice_{order.id}.pdf"'
        return response

    return render(request, 'checkout.html', {
        'items': items,
        'total': total,
        'form': request.POST
    })

def checkout_success(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'checkout_success.html', {'order': order})

def place_order(request):
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        address1 = request.POST.get('address_line1', '').strip()
        address2 = request.POST.get('address_line2', '').strip()
        city = request.POST.get('city', '').strip()
        state = request.POST.get('state', '').strip()
        postal_code = request.POST.get('postal_code', '').strip()

        cart = request.session.get('cart', {})
        total = 0

        for product_id, quantity in cart.items():
            try:
                product = Product.objects.get(id=int(product_id))
                total += product.price * int(quantity)
            except Product.DoesNotExist:
                continue

        if not full_name:
            messages.error(request, "Full name is required.")
        elif not phone.isdigit() or len(phone) != 10:
            messages.error(request, "Phone number must be 10 digits.")
        elif not address1 or not city or not state or not postal_code:
            messages.error(request, "All address fields are required.")
        else:
            order = Order.objects.create(
                full_name=full_name,
                phone=phone,
                address_line1=address1,
                address_line2=address2,
                city=city,
                state=state,
                postal_code=postal_code,
                total_amount=total
            )

            for product_id, quantity in cart.items():
                try:
                    product = Product.objects.get(id=int(product_id))
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=quantity,
                        price=product.price,
                        subtotal=product.price * int(quantity)
                    )
                except Product.DoesNotExist:
                    continue

            request.session['cart'] = {}
            from django.urls import reverse
            url = reverse('checkout_success', args=[order.id])
            return redirect(url)

        messages.error(request, "Please correct the errors below.")

    return redirect('cart')

def download_invoice(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if not order.invoice:
        pdf_bytes = generate_invoice_pdf(order)
        return HttpResponse(pdf_bytes, content_type='application/pdf')
    try:
        return FileResponse(order.invoice.open('rb'), as_attachment=True, filename=f"invoice_{order.id}.pdf")
    except FileNotFoundError:
        raise Http404("Invoice not found")

def signup_view(request):
    """Handles user registration"""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # Auto-login after registration
            messages.success(request, "Account created successfully! 🎉")
            return redirect('home')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = UserRegistrationForm()
    return render(request, 'registration/signup.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}! 👋")
            return redirect('home')
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
    return render(request, 'registration/login.html', {'form': form})


@login_required
def logout_view(request):
    """Logs out the current user"""
    logout(request)
    messages.info(request, "You’ve been logged out successfully. 👋")
    return redirect('home')


@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Prevents logout after password change
            messages.success(request, "Password updated successfully! 🔒")
            return redirect('profile')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'registration/password_change.html', {'form': form})


@login_required
def profile_view(request):
    user_profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileForm(request.POST, request.FILES, instance=user_profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "✅ Profile updated successfully!")
            return redirect('profile')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileForm(instance=user_profile)

    return render(request, 'registration/profile.html', {
        'user_form': user_form,
        'profile_form': profile_form,
    })

def search_products(request):
    query = request.GET.get('q', '').strip()
    if not query:
        return redirect('products')

    results = Product.objects.filter(
        Q(name__icontains=query) | Q(description__icontains=query)
    )

    if results.count() == 1:
        product = results.first()
        return redirect('product_detail', slug=product.slug)

    return render(request, 'search_results.html', {
        'query': query,
        'results': results
    })

@user_passes_test(lambda u: u.is_superuser)
def admin_dashboard(request):
    products = Product.objects.all()
    return render(request, 'admin_dashboard/dashboard.html', {'products': products})

@user_passes_test(lambda u: u.is_superuser)
def add_product(request):
    if not request.user.is_superuser:
        return redirect('home')

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Product added successfully!")
            return redirect('admin_dashboard')
    else:
        form = ProductForm()

    return render(request, 'admin_dashboard/add_product.html', {'form': form})

@user_passes_test(lambda u: u.is_superuser)
def edit_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            return redirect('admin_dashboard')
    else:
        form = ProductForm(instance=product)
    return render(request, 'admin_dashboard/add_product.html', {'form': form})


@user_passes_test(lambda u: u.is_superuser)
def delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.delete()
    messages.warning(request, "🗑️ Product deleted successfully!")
    return redirect('admin_dashboard')

