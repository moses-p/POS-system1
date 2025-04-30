from create_order_direct import direct_create_order
import sqlite3

def test_direct_order_creation():
    print("=== Testing Direct SQL Order Creation ===")
    
    # First check if any products exist in the database
    try:
        conn = sqlite3.connect('instance/pos.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, price FROM product LIMIT 1")
        product = cursor.fetchone()
        conn.close()
        
        if not product:
            print("No products found in the database. Cannot test order creation.")
            return
            
        print(f"Found product: ID={product[0]}, Name={product[1]}, Price={product[2]}")
        
        # Create test order data
        customer_data = {
            'customer_name': 'Test Customer',
            'customer_phone': '0777777777',
            'customer_email': 'test@example.com',
            'customer_address': 'Test Address'
        }
        
        items_data = [
            {
                'product_id': product[0],
                'quantity': 1,
                'price': float(product[2])
            }
        ]
        
        print(f"\nAttempting to create order with product {product[0]}")
        order_id, result = direct_create_order(customer_data, items_data, 'test')
        
        if order_id:
            print(f"\nSUCCESS! Created order with ID {order_id} and reference {result}")
            
            # Verify the order exists in the database
            conn = sqlite3.connect('instance/pos.db')
            cursor = conn.cursor()
            cursor.execute("SELECT id, reference_number FROM [order] WHERE id = ?", (order_id,))
            order = cursor.fetchone()
            
            if order:
                print(f"Verified order in database: ID={order[0]}, Reference={order[1]}")
            else:
                print("Warning: Order created but not found in database verification!")
                
            # Cleanup - delete the test order
            print("\nCleaning up (deleting test order)...")
            cursor.execute("DELETE FROM order_item WHERE order_id = ?", (order_id,))
            cursor.execute("DELETE FROM [order] WHERE id = ?", (order_id,))
            conn.commit()
            
            cursor.execute("SELECT id FROM [order] WHERE id = ?", (order_id,))
            if not cursor.fetchone():
                print("Order deleted successfully")
            else:
                print("Warning: Failed to delete test order")
                
            conn.close()
            
        else:
            print(f"\nFAILED to create order: {result}")
            
    except Exception as e:
        print(f"Error during test: {str(e)}")
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    test_direct_order_creation() 