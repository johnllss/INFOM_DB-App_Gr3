CREATE SCHEMA IF NOT EXISTS dbgolf;

USE dbgolf;

CREATE TABLE payment (
	payment_id			  BIGINT PRIMARY KEY AUTO_INCREMENT,
  total_price			  DECIMAL(8,2) NOT NULL,
  date_paid			    DATETIME, -- null = not yet paid
  payment_method		ENUM('Cash on Delivery', 'GCash', 'Credit Card'),
  status				    ENUM('Cancelled', 'Pending', 'Paid'),
  discount_applied	DECIMAL(1,2), -- null = unsubscribed
  FOREIGN KEY 		  (user_id) REFERENCES users(user_id),
  FOREIGN KEY 		  (session_id) REFERENCES session(session_id),
  FOREIGN KEY 		  (cart_id) REFERENCES cart(cart_id)
);

CREATE TABLE staff (
  staff_id			  BIGINT PRIMARY KEY AUTO_INCREMENT,
  name				    VARCHAR(100) NOT NULL,
  email				    VARCHAR(100) NOT NULL,
  contact				  VARCHAR(20) NOT NULL,
  role				    VARCHAR(50) NOT NULL,
  status				  ENUM('Available', 'Occupied') NOT NULL,
  service_fee			DECIMAL(8,2) NOT NULL
);
