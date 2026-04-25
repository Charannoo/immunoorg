#!/usr/bin/env python3
"""
ImmunoOrg 2.0 Smoke Tests
=========================
Quick validation of all 4 implementation phases without pytest.
"""

import sys
import traceback


def test_phase1_llm_adversary():
    """Test Phase 1: LLM-driven Adversary."""
    print("\n" + "="*70)
    print("PHASE 1: LLM-Driven Adversary")
    print("="*70)
    
    try:
        from immunoorg.llm_adversary import LLMAdversary
        from immunoorg.network_graph import NetworkGraph
        
        print("✓ Imports successful")
        
        # Create network
        net = NetworkGraph(difficulty=2, seed=42)
        net.generate_topology()
        print(f"✓ Network generated: {len(net.get_all_nodes())} nodes")
        
        # Create LLM adversary
        adversary = LLMAdversary(net, difficulty=2, seed=42)
        print(f"✓ LLM Adversary initialized")
        
        # Test attack generation
        attack = adversary.generate_next_attack(sim_time=0.0)
        print(f"✓ Attack generated: {attack.vector.value} → {attack.target_node}")
        
        # Test adaptation
        adversary.observe_defender_action("block_port")
        print(f"✓ Adversary adapted to defense")
        
        # Get rationale
        rationale = adversary.get_attack_rationale()
        print(f"✓ Rationale: {rationale[:60]}...")
        
        return True
    except Exception as e:
        print(f"✗ Phase 1 FAILED: {e}")
        traceback.print_exc()
        return False


def test_phase2_dynamic_trust():
    """Test Phase 2: Dynamic Organizational Trust."""
    print("\n" + "="*70)
    print("PHASE 2: Dynamic Organizational Trust")
    print("="*70)
    
    try:
        from immunoorg.org_dynamics import DynamicOrgDynamicsEngine
        from immunoorg.org_graph import OrgGraph
        from immunoorg.network_graph import NetworkGraph
        
        print("✓ Imports successful")
        
        # Create org and network
        net = NetworkGraph(difficulty=2, seed=42)
        net.generate_topology()
        org = OrgGraph(difficulty=2, seed=42)
        org.generate_org_structure(net.get_all_node_ids())
        print(f"✓ Org structure created: {len(org.get_all_nodes())} departments")
        
        # Create trust engine
        engine = DynamicOrgDynamicsEngine()
        print(f"✓ Trust engine initialized")
        
        # Record events
        engine.record_approval_granted("dept-it_ops", "dept-engineering", sim_time=0.0)
        engine.record_approval_denied("dept-security", "dept-engineering", severity=1.0, sim_time=1.0)
        print(f"✓ Trust events recorded: {len(engine.metrics.trust_history)} events")
        
        # Apply dynamics
        edges_before = len(org.get_active_edges())
        engine.apply_trust_dynamics(org.get_all_edges(), org.nodes, sim_time=10.0)
        edges_after = len(org.get_active_edges())
        print(f"✓ Trust dynamics applied: {edges_before} → {edges_after} edges")
        
        # Get report
        report = engine.get_trust_report()
        print(f"✓ Report: {report['total_denials']} denials, {report['total_successes']} approvals")
        
        return True
    except Exception as e:
        print(f"✗ Phase 2 FAILED: {e}")
        traceback.print_exc()
        return False


def test_phase3_mock_apis():
    """Test Phase 3: Mock API Server."""
    print("\n" + "="*70)
    print("PHASE 3: Mock REST/GraphQL API Server")
    print("="*70)
    
    try:
        from immunoorg.mock_api_server import RealisticAPIMockServer
        
        print("✓ Imports successful")
        
        # Create server
        server = RealisticAPIMockServer(seed=42)
        print(f"✓ Mock API server initialized")
        
        # Test REST call
        rest_response = server.call_rest(
            "google_calendar_create",
            {
                "title": "Board Meeting",
                "startTime": "2026-04-25T10:00:00Z",
                "endTime": "2026-04-25T11:00:00Z",
            }
        )
        print(f"✓ REST call: status={rest_response['status']}, event_id={rest_response['data'].get('id')}")
        
        # Test GraphQL call
        gql_response = server.call_graphql("query { calendar_events { eventId title } }")
        print(f"✓ GraphQL call: status={gql_response['status']}")
        
        # Get status report
        report = server.get_api_status_report()
        print(f"✓ Status report: {report['rest_requests_made']} REST calls, {report['graphql_queries_made']} GraphQL calls")
        
        return True
    except Exception as e:
        print(f"✗ Phase 3 FAILED: {e}")
        traceback.print_exc()
        return False


def test_phase4_mitre_ttp():
    """Test Phase 4: MITRE ATT&CK Integration."""
    print("\n" + "="*70)
    print("PHASE 4: MITRE ATT&CK TTP Integration")
    print("="*70)
    
    try:
        from immunoorg.mitre_ttp import MITRETTPEngine, MITREtactic
        from immunoorg.belief_map import BeliefMap
        
        print("✓ Imports successful")
        
        # Create TTP engine
        engine = MITRETTPEngine()
        print(f"✓ MITRE TTP engine initialized: {len(engine.techniques)} techniques, {len(engine.chains)} chains")
        
        # Test technique retrieval
        recon = engine.get_techniques_by_tactic(MITREtactic.RECONNAISSANCE)
        print(f"✓ Reconnaissance techniques: {len(recon)}")
        
        # Test attack generation
        attack = engine.generate_ttp_based_attack(difficulty=2)
        print(f"✓ TTP-based attack: {attack.get('chain_name', 'Random techniques')}")
        
        # Test correlation
        correlation = engine.correlate_indicators_to_ttp(["phishing", "lateral_movement"])
        print(f"✓ Indicator correlation: {len(correlation['likely_techniques'])} techniques found")
        
        # Test BeliefMap integration
        belief = BeliefMap()
        ttp_correlation = belief.correlate_attack_to_ttp(["credential_access", "command_execution"])
        print(f"✓ BeliefMap TTP analysis: {len(ttp_correlation['likely_techniques'])} likely techniques")
        
        # Test defensive strategy
        strategy = belief.suggest_defensive_strategy_from_ttp(["T1566", "T1110"])
        print(f"✓ Defensive strategies: {len(strategy['recommended_mitigations'])} mitigations")
        
        # Get overview
        overview = engine.get_mitre_overview()
        print(f"✓ MITRE overview: {overview['total_tactics']} tactics, max difficulty {overview['max_difficulty']}")
        
        return True
    except Exception as e:
        print(f"✗ Phase 4 FAILED: {e}")
        traceback.print_exc()
        return False


def test_integration():
    """Test integration of all phases."""
    print("\n" + "="*70)
    print("INTEGRATION TEST: All Phases Together")
    print("="*70)
    
    try:
        from immunoorg.network_graph import NetworkGraph
        from immunoorg.org_graph import OrgGraph
        from immunoorg.permission_flow import PermissionFlowEngine
        from immunoorg.llm_adversary import LLMAdversary
        from immunoorg.org_dynamics import DynamicOrgDynamicsEngine
        from immunoorg.belief_map import BeliefMap
        from immunoorg.mock_api_server import RealisticAPIMockServer
        
        print("✓ All imports successful")
        
        # Setup full environment
        net = NetworkGraph(difficulty=2, seed=42)
        net.generate_topology()
        org = OrgGraph(difficulty=2, seed=42)
        org.generate_org_structure(net.get_all_node_ids())
        
        print(f"✓ Environment setup: {len(net.get_all_nodes())} network nodes, {len(org.get_all_nodes())} departments")
        
        # Setup all engines
        adversary = LLMAdversary(net, difficulty=2, seed=42)
        permission_flow = PermissionFlowEngine(org, seed=42, enable_dynamic_trust=True)
        belief_map = BeliefMap()
        api_server = RealisticAPIMockServer(seed=42)
        
        print(f"✓ All engines initialized")
        
        # Simulate a turn
        attack = adversary.generate_next_attack(sim_time=0.0)
        print(f"✓ Attack generated: {attack.vector.value}")
        
        from immunoorg.models import ActionType
        approval = permission_flow.request_approval(
            "isolate_node", ActionType.TACTICAL, "dept-it_ops", attack.target_node, 0.8, 0.0
        )
        print(f"✓ Approval request created")
        
        resolved = permission_flow.process_pending(sim_time=5.0, threat_level=0.7)
        print(f"✓ Approvals processed: {len(resolved)} resolved")
        
        api_response = api_server.call_rest("outlook_email_send", {
            "subject": "Incident Response Update",
            "body": "Attack contained",
            "to": "team@company.com"
        })
        print(f"✓ API call made: {api_response['status']}")
        
        ttp_analysis = belief_map.correlate_attack_to_ttp(["lateral_movement", "credential_access"])
        print(f"✓ TTP analysis: {len(ttp_analysis['likely_techniques'])} techniques")
        
        print(f"✓ Full integration test PASSED")
        
        return True
    except Exception as e:
        print(f"✗ Integration test FAILED: {e}")
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n")
    print("+=" + "="*68 + "=+")
    print("|" + " "*68 + "|")
    print("|" + "  ImmunoOrg 2.0 - Smoke Test Suite".center(68) + "|")
    print("|" + " "*68 + "|")
    print("+=" + "="*68 + "=+")
    
    results = {
        "Phase 1: LLM-Driven Adversary": test_phase1_llm_adversary(),
        "Phase 2: Dynamic Org Trust": test_phase2_dynamic_trust(),
        "Phase 3: Mock API Server": test_phase3_mock_apis(),
        "Phase 4: MITRE TTP Integration": test_phase4_mitre_ttp(),
        "Integration Test": test_integration(),
    }
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name}: {status}")
    
    total_passed = sum(1 for v in results.values() if v)
    total_tests = len(results)
    
    print("\n" + "="*70)
    print(f"Result: {total_passed}/{total_tests} tests passed")
    print("="*70)
    
    return 0 if total_passed == total_tests else 1


if __name__ == "__main__":
    sys.exit(main())
