export type KnowledgeType =
  | "conversation"
  | "fact"
  | "document"
  | "document_chunk"
  | "embedding"
  | "training_sample"
  | "lora_adapter"
  | "memory_node"
  | "knowledge_category"
  | "verification_certificate"

export type KnowledgeStatus = "active" | "unlearned" | "pending" | "corrupted"

export type VerificationStatus = "verified" | "pending" | "failed" | "not_requested"

export type StorageLocation =
  | "conversation_store"
  | "embedding_store"
  | "vector_database"
  | "training_dataset"
  | "memory_manager"
  | "knowledge_graph"
  | "lora_adapter"
  | "model_registry"
  | "cache"

export type EdgeRelation =
  | "learned_from"
  | "embedded_into"
  | "trained_on"
  | "retrieved_by"
  | "influences"
  | "generated_from"
  | "verified_by"

export interface KnowledgeItem {
  id: string
  type: KnowledgeType
  title: string
  description: string
  sourceConversationId: string | null
  sourceMessageId: string | null
  dateLearned: string
  lastAccessed: string
  learningConfidence: number
  importanceScore: number
  influenceScore: number
  referencedResponseCount: number
  status: KnowledgeStatus
  verificationStatus: VerificationStatus
  certificateId: string | null
  storageLocations: Record<StorageLocation, "exists" | "removed" | "never_stored">
  associatedEmbeddings: string[]
  trainingSamples: string[]
  loraAdapterVersion: string | null
  memoryGraphConnections: string[]
  tags: string[]
}

export interface KnowledgeEdge {
  id: string
  source: string
  target: string
  relation: EdgeRelation
  weight: number
  label: string
}

export interface KnowledgeGraphNode {
  id: string
  type: KnowledgeType
  label: string
  x: number
  y: number
  size: number
  color: string
  item: KnowledgeItem
}

export interface KnowledgeGraphEdge {
  id: string
  source: string
  target: string
  relation: EdgeRelation
  label: string
  weight: number
}

export interface KnowledgeLineageStep {
  id: string
  type: KnowledgeType
  label: string
  description: string
  timestamp: string
  status: "completed" | "current" | "pending" | "removed"
}

export interface InfluenceNode {
  id: string
  type: KnowledgeType
  label: string
  influenceScore: number
  referenceCount: number
  importance: number
  deletionCost: number
  retrainingCost: number
}

export interface UnlearningImpact {
  selectedKnowledge: KnowledgeItem
  dependentEmbeddings: string[]
  dependentChunks: string[]
  dependentTrainingSamples: string[]
  dependentAdapter: string | null
  estimatedUtilityLoss: number
  estimatedPrivacyImprovement: number
  estimatedRuntimeMs: number
  algorithmSelected: string
  expectedCertificate: {
    algorithm: string
    merkleRoot: string
    status: string
  }
}

export interface UnlearningPipelineStep {
  step: number
  label: string
  status: "pending" | "running" | "completed" | "failed"
  startedAt: string | null
  completedAt: string | null
  details: string | null
  durationMs: number | null
}

export interface PostUnlearningComparison {
  before: {
    totalNodes: number
    totalEdges: number
    totalEmbeddings: number
    totalTrainingSamples: number
    adapterVersion: string
    modelVersion: string
  }
  after: {
    totalNodes: number
    totalEdges: number
    totalEmbeddings: number
    totalTrainingSamples: number
    adapterVersion: string
    modelVersion: string
  }
  removedNodes: string[]
  updatedEdges: string[]
  deletedEmbeddings: string[]
  deletedTrainingSamples: string[]
  privacyImprovement: number
  membershipAttackReduction: number
  utilityRetention: number
}

export interface TimelineEvent {
  id: string
  date: string
  type: "conversation_created" | "knowledge_learned" | "embedding_generated" | "training_sample_created" | "referenced_in_response" | "machine_unlearned" | "certificate_generated" | "verification_pass" | "verification_fail"
  title: string
  description: string
  knowledgeId: string
  metadata: Record<string, unknown>
}

export interface VerificationRecord {
  id: string
  deletedKnowledgeIds: string[]
  deletedEmbeddings: string[]
  deletedTrainingSamples: string[]
  updatedLoRAVersion: string
  oldModelVersion: string
  newModelVersion: string
  hashBefore: string
  hashAfter: string
  merkleRoot: string
  digitalSignature: string
  verificationStatus: VerificationStatus
  verifiedAt: string | null
  certificateUrl: string | null
}

export const KNOWLEDGE_TYPE_COLORS: Record<KnowledgeType, string> = {
  conversation: "#3b82f6",
  fact: "#10b981",
  document: "#8b5cf6",
  document_chunk: "#a78bfa",
  embedding: "#f59e0b",
  training_sample: "#ef4444",
  lora_adapter: "#ec4899",
  memory_node: "#06b6d4",
  knowledge_category: "#64748b",
  verification_certificate: "#22d3ee",
}

export const KNOWLEDGE_TYPE_LABELS: Record<KnowledgeType, string> = {
  conversation: "Conversation",
  fact: "Fact",
  document: "Document",
  document_chunk: "Document Chunk",
  embedding: "Embedding",
  training_sample: "Training Sample",
  lora_adapter: "LoRA Adapter",
  memory_node: "Memory Node",
  knowledge_category: "Knowledge Category",
  verification_certificate: "Certificate",
}

export const STORAGE_LOCATION_LABELS: Record<StorageLocation, string> = {
  conversation_store: "Conversation Store",
  embedding_store: "Embedding Store",
  vector_database: "Vector Database",
  training_dataset: "Training Dataset",
  memory_manager: "Memory Manager",
  knowledge_graph: "Knowledge Graph",
  lora_adapter: "LoRA Adapter",
  model_registry: "Model Registry",
  cache: "Cache",
}

export const EDGE_RELATION_LABELS: Record<EdgeRelation, string> = {
  learned_from: "Learned From",
  embedded_into: "Embedded Into",
  trained_on: "Trained On",
  retrieved_by: "Retrieved By",
  influences: "Influences",
  generated_from: "Generated From",
  verified_by: "Verified By",
}
