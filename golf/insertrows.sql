USE `golf_db`;

-- ==========================================
-- 1. INSERT USERS (ID 1-10)
-- Note: 'hash' is a placeholder. 
-- ==========================================
INSERT INTO `user` (first_name, last_name, email, hash, contact, membership_tier, loyalty_points, is_admin) VALUES
('Admin', 'User', 'admin@teetrack.com', 'pbkdf2:sha256:dummyhash', '09170000001', 'Diamond', 5000, 1),
('Tiger', 'Woods', 'tiger@golf.com', 'pbkdf2:sha256:dummyhash', '09170000002', 'Platinum', 1200, 0),
('Rory', 'McIlroy', 'rory@golf.com', 'pbkdf2:sha256:dummyhash', '09170000003', 'Gold', 850, 0),
('Juan', 'Dela Cruz', 'juan@test.com', 'pbkdf2:sha256:dummyhash', '09170000004', 'Silver', 200, 0),
('Maria', 'Clara', 'maria@test.com', 'pbkdf2:sha256:dummyhash', '09170000005', 'Bronze', 50, 0),
('Jose', 'Rizal', 'jose@history.com', 'pbkdf2:sha256:dummyhash', '09170000006', 'Gold', 600, 0),
('Andres', 'Bonifacio', 'andres@rev.com', 'pbkdf2:sha256:dummyhash', '09170000007', 'Unsubscribed', 0, 0),
('Gab', 'Developer', 'gab@teetrack.com', 'pbkdf2:sha256:dummyhash', '09170000008', 'Diamond', 9999, 1),
('Alice', 'Wonderland', 'alice@book.com', 'pbkdf2:sha256:dummyhash', '09170000009', 'Silver', 150, 0),
('Bob', 'Builder', 'bob@tv.com', 'pbkdf2:sha256:dummyhash', '09170000010', 'Bronze', 20, 0);

-- ==========================================
-- 2. INSERT STAFF (ID 1-10)
-- ==========================================
INSERT INTO `staff` (name, email, contact, max_clients, role, status, service_fee) VALUES
('Coach Carter', 'carter@coach.com', '09991112222', 1, 'Coach', 'Available', 2500.00),
('Coach Phil', 'phil@jackson.com', '09991113333', 1, 'Coach', 'Available', 3000.00),
('Coach Ted', 'ted@lasso.com', '09991114444', 1, 'Coach', 'Occupied', 2000.00),
('Coach Pat', 'pat@riley.com', '09991115555', 1, 'Coach', 'Available', 2800.00),
('Coach Spo', 'spo@heat.com', '09991116666', 1, 'Coach', 'Available', 3500.00),
('Caddie Mike', 'mike@caddie.com', '09220001111', 1, 'Caddie', 'Available', 500.00),
('Caddie Steve', 'steve@caddie.com', '09220002222', 1, 'Caddie', 'Occupied', 500.00),
('Caddie John', 'john@caddie.com', '09220003333', 1, 'Caddie', 'Available', 600.00),
('Caddie Bill', 'bill@caddie.com', '09220004444', 1, 'Caddie', 'Available', 450.00),
('Caddie Tom', 'tom@caddie.com', '09220005555', 1, 'Caddie', 'Available', 550.00);

-- ==========================================
-- 3. INSERT GOLF SESSIONS (ID 1-10)
-- Mix of Fairway, Range, Past and Future dates
-- ==========================================
INSERT INTO `golf_session` (type, holes, session_schedule, people_limit, status, session_price) VALUES
('Fairway', 'FULL 18', DATE_ADD(NOW(), INTERVAL 1 DAY), 8, 'Available', 5000.00),
('Fairway', '9 FRONT', DATE_ADD(NOW(), INTERVAL 2 DAY), 8, 'Available', 3000.00),
('Driving Range', NULL, DATE_ADD(NOW(), INTERVAL 3 HOUR), 25, 'Available', 1000.00),
('Driving Range', NULL, NOW(), 25, 'Ongoing', 1000.00),
('Fairway', '9 BACK', DATE_ADD(NOW(), INTERVAL 5 DAY), 8, 'Available', 3000.00),
('Fairway', 'FULL 18', DATE_SUB(NOW(), INTERVAL 2 DAY), 8, 'Finished', 5000.00), -- Past session
('Driving Range', NULL, DATE_SUB(NOW(), INTERVAL 1 DAY), 25, 'Finished', 1000.00),
('Fairway', 'FULL 18', DATE_ADD(NOW(), INTERVAL 1 WEEK), 8, 'Available', 5000.00),
('Driving Range', NULL, DATE_ADD(NOW(), INTERVAL 4 HOUR), 25, 'Fully Booked', 1000.00),
('Fairway', '9 FRONT', DATE_ADD(NOW(), INTERVAL 3 DAY), 8, 'Available', 3000.00);

-- ==========================================
-- 4. INSERT CARTS (ID 1-10)
-- Some active (currently shopping), some archived (already bought)
-- ==========================================
INSERT INTO `cart` (total_price, user_id, status) VALUES
(0.00, 1, 'active'),           -- Admin's empty active cart
(3500.00, 2, 'archived'),       -- Tiger bought balls
(25000.00, 3, 'archived'),      -- Rory bought a driver
(1500.00, 4, 'active'),         -- Juan has items in cart
(0.00, 5, 'active'),            -- Maria empty cart
(5000.00, 6, 'archived'),       -- Jose bought equipment
(0.00, 7, 'active'),
(10000.00, 8, 'archived'),      -- Gab bought huge haul
(200.00, 9, 'active'),
(0.00, 10, 'active');

-- ==========================================
-- 5. INSERT ITEMS (ID 1-10)
-- Some in Shop (cart_id NULL), Some in Carts
-- ==========================================
INSERT INTO `item` (name, category, type, quantity, price, cart_id) VALUES
('Titleist Pro V1 (Dozen)', 'Balls', 'Sale', 50, 3500.00, NULL),       -- In Shop
('Callaway Paradym Driver', 'Clubs', 'Sale', 10, 38000.00, NULL),      -- In Shop
('TaylorMade Putter', 'Clubs', 'Rental', 5, 1000.00, NULL),            -- In Shop
('Nike Golf Polo', 'Apparel', 'Sale', 20, 2500.00, NULL),              -- In Shop
('Titleist Pro V1 (Dozen)', 'Balls', 'Sale', 1, 3500.00, 2),           -- In Tiger's archived cart
('Callaway Mavrik', 'Clubs', 'Sale', 1, 25000.00, 3),                  -- In Rory's archived cart
('Golf Glove', 'Apparel', 'Sale', 2, 750.00, 4),                       -- In Juan's active cart
('Sun Mountain Bag', 'Bags', 'Sale', 1, 12000.00, NULL),               -- In Shop
('Range Finder', 'Equipment', 'Sale', 1, 10000.00, 8),                 -- In Gab's archived cart
('Tee Pack', 'Miscellaneous', 'Sale', 100, 200.00, NULL);              -- In Shop

-- ==========================================
-- 6. INSERT SESSION USERS (Bookings) (ID 1-10)
-- Linking Users to Sessions and Staff
-- ==========================================
INSERT INTO `session_user` (user_id, session_id, coach_id, caddie_id, score_fairway, longest_range, buckets, status) VALUES
(2, 6, 1, 6, 72, NULL, NULL, 'Confirmed'),     -- Tiger played Fairway (Finished) with Coach 1 & Caddie 6
(3, 6, 2, 7, 68, NULL, NULL, 'Confirmed'),     -- Rory played same session
(4, 3, NULL, NULL, NULL, NULL, 2, 'Pending'),  -- Juan pending for Range
(6, 7, NULL, NULL, NULL, 250, 5, 'Confirmed'), -- Jose finished Range session
(8, 1, 5, 8, NULL, NULL, NULL, 'Confirmed'),   -- Gab confirmed for future Fairway
(2, 3, NULL, NULL, NULL, NULL, 3, 'Pending'),  -- Tiger pending for Range
(5, 4, 3, NULL, NULL, 150, 1, 'Confirmed'),    -- Maria in ongoing Range
(1, 1, NULL, NULL, NULL, NULL, NULL, 'Confirmed'), -- Admin playing Fairway
(9, 2, 4, 9, NULL, NULL, NULL, 'Pending'),     -- Alice pending Fairway
(10, 7, NULL, NULL, NULL, 100, 2, 'Confirmed'); -- Bob finished Range

-- ==========================================
-- 7. INSERT PAYMENTS (ID 1-10)
-- transaction_ref format: YYYYMMDDHHMMSS-UserID
-- ==========================================
INSERT INTO `payment` (total_price, date_paid, payment_method, status, discount_applied, user_id, cart_id, session_user_id, transaction_ref) VALUES
-- 1. Tiger paid for his cart
(3500.00, NOW(), 'Credit Card', 'Paid', 0.00, 2, 2, NULL, '20231120100000-2'),
-- 2. Rory paid for his cart
(25000.00, NOW(), 'GCash', 'Paid', 500.00, 3, 3, NULL, '20231120100500-3'),
-- 3. Tiger paid for his session (Session User ID 1)
(5000.00, NOW(), 'Credit Card', 'Paid', 1000.00, 2, NULL, 1, '20231120120000-2'),
-- 4. Rory paid for his session (Session User ID 2)
(5000.00, NOW(), 'Cash', 'Paid', 1000.00, 3, NULL, 2, '20231120120000-3'),
-- 5. Jose paid for his cart
(5000.00, NOW(), 'GCash', 'Paid', 0.00, 6, 6, NULL, '20231121090000-6'),
-- 6. Jose paid for his range session (Session User ID 4)
(1500.00, NOW(), 'GCash', 'Paid', 100.00, 6, NULL, 4, '20231121090000-6'), -- Grouped with cart above by time/logic usually
-- 7. Gab paid for his cart
(10000.00, NOW(), 'Credit Card', 'Paid', 2500.00, 8, 8, NULL, '20231122083000-8'),
-- 8. Gab paid for his session (Session User ID 5)
(8500.00, NOW(), 'Credit Card', 'Paid', 1500.00, 8, NULL, 5, '20231122083000-8'), -- Grouped with cart above
-- 9. Bob paid for his range session (Session User ID 10)
(600.00, NOW(), 'Cash', 'Paid', 0.00, 10, NULL, 10, '20231123140000-10'),
-- 10. Membership Payment (Example)
(30000.00, NOW(), 'Credit Card', 'Paid', 0.00, 2, NULL, NULL, '20230101000000-2');