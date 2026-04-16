
from .semantic_ir import SemanticDiagram, SemanticEdge, SemanticGroup, SemanticNode


def workflow_example() -> SemanticDiagram:
    nodes = [
        SemanticNode('start', 'Start review', 'terminator', 'workflow', row_hint=0, col_hint=0, meta={'role': 'start'}),
        SemanticNode('validate', 'Validate invoice lines and vendor coding', 'process', 'workflow', row_hint=0, col_hint=1, meta={'role': 'validate'}),
        SemanticNode('stock', 'High-risk supplier or amount threshold reached?', 'decision', 'workflow', row_hint=0, col_hint=2, meta={'role': 'decision'}),
        SemanticNode('reserve', 'Request approver sign-off', 'process', 'workflow', row_hint=-1, col_hint=3, meta={'role': 'approve'}),
        SemanticNode('notify', 'Send back for correction', 'process', 'workflow', row_hint=1, col_hint=3, meta={'role': 'reject'}),
        SemanticNode('charge', 'Post payable entry', 'process', 'workflow', row_hint=-1, col_hint=4, meta={'role': 'post'}),
        SemanticNode('done', 'Invoice booked', 'terminator', 'workflow', row_hint=-1, col_hint=5, meta={'role': 'done'}),
    ]
    edges = [
        SemanticEdge('e0', 'start', 'validate'),
        SemanticEdge('e1', 'validate', 'stock'),
        SemanticEdge('e2', 'stock', 'reserve', label='yes'),
        SemanticEdge('e3', 'stock', 'notify', label='no'),
        SemanticEdge('e4', 'reserve', 'charge'),
        SemanticEdge('e5', 'charge', 'done'),
        SemanticEdge('e6', 'notify', 'validate', label='retry', dashed=True),
    ]
    return SemanticDiagram('workflow_invoice_review', 'Invoice review workflow', 'workflow', nodes, edges)


def static_structure_example() -> SemanticDiagram:
    nodes = [
        SemanticNode('ctrl', 'BillingFacade', 'class', 'static_structure', row_hint=0, col_hint=0, methods=['+ createInvoice(cmd)', '+ cancelInvoice(id)'], meta={'role': 'controller'}),
        SemanticNode('svc', 'InvoiceService', 'class', 'static_structure', row_hint=0, col_hint=1, methods=['+ priceDraft()', '+ finalize()'], meta={'role': 'service'}),
        SemanticNode('repo', 'PricingPort', 'interface', 'static_structure', row_hint=1, col_hint=1, methods=['+ quote(orderCtx)'], meta={'role': 'port'}),
        SemanticNode('jwt', 'EventPublisher', 'class', 'static_structure', row_hint=0, col_hint=2, methods=['+ publish(evt)'], meta={'role': 'publisher'}),
        SemanticNode('db', 'InvoiceAggregate', 'class', 'static_structure', row_hint=1, col_hint=2, attrs=['invoice_id', 'status', 'net_amount'], meta={'role': 'aggregate'}),
    ]
    edges = [
        SemanticEdge('e0', 'ctrl', 'svc', label='delegates', dashed=True),
        SemanticEdge('e1', 'svc', 'repo', label='quotes', dashed=True),
        SemanticEdge('e2', 'svc', 'jwt', label='publishes', dashed=True),
        SemanticEdge('e3', 'repo', 'db', label='feeds'),
    ]
    return SemanticDiagram('static_billing', 'Billing static structure', 'static_structure', nodes, edges)


def component_cluster_example() -> SemanticDiagram:
    nodes = [
        SemanticNode('web', 'Ops Console', 'component', 'component_cluster', row_hint=1, col_hint=0, group='ui', meta={'role': 'entry'}),
        SemanticNode('api', 'API Edge', 'component', 'component_cluster', row_hint=0, col_hint=1, group='control', meta={'role': 'gateway'}),
        SemanticNode('auth', 'Alert Engine', 'component', 'component_cluster', row_hint=2, col_hint=1, group='control', meta={'role': 'alerts'}),
        SemanticNode('order', 'Metrics Service', 'component', 'component_cluster', row_hint=0, col_hint=2, group='domain', meta={'role': 'metrics'}),
        SemanticNode('pay', 'Tracing Service', 'component', 'component_cluster', row_hint=2, col_hint=2, group='domain', meta={'role': 'tracing'}),
        SemanticNode('db', 'Telemetry Store', 'database', 'component_cluster', row_hint=1, col_hint=3, group='infra', meta={'role': 'store'}),
    ]
    groups = [
        SemanticGroup('ui', 'UI', 'frame', ['web']),
        SemanticGroup('control', 'Control Plane', 'frame', ['api', 'auth']),
        SemanticGroup('domain', 'Observability Domain', 'frame', ['order', 'pay']),
        SemanticGroup('infra', 'Infrastructure', 'frame', ['db']),
    ]
    edges = [
        SemanticEdge('e0', 'web', 'api', label='HTTPS'),
        SemanticEdge('e1', 'api', 'auth', label='Rules', dashed=True),
        SemanticEdge('e2', 'api', 'order', label='gRPC'),
        SemanticEdge('e3', 'order', 'pay', label='spans', dashed=True),
        SemanticEdge('e4', 'auth', 'db', label='alerts'),
        SemanticEdge('e5', 'order', 'db', label='metrics'),
        SemanticEdge('e6', 'pay', 'db', label='traces'),
    ]
    return SemanticDiagram('components_observability', 'Observability component cluster', 'component_cluster', nodes, edges, groups=groups)


def technical_blueprint_example(patched: bool = False) -> SemanticDiagram:
    nodes = [
        SemanticNode('plc', 'Robot PLC', 'device', 'technical_blueprint', row_hint=1, col_hint=1, group='cab', meta={'role': 'controller'}),
        SemanticNode('servo', 'Conveyor Drive', 'device', 'technical_blueprint', row_hint=0, col_hint=2, group='cab', meta={'role': 'drive'}),
        SemanticNode('io', 'Remote Safety IO', 'device', 'technical_blueprint', row_hint=2, col_hint=2, group='cab', meta={'role': 'io'}),
        SemanticNode('hmi', 'Operator Panel', 'device', 'technical_blueprint', row_hint=1, col_hint=0, meta={'role': 'panel'}),
        SemanticNode('motor', 'Conveyor Motor', 'device', 'technical_blueprint', row_hint=0, col_hint=4, meta={'role': 'actuator'}),
        SemanticNode('sensor', 'Barcode Camera', 'device', 'technical_blueprint', row_hint=2, col_hint=4, meta={'role': 'sensor'}),
        SemanticNode('tb', 'TITLE BLOCK', 'title_block', 'technical_blueprint', row_hint=3, col_hint=4, meta={'role': 'title_block'}),
    ]
    groups = [SemanticGroup('cab', 'Packaging Cell Cabinet', 'frame', ['plc', 'servo', 'io'])]
    keepouts = [(760, 345, 1180, 520)]
    edges = [
        SemanticEdge('e0', 'hmi', 'plc', label='Ops'),
        SemanticEdge('e1', 'plc', 'servo', label='Fieldbus'),
        SemanticEdge('e2', 'servo', 'motor', label='Power'),
        SemanticEdge('e3', 'plc', 'io', label='Safety'),
        SemanticEdge('e4', 'io', 'sensor', label='Trigger'),
    ]
    if patched:
        nodes.append(SemanticNode('insp', 'Vision PC', 'device', 'technical_blueprint', row_hint=1, col_hint=3, group='cab', meta={'role': 'vision'}))
        edges.extend([
            SemanticEdge('e5', 'plc', 'insp', label='Quality'),
            SemanticEdge('e6', 'insp', 'sensor', label='GigE'),
        ])
    return SemanticDiagram('blueprint_packaging_patch' if patched else 'blueprint_packaging', 'Packaging cell blueprint', 'technical_blueprint', nodes, edges, groups=groups, keepouts=keepouts)


def istar_example() -> SemanticDiagram:
    nodes = [
        SemanticNode('actor', 'Subscription Actor', 'task', 'istar', row_hint=1, col_hint=0, group='actor_boundary', meta={'role': 'actor'}),
        SemanticNode('goal1', 'Recover Failed Renewal', 'goal', 'istar', row_hint=0, col_hint=1, group='actor_boundary', meta={'role': 'goal_primary'}),
        SemanticNode('task1', 'Retry Card Charge', 'task', 'istar', row_hint=1, col_hint=1, group='actor_boundary', meta={'role': 'task_retry'}),
        SemanticNode('res1', 'Billing Gateway', 'resource', 'istar', row_hint=2, col_hint=1, group='actor_boundary', meta={'role': 'resource_gateway'}),
        SemanticNode('soft1', 'Reduce Churn', 'softgoal', 'istar', row_hint=0, col_hint=2, group='actor_boundary', meta={'role': 'softgoal'}),
        SemanticNode('goal2', 'Fast Recovery', 'goal', 'istar', row_hint=2, col_hint=2, group='actor_boundary', meta={'role': 'goal_secondary'}),
    ]
    groups = [SemanticGroup('actor_boundary', 'Subscription Management Actor', 'frame', [n.id for n in nodes])]
    edges = [
        SemanticEdge('e0', 'goal1', 'task1', label='means-end'),
        SemanticEdge('e1', 'task1', 'res1', label='needs'),
        SemanticEdge('e2', 'task1', 'soft1', label='helps'),
        SemanticEdge('e3', 'res1', 'goal2', label='supports'),
    ]
    return SemanticDiagram('istar_subscription', 'iStar renewal model', 'istar', nodes, edges, groups=groups)


def architecture_flow_example() -> SemanticDiagram:
    nodes = [
        SemanticNode('local', 'Local File\nRepository', 'process', 'architecture_flow', row_hint=0, col_hint=0, meta={'role': 'repo_local'}),
        SemanticNode('build', 'Gradle Build', 'process', 'architecture_flow', row_hint=1, col_hint=0, meta={'role': 'build'}),
        SemanticNode('cache', 'Gradle Cache', 'process', 'architecture_flow', row_hint=2, col_hint=0, meta={'role': 'cache'}),
        SemanticNode('network', 'Network', 'network', 'architecture_flow', row_hint=1, col_hint=1, meta={'role': 'hub'}),
        SemanticNode('maven', 'Maven\nRepository', 'process', 'architecture_flow', row_hint=0, col_hint=2, meta={'role': 'maven'}),
        SemanticNode('ivy', 'Ivy\nRepository', 'process', 'architecture_flow', row_hint=2, col_hint=2, meta={'role': 'ivy'}),
    ]
    edges = [
        SemanticEdge('e0', 'build', 'local', label='access artifacts'),
        SemanticEdge('e1', 'cache', 'build', label='access artifacts'),
        SemanticEdge('e2', 'build', 'cache', label='store artifacts'),
        SemanticEdge('e3', 'build', 'network', label='download artifacts'),
        SemanticEdge('e4', 'network', 'maven', label=''),
        SemanticEdge('e5', 'network', 'ivy', label=''),
    ]
    return SemanticDiagram('architecture_gradle_repos', 'Artifact resolution architecture', 'architecture_flow', nodes, edges)


def llm_layered_architecture_example() -> SemanticDiagram:
    nodes = [
        SemanticNode('client', 'Client Apps', 'process', 'layered_architecture', row_hint=0, col_hint=0, group='User Entry'),
        SemanticNode('gateway', 'API Gateway', 'process', 'layered_architecture', row_hint=1, col_hint=0, group='Ingress'),
        SemanticNode('orchestrator', 'Agent\nOrchestrator', 'process', 'layered_architecture', row_hint=2, col_hint=0, group='Orchestration'),
        SemanticNode('retrieval', 'Retrieval Layer', 'process', 'layered_architecture', row_hint=3, col_hint=0, group='Retrieval'),
        SemanticNode('serving', 'Model Serving', 'process', 'layered_architecture', row_hint=4, col_hint=0, group='Inference'),
        SemanticNode('safety', 'Safety\nGuardrails', 'process', 'layered_architecture', row_hint=5, col_hint=0, group='Safety & Evaluation'),
        SemanticNode('obs', 'Observability', 'process', 'layered_architecture', row_hint=6, col_hint=0, group='Monitoring'),
        SemanticNode('store', 'Storage', 'database', 'layered_architecture', row_hint=7, col_hint=0, group='Data Stores'),
        SemanticNode('eval', 'Evaluation Hub', 'process', 'layered_architecture', row_hint=5, col_hint=1, group='Safety & Evaluation'),
    ]
    groups = [
        SemanticGroup('User Entry', 'User Entry', 'frame', ['client']),
        SemanticGroup('Ingress', 'Ingress', 'frame', ['gateway']),
        SemanticGroup('Orchestration', 'Orchestration', 'frame', ['orchestrator']),
        SemanticGroup('Retrieval', 'Retrieval', 'frame', ['retrieval']),
        SemanticGroup('Inference', 'Inference', 'frame', ['serving']),
        SemanticGroup('Safety & Evaluation', 'Safety & Evaluation', 'frame', ['safety', 'eval']),
        SemanticGroup('Monitoring', 'Monitoring', 'frame', ['obs']),
        SemanticGroup('Data Stores', 'Data Stores', 'frame', ['store']),
    ]
    edges = [
        SemanticEdge('e0', 'client', 'gateway', label=''),
        SemanticEdge('e1', 'gateway', 'orchestrator', label=''),
        SemanticEdge('e2', 'orchestrator', 'retrieval', label=''),
        SemanticEdge('e3', 'orchestrator', 'serving', label=''),
        SemanticEdge('e4', 'retrieval', 'store', label=''),
        SemanticEdge('e5', 'serving', 'safety', label=''),
        SemanticEdge('e6', 'safety', 'eval', label=''),
        SemanticEdge('e7', 'safety', 'gateway', label='', dashed=True),
        SemanticEdge('e8', 'obs', 'store', label=''),
        SemanticEdge('e9', 'gateway', 'obs', label='', dashed=True),
    ]
    return SemanticDiagram('llm_layered_architecture', 'Layered LLM systems architecture', 'layered_architecture', nodes, edges, groups=groups)


def llm_layered_architecture_patch_policy() -> SemanticDiagram:
    d = llm_layered_architecture_example()
    # insert policy engine between gateway and orchestrator
    d.nodes.extend([
        SemanticNode('policy', 'Policy Engine', 'process', 'layered_architecture', row_hint=1, col_hint=1, group='Ingress'),
    ])
    d.groups[1].members.append('policy')
    d.edges = [e for e in d.edges if e.id != 'e1'] + [
        SemanticEdge('e1a', 'gateway', 'policy', label=''),
        SemanticEdge('e1b', 'policy', 'orchestrator', label=''),
    ]
    return d


def llm_layered_architecture_patch_retrieval_split() -> SemanticDiagram:
    d = llm_layered_architecture_example()
    d.nodes = [n for n in d.nodes if n.id != 'retrieval'] + [
        SemanticNode('recall', 'Recall', 'process', 'layered_architecture', row_hint=3, col_hint=0, group='Retrieval'),
        SemanticNode('rerank', 'Rerank', 'process', 'layered_architecture', row_hint=3, col_hint=1, group='Retrieval'),
    ]
    for g in d.groups:
        if g.id == 'Retrieval':
            g.members = ['recall', 'rerank']
    d.edges = [e for e in d.edges if e.src != 'retrieval' and e.dst != 'retrieval'] + [
        SemanticEdge('e2a', 'orchestrator', 'recall', label=''),
        SemanticEdge('e2b', 'recall', 'rerank', label=''),
        SemanticEdge('e4a', 'recall', 'store', label=''),
        SemanticEdge('e4b', 'rerank', 'serving', label='', dashed=True),
    ]
    return d


def llm_layered_architecture_patch_serving_rename() -> SemanticDiagram:
    d = llm_layered_architecture_example()
    for n in d.nodes:
        if n.id == 'serving':
            n.label = 'Inference Runtime'
    d.nodes.append(SemanticNode('scheduler', 'Batch Scheduler', 'process', 'layered_architecture', row_hint=4, col_hint=1, group='Inference'))
    for g in d.groups:
        if g.id == 'Inference':
            g.members.append('scheduler')
    d.edges.append(SemanticEdge('e10', 'serving', 'scheduler', label=''))
    return d


def llm_layered_architecture_patch_guardrail_rewire() -> SemanticDiagram:
    d = llm_layered_architecture_example()
    d.edges = [e for e in d.edges if not (e.src == 'safety' and e.dst == 'store')]
    d.edges.append(SemanticEdge('e11', 'safety', 'eval', label=''))
    return d


def transformer_architecture_example() -> SemanticDiagram:
    nodes = [
        SemanticNode('input', 'Input Tokens', 'process', 'transformer_stack', meta={'role': 'input'}),
        SemanticNode('embed', 'Embedding', 'process', 'transformer_stack', meta={'role': 'embed'}),
        SemanticNode('attn', 'Multi-Head\nSelf-Attention', 'process', 'transformer_stack', meta={'role': 'attn'}),
        SemanticNode('ffn', 'FFN', 'process', 'transformer_stack', meta={'role': 'ffn'}),
        SemanticNode('cross', 'Cross Attention', 'process', 'transformer_stack', meta={'role': 'cross'}),
        SemanticNode('decoder', 'Decoder Stack', 'process', 'transformer_stack', meta={'role': 'decoder'}),
        SemanticNode('output', 'Output Tokens', 'process', 'transformer_stack', meta={'role': 'output'}),
    ]
    edges = [
        SemanticEdge('e0', 'input', 'embed'),
        SemanticEdge('e1', 'embed', 'attn', label=''),
        SemanticEdge('e2', 'attn', 'ffn', label=''),
        SemanticEdge('e3', 'ffn', 'cross', label=''),
        SemanticEdge('e4', 'cross', 'decoder', label=''),
        SemanticEdge('e5', 'decoder', 'output'),
    ]
    return SemanticDiagram('transformer_architecture', 'Transformer-style architecture', 'transformer_stack', nodes, edges)


def react_loop_example() -> SemanticDiagram:
    nodes = [
        SemanticNode('query', 'User Query', 'process', 'react_loop'),
        SemanticNode('reason', 'Reasoning', 'process', 'react_loop'),
        SemanticNode('tool', 'Tool Action', 'process', 'react_loop'),
        SemanticNode('observe', 'Environment\nObservation', 'process', 'react_loop'),
        SemanticNode('memory', 'Memory Update', 'process', 'react_loop'),
        SemanticNode('answer', 'Final Answer', 'terminator', 'react_loop'),
    ]
    edges = [
        SemanticEdge('e0', 'query', 'reason'),
        SemanticEdge('e1', 'reason', 'tool', label='thought'),
        SemanticEdge('e2', 'tool', 'observe', label='act'),
        SemanticEdge('e3', 'observe', 'memory', label='observe'),
        SemanticEdge('e4', 'memory', 'reason', label='update'),
        SemanticEdge('e5', 'reason', 'answer', label='answer'),
    ]
    return SemanticDiagram('react_loop', 'ReAct loop', 'react_loop', nodes, edges)


def rag_pipeline_example() -> SemanticDiagram:
    nodes = [
        SemanticNode('doc', 'Document Import', 'process', 'rag_pipeline', row_hint=0, col_hint=0, group='Offline Ingestion'),
        SemanticNode('chunk', 'Chunking', 'process', 'rag_pipeline', row_hint=0, col_hint=1, group='Offline Ingestion'),
        SemanticNode('embed', 'Embedding', 'process', 'rag_pipeline', row_hint=0, col_hint=2, group='Offline Ingestion'),
        SemanticNode('vecdb', 'Vector Store', 'database', 'rag_pipeline', row_hint=0, col_hint=3, group='Offline Ingestion'),
        SemanticNode('recall', 'Recall', 'process', 'rag_pipeline', row_hint=1, col_hint=1, group='Online Inference'),
        SemanticNode('rerank', 'Rerank', 'process', 'rag_pipeline', row_hint=1, col_hint=2, group='Online Inference'),
        SemanticNode('pack', 'Context Packing', 'process', 'rag_pipeline', row_hint=1, col_hint=3, group='Online Inference'),
        SemanticNode('llm', 'LLM Inference', 'process', 'rag_pipeline', row_hint=1, col_hint=4, group='Online Inference'),
        SemanticNode('answer', 'Answer Output', 'terminator', 'rag_pipeline', row_hint=1, col_hint=5, group='Online Inference'),
        SemanticNode('feedback', 'Feedback Loop', 'process', 'rag_pipeline', row_hint=2, col_hint=5, group='Continuous Improvement'),
    ]
    groups = [
        SemanticGroup('Offline Ingestion', 'Offline Ingestion', 'frame', ['doc','chunk','embed','vecdb']),
        SemanticGroup('Online Inference', 'Online Inference', 'frame', ['recall','rerank','pack','llm','answer']),
        SemanticGroup('Continuous Improvement', 'Continuous Improvement', 'frame', ['feedback']),
    ]
    edges = [
        SemanticEdge('e0', 'doc', 'chunk', label=''),
        SemanticEdge('e1', 'chunk', 'embed', label=''),
        SemanticEdge('e2', 'embed', 'vecdb', label='index'),
        SemanticEdge('e3', 'vecdb', 'recall', label=''),
        SemanticEdge('e4', 'recall', 'rerank', label=''),
        SemanticEdge('e5', 'rerank', 'pack', label=''),
        SemanticEdge('e6', 'pack', 'llm', label=''),
        SemanticEdge('e7', 'llm', 'answer', label=''),
        SemanticEdge('e8', 'answer', 'feedback', label=''),
        SemanticEdge('e9', 'feedback', 'rerank', label=''),
    ]
    return SemanticDiagram('rag_pipeline', 'RAG system architecture', 'rag_pipeline', nodes, edges, groups=groups)


def multiagent_code_review_example() -> SemanticDiagram:
    nodes = [
        SemanticNode('request', 'Request Intake', 'process', 'layered_architecture', row_hint=0, col_hint=0, group='Request Intake'),
        SemanticNode('planner', 'Planner', 'process', 'layered_architecture', row_hint=1, col_hint=0, group='Planner'),
        SemanticNode('workers', 'Worker Agents', 'process', 'layered_architecture', row_hint=2, col_hint=0, group='Worker Agents'),
        SemanticNode('sandbox', 'Tool Sandbox', 'process', 'layered_architecture', row_hint=3, col_hint=0, group='Tool Sandbox'),
        SemanticNode('verifier', 'Verifier', 'process', 'layered_architecture', row_hint=4, col_hint=0, group='Verifier'),
        SemanticNode('memory', 'Memory', 'database', 'layered_architecture', row_hint=5, col_hint=0, group='Memory'),
        SemanticNode('report', 'Report Output', 'terminator', 'layered_architecture', row_hint=6, col_hint=0, group='Report Output'),
    ]
    groups = [SemanticGroup(lbl, lbl, 'frame', [nid]) for lbl, nid in [('Request Intake','request'),('Planner','planner'),('Worker Agents','workers'),('Tool Sandbox','sandbox'),('Verifier','verifier'),('Memory','memory'),('Report Output','report')]]
    edges = [
        SemanticEdge('e0','request','planner',label=''),
        SemanticEdge('e1','planner','workers',label=''),
        SemanticEdge('e2','workers','sandbox',label=''),
        SemanticEdge('e3','sandbox','verifier',label=''),
        SemanticEdge('e4','verifier','report',label=''),
        SemanticEdge('e5','workers','memory',label=''),
        SemanticEdge('e6','verifier','memory',label=''),
        SemanticEdge('e7','memory','planner',label='',dashed=True),
    ]
    return SemanticDiagram('multiagent_code_review', 'Multi-agent code review platform', 'layered_architecture', nodes, edges, groups=groups)


def technical_blueprint_llm_example() -> SemanticDiagram:
    nodes = [
        SemanticNode('gateway', 'Gateway Rack', 'device', 'technical_blueprint', row_hint=1, col_hint=0, group='infra'),
        SemanticNode('orchestrator', 'Orchestrator Node', 'device', 'technical_blueprint', row_hint=1, col_hint=1, group='infra'),
        SemanticNode('retrieval', 'Retrieval Node', 'device', 'technical_blueprint', row_hint=0, col_hint=2, group='infra'),
        SemanticNode('runtime', 'Inference Runtime', 'device', 'technical_blueprint', row_hint=2, col_hint=2, group='infra'),
        SemanticNode('safety', 'Safety / Eval Node', 'device', 'technical_blueprint', row_hint=1, col_hint=3, group='infra'),
        SemanticNode('store', 'Storage Array', 'device', 'technical_blueprint', row_hint=1, col_hint=4, group='infra'),
        SemanticNode('tb', 'TITLE BLOCK', 'title_block', 'technical_blueprint', row_hint=3, col_hint=4),
    ]
    groups = [SemanticGroup('infra', 'LLM Platform Cabinet', 'frame', ['gateway','orchestrator','retrieval','runtime','safety','store'])]
    keepouts = [(760, 340, 1180, 510)]
    edges = [
        SemanticEdge('e0','gateway','orchestrator',label=''),
        SemanticEdge('e1','orchestrator','retrieval',label=''),
        SemanticEdge('e2','orchestrator','runtime',label=''),
        SemanticEdge('e3','runtime','safety',label=''),
        SemanticEdge('e4','retrieval','store',label=''),
        SemanticEdge('e5','safety','store',label=''),
    ]
    return SemanticDiagram('llm_blueprint', 'LLM infrastructure blueprint', 'technical_blueprint', nodes, edges, groups=groups, keepouts=keepouts)


def ai_app_stack_example() -> SemanticDiagram:
    nodes = [
        SemanticNode('apps', 'Client Apps', 'process', 'layered_architecture', row_hint=0, col_hint=0, group='Experience'),
        SemanticNode('orch', 'Orchestration', 'process', 'layered_architecture', row_hint=1, col_hint=0, group='Core Platform'),
        SemanticNode('retrieval', 'Retrieval', 'process', 'layered_architecture', row_hint=1, col_hint=1, group='Core Platform'),
        SemanticNode('serving', 'Serving', 'process', 'layered_architecture', row_hint=1, col_hint=2, group='Core Platform'),
        SemanticNode('eval', 'Evaluation', 'process', 'layered_architecture', row_hint=2, col_hint=1, group='Operations'),
        SemanticNode('obs', 'Observability', 'process', 'layered_architecture', row_hint=2, col_hint=2, group='Operations'),
        SemanticNode('store', 'Storage', 'database', 'layered_architecture', row_hint=3, col_hint=1, group='Foundation'),
    ]
    groups = [
        SemanticGroup('Experience', 'Experience', 'frame', ['apps']),
        SemanticGroup('Core Platform', 'Core Platform', 'frame', ['orch','retrieval','serving']),
        SemanticGroup('Operations', 'Operations', 'frame', ['eval','obs']),
        SemanticGroup('Foundation', 'Foundation', 'frame', ['store']),
    ]
    edges = [
        SemanticEdge('e0','apps','orch',label=''),
        SemanticEdge('e1','orch','retrieval',label=''),
        SemanticEdge('e2','orch','serving',label=''),
        SemanticEdge('e3','retrieval','store',label=''),
        SemanticEdge('e4','serving','eval',label=''),
        SemanticEdge('e5','serving','obs',label=''),
        SemanticEdge('e6','obs','store',label=''),
    ]
    return SemanticDiagram('ai_app_stack', 'Modern AI application stack', 'layered_architecture', nodes, edges, groups=groups)


def platform_topology_example() -> SemanticDiagram:
    nodes = [
        SemanticNode('clients', 'Clients', 'process', 'layered_architecture', row_hint=0, col_hint=0, group='Entry'),
        SemanticNode('gateway', 'Routing Gateway', 'process', 'layered_architecture', row_hint=1, col_hint=0, group='Entry'),
        SemanticNode('agents', 'Agent Fabric', 'process', 'layered_architecture', row_hint=2, col_hint=0, group='Control Plane'),
        SemanticNode('retrieval', 'Retrieval Cluster', 'process', 'layered_architecture', row_hint=2, col_hint=1, group='Control Plane'),
        SemanticNode('models', 'Model Fleet', 'process', 'layered_architecture', row_hint=2, col_hint=2, group='Data Plane'),
        SemanticNode('eval', 'Evaluation Hub', 'process', 'layered_architecture', row_hint=3, col_hint=1, group='Operations'),
        SemanticNode('stores', 'Data Stores', 'database', 'layered_architecture', row_hint=4, col_hint=1, group='Foundation'),
    ]
    groups = [
        SemanticGroup('Entry', 'Entry', 'frame', ['clients','gateway']),
        SemanticGroup('Control Plane', 'Control Plane', 'frame', ['agents','retrieval']),
        SemanticGroup('Data Plane', 'Data Plane', 'frame', ['models']),
        SemanticGroup('Operations', 'Operations', 'frame', ['eval']),
        SemanticGroup('Foundation', 'Foundation', 'frame', ['stores']),
    ]
    edges = [
        SemanticEdge('e0','clients','gateway',label=''),
        SemanticEdge('e1','gateway','agents',label=''),
        SemanticEdge('e2','agents','retrieval',label=''),
        SemanticEdge('e3','agents','models',label=''),
        SemanticEdge('e4','retrieval','stores',label=''),
        SemanticEdge('e5','models','eval',label=''),
        SemanticEdge('e6','eval','stores',label=''),
    ]
    return SemanticDiagram('platform_topology', 'LLM application platform topology', 'layered_architecture', nodes, edges, groups=groups)


def coding_copilot_platform_example() -> SemanticDiagram:
    nodes = [
        SemanticNode('editor', 'IDE / Chat UI', 'process', 'layered_architecture', row_hint=0, col_hint=0, group='Client Apps'),
        SemanticNode('gateway', 'Gateway', 'process', 'layered_architecture', row_hint=1, col_hint=0, group='Gateway'),
        SemanticNode('planner', 'Planner / Orchestrator', 'process', 'layered_architecture', row_hint=2, col_hint=0, group='Orchestration'),
        SemanticNode('tools', 'Tool Sandbox', 'process', 'layered_architecture', row_hint=2, col_hint=1, group='Orchestration'),
        SemanticNode('retrieval', 'Code Retrieval', 'process', 'layered_architecture', row_hint=3, col_hint=0, group='Retrieval'),
        SemanticNode('runtime', 'Inference Runtime', 'process', 'layered_architecture', row_hint=3, col_hint=1, group='Serving'),
        SemanticNode('eval', 'Evaluation', 'process', 'layered_architecture', row_hint=4, col_hint=0, group='Safety & Quality'),
        SemanticNode('memory', 'Memory / Index', 'database', 'layered_architecture', row_hint=5, col_hint=0, group='Storage'),
    ]
    groups = [
        SemanticGroup('Client Apps', 'Client Apps', 'frame', ['editor']),
        SemanticGroup('Gateway', 'Gateway', 'frame', ['gateway']),
        SemanticGroup('Orchestration', 'Orchestration', 'frame', ['planner','tools']),
        SemanticGroup('Retrieval', 'Retrieval', 'frame', ['retrieval']),
        SemanticGroup('Serving', 'Serving', 'frame', ['runtime']),
        SemanticGroup('Safety & Quality', 'Safety & Quality', 'frame', ['eval']),
        SemanticGroup('Storage', 'Storage', 'frame', ['memory']),
    ]
    edges = [
        SemanticEdge('e0','editor','gateway',label=''),
        SemanticEdge('e1','gateway','planner',label=''),
        SemanticEdge('e2','planner','tools',label=''),
        SemanticEdge('e3','planner','retrieval',label=''),
        SemanticEdge('e4','planner','runtime',label=''),
        SemanticEdge('e5','retrieval','memory',label=''),
        SemanticEdge('e6','runtime','eval',label=''),
        SemanticEdge('e7','tools','eval',label=''),
    ]
    return SemanticDiagram('coding_copilot_platform', 'AI coding copilot platform', 'layered_architecture', nodes, edges, groups=groups)
