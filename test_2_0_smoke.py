import sys
sys.path.insert(0, '.')

from immunoorg.environment import ImmunoOrgEnvironment
from immunoorg.models import ImmunoAction, ActionType, TacticalAction, DiagnosticAction, StrategicAction

print('=== ImmunoOrg 2.0 End-to-End Smoke Test ===')

env = ImmunoOrgEnvironment(difficulty=1, seed=42)
obs = env.reset()
print(f'RESET OK | Phase: {obs.current_phase.value} | Nodes: {len(obs.visible_nodes)}')

# Step 1: Scan logs
a1 = ImmunoAction(action_type=ActionType.TACTICAL, tactical_action=TacticalAction.SCAN_LOGS, target='web-server-01', reasoning='Detection phase scan.')
obs, r1, done = env.step(a1)
print(f'STEP 1 (scan_logs)    | reward={r1:+.3f} | pipeline_integrity={env._last_pipeline_integrity:.2f}')

# Step 2: Start migration (new 2.0 action)
a2 = ImmunoAction(action_type=ActionType.TACTICAL, tactical_action=TacticalAction.START_MIGRATION, target='', reasoning='Initiate 50-step MTD workflow.')
obs, r2, done = env.step(a2)
print(f'STEP 2 (start_migr.)  | reward={r2:+.3f} | migration active={env.migration_engine.is_active}')

# Step 3: Check executive context (new 2.0 action)
a3 = ImmunoAction(action_type=ActionType.DIAGNOSTIC, diagnostic_action=DiagnosticAction.CHECK_EXECUTIVE_CONTEXT, target='', reasoning='Check dual-mode state.')
obs, r3, done = env.step(a3)
print(f'STEP 3 (exec ctx)     | reward={r3:+.3f} | exec tasks={len(env.executive_context.state.active_tasks)}')

# Step 4: Deploy honeypot
a4 = ImmunoAction(action_type=ActionType.TACTICAL, tactical_action=TacticalAction.DEPLOY_HONEYPOT, target='', reasoning='Deploy honeytoken infrastructure.')
obs, r4, done = env.step(a4)
print(f'STEP 4 (honeypot)     | reward={r4:+.3f} | honeypots={env.migration_engine.state.active_honeypots}')

# Run 10 more steps
for i in range(10):
    actions = [
        ImmunoAction(action_type=ActionType.TACTICAL, tactical_action=TacticalAction.ISOLATE_NODE, target='db-server-01', reasoning='Contain.'),
        ImmunoAction(action_type=ActionType.DIAGNOSTIC, diagnostic_action=DiagnosticAction.IDENTIFY_SILO, target='', reasoning='Find silos.'),
        ImmunoAction(action_type=ActionType.STRATEGIC, strategic_action=StrategicAction.ESTABLISH_DEVSECOPS, target='dept-security', secondary_target='dept-engineering', reasoning='Fix root cause.'),
    ]
    obs, r, done = env.step(actions[i % 3])
    if done:
        break

print(f'10 STEPS DONE | cumulative_reward={env.state.cumulative_reward:.3f}')

# War Room
wr = env.war_room
transcript = wr.get_latest_transcript().encode('ascii', 'replace').decode('ascii')
print(f'WAR ROOM debates={len(wr.debate_history)} | transcript={transcript[:80]}...')

# Pipeline Mesh
mesh = env.devsecops_mesh
blocked = sum(1 for e in mesh.all_events if e.severity.value == "blocked")
print(f'MESH events={len(mesh.all_events)} | blocked={blocked} | avg_integrity={mesh.get_pipeline_integrity_avg():.2f}')

# Migration
mp = env.migration_engine.get_progress()
print(f'MIGRATION step={mp["current_step"]}/{mp["total_steps"]} | phase={mp["current_phase"]} | honeytokens={mp["honeytoken_activations"]}')

# Reward Tracks
tracks = env.reward_calc.get_track_scores()
print('REWARD TRACKS:', {k: f"{v:+.3f}" for k, v in tracks.items()})

# Patronus
patronus = env.executive_context.get_patronus_score()
print(f'PATRONUS SCORE: {patronus:.3f}')

# Self-improvement + forensics
from immunoorg.self_improvement import TimeTravelForensics
ttf = TimeTravelForensics()
kc = ttf.reconstruct_kill_chain(["sql_injection on db-server-01", "lateral move to app-server-02"], 50.0)
patch = ttf.generate_patch_candidate(kc["root_cause"], "VULN-001", 55.0)
ttf.add_to_training_dataset(patch, kc)
root = kc['root_cause'][:40].encode('ascii','replace').decode('ascii')
print(f'FORENSICS: root_cause={root} | patch_quality={patch.quality_score:.3f} | in_training={patch.added_to_training}')

print()
print('=== ALL 2.0 SYSTEMS OPERATIONAL ===')
