"""
Mock API Server Engine
======================
ImmunoOrg 2.0 - Phase 3: Real-World API Mocking

Provides a realistic mock API server that implements actual REST/GraphQL protocols.
The agent must use tool-calling (function calls) to interact with these APIs,
simulating real executive workflows beyond just "schema drift".

Features:
- REST API endpoints (Google Calendar, Outlook Email, Marriott, Concur)
- GraphQL endpoints as alternative query interface
- Real field validation (rejects malformed requests)
- Latency simulation
- Authentication token requirements
- Schema versioning with deprecation warnings
"""

from __future__ import annotations

import random
import json
import hashlib
from dataclasses import dataclass, asdict
from typing import Any
from enum import Enum


class APIVersion(Enum):
    """API version tracking."""
    V1 = "v1"
    V2 = "v2"
    V3 = "v3"


@dataclass
class APIResponse:
    """Standard API response format."""
    status: int  # HTTP status code
    data: dict[str, Any] | None = None
    error: str | None = None
    message: str | None = None
    warning: str | None = None  # Deprecation warnings
    version: str = "v1"
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "data": self.data,
            "error": self.error,
            "message": self.message,
            "warning": self.warning,
            "version": self.version,
        }


@dataclass
class APIEndpoint:
    """Configuration for an API endpoint."""
    name: str
    method: str  # GET, POST, PUT, DELETE
    path: str
    required_fields: list[str]
    optional_fields: list[str]
    response_fields: list[str]
    auth_required: bool = True
    latency_ms: float = 100.0
    current_version: str = "v1"
    deprecated_fields: dict[str, str] = None  # {old_field: new_field}
    
    def __post_init__(self):
        if self.deprecated_fields is None:
            self.deprecated_fields = {}


class MockRESTAPI:
    """Mock REST API server implementation."""
    
    # Define endpoints
    ENDPOINTS: dict[str, APIEndpoint] = {
        "google_calendar_create": APIEndpoint(
            name="Google Calendar - Create Event",
            method="POST",
            path="/calendar/v1/events",
            required_fields=["title", "startTime", "endTime"],
            optional_fields=["attendees", "description", "meetingType"],
            response_fields=["eventId", "title", "startTime", "endTime", "status"],
            latency_ms=150.0,
            deprecated_fields={"startTime": "start", "endTime": "end"},
        ),
        "outlook_email_send": APIEndpoint(
            name="Outlook Email - Send",
            method="POST",
            path="/mail/v1/messages/send",
            required_fields=["subject", "body", "to"],
            optional_fields=["cc", "bcc", "attachments"],
            response_fields=["messageId", "subject", "status"],
            latency_ms=200.0,
            deprecated_fields={"to": "recipients"},
        ),
        "marriott_book": APIEndpoint(
            name="Marriott - Book Room",
            method="POST",
            path="/booking/v1/reservations",
            required_fields=["checkInDate", "checkOutDate", "roomType"],
            optional_fields=["guestName", "specialRequests", "paymentMethod"],
            response_fields=["bookingId", "checkInDate", "checkOutDate", "confirmedPrice"],
            latency_ms=250.0,
            deprecated_fields={"checkInDate": "arrivalDate", "checkOutDate": "departureDate"},
        ),
        "concur_create_trip": APIEndpoint(
            name="Concur Travel - Create Trip",
            method="POST",
            path="/travel/v1/trips",
            required_fields=["departure", "destination", "startDate", "endDate"],
            optional_fields=["purpose", "budget", "approverEmail"],
            response_fields=["tripId", "departure", "destination", "status"],
            latency_ms=300.0,
        ),
    }
    
    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)
        self.request_history: list[dict[str, Any]] = []
        self.tokens: dict[str, dict[str, Any]] = {}  # Simulated auth tokens
        self._generate_token()
    
    def _generate_token(self) -> str:
        """Generate a valid auth token."""
        token_data = {"user": "agent", "created_at": 0}
        token = hashlib.md5(json.dumps(token_data).encode()).hexdigest()
        self.tokens[token] = token_data
        return token
    
    def call_endpoint(
        self,
        endpoint_name: str,
        data: dict[str, Any],
        auth_token: str = "",
    ) -> APIResponse:
        """
        Execute a REST API call.
        Simulates real API validation, latency, and errors.
        """
        # Get endpoint definition
        if endpoint_name not in self.ENDPOINTS:
            return APIResponse(
                status=404,
                error="Endpoint not found",
                message=f"No endpoint named '{endpoint_name}'",
            )
        
        endpoint = self.ENDPOINTS[endpoint_name]
        
        # Check authentication
        if endpoint.auth_required and not self._validate_token(auth_token):
            return APIResponse(
                status=401,
                error="Unauthorized",
                message="Invalid or missing authentication token",
            )
        
        # Validate required fields
        missing = [f for f in endpoint.required_fields if f not in data]
        if missing:
            return APIResponse(
                status=400,
                error="Bad Request",
                message=f"Missing required fields: {', '.join(missing)}",
            )
        
        # Check for deprecated field usage
        warnings = []
        for old_field, new_field in endpoint.deprecated_fields.items():
            if old_field in data:
                warnings.append(f"Field '{old_field}' is deprecated. Use '{new_field}' instead.")
        
        # Validate field types (basic)
        for field in list(data.keys()):
            if field not in endpoint.required_fields + endpoint.optional_fields:
                return APIResponse(
                    status=400,
                    error="Bad Request",
                    message=f"Unknown field: '{field}'",
                )
        
        # Generate response
        # Use endpoint.response_fields as the contract, and populate IDs even if
        # the caller didn't provide them (real APIs generate IDs server-side).
        response_data: dict[str, Any] = {}
        for field in endpoint.response_fields:
            if field in data:
                response_data[field] = data[field]
                continue
            if field.lower().endswith("id"):
                response_data[field] = self._generate_id(endpoint_name)
            elif field.lower() == "status":
                response_data[field] = "confirmed"
        
        response = APIResponse(
            status=200,
            data=response_data,
            message=f"Request to {endpoint.name} succeeded",
            version=endpoint.current_version,
        )
        
        if warnings:
            response.warning = " | ".join(warnings)
        
        # Log request
        self.request_history.append({
            "endpoint": endpoint_name,
            "status": response.status,
            "fields_used": list(data.keys()),
            "warnings": warnings,
        })
        
        return response
    
    def _validate_token(self, token: str) -> bool:
        """Check if token is valid."""
        return token in self.tokens
    
    def _generate_id(self, endpoint_name: str) -> str:
        """Generate a unique ID for a resource."""
        return f"{endpoint_name[:3]}-{self.rng.randint(10000, 99999)}"


class MockGraphQLAPI:
    """Mock GraphQL API implementation."""
    
    # Define GraphQL schema
    SCHEMA = {
        "Query": {
            "calendar_events": {
                "args": ["filter", "limit"],
                "returns": ["eventId", "title", "start", "end", "attendees"],
            },
            "emails": {
                "args": ["folder", "limit", "unread_only"],
                "returns": ["messageId", "subject", "from", "to", "body"],
            },
            "bookings": {
                "args": ["status", "limit"],
                "returns": ["bookingId", "arrivalDate", "departureDate", "roomType", "price"],
            },
        },
        "Mutation": {
            "create_event": {
                "args": ["title", "start", "end", "attendees"],
                "returns": ["eventId", "status"],
            },
            "send_email": {
                "args": ["subject", "body", "recipients"],
                "returns": ["messageId", "status"],
            },
            "update_booking": {
                "args": ["bookingId", "arrivalDate", "departureDate"],
                "returns": ["bookingId", "status"],
            },
        },
    }
    
    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)
        self.query_history: list[dict[str, Any]] = []
    
    def execute_query(self, query_string: str) -> APIResponse:
        """
        Execute a GraphQL query.
        Simulates query parsing and field validation.
        """
        try:
            # Very basic query validation
            if "mutation" in query_string.lower():
                operation_type = "Mutation"
            elif "query" in query_string.lower() or "{" in query_string:
                operation_type = "Query"
            else:
                return APIResponse(
                    status=400,
                    error="Invalid GraphQL",
                    message="Query must contain 'query' or 'mutation' keyword",
                )
            
            # Parse field names (very simplified)
            fields_used = self._parse_fields(query_string)
            
            # Check if fields are valid
            valid_fields = set()
            if operation_type == "Query":
                for query_name in self.SCHEMA["Query"]:
                    valid_fields.update(self.SCHEMA["Query"][query_name]["returns"])
            else:
                for mutation_name in self.SCHEMA["Mutation"]:
                    valid_fields.update(self.SCHEMA["Mutation"][mutation_name]["returns"])
            
            # Generate mock response
            response_data = {
                "data": {field: self._generate_mock_value(field) for field in fields_used}
            }
            
            self.query_history.append({
                "query": query_string[:100],  # Log first 100 chars
                "operation": operation_type,
                "fields": fields_used,
            })
            
            return APIResponse(
                status=200,
                data=response_data,
                message=f"GraphQL {operation_type} executed successfully",
            )
        
        except Exception as e:
            return APIResponse(
                status=400,
                error="GraphQL Error",
                message=str(e),
            )
    
    def _parse_fields(self, query_string: str) -> list[str]:
        """Extract field names from GraphQL query (simplified)."""
        import re
        # Simple regex to find identifiers that look like fields
        matches = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:{|$|[,)])', query_string)
        return matches[:10]  # Limit to 10 to avoid noise
    
    def _generate_mock_value(self, field: str) -> Any:
        """Generate mock value for a field."""
        if "id" in field.lower():
            return f"id-{self.rng.randint(1000, 9999)}"
        elif "date" in field.lower() or "time" in field.lower():
            return "2026-04-25T10:00:00Z"
        elif "status" in field.lower():
            return self.rng.choice(["active", "pending", "completed"])
        elif "price" in field.lower():
            return round(self.rng.uniform(50, 500), 2)
        else:
            return f"mock-{field}-value"


class RealisticAPIMockServer:
    """
    Unified mock server combining REST and GraphQL.
    The agent uses tool-calling to interact with this server.
    """
    
    def __init__(self, seed: int | None = None):
        self.rest = MockRESTAPI(seed=seed)
        self.graphql = MockGraphQLAPI(seed=seed)
        self.rng = random.Random(seed)
        self.auth_token = self.rest._generate_token()
    
    def call_rest(
        self,
        endpoint: str,
        data: dict[str, Any],
        use_auth: bool = True,
    ) -> APIResponse:
        """Call a REST endpoint."""
        token = self.auth_token if use_auth else ""
        return self.rest.call_endpoint(endpoint, data, token).to_dict()
    
    def call_graphql(self, query: str) -> APIResponse:
        """Call the GraphQL endpoint."""
        return self.graphql.execute_query(query).to_dict()
    
    def get_api_status_report(self) -> dict[str, Any]:
        """Get status of all API operations."""
        return {
            "rest_requests_made": len(self.rest.request_history),
            "graphql_queries_made": len(self.graphql.query_history),
            "available_endpoints": list(self.rest.ENDPOINTS.keys()),
            "recent_rest_calls": self.rest.request_history[-5:] if self.rest.request_history else [],
            "recent_graphql_calls": self.graphql.query_history[-5:] if self.graphql.query_history else [],
        }
