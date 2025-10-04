#!/usr/bin/env python3
"""
Deployment script for HydroAlert Backend
Handles database migrations, environment checks, and deployment validation
"""

import os
import sys
import subprocess
import asyncio
from pathlib import Path
from sqlalchemy import text
from app.database.connection import engine
from app.core.config import settings

class DeploymentManager:
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.migrations_dir = self.base_dir / "migrations"
        self.uploads_dir = self.base_dir / "uploads"
    
    def check_environment(self):
        """Check environment variables and dependencies"""
        print("🔍 Checking environment...")
        
        # Check required environment variables
        required_vars = [
            "DATABASE_URL",
            "JWT_SECRET_KEY"
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
            return False
        
        print("✅ Environment variables check passed")
        return True
    
    def check_dependencies(self):
        """Check if all required dependencies are installed"""
        print("🔍 Checking dependencies...")
        
        try:
            import fastapi
            import sqlmodel
            import asyncpg
            import geoalchemy2
            import aiofiles
            print("✅ All dependencies are installed")
            return True
        except ImportError as e:
            print(f"❌ Missing dependency: {e}")
            return False
    
    def create_directories(self):
        """Create necessary directories"""
        print("📁 Creating directories...")
        
        directories = [
            self.uploads_dir,
            self.uploads_dir / "evidence",
            self.uploads_dir / "temp"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            print(f"✅ Created directory: {directory}")
    
    async def run_database_migrations(self):
        """Run database migrations"""
        print("🗄️ Running database migrations...")
        
        try:
            # Read and execute PostGIS migration
            migration_file = self.migrations_dir / "postgis_migration.sql"
            if migration_file.exists():
                with open(migration_file, 'r') as f:
                    migration_sql = f.read()
                
                async with engine.begin() as conn:
                    # Split SQL into individual statements
                    statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip()]
                    
                    for statement in statements:
                        if statement:
                            await conn.execute(text(statement))
                
                print("✅ PostGIS migration completed")
            else:
                print("⚠️ No migration file found")
                
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            return False
        
        return True
    
    async def test_database_connection(self):
        """Test database connection"""
        print("🔗 Testing database connection...")
        
        try:
            async with engine.begin() as conn:
                result = await conn.execute(text("SELECT 1"))
                print("✅ Database connection successful")
                return True
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return False
    
    async def test_postgis_extension(self):
        """Test PostGIS extension"""
        print("🗺️ Testing PostGIS extension...")
        
        try:
            async with engine.begin() as conn:
                result = await conn.execute(text("SELECT PostGIS_Version()"))
                version = result.fetchone()[0]
                print(f"✅ PostGIS extension active: {version}")
                return True
        except Exception as e:
            print(f"❌ PostGIS extension test failed: {e}")
            return False
    
    def run_tests(self):
        """Run unit tests"""
        print("🧪 Running unit tests...")
        
        try:
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                "tests/", "-v", "--tb=short"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ All tests passed")
                return True
            else:
                print(f"❌ Tests failed:\n{result.stdout}\n{result.stderr}")
                return False
        except Exception as e:
            print(f"❌ Test execution failed: {e}")
            return False
    
    async def validate_endpoints(self):
        """Validate API endpoints are working"""
        print("🌐 Validating API endpoints...")
        
        try:
            import httpx
            
            async with httpx.AsyncClient() as client:
                # Test health endpoint
                response = await client.get("http://localhost:8002/health")
                if response.status_code == 200:
                    print("✅ Health endpoint working")
                else:
                    print(f"❌ Health endpoint failed: {response.status_code}")
                    return False
                
                # Test docs endpoint
                response = await client.get("http://localhost:8002/docs")
                if response.status_code == 200:
                    print("✅ API documentation accessible")
                else:
                    print(f"❌ API docs failed: {response.status_code}")
                    return False
                
                print("✅ API endpoints validation passed")
                return True
                
        except Exception as e:
            print(f"❌ API validation failed: {e}")
            return False
    
    async def deploy(self):
        """Main deployment process"""
        print("🚀 Starting HydroAlert Backend deployment...")
        print("=" * 50)
        
        # Step 1: Environment check
        if not self.check_environment():
            print("❌ Environment check failed")
            return False
        
        # Step 2: Dependencies check
        if not self.check_dependencies():
            print("❌ Dependencies check failed")
            return False
        
        # Step 3: Create directories
        self.create_directories()
        
        # Step 4: Database migrations
        if not await self.run_database_migrations():
            print("❌ Database migration failed")
            return False
        
        # Step 5: Test database connection
        if not await self.test_database_connection():
            print("❌ Database connection test failed")
            return False
        
        # Step 6: Test PostGIS extension
        if not await self.test_postgis_extension():
            print("❌ PostGIS extension test failed")
            return False
        
        # Step 7: Run tests
        if not self.run_tests():
            print("❌ Unit tests failed")
            return False
        
        # Step 8: Validate endpoints (if server is running)
        # Note: This assumes the server is already running
        # In a real deployment, you might start the server here
        
        print("=" * 50)
        print("🎉 Deployment completed successfully!")
        print("\n📋 Deployment Summary:")
        print("✅ Environment variables configured")
        print("✅ Dependencies installed")
        print("✅ Directories created")
        print("✅ Database migrations applied")
        print("✅ PostGIS extension active")
        print("✅ Unit tests passed")
        print("\n🌐 API Endpoints:")
        print("   - Health: http://localhost:8002/health")
        print("   - Docs: http://localhost:8002/docs")
        print("   - Mobile Reports: http://localhost:8002/api/mobile/reports/")
        print("   - Mobile Alerts: http://localhost:8002/api/mobile/alerts/")
        print("\n📁 File Upload Directory: uploads/")
        print("🗺️ PostGIS: Enabled for geospatial queries")
        
        return True

async def main():
    """Main entry point"""
    deployer = DeploymentManager()
    success = await deployer.deploy()
    
    if not success:
        print("\n❌ Deployment failed!")
        sys.exit(1)
    else:
        print("\n✅ Deployment successful!")

if __name__ == "__main__":
    asyncio.run(main())
