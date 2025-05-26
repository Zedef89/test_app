# new_backend/transaction_queries.py
import datetime

def create_transaction_record(db_conn, initiating_user_id: int, receiving_user_id: int, 
                              amount: float, currency: str,
                              paypal_payment_id: str = None, # PAYID-XXX from PayPal
                              transaction_status: str = 'pending', 
                              match_request_id: int = None, payment_method: str = 'paypal'):
    cursor = db_conn.cursor()
    try:
        # Using schema column names: initiating_user_id, receiving_user_id
        # paypal_payment_id is stored. transaction_reference_id (SALE-ID) updated later.
        query = """
        INSERT INTO transactions (initiating_user_id, receiving_user_id, match_request_id, 
                                 amount, currency, payment_method, paypal_payment_id, transaction_status, 
                                 created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        """
        cursor.execute(query, (initiating_user_id, receiving_user_id, match_request_id,
                                 amount, currency, payment_method, paypal_payment_id, transaction_status))
        db_conn.commit()
        return cursor.lastrowid # This is our internal_transaction_id (the auto-incremented PK)
    except Exception as e:
        db_conn.rollback()
        raise e
    finally:
        cursor.close()

def get_transaction_by_id(db_conn, internal_transaction_id: int): # Fetches our DB transaction
    cursor = db_conn.cursor(dictionary=True)
    try:
        # Join with users table to get initiator/receiver details for TransactionResponse
        # Using schema column names: initiating_user_id, receiving_user_id
        query = """
            SELECT 
                t.*, 
                t.id as internal_transaction_id, -- ensure 'id' is also aliased if needed by Pydantic from_query_result
                u_init.id as init_user_id, u_init.username as init_username, u_init.email as init_email,
                u_recv.id as recv_user_id, u_recv.username as recv_username, u_recv.email as recv_email
            FROM transactions t
            LEFT JOIN users u_init ON t.initiating_user_id = u_init.id
            LEFT JOIN users u_recv ON t.receiving_user_id = u_recv.id
            WHERE t.id = %s
        """
        cursor.execute(query, (internal_transaction_id,))
        return cursor.fetchone()
    finally:
        cursor.close()

def get_transaction_by_paypal_payment_id(db_conn, paypal_payment_id: str): # paypal_payment_id is PAYID-XXX
    cursor = db_conn.cursor(dictionary=True)
    try:
        # Using schema column names: initiating_user_id, receiving_user_id
        query = """
            SELECT t.*,
                t.id as internal_transaction_id, 
                u_init.id as init_user_id, u_init.username as init_username, u_init.email as init_email,
                u_recv.id as recv_user_id, u_recv.username as recv_username, u_recv.email as recv_email
            FROM transactions t
            LEFT JOIN users u_init ON t.initiating_user_id = u_init.id
            LEFT JOIN users u_recv ON t.receiving_user_id = u_recv.id
            WHERE t.paypal_payment_id = %s
        """
        cursor.execute(query, (paypal_payment_id,))
        return cursor.fetchone()
    finally:
        cursor.close()

def update_transaction_on_paypal_success(db_conn, internal_transaction_id: int, paypal_sale_id: str, new_status: str):
    cursor = db_conn.cursor()
    try:
        # paypal_sale_id (SALE-XXX) is stored in transaction_reference_id
        query = "UPDATE transactions SET transaction_reference_id = %s, transaction_status = %s, updated_at = NOW() WHERE id = %s"
        cursor.execute(query, (paypal_sale_id, new_status, internal_transaction_id))
        db_conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        db_conn.rollback()
        raise e
    finally:
        cursor.close()

def update_transaction_status(db_conn, internal_transaction_id: int, new_status: str):
    cursor = db_conn.cursor()
    try:
        query = "UPDATE transactions SET transaction_status = %s, updated_at = NOW() WHERE id = %s"
        cursor.execute(query, (new_status, internal_transaction_id))
        db_conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        db_conn.rollback()
        raise e
    finally:
        cursor.close()

def list_transactions_for_user(db_conn, user_id: int, page: int = 1, page_size: int = 10):
    cursor = db_conn.cursor(dictionary=True)
    # Count total
    # Using schema column names: initiating_user_id, receiving_user_id
    count_query = "SELECT COUNT(id) as total_count FROM transactions WHERE initiating_user_id = %s OR receiving_user_id = %s"
    cursor.execute(count_query, (user_id, user_id))
    total_count_result = cursor.fetchone()
    total_count = total_count_result['total_count'] if total_count_result else 0

    offset = (page - 1) * page_size
    query_ids = """
        SELECT id FROM transactions 
        WHERE initiating_user_id = %s OR receiving_user_id = %s
        ORDER BY created_at DESC LIMIT %s OFFSET %s
    """
    cursor.execute(query_ids, (user_id, user_id, page_size, offset))
    transaction_ids_data = cursor.fetchall()
    # Close this cursor as get_transaction_by_id will open its own
    cursor.close() 

    detailed_transactions = []
    if transaction_ids_data:
        for row in transaction_ids_data:
            # Re-use db_conn, get_transaction_by_id will manage its own cursor
            tx_detail = get_transaction_by_id(db_conn, row['id']) 
            if tx_detail:
                detailed_transactions.append(tx_detail)
    
    return detailed_transactions, total_count

def update_paypal_payment_id(db_conn, internal_transaction_id: int, paypal_payment_id_from_paypal: str):
    cursor = db_conn.cursor()
    try:
        query = "UPDATE transactions SET paypal_payment_id = %s, updated_at = NOW() WHERE id = %s"
        cursor.execute(query, (paypal_payment_id_from_paypal, internal_transaction_id))
        db_conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        db_conn.rollback()
        raise e
    finally:
        cursor.close()
