import { create } from "zustand"
import type {
  KnowledgeItem,
  KnowledgeEdge,
  KnowledgeGraphNode,
  KnowledgeGraphEdge,
  KnowledgeLineageStep,
  InfluenceNode,
  UnlearningImpact,
  UnlearningPipelineStep,
  TimelineEvent,
  VerificationRecord,
  KnowledgeType,
} from "@/lib/types/knowledge"

const mockKnowledgeItems: KnowledgeItem[] = [
  {
    id: "k-001",
    type: "conversation",
    title: "Conversation #12 - Medical History Discussion",
    description: "User discussed personal medical history including prior diagnoses and medications.",
    sourceConversationId: "conv-012",
    sourceMessageId: null,
    dateLearned: "2026-07-10T09:15:00Z",
    lastAccessed: "2026-07-14T08:30:00Z",
    learningConfidence: 0.94,
    importanceScore: 0.87,
    influenceScore: 0.72,
    referencedResponseCount: 12,
    status: "active",
    verificationStatus: "verified",
    certificateId: null,
    storageLocations: {
      conversation_store: "exists",
      embedding_store: "exists",
      vector_database: "exists",
      training_dataset: "exists",
      memory_manager: "exists",
      knowledge_graph: "exists",
      lora_adapter: "exists",
      model_registry: "exists",
      cache: "exists",
    },
    associatedEmbeddings: ["emb-201", "emb-202", "emb-203"],
    trainingSamples: ["ts-091", "ts-092"],
    loraAdapterVersion: "v8",
    memoryGraphConnections: ["mem-044", "mem-045"],
    tags: ["medical", "personal", "sensitive"],
  },
  {
    id: "k-002",
    type: "fact",
    title: "User prefers TypeScript over JavaScript",
    description: "Learned preference from multiple conversations about programming language choices.",
    sourceConversationId: "conv-005",
    sourceMessageId: "msg-019",
    dateLearned: "2026-07-10T14:22:00Z",
    lastAccessed: "2026-07-13T16:45:00Z",
    learningConfidence: 0.89,
    importanceScore: 0.45,
    influenceScore: 0.31,
    referencedResponseCount: 8,
    status: "active",
    verificationStatus: "verified",
    certificateId: null,
    storageLocations: {
      conversation_store: "exists",
      embedding_store: "exists",
      vector_database: "exists",
      training_dataset: "exists",
      memory_manager: "exists",
      knowledge_graph: "exists",
      lora_adapter: "exists",
      model_registry: "never_stored",
      cache: "exists",
    },
    associatedEmbeddings: ["emb-105"],
    trainingSamples: ["ts-044"],
    loraAdapterVersion: "v8",
    memoryGraphConnections: ["mem-012"],
    tags: ["preference", "programming"],
  },
  {
    id: "k-003",
    type: "document",
    title: "Project Requirements Document",
    description: "Uploaded project requirements document covering system architecture and API specifications.",
    sourceConversationId: null,
    sourceMessageId: null,
    dateLearned: "2026-07-11T10:00:00Z",
    lastAccessed: "2026-07-14T07:15:00Z",
    learningConfidence: 0.96,
    importanceScore: 0.91,
    influenceScore: 0.85,
    referencedResponseCount: 24,
    status: "active",
    verificationStatus: "verified",
    certificateId: null,
    storageLocations: {
      conversation_store: "never_stored",
      embedding_store: "exists",
      vector_database: "exists",
      training_dataset: "exists",
      memory_manager: "exists",
      knowledge_graph: "exists",
      lora_adapter: "exists",
      model_registry: "exists",
      cache: "exists",
    },
    associatedEmbeddings: ["emb-301", "emb-302", "emb-303", "emb-304"],
    trainingSamples: ["ts-101", "ts-102", "ts-103"],
    loraAdapterVersion: "v8",
    memoryGraphConnections: ["mem-078", "mem-079", "mem-080"],
    tags: ["document", "architecture", "api"],
  },
  {
    id: "k-004",
    type: "embedding",
    title: "Embedding #204 - Medical Context Vector",
    description: "768-dimensional vector representation of medical history context from Conversation #12.",
    sourceConversationId: "conv-012",
    sourceMessageId: "msg-041",
    dateLearned: "2026-07-11T11:30:00Z",
    lastAccessed: "2026-07-14T06:00:00Z",
    learningConfidence: 0.92,
    importanceScore: 0.78,
    influenceScore: 0.69,
    referencedResponseCount: 6,
    status: "active",
    verificationStatus: "verified",
    certificateId: null,
    storageLocations: {
      conversation_store: "never_stored",
      embedding_store: "exists",
      vector_database: "exists",
      training_dataset: "exists",
      memory_manager: "never_stored",
      knowledge_graph: "exists",
      lora_adapter: "exists",
      model_registry: "never_stored",
      cache: "exists",
    },
    associatedEmbeddings: ["emb-204"],
    trainingSamples: ["ts-091"],
    loraAdapterVersion: "v8",
    memoryGraphConnections: ["mem-044"],
    tags: ["embedding", "vector", "medical"],
  },
  {
    id: "k-005",
    type: "training_sample",
    title: "Training Sample #91 - Medical Q&A Pair",
    description: "Fine-tuning sample derived from medical history conversation, used in LoRA adapter v8 training.",
    sourceConversationId: "conv-012",
    sourceMessageId: "msg-041",
    dateLearned: "2026-07-12T08:45:00Z",
    lastAccessed: "2026-07-13T20:10:00Z",
    learningConfidence: 0.88,
    importanceScore: 0.82,
    influenceScore: 0.76,
    referencedResponseCount: 3,
    status: "active",
    verificationStatus: "verified",
    certificateId: null,
    storageLocations: {
      conversation_store: "never_stored",
      embedding_store: "never_stored",
      vector_database: "never_stored",
      training_dataset: "exists",
      memory_manager: "never_stored",
      knowledge_graph: "exists",
      lora_adapter: "exists",
      model_registry: "exists",
      cache: "never_stored",
    },
    associatedEmbeddings: ["emb-204"],
    trainingSamples: ["ts-091"],
    loraAdapterVersion: "v8",
    memoryGraphConnections: ["mem-044"],
    tags: ["training", "medical", "qa-pair"],
  },
  {
    id: "k-006",
    type: "lora_adapter",
    title: "LoRA Adapter v8 - Current Production",
    description: "Current production LoRA adapter trained on 1,247 samples including medical context data.",
    sourceConversationId: null,
    sourceMessageId: null,
    dateLearned: "2026-07-12T12:00:00Z",
    lastAccessed: "2026-07-14T09:00:00Z",
    learningConfidence: 0.95,
    importanceScore: 0.98,
    influenceScore: 0.94,
    referencedResponseCount: 89,
    status: "active",
    verificationStatus: "verified",
    certificateId: null,
    storageLocations: {
      conversation_store: "never_stored",
      embedding_store: "never_stored",
      vector_database: "never_stored",
      training_dataset: "exists",
      memory_manager: "never_stored",
      knowledge_graph: "exists",
      lora_adapter: "exists",
      model_registry: "exists",
      cache: "exists",
    },
    associatedEmbeddings: [],
    trainingSamples: ["ts-001", "ts-002", "...1,247 total"],
    loraAdapterVersion: "v8",
    memoryGraphConnections: ["mem-001", "mem-002", "...45 total"],
    tags: ["adapter", "production", "lora"],
  },
  {
    id: "k-007",
    type: "memory_node",
    title: "Memory Node #44 - Health Context",
    description: "Memory graph node linking medical history facts to response generation patterns.",
    sourceConversationId: "conv-012",
    sourceMessageId: "msg-041",
    dateLearned: "2026-07-11T14:20:00Z",
    lastAccessed: "2026-07-14T05:30:00Z",
    learningConfidence: 0.86,
    importanceScore: 0.73,
    influenceScore: 0.61,
    referencedResponseCount: 5,
    status: "active",
    verificationStatus: "verified",
    certificateId: null,
    storageLocations: {
      conversation_store: "never_stored",
      embedding_store: "exists",
      vector_database: "never_stored",
      training_dataset: "never_stored",
      memory_manager: "exists",
      knowledge_graph: "exists",
      lora_adapter: "exists",
      model_registry: "never_stored",
      cache: "exists",
    },
    associatedEmbeddings: ["emb-204"],
    trainingSamples: ["ts-091"],
    loraAdapterVersion: "v8",
    memoryGraphConnections: ["mem-044", "mem-045", "mem-046"],
    tags: ["memory", "health", "context"],
  },
  {
    id: "k-008",
    type: "knowledge_category",
    title: "Medical Information",
    description: "Knowledge category aggregating all medical-related learned information across conversations.",
    sourceConversationId: null,
    sourceMessageId: null,
    dateLearned: "2026-07-10T09:15:00Z",
    lastAccessed: "2026-07-14T08:30:00Z",
    learningConfidence: 0.91,
    importanceScore: 0.88,
    influenceScore: 0.79,
    referencedResponseCount: 31,
    status: "active",
    verificationStatus: "verified",
    certificateId: null,
    storageLocations: {
      conversation_store: "exists",
      embedding_store: "exists",
      vector_database: "exists",
      training_dataset: "exists",
      memory_manager: "exists",
      knowledge_graph: "exists",
      lora_adapter: "exists",
      model_registry: "exists",
      cache: "exists",
    },
    associatedEmbeddings: ["emb-201", "emb-202", "emb-203", "emb-204"],
    trainingSamples: ["ts-091", "ts-092"],
    loraAdapterVersion: "v8",
    memoryGraphConnections: ["mem-044", "mem-045"],
    tags: ["category", "medical"],
  },
  {
    id: "k-009",
    type: "verification_certificate",
    title: "Certificate #CERT-2026-0714 - Batch Unlearn",
    description: "Verification certificate for batch unlearning of 3 knowledge items on 2026-07-14.",
    sourceConversationId: null,
    sourceMessageId: null,
    dateLearned: "2026-07-14T10:00:00Z",
    lastAccessed: "2026-07-14T10:00:00Z",
    learningConfidence: 1.0,
    importanceScore: 0.95,
    influenceScore: 0.0,
    referencedResponseCount: 0,
    status: "active",
    verificationStatus: "verified",
    certificateId: "CERT-2026-0714-001",
    storageLocations: {
      conversation_store: "never_stored",
      embedding_store: "never_stored",
      vector_database: "never_stored",
      training_dataset: "never_stored",
      memory_manager: "never_stored",
      knowledge_graph: "exists",
      lora_adapter: "never_stored",
      model_registry: "exists",
      cache: "never_stored",
    },
    associatedEmbeddings: [],
    trainingSamples: [],
    loraAdapterVersion: null,
    memoryGraphConnections: [],
    tags: ["certificate", "verification"],
  },
  {
    id: "k-010",
    type: "fact",
    title: "User's favorite color is blue",
    description: "Simple preference fact learned from casual conversation.",
    sourceConversationId: "conv-003",
    sourceMessageId: "msg-008",
    dateLearned: "2026-07-10T11:05:00Z",
    lastAccessed: "2026-07-12T14:20:00Z",
    learningConfidence: 0.97,
    importanceScore: 0.15,
    influenceScore: 0.08,
    referencedResponseCount: 2,
    status: "active",
    verificationStatus: "verified",
    certificateId: null,
    storageLocations: {
      conversation_store: "exists",
      embedding_store: "exists",
      vector_database: "exists",
      training_dataset: "exists",
      memory_manager: "exists",
      knowledge_graph: "exists",
      lora_adapter: "exists",
      model_registry: "never_stored",
      cache: "exists",
    },
    associatedEmbeddings: ["emb-050"],
    trainingSamples: ["ts-018"],
    loraAdapterVersion: "v8",
    memoryGraphConnections: ["mem-009"],
    tags: ["preference", "casual"],
  },
]

const mockEdges: KnowledgeEdge[] = [
  { id: "e-001", source: "k-001", target: "k-004", relation: "embedded_into", weight: 0.92, label: "Embedded Into" },
  { id: "e-002", source: "k-004", target: "k-005", relation: "trained_on", weight: 0.88, label: "Trained On" },
  { id: "e-003", source: "k-005", target: "k-006", relation: "trained_on", weight: 0.95, label: "Trained On" },
  { id: "e-004", source: "k-004", target: "k-007", relation: "influences", weight: 0.76, label: "Influences" },
  { id: "e-005", source: "k-001", target: "k-008", relation: "learned_from", weight: 0.87, label: "Learned From" },
  { id: "e-006", source: "k-002", target: "k-008", relation: "learned_from", weight: 0.45, label: "Learned From" },
  { id: "e-007", source: "k-003", target: "k-004", relation: "embedded_into", weight: 0.96, label: "Embedded Into" },
  { id: "e-008", source: "k-006", target: "k-009", relation: "verified_by", weight: 1.0, label: "Verified By" },
  { id: "e-009", source: "k-007", target: "k-006", relation: "influences", weight: 0.61, label: "Influences" },
  { id: "e-010", source: "k-010", target: "k-008", relation: "learned_from", weight: 0.15, label: "Learned From" },
]

const mockGraphNodes: KnowledgeGraphNode[] = [
  { id: "k-001", type: "conversation", label: "Conv #12", x: 120, y: 80, size: 28, color: "#3b82f6", item: mockKnowledgeItems[0] },
  { id: "k-002", type: "fact", label: "TS > JS", x: 340, y: 60, size: 18, color: "#10b981", item: mockKnowledgeItems[1] },
  { id: "k-003", type: "document", label: "Requirements Doc", x: 520, y: 120, size: 30, color: "#8b5cf6", item: mockKnowledgeItems[2] },
  { id: "k-004", type: "embedding", label: "Emb #204", x: 280, y: 180, size: 20, color: "#f59e0b", item: mockKnowledgeItems[3] },
  { id: "k-005", type: "training_sample", label: "TS #91", x: 200, y: 280, size: 22, color: "#ef4444", item: mockKnowledgeItems[4] },
  { id: "k-006", type: "lora_adapter", label: "LoRA v8", x: 380, y: 340, size: 34, color: "#ec4899", item: mockKnowledgeItems[5] },
  { id: "k-007", type: "memory_node", label: "Mem #44", x: 140, y: 350, size: 20, color: "#06b6d4", item: mockKnowledgeItems[6] },
  { id: "k-008", type: "knowledge_category", label: "Medical Info", x: 450, y: 220, size: 26, color: "#64748b", item: mockKnowledgeItems[7] },
  { id: "k-009", type: "verification_certificate", label: "Cert #001", x: 540, y: 350, size: 24, color: "#22d3ee", item: mockKnowledgeItems[8] },
  { id: "k-010", type: "fact", label: "Fav Color", x: 560, y: 50, size: 14, color: "#10b981", item: mockKnowledgeItems[9] },
]

const mockGraphEdges: KnowledgeGraphEdge[] = [
  { id: "ge-001", source: "k-001", target: "k-004", relation: "embedded_into", label: "Embedded Into", weight: 0.92 },
  { id: "ge-002", source: "k-004", target: "k-005", relation: "trained_on", label: "Trained On", weight: 0.88 },
  { id: "ge-003", source: "k-005", target: "k-006", relation: "trained_on", label: "Trained On", weight: 0.95 },
  { id: "ge-004", source: "k-004", target: "k-007", relation: "influences", label: "Influences", weight: 0.76 },
  { id: "ge-005", source: "k-001", target: "k-008", relation: "learned_from", label: "Learned From", weight: 0.87 },
  { id: "ge-006", source: "k-002", target: "k-008", relation: "learned_from", label: "Learned From", weight: 0.45 },
  { id: "ge-007", source: "k-003", target: "k-004", relation: "embedded_into", label: "Embedded Into", weight: 0.96 },
  { id: "ge-008", source: "k-006", target: "k-009", relation: "verified_by", label: "Verified By", weight: 1.0 },
  { id: "ge-009", source: "k-007", target: "k-006", relation: "influences", label: "Influences", weight: 0.61 },
  { id: "ge-010", source: "k-010", target: "k-008", relation: "learned_from", label: "Learned From", weight: 0.15 },
]

const mockLineage: KnowledgeLineageStep[] = [
  { id: "l-1", type: "conversation", label: "Conversation #12", description: "Medical history discussion initiated", timestamp: "2026-07-10T09:15:00Z", status: "completed" },
  { id: "l-2", type: "document_chunk", label: "Message #41", description: "User message with personal health details", timestamp: "2026-07-10T09:17:00Z", status: "completed" },
  { id: "l-3", type: "document_chunk", label: "Chunk #18", description: "Text chunk extracted and preprocessed", timestamp: "2026-07-10T09:17:30Z", status: "completed" },
  { id: "l-4", type: "embedding", label: "Embedding #204", description: "768-dim vector generated via text-embedding-3", timestamp: "2026-07-11T11:30:00Z", status: "completed" },
  { id: "l-5", type: "training_sample", label: "Training Sample #91", description: "Q&A pair formatted for LoRA fine-tuning", timestamp: "2026-07-12T08:45:00Z", status: "completed" },
  { id: "l-6", type: "lora_adapter", label: "LoRA Adapter v8", description: "Adapter retrained including this sample", timestamp: "2026-07-12T12:00:00Z", status: "completed" },
  { id: "l-7", type: "memory_node", label: "Memory Node #44", description: "Memory graph updated with health context", timestamp: "2026-07-11T14:20:00Z", status: "completed" },
  { id: "l-8", type: "fact", label: "Response #44", description: "AI referenced this knowledge in response", timestamp: "2026-07-13T10:15:00Z", status: "completed" },
  { id: "l-9", type: "verification_certificate", label: "Verification Record", description: "Cryptographic verification pending", timestamp: "2026-07-14T10:00:00Z", status: "current" },
]

const mockTimeline: TimelineEvent[] = [
  { id: "t-001", date: "2026-07-10", type: "conversation_created", title: "Conversation Created", description: "Medical history discussion started with the AI assistant.", knowledgeId: "k-001", metadata: {} },
  { id: "t-002", date: "2026-07-10", type: "knowledge_learned", title: "Knowledge Learned", description: "Medical facts extracted and stored in knowledge graph.", knowledgeId: "k-001", metadata: { confidence: 0.94 } },
  { id: "t-003", date: "2026-07-10", type: "knowledge_learned", title: "Preference Learned", description: "TypeScript preference fact stored.", knowledgeId: "k-002", metadata: { confidence: 0.89 } },
  { id: "t-004", date: "2026-07-11", type: "embedding_generated", title: "Embedding Generated", description: "768-dimensional vector created for medical context.", knowledgeId: "k-004", metadata: { dimensions: 768 } },
  { id: "t-005", date: "2026-07-11", type: "embedding_generated", title: "Document Embedded", description: "Project requirements document chunked and embedded.", knowledgeId: "k-003", metadata: { chunks: 4 } },
  { id: "t-006", date: "2026-07-12", type: "training_sample_created", title: "Training Sample Created", description: "Medical Q&A pair formatted for LoRA fine-tuning.", knowledgeId: "k-005", metadata: { sampleType: "qa_pair" } },
  { id: "t-007", date: "2026-07-12", type: "training_sample_created", title: "Adapter Retrained", description: "LoRA adapter v8 trained on 1,247 samples.", knowledgeId: "k-006", metadata: { totalSamples: 1247 } },
  { id: "t-008", date: "2026-07-13", type: "referenced_in_response", title: "Referenced in Response", description: "AI used medical knowledge in a response to user query.", knowledgeId: "k-001", metadata: { responseId: "resp-044" } },
  { id: "t-009", date: "2026-07-14", type: "machine_unlearned", title: "Machine Unlearned", description: "Batch unlearning initiated for selected knowledge items.", knowledgeId: "k-009", metadata: { itemCount: 3 } },
  { id: "t-010", date: "2026-07-14", type: "certificate_generated", title: "Certificate Generated", description: "Cryptographic proof of unlearning generated.", knowledgeId: "k-009", metadata: { certId: "CERT-2026-0714-001" } },
  { id: "t-011", date: "2026-07-14", type: "verification_pass", title: "Verification PASS", description: "Third-party verification confirmed successful unlearning.", knowledgeId: "k-009", metadata: { result: "PASS" } },
]

const mockPipelineSteps: UnlearningPipelineStep[] = [
  { step: 1, label: "Scanning Dependencies", status: "completed", startedAt: "2026-07-14T10:00:01Z", completedAt: "2026-07-14T10:00:03Z", details: "Found 7 dependent items", durationMs: 2100 },
  { step: 2, label: "Finding Conversations", status: "completed", startedAt: "2026-07-14T10:00:03Z", completedAt: "2026-07-14T10:00:05Z", details: "2 conversations affected", durationMs: 1800 },
  { step: 3, label: "Finding Chunks", status: "completed", startedAt: "2026-07-14T10:00:05Z", completedAt: "2026-07-14T10:00:07Z", details: "5 text chunks identified", durationMs: 1600 },
  { step: 4, label: "Finding Embeddings", status: "completed", startedAt: "2026-07-14T10:00:07Z", completedAt: "2026-07-14T10:00:09Z", details: "4 embeddings to remove", durationMs: 2200 },
  { step: 5, label: "Finding Training Samples", status: "completed", startedAt: "2026-07-14T10:00:09Z", completedAt: "2026-07-14T10:00:11Z", details: "3 training samples found", durationMs: 1900 },
  { step: 6, label: "Finding Memory Nodes", status: "completed", startedAt: "2026-07-14T10:00:11Z", completedAt: "2026-07-14T10:00:13Z", details: "2 memory nodes flagged", durationMs: 1500 },
  { step: 7, label: "Finding LoRA Records", status: "completed", startedAt: "2026-07-14T10:00:13Z", completedAt: "2026-07-14T10:00:15Z", details: "Adapter v8 affected", durationMs: 1700 },
  { step: 8, label: "Adaptive Controller", status: "completed", startedAt: "2026-07-14T10:00:15Z", completedAt: "2026-07-14T10:00:18Z", details: "Selected hybrid strategy", durationMs: 2800 },
  { step: 9, label: "Selected Algorithm", status: "completed", startedAt: "2026-07-14T10:00:18Z", completedAt: "2026-07-14T10:00:19Z", details: "SISA + Influence Function", durationMs: 900 },
  { step: 10, label: "Retraining Adapter", status: "completed", startedAt: "2026-07-14T10:00:19Z", completedAt: "2026-07-14T10:00:45Z", details: "Adapter v9 trained in 26s", durationMs: 26000 },
  { step: 11, label: "Updating Registry", status: "completed", startedAt: "2026-07-14T10:00:45Z", completedAt: "2026-07-14T10:00:47Z", details: "Model registry updated", durationMs: 1800 },
  { step: 12, label: "Running Membership Inference Attack", status: "completed", startedAt: "2026-07-14T10:00:47Z", completedAt: "2026-07-14T10:01:12Z", details: "MIA accuracy dropped from 0.87 to 0.51", durationMs: 25000 },
  { step: 13, label: "Utility Evaluation", status: "completed", startedAt: "2026-07-14T10:01:12Z", completedAt: "2026-07-14T10:01:30Z", details: "Utility retained: 94.2%", durationMs: 18000 },
  { step: 14, label: "Privacy Evaluation", status: "completed", startedAt: "2026-07-14T10:01:30Z", completedAt: "2026-07-14T10:01:45Z", details: "Privacy improvement: +34.7%", durationMs: 15000 },
  { step: 15, label: "Computing SHA256", status: "completed", startedAt: "2026-07-14T10:01:45Z", completedAt: "2026-07-14T10:01:46Z", details: "Hash: a3f2c8...9e1b", durationMs: 800 },
  { step: 16, label: "Building Merkle Tree", status: "completed", startedAt: "2026-07-14T10:01:46Z", completedAt: "2026-07-14T10:01:48Z", details: "Root: 7b4e2f...a8c3", durationMs: 1500 },
  { step: 17, label: "Digital Signature", status: "completed", startedAt: "2026-07-14T10:01:48Z", completedAt: "2026-07-14T10:01:49Z", details: "Ed25519 signature generated", durationMs: 600 },
  { step: 18, label: "Generating Certificate", status: "completed", startedAt: "2026-07-14T10:01:49Z", completedAt: "2026-07-14T10:01:51Z", details: "CERT-2026-0714-001", durationMs: 1800 },
  { step: 19, label: "Updating Audit Ledger", status: "completed", startedAt: "2026-07-14T10:01:51Z", completedAt: "2026-07-14T10:01:53Z", details: "Audit event #AE-1024 recorded", durationMs: 1400 },
  { step: 20, label: "Refreshing Knowledge Graph", status: "completed", startedAt: "2026-07-14T10:01:53Z", completedAt: "2026-07-14T10:01:55Z", details: "Graph topology updated", durationMs: 2000 },
]

const mockVerificationRecord: VerificationRecord = {
  id: "vr-001",
  deletedKnowledgeIds: ["k-010", "k-002", "k-007"],
  deletedEmbeddings: ["emb-050", "emb-105", "emb-204"],
  deletedTrainingSamples: ["ts-018", "ts-044", "ts-091"],
  updatedLoRAVersion: "v9",
  oldModelVersion: "v8.3.1",
  newModelVersion: "v9.0.0",
  hashBefore: "3a7b2f8c9e1d4f6a8b0c3d5e7f9a1b2c4d6e8f0a3b5c7d9e1f3a5b7c9d1e3f",
  hashAfter: "9e1b3c5d7f9a1b2c4d6e8f0a3b5c7d9e1f3a5b7c9d1e3f5a7b2f8c9e1d4f6a",
  merkleRoot: "7b4e2f1a8c3d5e7f9a1b3c5d7e9f1a3b5c7d9e1f3a5b7c9d1e3f5a7b2f8c9e",
  digitalSignature: "Ed25519:3a7b2f8c9e1d4f6a8b0c3d5e7f9a1b2c4d6e8f0a3b5c7d9e1f3a5b7c9d1e3f5a7b2f8c9e1d4f6a8b0c3d5e7f9a1b2c4d6e8f0a3b5c7d9e1f3a5b7c9d1e3f",
  verificationStatus: "verified",
  verifiedAt: "2026-07-14T10:02:00Z",
  certificateUrl: null,
}

interface KnowledgeState {
  items: KnowledgeItem[]
  edges: KnowledgeEdge[]
  graphNodes: KnowledgeGraphNode[]
  graphEdges: KnowledgeGraphEdge[]
  lineage: KnowledgeLineageStep[]
  timeline: TimelineEvent[]
  pipelineSteps: UnlearningPipelineStep[]
  verificationRecord: VerificationRecord
  selectedItemId: string | null
  unlearningItemId: string | null
  isUnlearning: boolean
  showImpactPreview: boolean
  showComparison: boolean
  activeView: "graph" | "list" | "timeline"
  filterType: KnowledgeType | "all"
  searchQuery: string

  selectItem: (id: string | null) => void
  startUnlearning: (id: string) => void
  confirmUnlearning: () => void
  resetUnlearning: () => void
  setShowImpactPreview: (show: boolean) => void
  setShowComparison: (show: boolean) => void
  setActiveView: (view: "graph" | "list" | "timeline") => void
  setFilterType: (type: KnowledgeType | "all") => void
  setSearchQuery: (query: string) => void
  getFilteredItems: () => KnowledgeItem[]
  getLineageForItem: (id: string) => KnowledgeLineageStep[]
  getImpactPreview: (id: string) => UnlearningImpact
  getInfluenceNodes: () => InfluenceNode[]
}

export const useKnowledgeStore = create<KnowledgeState>((set, get) => ({
  items: mockKnowledgeItems,
  edges: mockEdges,
  graphNodes: mockGraphNodes,
  graphEdges: mockGraphEdges,
  lineage: mockLineage,
  timeline: mockTimeline,
  pipelineSteps: mockPipelineSteps,
  verificationRecord: mockVerificationRecord,
  selectedItemId: null,
  unlearningItemId: null,
  isUnlearning: false,
  showImpactPreview: false,
  showComparison: false,
  activeView: "graph",
  filterType: "all",
  searchQuery: "",

  selectItem: (id) => set({ selectedItemId: id }),

  startUnlearning: (id) => set({ unlearningItemId: id, showImpactPreview: true }),

  confirmUnlearning: () => {
    set({ isUnlearning: true, showImpactPreview: false })
    const steps = [...get().pipelineSteps]
    let currentStep = 0

    const advanceStep = () => {
      if (currentStep >= steps.length) {
        set({ isUnlearning: false, showComparison: true })
        return
      }
      steps[currentStep] = { ...steps[currentStep], status: "running", startedAt: new Date().toISOString() }
      set({ pipelineSteps: [...steps] })

      setTimeout(() => {
        steps[currentStep] = {
          ...steps[currentStep],
          status: "completed",
          completedAt: new Date().toISOString(),
          durationMs: Math.floor(Math.random() * 3000) + 500,
        }
        set({ pipelineSteps: [...steps] })
        currentStep++
        advanceStep()
      }, 400)
    }
    advanceStep()
  },

  resetUnlearning: () =>
    set({
      unlearningItemId: null,
      isUnlearning: false,
      showImpactPreview: false,
      showComparison: false,
      pipelineSteps: mockPipelineSteps.map((s) => ({ ...s, status: "pending" as const, startedAt: null, completedAt: null, durationMs: null })),
    }),

  setShowImpactPreview: (show) => set({ showImpactPreview: show }),
  setShowComparison: (show) => set({ showComparison: show }),
  setActiveView: (view) => set({ activeView: view }),
  setFilterType: (type) => set({ filterType: type }),
  setSearchQuery: (query) => set({ searchQuery: query }),

  getFilteredItems: () => {
    const { items, filterType, searchQuery } = get()
    let filtered = items
    if (filterType !== "all") {
      filtered = filtered.filter((i) => i.type === filterType)
    }
    if (searchQuery) {
      const q = searchQuery.toLowerCase()
      filtered = filtered.filter(
        (i) => i.title.toLowerCase().includes(q) || i.description.toLowerCase().includes(q) || i.tags.some((t) => t.includes(q))
      )
    }
    return filtered
  },

  getLineageForItem: (id) => {
    const item = get().items.find((i) => i.id === id)
    if (!item) return []
    return get().lineage
  },

  getImpactPreview: (id) => {
    const item = get().items.find((i) => i.id === id) || mockKnowledgeItems[0]
    return {
      selectedKnowledge: item,
      dependentEmbeddings: item.associatedEmbeddings,
      dependentChunks: ["chunk-18", "chunk-19", "chunk-20"],
      dependentTrainingSamples: item.trainingSamples,
      dependentAdapter: item.loraAdapterVersion,
      estimatedUtilityLoss: 0.058,
      estimatedPrivacyImprovement: 0.347,
      estimatedRuntimeMs: 54000,
      algorithmSelected: "Hybrid (SISA + Influence Function)",
      expectedCertificate: {
        algorithm: "Ed25519 + SHA256 Merkle Tree",
        merkleRoot: "7b4e2f...a8c3",
        status: "will_be_generated",
      },
    }
  },

  getInfluenceNodes: () => {
    return get().items
      .filter((i) => i.type !== "verification_certificate")
      .map((i) => ({
        id: i.id,
        type: i.type,
        label: i.title.substring(0, 30),
        influenceScore: i.influenceScore,
        referenceCount: i.referencedResponseCount,
        importance: i.importanceScore,
        deletionCost: Math.round(i.influenceScore * 100),
        retrainingCost: Math.round(i.importanceScore * 200),
      }))
  },
}))
