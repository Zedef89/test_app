# new_backend/messaging_queries.py
import datetime
from typing import List

def check_match_exists_for_conversation(db_conn, user1_id: int, user2_id: int) -> bool:
    """
    Checks if an 'accepted' match exists between user1_id and user2_id.
    Users can be in either family or caregiver role in the match.
    This function handles the lookup of profile_ids from user_ids.
    """
    cursor = db_conn.cursor(dictionary=True)
    try:
        # Get profile IDs for user1
        cursor.execute("SELECT id FROM family_profiles WHERE user_id = %s", (user1_id,))
        user1_family_profile = cursor.fetchone()
        cursor.execute("SELECT id FROM caregiver_profiles WHERE user_id = %s", (user1_id,))
        user1_caregiver_profile = cursor.fetchone()

        # Get profile IDs for user2
        cursor.execute("SELECT id FROM family_profiles WHERE user_id = %s", (user2_id,))
        user2_family_profile = cursor.fetchone()
        cursor.execute("SELECT id FROM caregiver_profiles WHERE user_id = %s", (user2_id,))
        user2_caregiver_profile = cursor.fetchone()

        match_found = False
        # Scenario 1: user1 is family, user2 is caregiver
        if user1_family_profile and user2_caregiver_profile:
            query_match = """
            SELECT 1 FROM match_requests 
            WHERE family_profile_id = %s AND caregiver_profile_id = %s AND request_status = 'accepted'
            LIMIT 1
            """
            cursor.execute(query_match, (user1_family_profile['id'], user2_caregiver_profile['id']))
            if cursor.fetchone():
                match_found = True
        
        # Scenario 2: user1 is caregiver, user2 is family
        if not match_found and user1_caregiver_profile and user2_family_profile:
            query_match = """
            SELECT 1 FROM match_requests 
            WHERE family_profile_id = %s AND caregiver_profile_id = %s AND request_status = 'accepted'
            LIMIT 1
            """
            cursor.execute(query_match, (user2_family_profile['id'], user1_caregiver_profile['id']))
            if cursor.fetchone():
                match_found = True
        
        return match_found
    finally:
        cursor.close()

def find_existing_conversation(db_conn, participant_user_ids: List[int]):
    if len(participant_user_ids) != 2:
        # This implementation specifically handles two-participant conversations.
        # For more participants, the query logic would need to be more general.
        return None 
    
    cursor = db_conn.cursor(dictionary=True)
    try:
        # Sort participant IDs to ensure consistent querying regardless of order
        p_sorted = sorted(participant_user_ids)
        
        # Query to find a conversation_id that has exactly these two participants
        # and no others (implicitly handled by joining on itself and matching distinct user_ids).
        # This query identifies conversations where both users are participants.
        # It then checks if the total number of participants in that conversation is exactly 2.
        query = """
        SELECT cp.conversation_id
        FROM conversation_participants cp
        JOIN (
            SELECT conversation_id
            FROM conversation_participants
            GROUP BY conversation_id
            HAVING COUNT(user_id) = 2  -- Ensures only 2 participants in the conversation
        ) AS valid_convos ON cp.conversation_id = valid_convos.conversation_id
        WHERE cp.user_id IN (%s, %s)
        GROUP BY cp.conversation_id
        HAVING COUNT(DISTINCT cp.user_id) = 2 -- Ensures both specified users are in this group
        LIMIT 1
        """
        cursor.execute(query, (p_sorted[0], p_sorted[1]))
        result = cursor.fetchone()
        return result['conversation_id'] if result else None
    finally:
        cursor.close()

def create_conversation_and_participants(db_conn, participant_user_ids: List[int]):
    cursor = db_conn.cursor()
    try:
        # Create the conversation
        # schema.sql: conversations has created_at, updated_at
        cursor.execute("INSERT INTO conversations (created_at, updated_at) VALUES (NOW(), NOW())")
        conversation_id = cursor.lastrowid
        
        # Add participants to the conversation
        # schema.sql: conversation_participants has conversation_id, user_id, joined_at
        participant_data = [(conversation_id, user_id) for user_id in participant_user_ids]
        cursor.executemany("INSERT INTO conversation_participants (conversation_id, user_id, joined_at) VALUES (%s, %s, NOW())", participant_data)
        
        db_conn.commit()
        return conversation_id
    except Exception as e:
        db_conn.rollback()
        raise e
    finally:
        cursor.close()

def get_conversation_details_by_id(db_conn, conversation_id: int):
    cursor = db_conn.cursor(dictionary=True)
    try:
        # Get conversation basic info (id, created_at, updated_at)
        cursor.execute("SELECT id, created_at, updated_at FROM conversations WHERE id = %s", (conversation_id,))
        convo_data = cursor.fetchone()
        if not convo_data:
            return None

        # Get participants
        # schema.sql: users.profile_picture
        p_query = """
            SELECT u.id as user_id, u.username, u.email, u.first_name, u.last_name, 
                   u.profile_picture AS profile_picture_url 
            FROM users u
            JOIN conversation_participants cp ON u.id = cp.user_id
            WHERE cp.conversation_id = %s
        """
        cursor.execute(p_query, (conversation_id,))
        participants_data = cursor.fetchall()
        convo_data['participants'] = participants_data

        # Get last message preview
        # schema.sql: messages.content, messages.sent_at
        lm_query = "SELECT content AS text, sent_at AS timestamp FROM messages WHERE conversation_id = %s ORDER BY sent_at DESC LIMIT 1"
        cursor.execute(lm_query, (conversation_id,))
        last_message = cursor.fetchone()
        convo_data['last_message'] = last_message
        
        return convo_data
    finally:
        cursor.close()

def get_conversations_for_user(db_conn, user_id: int, page: int = 1, page_size: int = 10):
    cursor = db_conn.cursor(dictionary=True)
    try:
        count_query = "SELECT COUNT(DISTINCT cp.conversation_id) as total_count FROM conversation_participants cp WHERE cp.user_id = %s"
        cursor.execute(count_query, (user_id,))
        total_count_result = cursor.fetchone()
        total_count = total_count_result['total_count'] if total_count_result else 0

        offset = (page - 1) * page_size
        query = """
        SELECT DISTINCT c.id as conversation_id
        FROM conversations c
        JOIN conversation_participants cp ON c.id = cp.conversation_id
        WHERE cp.user_id = %s
        ORDER BY c.updated_at DESC
        LIMIT %s OFFSET %s
        """
        cursor.execute(query, (user_id, page_size, offset))
        conversation_ids_data = cursor.fetchall()
        
        detailed_conversations = []
        if conversation_ids_data: # Only proceed if there are conversations
            for row in conversation_ids_data:
                # Use a new cursor for sub-queries or ensure the main cursor isn't closed prematurely if reused.
                # For simplicity with N+1, get_conversation_details_by_id handles its own cursor.
                convo_detail = get_conversation_details_by_id(db_conn, row['conversation_id'])
                if convo_detail:
                    detailed_conversations.append(convo_detail)
        
        return detailed_conversations, total_count
    finally:
        cursor.close() # Ensure the main cursor for this function is closed

def create_message(db_conn, conversation_id: int, sender_user_id: int, text: str):
    cursor = db_conn.cursor()
    try:
        # schema.sql: messages.content, messages.sent_at
        msg_query = "INSERT INTO messages (conversation_id, sender_id, content, sent_at, is_read) VALUES (%s, %s, %s, NOW(), FALSE)"
        # Note: schema.sql has messages.sender_id, not sender_user_id. Correcting here.
        cursor.execute(msg_query, (conversation_id, sender_user_id, text))
        message_id = cursor.lastrowid
            
        convo_update_query = "UPDATE conversations SET updated_at = NOW() WHERE id = %s"
        cursor.execute(convo_update_query, (conversation_id,))
            
        db_conn.commit()
        return message_id
    except Exception as e:
        db_conn.rollback()
        raise e
    finally:
        cursor.close()

def get_message_details_by_id(db_conn, message_id: int):
    cursor = db_conn.cursor(dictionary=True)
    try:
        # schema.sql: messages.content, messages.sent_at, messages.sender_id
        # schema.sql: users.profile_picture
        query = """
            SELECT m.id, m.conversation_id, m.content AS text, m.sent_at AS timestamp, m.is_read,
                   s.id as sender_id, s.username as sender_username, s.email as sender_email, 
                   s.first_name as sender_first_name, s.last_name as sender_last_name, 
                   s.profile_picture as sender_profile_picture_url
            FROM messages m
            JOIN users s ON m.sender_id = s.id  -- Corrected: m.sender_id
            WHERE m.id = %s
        """
        cursor.execute(query, (message_id,))
        msg_data = cursor.fetchone()
        return msg_data
    finally:
        cursor.close()

def get_messages_for_conversation(db_conn, conversation_id: int, page: int = 1, page_size: int = 10):
    cursor = db_conn.cursor(dictionary=True)
    try:
        count_query = "SELECT COUNT(id) as total_count FROM messages WHERE conversation_id = %s"
        cursor.execute(count_query, (conversation_id,))
        total_count_result = cursor.fetchone()
        total_count = total_count_result['total_count'] if total_count_result else 0

        offset = (page - 1) * page_size
        # schema.sql: messages.sent_at
        query = """
        SELECT id as message_id FROM messages 
        WHERE conversation_id = %s 
        ORDER BY sent_at DESC  -- Corrected: sent_at
        LIMIT %s OFFSET %s
        """
        cursor.execute(query, (conversation_id, page_size, offset))
        message_ids_data = cursor.fetchall()
        
        detailed_messages = []
        if message_ids_data: # Only proceed if there are messages
            for row in message_ids_data:
                msg_detail = get_message_details_by_id(db_conn, row['message_id'])
                if msg_detail:
                    detailed_messages.append(msg_detail)
        
        return detailed_messages, total_count
    finally:
        cursor.close() # Ensure the main cursor for this function is closed

def mark_messages_as_read(db_conn, conversation_id: int, recipient_user_id: int):
    cursor = db_conn.cursor()
    try:
        # schema.sql: messages.sender_id
        query = "UPDATE messages SET is_read = TRUE WHERE conversation_id = %s AND sender_id != %s AND is_read = FALSE"
        # Corrected: sender_id
        cursor.execute(query, (conversation_id, recipient_user_id))
        updated_count = cursor.rowcount
        db_conn.commit()
        return updated_count
    except Exception as e:
        db_conn.rollback()
        raise e
    finally:
        cursor.close()

def check_user_in_conversation(db_conn, user_id: int, conversation_id: int) -> bool:
    cursor = db_conn.cursor(dictionary=True)
    try:
        query = "SELECT 1 FROM conversation_participants WHERE user_id = %s AND conversation_id = %s LIMIT 1"
        cursor.execute(query, (user_id, conversation_id))
        return cursor.fetchone() is not None
    finally:
        cursor.close()
