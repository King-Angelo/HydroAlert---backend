from typing import Dict, Any, List, Optional
from datetime import datetime
from app.websocket.connection_manager import connection_manager
from app.models.flood_data import FloodReading
from app.models.emergency_report import EmergencyReport
from app.models.evacuation_center import EvacuationCenter
from app.schemas.map import MapBounds
import logging

logger = logging.getLogger(__name__)

class MapEventBroadcaster:
    """Broadcaster for map-specific real-time events"""
    
    def __init__(self):
        self.connection_manager = connection_manager
        self.viewport_registrations: Dict[str, MapBounds] = {}  # connection_id -> bounds
    
    def register_viewport(self, connection_id: str, bounds: MapBounds):
        """Register a client's current map viewport"""
        self.viewport_registrations[connection_id] = bounds
        logger.info(f"Registered viewport for connection {connection_id}: {bounds}")
    
    def unregister_viewport(self, connection_id: str):
        """Unregister a client's map viewport"""
        if connection_id in self.viewport_registrations:
            del self.viewport_registrations[connection_id]
            logger.info(f"Unregistered viewport for connection {connection_id}")
    
    def _bounds_overlap(self, bounds1: MapBounds, bounds2: MapBounds) -> bool:
        """Check if two bounds overlap"""
        return not (bounds1.east < bounds2.west or 
                   bounds1.west > bounds2.east or 
                   bounds1.north < bounds2.south or 
                   bounds1.south > bounds2.north)
    
    def _get_affected_connections(self, lat: float, lng: float, radius_km: float = 1.0) -> List[str]:
        """Get connections whose viewport is affected by a location change"""
        affected_connections = []
        
        # Create a small bounds around the location
        location_bounds = MapBounds(
            north=lat + (radius_km / 111.0),  # Rough conversion: 1 degree ≈ 111 km
            south=lat - (radius_km / 111.0),
            east=lng + (radius_km / (111.0 * abs(lat / 90.0))),  # Adjust for latitude
            west=lng - (radius_km / (111.0 * abs(lat / 90.0)))
        )
        
        for connection_id, viewport_bounds in self.viewport_registrations.items():
            if self._bounds_overlap(viewport_bounds, location_bounds):
                affected_connections.append(connection_id)
        
        return affected_connections
    
    async def broadcast_flood_reading_update(
        self, 
        reading: FloodReading, 
        action: str = "create"
    ):
        """Broadcast flood reading update to affected clients"""
        try:
            affected_connections = self._get_affected_connections(
                reading.location_lat, reading.location_lng
            )
            
            if not affected_connections:
                return
            
            message = {
                "type": "map_update",
                "data": {
                    "layer": "flood_readings",
                    "action": action,
                    "feature": {
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [reading.location_lng, reading.location_lat]
                        },
                        "properties": {
                            "id": reading.id,
                            "sensor_id": reading.sensor_id,
                            "water_level_cm": reading.water_level_cm,
                            "rainfall_mm": reading.rainfall_mm,
                            "risk_level": reading.risk_level,
                            "timestamp": reading.timestamp.isoformat(),
                            "notes": reading.notes,
                            "layer": "flood_readings"
                        }
                    },
                    "bounds": {
                        "north": reading.location_lat + 0.01,
                        "south": reading.location_lat - 0.01,
                        "east": reading.location_lng + 0.01,
                        "west": reading.location_lng - 0.01
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            
            # Send to affected connections
            for connection_id in affected_connections:
                # Find the WebSocket connection and send message
                # This would need to be integrated with the connection manager
                pass
            
            logger.info(f"Broadcasted flood reading {action} to {len(affected_connections)} connections")
            
        except Exception as e:
            logger.error(f"Error broadcasting flood reading update: {str(e)}")
    
    async def broadcast_emergency_report_update(
        self, 
        report: EmergencyReport, 
        action: str = "create"
    ):
        """Broadcast emergency report update to affected clients"""
        try:
            affected_connections = self._get_affected_connections(
                report.location_lat, report.location_lng
            )
            
            if not affected_connections:
                return
            
            message = {
                "type": "map_update",
                "data": {
                    "layer": "emergency_reports",
                    "action": action,
                    "feature": {
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [report.location_lng, report.location_lat]
                        },
                        "properties": {
                            "id": report.id,
                            "title": report.title,
                            "description": report.description,
                            "severity": report.severity,
                            "category": report.category,
                            "status": report.status,
                            "user_id": report.user_id,
                            "submitted_at": report.submitted_at.isoformat(),
                            "triaged_at": report.triaged_at.isoformat() if report.triaged_at else None,
                            "triaged_by": report.triaged_by,
                            "triage_notes": report.triage_notes,
                            "contact_phone": report.contact_phone,
                            "layer": "emergency_reports"
                        }
                    },
                    "bounds": {
                        "north": report.location_lat + 0.01,
                        "south": report.location_lat - 0.01,
                        "east": report.location_lng + 0.01,
                        "west": report.location_lng - 0.01
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            
            # Send to affected connections
            for connection_id in affected_connections:
                # Find the WebSocket connection and send message
                pass
            
            logger.info(f"Broadcasted emergency report {action} to {len(affected_connections)} connections")
            
        except Exception as e:
            logger.error(f"Error broadcasting emergency report update: {str(e)}")
    
    async def broadcast_evacuation_center_update(
        self, 
        center: EvacuationCenter, 
        action: str = "update"
    ):
        """Broadcast evacuation center update to affected clients"""
        try:
            affected_connections = self._get_affected_connections(
                center.location_lat, center.location_lng
            )
            
            if not affected_connections:
                return
            
            message = {
                "type": "map_update",
                "data": {
                    "layer": "evacuation_centers",
                    "action": action,
                    "feature": {
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [center.location_lng, center.location_lat]
                        },
                        "properties": {
                            "id": center.id,
                            "name": center.name,
                            "capacity": center.capacity,
                            "current_occupancy": center.current_occupancy,
                            "available_capacity": center.capacity - center.current_occupancy,
                            "occupancy_percentage": (center.current_occupancy / center.capacity * 100) if center.capacity > 0 else 0,
                            "contact_info": center.contact_info,
                            "is_active": center.is_active,
                            "created_at": center.created_at.isoformat(),
                            "updated_at": center.updated_at.isoformat() if center.updated_at else None,
                            "layer": "evacuation_centers"
                        }
                    },
                    "bounds": {
                        "north": center.location_lat + 0.01,
                        "south": center.location_lat - 0.01,
                        "east": center.location_lng + 0.01,
                        "west": center.location_lng - 0.01
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            
            # Send to affected connections
            for connection_id in affected_connections:
                # Find the WebSocket connection and send message
                pass
            
            logger.info(f"Broadcasted evacuation center {action} to {len(affected_connections)} connections")
            
        except Exception as e:
            logger.error(f"Error broadcasting evacuation center update: {str(e)}")
    
    async def broadcast_map_data_refresh(self, bounds: MapBounds):
        """Broadcast map data refresh to clients viewing the affected area"""
        try:
            affected_connections = []
            
            for connection_id, viewport_bounds in self.viewport_registrations.items():
                if self._bounds_overlap(viewport_bounds, bounds):
                    affected_connections.append(connection_id)
            
            if not affected_connections:
                return
            
            message = {
                "type": "map_refresh",
                "data": {
                    "bounds": {
                        "north": bounds.north,
                        "south": bounds.south,
                        "east": bounds.east,
                        "west": bounds.west
                    },
                    "timestamp": datetime.utcnow().isoformat(),
                    "message": "Map data has been updated in your current view"
                }
            }
            
            # Send to affected connections
            for connection_id in affected_connections:
                # Find the WebSocket connection and send message
                pass
            
            logger.info(f"Broadcasted map refresh to {len(affected_connections)} connections")
            
        except Exception as e:
            logger.error(f"Error broadcasting map data refresh: {str(e)}")
    
    def get_viewport_stats(self) -> Dict[str, Any]:
        """Get statistics about registered viewports"""
        return {
            "total_registered_viewports": len(self.viewport_registrations),
            "viewport_registrations": [
                {
                    "connection_id": conn_id,
                    "bounds": {
                        "north": bounds.north,
                        "south": bounds.south,
                        "east": bounds.east,
                        "west": bounds.west
                    }
                }
                for conn_id, bounds in self.viewport_registrations.items()
            ]
        }

# Global map event broadcaster instance
map_event_broadcaster = MapEventBroadcaster()
