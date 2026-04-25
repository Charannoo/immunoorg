"""
Executive Context Engine with Real API Mocking
==============================================
ImmunoOrg 2.0 — Theme 3.2: World Modeling (Personalized Tasks)
Bonus Prize: Patronus AI — Consumer Workflows with Schema Drift

Simulates the executive's digital workflow running in parallel with the
active threat response. The defender agent must maintain two mental models
simultaneously: the threat response model AND the executive context model.

Phase 3: Integrated with realistic REST/GraphQL mock APIs.
Agents must use tool-calling to interact with actual API endpoints.
"""

from __future__ import annotations

import random
from typing import Any

from immunoorg.models import (
    ExecutiveTask, ExecutiveContextState, SchemaDriftEvent,
)
from immunoorg.mock_api_server import RealisticAPIMockServer


# ── Simulated API Schemas ─────────────────────────────────────────────────

API_SCHEMAS_V1: dict[str, dict[str, Any]] = {
    "google_calendar": {
        "fields": ["eventId", "title", "startTime", "endTime", "attendees"],
        "version": "v1",
    },
    "marriott_booking": {
        "fields": ["bookingId", "checkInDate", "checkOutDate", "roomType", "guestName"],
        "version": "v1",
    },
    "outlook_email": {
        "fields": ["messageId", "subject", "body", "recipients", "attachments"],
        "version": "v1",
    },
    "concur_travel": {
        "fields": ["tripId", "departure", "destination", "flightNumber", "status"],
        "version": "v1",
    },
}

# Schema changes injected mid-episode (simulating vendor API updates without notice)
DRIFT_EVENTS: list[dict[str, Any]] = [
    {
        "api_name": "google_calendar",
        "old_field": "startTime",
        "new_field": "start",
        "change_type": "field_rename",
        "inject_at_step": 15,
    },
    {
        "api_name": "marriott_booking",
        "old_field": "checkInDate",
        "new_field": "arrivalDate",
        "change_type": "field_rename",
        "inject_at_step": 25,
    },
    {
        "api_name": "outlook_email",
        "old_field": "recipients",
        "new_field": "to",
        "change_type": "field_rename",
        "inject_at_step": 35,
    },
    {
        "api_name": "google_calendar",
        "old_field": None,
        "new_field": "meetingType",
        "change_type": "new_required",
        "inject_at_step": 40,
    },
]

# Simulated executive tasks
EXECUTIVE_TASK_TEMPLATES = [
    {"type": "email", "description": "Draft urgent response to board about security incident",
     "api": "outlook_email", "priority": 0.9, "deadline_offset": 20},
    {"type": "calendar", "description": "Reschedule 3pm board call — conflict during migration",
     "api": "google_calendar", "priority": 0.8, "deadline_offset": 30},
    {"type": "travel", "description": "Book flight to NYC for emergency investor meeting",
     "api": "concur_travel", "priority": 0.7, "deadline_offset": 50},
    {"type": "calendar", "description": "Send quarterly security review materials",
     "api": "outlook_email", "priority": 0.85, "deadline_offset": 15},
    {"type": "document", "description": "Finalize board presentation before 5 PM deadline",
     "api": "outlook_email", "priority": 1.0, "deadline_offset": 10},
    {"type": "travel", "description": "Handle dinner conflict appearing on calendar during migration",
     "api": "marriott_booking", "priority": 0.5, "deadline_offset": 60},
]


class ExecutiveContextEngine:
    """
    Maintains the executive's digital workflow in parallel with threat response.
    Injects API schema drift events at configured simulation steps.
    
    Phase 3: Integrated with realistic REST/GraphQL mock APIs.

    The agent earns reward for:
    - Completing executive tasks despite ongoing incident
    - Detecting and adapting to schema drift without dropping tasks
    - Not confusing threat-response actions with executive workflow actions
    - Making correct REST/GraphQL API calls to complete tasks
    """

    def __init__(self, rng: random.Random | None = None, enable_mock_apis: bool = True):
        self.rng = rng or random.Random()
        self._state = ExecutiveContextState(
            api_schemas={k: dict(v) for k, v in API_SCHEMAS_V1.items()}
        )
        self._drift_queue = list(DRIFT_EVENTS)
        self._tasks_initialized = False
        
        # Phase 3: Initialize mock API server
        self.enable_mock_apis = enable_mock_apis
        self.mock_api_server: RealisticAPIMockServer | None = None
        if enable_mock_apis:
            self.mock_api_server = RealisticAPIMockServer(seed=None)

    @property
    def state(self) -> ExecutiveContextState:
        return self._state

    def initialize_tasks(self, sim_time: float) -> None:
        """Populate initial executive task queue."""
        for template in EXECUTIVE_TASK_TEMPLATES:
            task = ExecutiveTask(
                task_type=template["type"],
                description=template["description"],
                api_name=template["api"],
                priority=template["priority"],
                deadline_sim_time=sim_time + template["deadline_offset"],
            )
            self._state.active_tasks.append(task)
        self._tasks_initialized = True

    def tick(self, sim_time: float, step_count: int) -> list[SchemaDriftEvent]:
        """
        Advance one simulation step. Injects schema drift events if scheduled.
        Returns list of new drift events injected this tick.
        """
        if not self._tasks_initialized:
            self.initialize_tasks(sim_time)

        new_drifts: list[SchemaDriftEvent] = []

        # Check for scheduled schema drift injections
        due_drifts = [d for d in self._drift_queue if d["inject_at_step"] <= step_count]
        for drift_template in due_drifts:
            self._drift_queue.remove(drift_template)
            drift_event = self._inject_drift(drift_template, sim_time)
            new_drifts.append(drift_event)

        # Simulate task completion / expiry
        expired = []
        for task in self._state.active_tasks:
            if task.deadline_sim_time <= sim_time and not task.completed:
                if task.blocked_by_drift:
                    self._state.tasks_dropped += 1
                    expired.append(task)
                elif self.rng.random() < 0.15:  # 15% chance agent auto-handles low-priority
                    if task.priority < 0.6:
                        task.completed = True
                        self._state.completed_tasks.append(task)
                        expired.append(task)

        for task in expired:
            if task in self._state.active_tasks:
                self._state.active_tasks.remove(task)

        return new_drifts

    def _inject_drift(self, template: dict[str, Any], sim_time: float) -> SchemaDriftEvent:
        """Inject a schema change into the simulated API."""
        api_name = template["api_name"]
        old_field = template.get("old_field")
        new_field = template["new_field"]
        change_type = template["change_type"]

        # Update the stored schema
        schema = self._state.api_schemas.get(api_name, {})
        fields = list(schema.get("fields", []))

        if change_type == "field_rename" and old_field in fields:
            fields[fields.index(old_field)] = new_field
        elif change_type == "new_required":
            fields.append(new_field)

        schema["fields"] = fields
        schema["version"] = f"v{int(schema.get('version', 'v1').lstrip('v')) + 1}"
        self._state.api_schemas[api_name] = schema

        # Mark tasks using this API as potentially blocked
        inferred_mapping = f"{old_field} → {new_field}" if old_field else f"new required field: {new_field}"
        drift_handled = self.rng.random() > 0.4  # 60% chance agent notices and adapts

        for task in self._state.active_tasks:
            if task.api_name == api_name and not task.completed:
                if not drift_handled:
                    task.blocked_by_drift = True
                else:
                    self._state.adaptation_successes += 1

        drift = SchemaDriftEvent(
            api_name=api_name,
            old_field=old_field or "",
            new_field=new_field,
            change_type=change_type,
            inferred_mapping=inferred_mapping,
            inference_confidence=self.rng.uniform(0.65, 0.95) if drift_handled else 0.0,
            gracefully_handled=drift_handled,
            detected_at=sim_time,
        )
        self._state.drift_events.append(drift)
        return drift

    def handle_executive_action(self, task_id: str) -> dict[str, Any]:
        """Agent explicitly completes an executive task."""
        for task in self._state.active_tasks:
            if task.task_id == task_id and not task.completed:
                task.completed = True
                self._state.completed_tasks.append(task)
                self._state.active_tasks.remove(task)
                return {
                    "success": True,
                    "task": task.description,
                    "reward_bonus": task.priority * 0.3,
                }
        return {"success": False, "reason": "Task not found or already completed"}

    def get_context_summary(self) -> str:
        """Format executive context for agent observation."""
        lines = [f"📋 Executive Context ({len(self._state.active_tasks)} pending tasks):"]
        for task in sorted(self._state.active_tasks, key=lambda t: -t.priority)[:4]:
            blocked = " ⚠️ BLOCKED BY DRIFT" if task.blocked_by_drift else ""
            lines.append(f"  [{task.priority:.0%}] {task.description}{blocked}")
        if self._state.drift_events:
            recent = self._state.drift_events[-2:]
            lines.append(f"🔄 Schema Drift Events ({len(self._state.drift_events)} total):")
            for d in recent:
                status = "✅ Handled" if d.gracefully_handled else "❌ Unhandled"
                lines.append(f"  {d.api_name}: {d.inferred_mapping} [{status}]")
        return "\n".join(lines)

    def get_patronus_score(self) -> float:
        """
        Patronus AI bonus score:
        - Task completion rate despite drift
        - Drift adaptation success rate
        - API call accuracy (Phase 3)
        """
        total_tasks = (
            len(self._state.active_tasks)
            + len(self._state.completed_tasks)
            + self._state.tasks_dropped
        )
        if total_tasks == 0:
            return 0.5
        completion_rate = len(self._state.completed_tasks) / total_tasks
        total_drifts = len(self._state.drift_events)
        adaptation_rate = (
            self._state.adaptation_successes / total_drifts
            if total_drifts > 0 else 1.0
        )
        return (completion_rate * 0.5 + adaptation_rate * 0.5)
    
    def handle_api_call(
        self,
        task_id: str,
        api_type: str,  # "rest" or "graphql"
        endpoint_or_query: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Agent attempts to call an API to complete an executive task.
        Returns the API response.
        """
        if not self.mock_api_server:
            return {"error": "Mock API server not enabled", "status": 500}
        
        data = data or {}
        
        try:
            if api_type == "rest":
                response = self.mock_api_server.call_rest(endpoint_or_query, data)
            elif api_type == "graphql":
                response = self.mock_api_server.call_graphql(endpoint_or_query)
            else:
                return {"error": f"Unknown API type: {api_type}", "status": 400}
            
            return response.to_dict()
        except Exception as e:
            return {"error": str(e), "status": 500}
    
    def get_api_status(self) -> dict[str, Any]:
        """Get the current status of all API operations."""
        if self.mock_api_server:
            return self.mock_api_server.get_api_status_report()
        return {"enabled": False}
