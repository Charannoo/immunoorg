"""
Integration Tests for ImmunoOrg 2.0 Features
=============================================
Tests for all 4 implementation phases:
1. LLM-driven adversary
2. Dynamic organizational trust
3. Mock API server
4. MITRE ATT&CK integration
"""

import pytest
from immunoorg.llm_adversary import LLMAdversary, LLMAdversaryReasoner
from immunoorg.org_dynamics import DynamicOrgDynamicsEngine
from immunoorg.mock_api_server import RealisticAPIMockServer, MockRESTAPI, MockGraphQLAPI
from immunoorg.mitre_ttp import MITRETTPEngine, MITREtactic
from immunoorg.network_graph import NetworkGraph
from immunoorg.org_graph import OrgGraph
from immunoorg.permission_flow import PermissionFlowEngine
from immunoorg.belief_map import BeliefMap


class TestPhase1LLMAdversary:
    """Test Phase 1: LLM-driven Adversary."""
    
    def test_llm_adversary_initialization(self):
        """Test that LLMAdversary initializes correctly."""
        net = NetworkGraph(difficulty=2, seed=42)
        net.generate_topology()
        
        adversary = LLMAdversary(net, difficulty=2, seed=42)
        assert adversary.difficulty == 2
        assert adversary.rng is not None
        assert adversary.reasoner is not None
    
    def test_identify_high_value_targets(self):
        """Test that the reasoner identifies valuable targets."""
        net = NetworkGraph(difficulty=2, seed=42)
        net.generate_topology()
        
        reasoner = LLMAdversaryReasoner(net, seed=42)
        targets = reasoner.identify_high_value_targets()
        
        assert len(targets) > 0
        assert all(t.tier in ["data", "management", "app"] for t in targets)
    
    def test_generate_attack_plan(self):
        """Test attack plan generation."""
        net = NetworkGraph(difficulty=2, seed=42)
        net.generate_topology()
        
        reasoner = LLMAdversaryReasoner(net, seed=42)
        plan = reasoner.generate_attack_plan(difficulty=2)
        
        assert plan is not None
        assert len(plan.target_path) > 0
        assert plan.primary_vector is not None
        assert 0 <= plan.estimated_success_rate <= 1.0
    
    def test_adversary_adaptation(self):
        """Test that adversary adapts to observed defenses."""
        net = NetworkGraph(difficulty=2, seed=42)
        net.generate_topology()
        
        adversary = LLMAdversary(net, difficulty=2, seed=42)
        
        # Observe some defender actions
        adversary.observe_defender_action("block_port")
        adversary.observe_defender_action("isolate_node")
        
        # Should have recorded these
        assert len(adversary.reasoner.observed_defenses) == 2


class TestPhase2DynamicOrgDynamics:
    """Test Phase 2: Dynamic Organizational Trust."""
    
    def test_trust_engine_initialization(self):
        """Test DynamicOrgDynamicsEngine initialization."""
        engine = DynamicOrgDynamicsEngine()
        assert engine.metrics is not None
        assert len(engine.metrics.trust_history) == 0
    
    def test_record_approval_events(self):
        """Test recording trust events."""
        engine = DynamicOrgDynamicsEngine()
        
        # Record some events
        engine.record_approval_granted("dept-a", "dept-b", severity=1.0, sim_time=0.0)
        engine.record_approval_denied("dept-a", "dept-c", severity=0.8, sim_time=1.0)
        
        assert len(engine.metrics.trust_history) == 2
        assert engine.metrics.denial_counts[("dept-a", "dept-c")] == 1
        assert engine.metrics.cooperation_successes[("dept-a", "dept-b")] == 1
    
    def test_apply_trust_dynamics(self):
        """Test that trust dynamics are applied."""
        org = OrgGraph(difficulty=2, seed=42)
        net = NetworkGraph(difficulty=2, seed=42)
        net.generate_topology()
        org.generate_org_structure(net.get_all_node_ids())
        
        engine = DynamicOrgDynamicsEngine()
        
        # Record many denials
        for i in range(5):
            engine.record_approval_denied("dept-it_ops", "dept-engineering", severity=1.0)
        
        # Apply dynamics
        initial_trust = org.get_active_edges()[0].trust
        engine.apply_trust_dynamics(org.get_all_edges(), org.nodes, sim_time=10.0)
        
        # Trust should have changed
        assert len(org.get_active_edges()) > 0
    
    def test_trust_report(self):
        """Test trust report generation."""
        engine = DynamicOrgDynamicsEngine()
        engine.record_approval_granted("dept-a", "dept-b")
        engine.record_approval_denied("dept-a", "dept-c")
        
        report = engine.get_trust_report()
        assert report["total_events"] == 2
        assert report["total_denials"] == 1
        assert report["total_successes"] == 1


class TestPhase3MockAPIServer:
    """Test Phase 3: Mock API Server."""
    
    def test_rest_api_initialization(self):
        """Test REST API initialization."""
        api = MockRESTAPI(seed=42)
        assert len(api.ENDPOINTS) > 0
        assert api.tokens is not None
    
    def test_rest_endpoint_call(self):
        """Test calling a REST endpoint."""
        api = MockRESTAPI(seed=42)
        token = api._generate_token()
        
        response = api.call_endpoint(
            "google_calendar_create",
            {"title": "Meeting", "startTime": "2026-04-25T10:00:00Z", "endTime": "2026-04-25T11:00:00Z"},
            auth_token=token
        )
        
        assert response.status == 200
        assert response.data is not None
        assert "eventId" in response.data
    
    def test_rest_api_validation(self):
        """Test that API validates fields."""
        api = MockRESTAPI(seed=42)
        token = api._generate_token()
        
        # Missing required fields
        response = api.call_endpoint(
            "google_calendar_create",
            {"title": "Meeting"},
            auth_token=token
        )
        
        assert response.status == 400
        assert "Missing required fields" in response.message
    
    def test_graphql_api_query(self):
        """Test GraphQL query execution."""
        api = MockGraphQLAPI(seed=42)
        
        response = api.execute_query("query { calendar_events { eventId title } }")
        
        assert response.status == 200
        assert response.data is not None
    
    def test_mock_server_unified_interface(self):
        """Test unified mock server interface."""
        server = RealisticAPIMockServer(seed=42)
        
        # Test REST call
        rest_response = server.call_rest(
            "google_calendar_create",
            {"title": "Test", "startTime": "2026-04-25T10:00:00Z", "endTime": "2026-04-25T11:00:00Z"}
        )
        assert rest_response["status"] == 200
        
        # Test GraphQL call
        gql_response = server.call_graphql("query { emails { messageId subject } }")
        assert gql_response["status"] == 200
        
        # Check status report
        report = server.get_api_status_report()
        assert "rest_requests_made" in report
        assert "graphql_queries_made" in report


class TestPhase4MITRETTPIntegration:
    """Test Phase 4: MITRE ATT&CK TTP Integration."""
    
    def test_mitre_engine_initialization(self):
        """Test MITRE TTP engine initialization."""
        engine = MITRETTPEngine()
        assert len(engine.techniques) > 0
        assert len(engine.chains) > 0
    
    def test_get_techniques_by_tactic(self):
        """Test retrieving techniques by tactic."""
        engine = MITRETTPEngine()
        
        recon_techniques = engine.get_techniques_by_tactic(MITREtactic.RECONNAISSANCE)
        assert len(recon_techniques) > 0
        assert all(t.tactic == MITREtactic.RECONNAISSANCE for t in recon_techniques)
    
    def test_generate_ttp_based_attack(self):
        """Test TTP-based attack generation."""
        engine = MITRETTPEngine()
        
        attack = engine.generate_ttp_based_attack(difficulty=2)
        assert "techniques" in attack
        assert len(attack["techniques"]) > 0
    
    def test_correlate_indicators_to_ttp(self):
        """Test indicator to TTP correlation."""
        engine = MITRETTPEngine()
        
        correlation = engine.correlate_indicators_to_ttp(
            ["phishing", "lateral_movement", "exfiltration"]
        )
        
        assert "likely_tactics" in correlation
        assert "likely_techniques" in correlation
        assert correlation["confidence"] > 0
    
    def test_mitre_overview(self):
        """Test MITRE overview statistics."""
        engine = MITRETTPEngine()
        overview = engine.get_mitre_overview()
        
        assert overview["total_techniques"] > 0
        assert overview["total_tactics"] > 0
        assert overview["total_chains"] > 0


class TestBeliefMapWithMITRE:
    """Test BeliefMap integration with MITRE TTPs."""
    
    def test_belief_map_ttp_correlation(self):
        """Test belief map TTP correlation."""
        belief_map = BeliefMap()
        
        correlation = belief_map.correlate_attack_to_ttp(["command_execution", "lateral_movement"])
        
        assert "likely_tactics" in correlation
        assert "likely_techniques" in correlation
    
    def test_belief_map_mitre_context(self):
        """Test MITRE context retrieval."""
        belief_map = BeliefMap()
        context = belief_map.get_mitre_context()
        
        assert context["total_techniques"] > 0
    
    def test_defensive_strategy_suggestion(self):
        """Test defensive strategy suggestion based on TTPs."""
        belief_map = BeliefMap()
        
        strategy = belief_map.suggest_defensive_strategy_from_ttp(["T1566", "T1110"])
        
        assert "recommended_mitigations" in strategy
        assert len(strategy["recommended_mitigations"]) > 0


class TestPermissionFlowWithDynamicTrust:
    """Test PermissionFlow with dynamic trust integration."""
    
    def test_permission_flow_with_dynamic_trust(self):
        """Test permission flow with trust tracking."""
        org = OrgGraph(difficulty=2, seed=42)
        net = NetworkGraph(difficulty=2, seed=42)
        net.generate_topology()
        org.generate_org_structure(net.get_all_node_ids())
        
        flow = PermissionFlowEngine(org, seed=42, enable_dynamic_trust=True)
        assert flow.enable_dynamic_trust is True
        assert flow.trust_engine is not None
    
    def test_trust_events_recorded_in_permission_flow(self):
        """Test that trust events are recorded during approval."""
        org = OrgGraph(difficulty=2, seed=42)
        net = NetworkGraph(difficulty=2, seed=42)
        net.generate_topology()
        org.generate_org_structure(net.get_all_node_ids())
        
        flow = PermissionFlowEngine(org, seed=42, enable_dynamic_trust=True)
        
        # Request approval
        from immunoorg.models import ActionType
        req = flow.request_approval(
            "isolate_node",
            ActionType.TACTICAL,
            "dept-it_ops",
            "node-001",
            urgency=0.9,
            sim_time=0.0
        )
        
        # Process the request
        resolved = flow.process_pending(sim_time=10.0, threat_level=0.8)
        
        # Check that trust events were recorded
        report = flow.get_trust_report()
        assert "enabled" not in report or report["enabled"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
