from app import app, db, Order, create_order
from datetime import datetime

def test_create_order():
    with app.app_context():
        # Define customer data
        customer_data = {
            'customer_name': 'Test Customer',
            'customer_phone': '0777777777',
            'customer_email': 'test@example.com',
            'customer_address': 'Test Address'
        }
        
        # Define items data
        items_data = [
            {
                'product_id': 1,  # Assuming product ID 1 exists
                'quantity': 1,
                'price': 100.0
            }
        ]
        
        try:
            # Create order directly
            new_order = Order(
                customer_name=customer_data['customer_name'],
                customer_phone=customer_data['customer_phone'],
                customer_email=customer_data['customer_email'],
                customer_address=customer_data['customer_address'],
                total_amount=100.0,
                order_type='test',
                status='pending'
            )
            
            # Generate a reference number
            now = datetime.utcnow()
            new_order.reference_number = f"TEST-{now.strftime('%Y%m%d')}-TEST"
            
            try:
                print("Trying to add order to session...")
                db.session.add(new_order)
                db.session.flush()
                print(f"Order flushed with ID: {new_order.id}")
                
                db.session.commit()
                print(f"Order committed successfully with ID: {new_order.id}")
                
                # Clean up test order to avoid cluttering the database
                db.session.delete(new_order)
                db.session.commit()
                print("Test order deleted")
                
            except Exception as e:
                db.session.rollback()
                print(f"Error during direct order creation: {str(e)}")
                
            # Try using the app's create_order function
            print("\nTrying with the create_order function...")
            order, error = create_order(customer_data, items_data, 'test')
            
            if error:
                print(f"Error from create_order: {error}")
            else:
                print(f"Order created successfully with ID: {order.id}")
                # Clean up
                db.session.delete(order)
                db.session.commit()
                print("Test order deleted")
                
        except Exception as e:
            print(f"Unexpected error: {str(e)}")

if __name__ == "__main__":
    test_create_order() 