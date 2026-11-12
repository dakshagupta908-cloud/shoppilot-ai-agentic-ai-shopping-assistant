from sqlalchemy.orm import Session

from app.models import Product

PRODUCTS = [
    ("lap-01", "IdeaPad Slim 5", "Lenovo", "Laptops", "Thin laptop for programming, study and daily work.", 57990, {"RAM": "16GB", "Storage": "512GB SSD", "Processor": "Ryzen 5 7530U", "Weight": "1.46 kg", "Battery": "Up to 8 hours"}, 4.4, "laptop"),
    ("lap-02", "Inspiron 14", "Dell", "Laptops", "Balanced 14-inch laptop for college and productivity.", 62990, {"RAM": "16GB", "Storage": "512GB SSD", "Processor": "Intel Core i5-1335U", "Weight": "1.54 kg", "Battery": "Up to 7 hours"}, 4.3, "laptop"),
    ("lap-03", "Vivobook 15 OLED", "ASUS", "Laptops", "OLED display laptop with capable everyday performance.", 64990, {"RAM": "16GB", "Storage": "512GB SSD", "Processor": "Intel Core i5-12500H", "Weight": "1.70 kg", "Display": "15.6-inch OLED"}, 4.5, "laptop"),
    ("lap-04", "Pavilion Aero 13", "HP", "Laptops", "Lightweight laptop suited to commuting and coursework.", 68990, {"RAM": "16GB", "Storage": "512GB SSD", "Processor": "Ryzen 5 8640U", "Weight": "0.99 kg", "Battery": "Up to 10 hours"}, 4.6, "laptop"),
    ("lap-05", "LOQ 15", "Lenovo", "Laptops", "Entry gaming laptop with dedicated graphics for heavier workloads.", 74990, {"RAM": "16GB", "Storage": "512GB SSD", "Processor": "Intel Core i5-12450H", "Graphics": "RTX 2050", "Weight": "2.4 kg"}, 4.4, "laptop"),
    ("lap-06", "MacBook Air 13", "Apple", "Laptops", "Fanless laptop for mobile productivity and long battery life.", 99900, {"RAM": "8GB", "Storage": "256GB SSD", "Processor": "Apple M2", "Weight": "1.24 kg", "Battery": "Up to 18 hours"}, 4.7, "laptop"),
    ("ph-01", "Pixel 8a", "Google", "Smartphones", "Android phone with computational photography features.", 52999, {"RAM": "8GB", "Storage": "128GB", "Camera": "64MP main", "Display": "6.1-inch OLED", "Battery": "4492 mAh"}, 4.5, "smartphone"),
    ("ph-02", "Galaxy A55 5G", "Samsung", "Smartphones", "Midrange 5G smartphone with a vivid AMOLED display.", 39999, {"RAM": "8GB", "Storage": "128GB", "Camera": "50MP main", "Display": "6.6-inch AMOLED", "Battery": "5000 mAh"}, 4.4, "smartphone"),
    ("ph-03", "iPhone 15", "Apple", "Smartphones", "Compact premium smartphone with a dual-camera system.", 69900, {"RAM": "6GB", "Storage": "128GB", "Camera": "48MP main", "Display": "6.1-inch OLED"}, 4.7, "smartphone"),
    ("ph-04", "Nothing Phone (2a)", "Nothing", "Smartphones", "Distinctive midrange phone with clean software and 5G.", 25999, {"RAM": "8GB", "Storage": "128GB", "Camera": "50MP dual", "Display": "6.7-inch AMOLED", "Battery": "5000 mAh"}, 4.3, "smartphone"),
    ("ph-05", "OnePlus 12R", "OnePlus", "Smartphones", "Performance-focused phone with fast charging.", 45999, {"RAM": "8GB", "Storage": "128GB", "Camera": "50MP main", "Display": "6.78-inch AMOLED", "Battery": "5500 mAh"}, 4.5, "smartphone"),
    ("hp-01", "WH-CH720N", "Sony", "Headphones", "Wireless noise-cancelling over-ear headphones for commuting.", 8990, {"Type": "Over-ear", "Noise cancellation": "Active", "Battery": "Up to 35 hours", "Connectivity": "Bluetooth"}, 4.4, "headphones"),
    ("hp-02", "Tune 770NC", "JBL", "Headphones", "Foldable wireless headphones with adaptive noise cancellation.", 7999, {"Type": "Over-ear", "Noise cancellation": "Adaptive ANC", "Battery": "Up to 70 hours", "Connectivity": "Bluetooth"}, 4.3, "headphones"),
    ("hp-03", "QuietComfort Headphones", "Bose", "Headphones", "Comfort-focused headphones with adjustable noise cancellation.", 24900, {"Type": "Over-ear", "Noise cancellation": "Adjustable ANC", "Battery": "Up to 24 hours", "Connectivity": "Bluetooth"}, 4.6, "headphones"),
    ("hp-04", "Soundcore Space One", "Anker", "Headphones", "Travel headphones with noise cancellation and long battery life.", 7999, {"Type": "Over-ear", "Noise cancellation": "Adaptive ANC", "Battery": "Up to 40 hours", "Connectivity": "Bluetooth"}, 4.2, "headphones"),
    ("kb-01", "K2 V2", "Keychron", "Keyboards", "Compact mechanical keyboard for desktop and laptop setups.", 8999, {"Layout": "75%", "Switches": "Mechanical", "Connectivity": "Bluetooth / USB-C", "Backlight": "White"}, 4.5, "keyboard"),
    ("kb-02", "MX Keys S", "Logitech", "Keyboards", "Low-profile wireless keyboard designed for productivity.", 11995, {"Layout": "Full size", "Switches": "Scissor", "Connectivity": "Bluetooth / USB receiver", "Backlight": "Smart"}, 4.6, "keyboard"),
    ("kb-03", "Aula F75", "Aula", "Keyboards", "Hot-swappable compact mechanical keyboard with tri-mode connectivity.", 6999, {"Layout": "75%", "Switches": "Mechanical hot-swap", "Connectivity": "Bluetooth / 2.4GHz / USB-C", "Backlight": "RGB"}, 4.3, "keyboard"),
    ("mon-01", "UltraGear 27GN800", "LG", "Monitors", "QHD gaming and productivity monitor with an IPS panel.", 22999, {"Size": "27-inch", "Resolution": "2560 x 1440", "Panel": "IPS", "Refresh rate": "144Hz"}, 4.5, "monitor"),
    ("mon-02", "S2722QC", "Dell", "Monitors", "4K USB-C monitor for a clean work-from-home setup.", 27999, {"Size": "27-inch", "Resolution": "3840 x 2160", "Panel": "IPS", "Connectivity": "USB-C"}, 4.4, "monitor"),
    ("mon-03", "M27Q", "Gigabyte", "Monitors", "QHD high-refresh monitor with a KVM feature.", 24999, {"Size": "27-inch", "Resolution": "2560 x 1440", "Panel": "IPS", "Refresh rate": "170Hz", "Feature": "KVM"}, 4.5, "monitor"),
    ("acc-01", "MX Master 3S", "Logitech", "Accessories", "Ergonomic wireless mouse with customizable controls.", 9995, {"Type": "Wireless mouse", "DPI": "Up to 8000", "Connectivity": "Bluetooth / USB receiver"}, 4.7, "accessory"),
    ("acc-02", "Anker 735 Charger", "Anker", "Accessories", "Compact multi-port USB-C charger for travel.", 4999, {"Output": "65W", "Ports": "2 USB-C, 1 USB-A", "Technology": "GaN"}, 4.5, "accessory"),
    ("acc-03", "T7 Shield 1TB", "Samsung", "Accessories", "Rugged portable SSD for backups and project files.", 9999, {"Capacity": "1TB", "Interface": "USB 3.2 Gen 2", "Durability": "IP65"}, 4.6, "accessory"),
    ("acc-04", "Laptop Stand", "Portronics", "Accessories", "Adjustable aluminum stand for improving desk ergonomics.", 1499, {"Material": "Aluminum alloy", "Adjustable": "Yes", "Compatibility": "Up to 15.6-inch laptops"}, 4.2, "accessory"),
]


def seed_products(db: Session) -> None:
    if db.query(Product).first():
        return
    for pid, name, brand, category, description, price, specs, rating, image in PRODUCTS:
        db.add(Product(
            id=pid, name=name, brand=brand, category=category, description=description,
            price=price, specifications=specs, rating=rating, stock_quantity=12,
            image_url=f"https://images.unsplash.com/photo-1517336714731-489689fd1ca8?auto=format&fit=crop&w=800&q=80" if image == "laptop" else
            f"https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=800&q=80" if image == "smartphone" else
            f"https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=800&q=80" if image == "headphones" else
            f"https://images.unsplash.com/photo-1587829741301-dc798b83add3?auto=format&fit=crop&w=800&q=80" if image == "keyboard" else
            f"https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?auto=format&fit=crop&w=800&q=80" if image == "monitor" else
            f"https://images.unsplash.com/photo-1523206489230-c012c64b2b48?auto=format&fit=crop&w=800&q=80",
        ))
    db.commit()
