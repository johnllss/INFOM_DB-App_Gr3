# Golf Club Management System

A comprehensive database-driven web application for managing golf club operations, including user memberships, golf sessions, staff management, inventory, and payments.

## Project Overview

This is the repository for CCINFOM's Database Application project. The system provides a complete solution for golf club management with features including:

- **User Management**: Registration, authentication, and membership tier system (Bronze, Silver, Gold, Platinum, Diamond)
- **Golf Sessions**: Booking system for Driving Range and Fairway sessions with flexible hole configurations (9 Front, 9 Back, Full 18)
- **Staff Management**: Coach and caddie allocation with availability tracking and service fee management
- **Shopping Cart & Payment**: Integrated cart system for item purchases (clubs, balls, bags, apparel, equipment) with support for both sales and rentals
- **Payment Processing**: Multiple payment methods (Cash, GCash, Credit Card) with discount and loyalty points system
- **Session Tracking**: Real-time session status updates (Available, Fully Booked, Ongoing, Finished) with automated scheduling
- **Reports**: Sales performance, staff performance, inventory, and customer value analytics

## Technology Stack

- **Backend**: Flask (Python)
- **Database**: MySQL 8.0
- **Session Management**: Flask-Session
- **Authentication**: Werkzeug Security (password hashing)
- **Frontend**: HTML, CSS, JavaScript with Jinja2 templating

## Database Schema

The application uses a relational database with the following core tables:
- `user` - User accounts and membership information
- `staff` - Coaches and caddies
- `golf_session` - Available golf sessions
- `session_user` - User session bookings
- `cart` - Shopping carts
- `item` - Golf equipment and merchandise
- `payment` - Payment transactions

## Known Issues

### Critical Issues
1. **Debug Mode in Production**: Application runs with `debug=True` which should be disabled for production deployment ([app.py:1185](golf/app.py#L1185))

### Pending Features
1. **Card Information Validation**: Credit card validation not yet implemented ([process.py:166](golf/process.py#L166))
2. **Payment Extraction Logic**: Cart ID and session user ID extraction needs refinement ([process.py:239](golf/process.py#L239))

## Future Improvements

### Analytics & Reporting
- [ ] Complete all pending report modules
- [ ] Real-time dashboard with charts and graphs
- [ ] Export functionality (PDF, Excel) for reports
- [ ] Predictive analytics for session booking trends
- [ ] Revenue forecasting tools

### Administrative Features
- [ ] Comprehensive admin dashboard
- [ ] Audit logging for all transactions

## Setup Instructions

1. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure MySQL database:
   - Update database credentials in `golf/app.py` (lines 26-30)
   - Run schema: `mysql -u root -p < golf/dbgolf_schema.sql`
   - Insert sample data: `mysql -u root -p golf_db < golf/insertrows.sql`

3. Run the application:
   ```bash
   python golf/app.py
   ```

4. Access the application at `http://localhost:5000`

## License

This project is developed for academic purposes as part of CCINFOM coursework at De La Salle University.
