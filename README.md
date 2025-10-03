# Hydro Alert Flood Monitoring System - Backend

A comprehensive FastAPI backend for barangay-level flood monitoring with real-time capabilities, JWT authentication, and PostgreSQL integration.

## Features

- **Modular API Design** - Separate routers for authentication, alerts, sensors, and WebSocket connections
- **JWT Authentication** - Secure token-based authentication with role-based access control
- **Real-time Updates** - WebSocket support for live flood status updates and emergency alerts
- **PostgreSQL Integration** - SQLModel ORM with async database operations
- **Sensor Data Management** - Endpoints for submitting and retrieving flood sensor data
- **Alert System** - Automated flood alert generation based on sensor thresholds

## Project Structure

```
Backend/
├── app/
│   ├── core/           # Core configuration and utilities
│   │   ├── config.py   # Application settings
│   │   ├── security.py # JWT token handling
│   │   ├── dependencies.py # FastAPI dependencies
│   │   └── websocket.py # WebSocket connection manager
│   ├── database/       # Database configuration
│   │   ├── connection.py # Async database setup
│   │   └── base.py     # Base model class
│   ├── models/         # SQLModel database models
│   │   ├── user.py     # User model with bcrypt hashing
│   │   └── sensor_data.py # Sensor data model
│   ├── schemas/        # Pydantic schemas
│   │   ├── auth.py     # Authentication schemas
│   │   ├── user.py     # User schemas
│   │   └── sensor_data.py # Sensor data schemas
│   └── routers/        # API route handlers
│       ├── auth.py     # Authentication endpoints
│       ├── alerts.py   # Alert management
│       ├── sensors.py  # Sensor data endpoints
│       └── websocket.py # WebSocket endpoints
├── main.py            # FastAPI application entry point
├── requirements.txt   # Python dependencies
├── .env.example      # Environment variables template
└── README.md         # This file
```

## API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - User login (returns JWT token)

### Alerts
- `GET /alerts/current` - Get current flood alerts (protected)
- `GET /alerts/history` - Get alert history (protected)
- `POST /alerts/sensor-data` - Submit sensor data (protected)

### Sensors
- `POST /sensors/data` - Submit sensor data (protected)
- `GET /sensors/data` - Get sensor data history (protected)
- `GET /sensors/data/latest` - Get latest sensor reading (protected)

### WebSocket
- `WS /ws/flood-updates` - Real-time flood updates
- `WS /ws/flood-updates/{user_id}` - User-specific updates
- `POST /ws/broadcast-flood-update` - Broadcast update (admin only)
- `POST /ws/broadcast-alert` - Broadcast emergency alert (admin only)

## Setup Instructions

1. **Clone and navigate to the project:**
   ```bash
   cd Backend
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials and JWT secret
   ```

5. **Set up PostgreSQL database:**
   ```sql
   CREATE DATABASE hydroalert;
   CREATE USER hydroalert_user WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE hydroalert TO hydroalert_user;
   ```

6. **Run the application:**
   ```bash
   python main.py
   ```

   Or with uvicorn directly:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

## Environment Variables

Create a `.env` file with the following variables:

```env
# Database
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/hydroalert

# JWT
JWT_SECRET_KEY=your-super-secret-jwt-key
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60

# App
APP_NAME=Hydro Alert API
DEBUG=false

# WebSocket
WEBSOCKET_CORS_ORIGINS=["http://localhost:3000"]
```

## Usage Examples

### Register a new user:
```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "resident1",
    "password": "password123",
    "email": "resident@example.com",
    "full_name": "John Doe",
    "role": "resident"
  }'
```

### Login:
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "resident1",
    "password": "password123"
  }'
```

### Submit sensor data (with JWT token):
```bash
curl -X POST "http://localhost:8000/sensors/data" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "water_level_cm": 25.5,
    "rainfall_mm": 15.2,
    "location_lat": 14.5995,
    "location_lng": 120.9842,
    "sensor_id": "SENSOR_001"
  }'
```

### Get current alerts:
```bash
curl -X GET "http://localhost:8000/alerts/current" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## WebSocket Connection

Connect to real-time updates:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/flood-updates');

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
    
    if (data.type === 'flood_update') {
        // Handle flood update
        console.log('Flood update:', data.data);
    } else if (data.type === 'emergency_alert') {
        // Handle emergency alert
        console.log('Emergency alert:', data.data);
    }
};
```

## Database Models

### User Model
- `id`: Primary key
- `username`: Unique username
- `email`: Optional email address
- `full_name`: User's full name
- `role`: Either "resident" or "admin"
- `hashed_password`: Bcrypt hashed password
- `is_active`: Account status
- `created_at`: Account creation timestamp

### SensorData Model
- `id`: Primary key
- `water_level_cm`: Water level in centimeters
- `rainfall_mm`: Rainfall in millimeters
- `location_lat`: Latitude coordinate
- `location_lng`: Longitude coordinate
- `sensor_id`: Sensor identifier
- `user_id`: Foreign key to User
- `notes`: Optional notes
- `created_at`: Data submission timestamp

## Security Features

- **JWT Authentication**: Secure token-based authentication
- **Password Hashing**: Bcrypt for secure password storage
- **Role-based Access**: Different permissions for residents and admins
- **CORS Protection**: Configurable CORS settings
- **Input Validation**: Pydantic models for request validation

## Development

The application uses:
- **FastAPI** for the web framework
- **SQLModel** for database ORM
- **PostgreSQL** with asyncpg driver
- **Pydantic** for data validation
- **PyJWT** for JWT token handling
- **Bcrypt** for password hashing
- **WebSockets** for real-time communication

## API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Production Deployment

For production deployment:

1. Set `DEBUG=false` in environment variables
2. Use a strong `JWT_SECRET_KEY`
3. Configure proper CORS origins
4. Use a production ASGI server like Gunicorn with Uvicorn workers
5. Set up proper database connection pooling
6. Configure reverse proxy (nginx) for SSL termination

```bash
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```
