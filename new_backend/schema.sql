-- SQL Schema for the new backend (MySQL)

-- Users table (combining Django User and UserProfile)
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(150) NOT NULL UNIQUE,
    password VARCHAR(128) NOT NULL, -- Store hashed passwords
    email VARCHAR(255) NOT NULL UNIQUE,
    first_name VARCHAR(150),
    last_name VARCHAR(150),
    is_staff BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    date_joined DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME NULL,
    -- UserProfile fields
    phone_number VARCHAR(20) UNIQUE,
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(100),
    zip_code VARCHAR(20),
    country VARCHAR(100),
    profile_picture VARCHAR(255), -- URL or path to file
    user_type ENUM('caregiver', 'family', 'admin') NOT NULL,
    bio TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Caregiver Profiles table
CREATE TABLE caregiver_profiles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    hourly_rate DECIMAL(10, 2),
    years_of_experience INT,
    skills_description TEXT,
    certifications TEXT, -- Could be JSON if storing multiple structured certs
    work_schedule_preferences TEXT, -- Could be JSON for more complex schedules
    availability_status ENUM('available', 'unavailable', 'booked') DEFAULT 'available',
    id_verified BOOLEAN DEFAULT FALSE,
    background_check_status ENUM('not_started', 'pending', 'completed_clear', 'completed_issues') DEFAULT 'not_started',
    languages_spoken VARCHAR(255), -- Comma-separated or JSON array
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Availability Slots table
CREATE TABLE availability_slots (
    id INT AUTO_INCREMENT PRIMARY KEY,
    caregiver_profile_id INT NOT NULL,
    day_of_week ENUM('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday') NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    is_recurring BOOLEAN DEFAULT FALSE,
    specific_date DATE NULL, -- For non-recurring slots
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (caregiver_profile_id) REFERENCES caregiver_profiles(id) ON DELETE CASCADE,
    UNIQUE (caregiver_profile_id, day_of_week, start_time, end_time, specific_date) -- Ensure no duplicate slots
);

-- Family Profiles table
CREATE TABLE family_profiles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    number_of_children INT,
    children_ages VARCHAR(255), -- Comma-separated or JSON array
    specific_needs TEXT,
    location_preferences TEXT,
    preferred_care_type ENUM('full_time', 'part_time', 'babysitting', 'nanny_share') DEFAULT 'part_time',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Photos table (for Caregiver Profiles)
CREATE TABLE photos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    caregiver_profile_id INT NOT NULL,
    image_url VARCHAR(255) NOT NULL,
    caption TEXT,
    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (caregiver_profile_id) REFERENCES caregiver_profiles(id) ON DELETE CASCADE
);

-- Match Requests table
CREATE TABLE match_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    family_profile_id INT NOT NULL,
    caregiver_profile_id INT NOT NULL,
    request_status ENUM('pending', 'accepted', 'declined', 'expired', 'completed') DEFAULT 'pending',
    message_to_caregiver TEXT,
    proposed_start_date DATETIME,
    proposed_end_date DATETIME,
    requested_hours_per_week INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (family_profile_id) REFERENCES family_profiles(id) ON DELETE CASCADE,
    FOREIGN KEY (caregiver_profile_id) REFERENCES caregiver_profiles(id) ON DELETE CASCADE,
    UNIQUE (family_profile_id, caregiver_profile_id, created_at) -- Avoid exact duplicate requests at the same time
);

-- Conversations table
CREATE TABLE conversations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    match_request_id INT NULL, -- Optional link to a specific match request
    subject VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (match_request_id) REFERENCES match_requests(id) ON DELETE SET NULL
);

-- Conversation Participants table
CREATE TABLE conversation_participants (
    id INT AUTO_INCREMENT PRIMARY KEY,
    conversation_id INT NOT NULL,
    user_id INT NOT NULL,
    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_read_at DATETIME NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE (conversation_id, user_id)
);

-- Messages table
CREATE TABLE messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    conversation_id INT NOT NULL,
    sender_id INT NOT NULL,
    content TEXT NOT NULL,
    sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_read BOOLEAN DEFAULT FALSE, -- Simple read status, could be enhanced by last_read_at in participants
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE -- Or SET NULL if user deletion shouldn't delete messages
);

-- Reviews table
CREATE TABLE reviews (
    id INT AUTO_INCREMENT PRIMARY KEY,
    match_request_id INT UNIQUE, -- A review is typically tied to a completed match/job
    reviewer_id INT NOT NULL, -- User ID of the family member writing the review
    reviewee_id INT NOT NULL, -- User ID of the caregiver being reviewed
    rating INT NOT NULL, -- e.g., 1-5
    comment TEXT,
    review_type ENUM('family_to_caregiver', 'caregiver_to_family') NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CHECK (rating >= 1 AND rating <= 5),
    FOREIGN KEY (match_request_id) REFERENCES match_requests(id) ON DELETE SET NULL,
    FOREIGN KEY (reviewer_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (reviewee_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Transactions table
CREATE TABLE transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    match_request_id INT, -- Link to the job/match this transaction is for
    initiating_user_id INT, -- User who initiated (paid) - typically family
    receiving_user_id INT, -- User who received (caregiver)
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'USD',
    transaction_status ENUM('pending', 'completed', 'failed', 'refunded') DEFAULT 'pending',
    payment_method VARCHAR(50), -- e.g., 'paypal', 'stripe_card_id_xxx'
    paypal_payment_id VARCHAR(255) UNIQUE NULL, -- To store PAYID-XXXX from PayPal payment creation
    transaction_reference_id VARCHAR(255) UNIQUE, -- ID from payment gateway (e.g., PayPal SALE-ID)
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (match_request_id) REFERENCES match_requests(id) ON DELETE SET NULL,
    FOREIGN KEY (initiating_user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (receiving_user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Indexes for common lookups (examples)
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_user_type ON users(user_type);
CREATE INDEX idx_caregiver_profiles_user_id ON caregiver_profiles(user_id);
CREATE INDEX idx_family_profiles_user_id ON family_profiles(user_id);
CREATE INDEX idx_match_requests_status ON match_requests(request_status);
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_sender_id ON messages(sender_id);
CREATE INDEX idx_reviews_reviewer_id ON reviews(reviewer_id);
CREATE INDEX idx_reviews_reviewee_id ON reviews(reviewee_id);
CREATE INDEX idx_transactions_status ON transactions(transaction_status);

-- Note: ENUM values are based on common use cases and Django model choices.
-- Adjust data types (e.g., TEXT vs VARCHAR, JSON for flexible fields) and constraints as needed.
-- Consider adding more specific indexes based on query patterns.
-- For `password` in `users` table, ensure it's stored hashed (application-level responsibility).
-- `profile_picture` and `image_url` store paths or URLs; actual file storage is separate.
-- `languages_spoken` and `children_ages` can be simple VARCHARs or more structured (e.g., JSON) if complex querying is needed.
-- `certifications` and `work_schedule_preferences` in `caregiver_profiles` are TEXT but could be JSON.
-- `ON DELETE SET NULL` is used for `transactions.initiating_user_id` to keep transaction records even if a user is deleted.
-- `ON DELETE CASCADE` is used for profile tables linked to `users` and for entities that don't make sense without their parent (e.g. photos, availability slots).
-- `reviews.match_request_id` is UNIQUE because one match should ideally have one review record (or one per direction).
-- `availability_slots` has a UNIQUE constraint to prevent duplicate time slots for a caregiver.
-- `messages.sender_id` ON DELETE CASCADE means if a user is deleted, their messages are also deleted. If messages should be kept (e.g. for auditing or context for other users), consider ON DELETE SET NULL and an 'anonymous' or 'deleted user' placeholder. For simplicity, CASCADE is used here.
-- `conversations.match_request_id` is ON DELETE SET NULL, meaning a conversation can exist even if the original match request is deleted.
-- `reviews.match_request_id` is ON DELETE SET NULL, so reviews can persist even if the match request is deleted.
-- `transactions.match_request_id`, `transactions.initiating_user_id`, `transactions.receiving_user_id` are ON DELETE SET NULL to preserve financial records.

-- Authentication Tokens table
CREATE TABLE auth_tokens (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    token VARCHAR(255) NOT NULL UNIQUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX idx_auth_tokens_token ON auth_tokens(token);
CREATE INDEX idx_auth_tokens_expires_at ON auth_tokens(expires_at);
