let products = [];
let cart = JSON.parse(localStorage.getItem('cart')) || [];
let currentPage = 1;

// Update cart count
function updateCartCount() {
    const cartCount = document.querySelector('.cart-count');
    if (cartCount) {
        const totalItems = cart.reduce((total, item) => total + item.quantity, 0);
        cartCount.textContent = totalItems;
    }
}

// Function to format price in Indian format
function formatIndianPrice(price) {
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR',
        minimumFractionDigits: 2
    }).format(price);
}

// Function to render products
function renderProducts(filteredProducts) {
    const container = document.getElementById('products-container');
    if (!container) return;

    if (!filteredProducts || filteredProducts.length === 0) {
        container.innerHTML = '<div class="no-products">No products found matching the selected filters</div>';
        return;
    }

    let productsHTML = '';
    filteredProducts.forEach(product => {
        const imageUrl = product.image_url.startsWith('/cart/static') ? 
            product.image_url : 
            `/cart/static/images/products/${product.category_name.toLowerCase()}/${product.image_url.split('/').pop()}`;
            
        productsHTML += `
            <div class="product-card">
                <div class="product-image">
                    <img src="${imageUrl}" 
                         alt="${product.name}"
                         onerror="this.src='/cart/static/images/no-image.png'">
                </div>
                <div class="product-info">
                    <h3>${product.name}</h3>
                    <div class="price">${formatIndianPrice(product.price)}</div>
                    <div class="weight">${product.weight}</div>
                    <div class="product-details">
                        <p>Fat: ${product.fat}g</p>
                        <p>Sugars: ${product.sugars}g</p>
                        <p>Sodium: ${product.sodium}mg</p>
                    </div>
                </div>
            </div>
        `;
    });

    container.innerHTML = productsHTML;
}

// Shopping Cart Functions
function addToCart(productId) {
    const product = products.find(p => p.id === productId);
    if (!product) return;

    const cartItem = cart.find(item => item.id === productId);
    if (cartItem) {
        cartItem.quantity += 1;
    } else {
        cart.push({
            id: product.id,
            name: product.name,
            price: product.price,
            quantity: 1,
            image_url: product.image_url
        });
    }

    localStorage.setItem('cart', JSON.stringify(cart));
    updateCartCount();
    showNotification('Product added to cart!');
    renderCart();
}

function removeFromCart(productId) {
    const index = cart.findIndex(item => item.id === productId);
    if (index !== -1) {
        if (cart[index].quantity > 1) {
            cart[index].quantity -= 1;
        } else {
            cart.splice(index, 1);
        }
        localStorage.setItem('cart', JSON.stringify(cart));
        updateCartCount();
        renderCart();
        showNotification('Product removed from cart!');
    }
}

function clearCart() {
    cart = [];
    localStorage.setItem('cart', JSON.stringify(cart));
    updateCartCount();
    renderCart();
    showNotification('Cart cleared!');
}

function renderCart() {
    const cartItems = document.getElementById('cart-items');
    const cartTotal = document.getElementById('cart-total-amount');
    if (!cartItems || !cartTotal) return;

    if (cart.length === 0) {
        cartItems.innerHTML = '<p>Your cart is empty</p>';
        cartTotal.textContent = '0.00';
        return;
    }

    let cartHTML = '';
    let total = 0;

    cart.forEach(item => {
        const itemTotal = item.price * item.quantity;
        total += itemTotal;
        cartHTML += `
            <div class="cart-item">
                <img src="${item.image_url}" alt="${item.name}" class="cart-item-image">
                <div class="cart-item-details">
                    <h4>${item.name}</h4>
                    <p>${formatIndianPrice(item.price)} x ${item.quantity}</p>
                </div>
                <div class="cart-item-actions">
                    <button onclick="removeFromCart(${item.id})">Remove</button>
                </div>
            </div>
        `;
    });

    cartItems.innerHTML = cartHTML;
    cartTotal.textContent = formatIndianPrice(total).replace('₹', '');
}

// Modal Functions
const modal = document.getElementById('shopping-cart-modal');
const cartTab = document.getElementById('cart-tab');
const closeBtn = document.querySelector('.close');

if (cartTab && modal) {
    cartTab.onclick = function() {
        modal.style.display = "block";
        renderCart();
    }
}

if (closeBtn && modal) {
    closeBtn.onclick = function() {
        modal.style.display = "none";
    }
}

if (modal) {
    window.onclick = function(event) {
        if (event.target == modal) {
            modal.style.display = "none";
        }
    }
}

// Function to show notification
function showNotification(message) {
    const notification = document.createElement('div');
    notification.className = 'notification';
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

// Function to get current category from URL
function getCurrentCategory() {
    const path = window.location.pathname;
    // Remove '/cart/' prefix and return the remaining path
    return path.replace('/cart/', '') || 'snacks';
}

// Function to fetch products
async function fetchProducts() {
    const container = document.getElementById('products-container');
    if (!container) return;

    container.innerHTML = '<div class="loading">Loading products...</div>';
        
    try {
        const category = getCurrentCategory();
        const response = await fetch(`/cart/${category}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const html = await response.text();
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        const productsData = JSON.parse(doc.getElementById('products-data')?.textContent || '[]');
        
        products = productsData;
        applyFilters();
    } catch (error) {
        console.error('Error fetching products:', error);
        container.innerHTML = '<div class="error">Unable to load products. Please try again later.</div>';
    }
}

// Filter function
function applyFilters() {
    let filtered = [...products];
    
    // Health filter
    const selectedHealth = document.querySelector('input[name="health"]:checked')?.value;
    if (selectedHealth && selectedHealth !== 'normal') {
        filtered = filtered.filter(product => {
            const healthRestrictions = product.health_restrictions ? product.health_restrictions.split(',') : [];
            return !healthRestrictions.includes(selectedHealth);
        });
    }

    // Sort
    const sortValue = document.getElementById('sort-select')?.value;
    if (sortValue) {
        switch (sortValue) {
            case 'price-high-low':
                filtered.sort((a, b) => b.price - a.price);
                break;
            case 'price-low-high':
                filtered.sort((a, b) => a.price - b.price);
                break;
            case 'weight-high-low':
                filtered.sort((a, b) => parseFloat(b.weight) - parseFloat(a.weight));
                break;
            case 'weight-low-high':
                filtered.sort((a, b) => parseFloat(a.weight) - parseFloat(b.weight));
                break;
        }
    }

    renderProducts(filtered);
}

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    updateCartCount();
    fetchProducts();

    // Add event listeners for filters
    const healthFilters = document.querySelectorAll('input[name="health"]');
    healthFilters.forEach(filter => {
        filter.addEventListener('change', applyFilters);
    });

    const sortSelect = document.getElementById('sort-select');
    if (sortSelect) {
        sortSelect.addEventListener('change', applyFilters);
    }

    // Add event listener for clear cart button
    const clearCartBtn = document.getElementById('clear-cart');
    if (clearCartBtn) {
        clearCartBtn.addEventListener('click', clearCart);
    }
});