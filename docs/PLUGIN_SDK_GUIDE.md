# VeriUnlearn Plugin SDK Guide

## Overview

The VeriUnlearn Plugin SDK enables extending the platform with custom algorithms, metrics, reports, dashboards, verification strategies, policies, data sources, and visualizations — all without modifying core code.

Plugins are registered in the database via the `PluginManagerService`, loaded dynamically via `importlib.import_module()`, and managed through the REST API at `POST /api/v2/research/plugins`.

## Supported Plugin Types

| Type | Interface | Purpose |
|------|-----------|---------|
| Algorithm | `AlgorithmPlugin` | Custom unlearning algorithms |
| Metric | `MetricPlugin` | Custom evaluation metrics |
| Report | `ReportPlugin` | Custom report formats and templates |
| Dashboard | `DashboardPlugin` | Custom dashboard widgets |
| Verification | `VerificationPlugin` | Custom verification strategies |
| Policy | `PolicyPlugin` | Custom compliance policy providers |
| DataSource | `DataSourcePlugin` | Custom data source connectors |
| Visualization | `VisualizationPlugin` | Custom chart and visualization modules |

## Plugin Architecture

### Database Model

Plugins are stored in the `plugin_entries` table:

| Column | Type | Description |
|--------|------|-------------|
| `id` | `int` | Primary key |
| `name` | `str` | Unique plugin name |
| `plugin_type` | `str` | One of the 8 supported types |
| `version` | `str` | Semantic version (default: `1.0.0`) |
| `author` | `str` | Plugin author |
| `description` | `str` | Human-readable description |
| `entry_point` | `str` | Python module path for dynamic import |
| `is_enabled` | `bool` | Whether the plugin is active |
| `config_json` | `dict` | Plugin-specific configuration |
| `metadata_json` | `dict` | Additional metadata |

### Loading Mechanism

The `PluginManagerService` handles the full lifecycle:

```
Register → Store in DB → Enable → Load via importlib → Use → Disable → Unregister
```

Loading uses `importlib.import_module(plugin.entry_point)` to dynamically import the plugin module at runtime.

### Interface Hierarchy

```
PluginBase (ABC)
├── initialize(context: PluginContext) → bool
├── shutdown() → bool
├── health_check() → bool
└── metadata: PluginMetadata

├── AlgorithmPlugin
│   ├── execute(model, data, config) → dict
│   ├── estimate_cost(dataset_size, model_params) → dict
│   └── supported_model_types() → list[str]
│
├── MetricPlugin
│   ├── compute(predictions, ground_truth, config) → float
│   ├── compute_batch(batch) → dict
│   └── metric_direction() → str
│
├── ReportPlugin
│   ├── generate(data, format) → bytes
│   ├── supported_formats() → list[str]
│   └── get_template(template_name) → str
│
├── DashboardPlugin
│   ├── get_config() → dict
│   ├── get_data(params) → dict
│   └── component_type() → str
│
├── VerificationPlugin
│   ├── verify(context) → dict
│   └── required_context_keys() → list[str]
│
├── PolicyPlugin
│   ├── evaluate(context) → dict
│   ├── get_regulations() → list[str]
│   └── generate_rules(data_profile) → list[dict]
│
├── DataSourcePlugin
│   ├── connect(config) → bool
│   ├── list_datasets() → list[dict]
│   ├── fetch(query) → dict
│   └── get_schema(dataset) → dict
│
└── VisualizationPlugin
    ├── render(data, chart_type) → dict
    └── supported_chart_types() → list[str]
```

### Key Data Types

**`PluginMetadata`** — Declarative metadata for plugin discovery:
```python
@dataclass
class PluginMetadata:
    plugin_id: str
    name: str
    version: str
    author: str
    description: str
    plugin_type: str
    entry_point: str
    dependencies: list[str]
    min_platform_version: str
    config_schema: dict | None
```

**`PluginContext`** — Runtime context injected during initialization:
```python
@dataclass
class PluginContext:
    tenant_id: str | None
    user_id: str
    config: dict
    event_bus: Any
```

**`PluginLifecycle`** — Runtime state tracking:
```python
@dataclass
class PluginLifecycle:
    loaded: bool
    initialized: bool
    error: str | None
    load_time_ms: float | None
```

---

## Creating a Plugin

### Step 1: Implement the Plugin Interface

Choose the appropriate plugin type and implement all abstract methods. All plugin types extend `PluginBase`, which requires lifecycle methods.

#### AlgorithmPlugin Example

```python
from app.future.sdk.interfaces import AlgorithmPlugin, PluginMetadata, PluginContext

class MyCustomAlgorithm(AlgorithmPlugin):

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            plugin_id="my_custom_algo",
            name="My Custom Algorithm",
            version="1.0.0",
            author="Your Name",
            description="A custom unlearning algorithm using domain-specific techniques",
            plugin_type="algorithm",
            entry_point="my_package.plugins.MyCustomAlgorithm",
            dependencies=["torch"],
            min_platform_version="6.0.0",
        )

    async def initialize(self, context: PluginContext) -> bool:
        # Load model weights, configure GPU, etc.
        self._config = context.config
        return True

    async def shutdown(self) -> bool:
        # Release GPU memory, close files
        return True

    async def health_check(self) -> bool:
        return True

    async def execute(self, model, data, config) -> dict:
        # Implement your unlearning logic here
        return {
            "status": "completed",
            "deleted_count": len(data),
            "execution_time_ms": 0.0,
            "metrics": {},
        }

    async def estimate_cost(self, dataset_size, model_params) -> dict:
        return {
            "gpu_hours": dataset_size * model_params / 1e9,
            "memory_gb": model_params * 4 / 1e9,
            "cost_tier": "medium",
        }

    def supported_model_types(self) -> list[str]:
        return ["pytorch", "transformer"]
```

#### MetricPlugin Example

```python
from app.future.sdk.interfaces import MetricPlugin, PluginMetadata, PluginContext

class FairnessMetric(MetricPlugin):

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            plugin_id="fairness_metric",
            name="Demographic Parity Fairness",
            version="1.0.0",
            author="Your Name",
            description="Measures demographic parity across protected groups",
            plugin_type="metric",
            entry_point="my_package.metrics.FairnessMetric",
        )

    async def initialize(self, context: PluginContext) -> bool:
        return True

    async def shutdown(self) -> bool:
        return True

    async def health_check(self) -> bool:
        return True

    async def compute(self, predictions, ground_truth, config) -> float:
        # Compute demographic parity difference
        groups = config.get("protected_groups", {})
        # ... fairness computation logic ...
        return 0.95  # fairness score

    async def compute_batch(self, batch) -> dict:
        results = []
        for item in batch:
            score = await self.compute(
                item["predictions"], item["ground_truth"], item.get("config", {})
            )
            results.append({"fairness_score": score})
        avg_score = sum(r["fairness_score"] for r in results) / len(results)
        return {"per_item": results, "aggregate": avg_score}

    def metric_direction(self) -> str:
        return "higher_is_better"
```

#### ReportPlugin Example

```python
from app.future.sdk.interfaces import ReportPlugin, PluginMetadata, PluginContext

class LaTeXReportPlugin(ReportPlugin):

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            plugin_id="latex_report",
            name="LaTeX Publication Report",
            version="1.0.0",
            author="Your Name",
            description="Generates LaTeX-formatted research reports",
            plugin_type="report",
            entry_point="my_package.reports.LaTeXReportPlugin",
        )

    async def initialize(self, context: PluginContext) -> bool:
        return True

    async def shutdown(self) -> bool:
        return True

    async def health_check(self) -> bool:
        return True

    async def generate(self, data: dict, format: str) -> bytes:
        # Generate LaTeX content from data
        latex = self._render_latex(data)
        return latex.encode("utf-8")

    async def supported_formats(self) -> list[str]:
        return ["latex", "pdf"]

    async def get_template(self, template_name: str) -> str:
        templates = {
            "ieee_paper": "\\documentclass{IEEEtran}...",
            "tech_report": "\\documentclass{article}...",
        }
        return templates.get(template_name, "")
```

#### DataSourcePlugin Example

```python
from app.future.sdk.interfaces import DataSourcePlugin, PluginMetadata, PluginContext

class PostgreSQLConnector(DataSourcePlugin):

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            plugin_id="postgres_connector",
            name="PostgreSQL Connector",
            version="1.0.0",
            author="Your Name",
            description="Connect to PostgreSQL databases as a data source",
            plugin_type="datasource",
            entry_point="my_package.connectors.PostgreSQLConnector",
            dependencies=["asyncpg"],
        )

    async def initialize(self, context: PluginContext) -> bool:
        self._conn = None
        return True

    async def shutdown(self) -> bool:
        if self._conn:
            await self._conn.close()
        return True

    async def health_check(self) -> bool:
        return self._conn is not None

    async def connect(self, config: dict) -> bool:
        # Establish PostgreSQL connection
        self._conn = await asyncpg.connect(config["dsn"])
        return True

    async def list_datasets(self) -> list[dict]:
        # List tables in the connected database
        rows = await self._conn.fetch(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public'"
        )
        return [{"name": r["table_name"], "type": "table"} for r in rows]

    async def fetch(self, query: dict) -> dict:
        sql = query.get("sql", "")
        rows = await self._conn.fetch(sql)
        return {"data": [dict(r) for r in rows], "row_count": len(rows)}

    async def get_schema(self, dataset: str) -> dict:
        rows = await self._conn.fetch(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = $1", dataset
        )
        return {"columns": [{"name": r["column_name"], "type": r["data_type"]} for r in rows]}
```

### Step 2: Register via API

Register your plugin using the REST API:

```
POST /api/v2/research/plugins
Content-Type: application/json
Authorization: Bearer <token>

{
    "name": "my_custom_algo",
    "plugin_type": "algorithm",
    "version": "1.0.0",
    "author": "Your Name",
    "description": "A custom unlearning algorithm",
    "entry_point": "my_package.plugins.MyCustomAlgorithm",
    "config_json": {
        "gpu_enabled": true,
        "batch_size": 32
    }
}
```

### Step 3: Load and Use

```
POST /api/v2/research/plugins/my_custom_algo/load
```

The plugin is loaded via `importlib.import_module(entry_point)`. The returned module can then be instantiated and used in the unlearning, verification, or governance pipelines.

---

## Configuration

### Plugin Configuration (`config_json`)

Each plugin can have a `config_json` dictionary stored in the database. This is passed to `initialize()` as part of the `PluginContext`:

```python
async def initialize(self, context: PluginContext) -> bool:
    gpu_enabled = context.config.get("gpu_enabled", False)
    batch_size = context.config.get("batch_size", 32)
    # Configure plugin based on settings...
    return True
```

### Runtime Configuration (`PluginContext`)

The `PluginContext` provides runtime information:

| Field | Type | Description |
|-------|------|-------------|
| `tenant_id` | `str \| None` | Current tenant (multi-tenant mode) |
| `user_id` | `str` | Current user triggering the plugin |
| `config` | `dict` | Plugin-specific configuration from `config_json` |
| `event_bus` | `Any` | Reference to the platform EventBus for publishing events |

---

## Plugin Management API

### List Plugins

```
GET /api/v2/research/plugins?type=algorithm&enabled_only=true
```

### Get Plugin Details

```
GET /api/v2/research/plugins/{name}
```

### Toggle Plugin

```
PATCH /api/v2/research/plugins/{name}/toggle
{"enabled": true}
```

### Unregister Plugin

```
DELETE /api/v2/research/plugins/{name}
```

### Load Plugin

```
POST /api/v2/research/plugins/{name}/load
```

---

## Built-in Algorithms (Algorithm Registry)

The platform ships with 8 built-in algorithms registered via `AlgorithmRegistryService.seed_builtin_algorithms()`:

| Algorithm | Complexity | Supported Models | Supported Datasets |
|-----------|-----------|-----------------|-------------------|
| SISA | Medium | transformer, linear, neural_network | tabular, text, image |
| InfluenceFunctions | High | transformer, neural_network | tabular, text |
| CertifiedRemoval | High | linear, neural_network | tabular, text |
| BadTeacher | Medium | transformer, neural_network | text, image |
| AmnesiacML | Low | neural_network | tabular, text, image |
| FineTuneForgetting | Low | transformer, neural_network | tabular, text, image |
| CatastrophicForgetting | Low | neural_network | tabular, text |
| RetrainingBaseline | High | transformer, linear, neural_network | tabular, text, image |

---

## Best Practices

### Idempotent Initialization

Ensure `initialize()` can be called multiple times without side effects:

```python
async def initialize(self, context: PluginContext) -> bool:
    if self._initialized:
        return True
    # ... perform one-time setup ...
    self._initialized = True
    return True
```

### Graceful Degradation

Handle missing dependencies and unavailable resources:

```python
async def execute(self, model, data, config) -> dict:
    try:
        result = await self._run_algorithm(model, data)
    except ImportError as e:
        return {"status": "error", "error": f"Missing dependency: {e}"}
    except RuntimeError as e:
        return {"status": "error", "error": f"Runtime error: {e}"}
    return result
```

### Health Checks

Implement meaningful health checks that verify the plugin's actual capability:

```python
async def health_check(self) -> bool:
    try:
        import torch
        return torch.cuda.is_available() if self._needs_gpu else True
    except ImportError:
        return False
```

### Version Compatibility

Declare `min_platform_version` in your metadata to prevent loading on incompatible platforms:

```python
@property
def metadata(self) -> PluginMetadata:
    return PluginMetadata(
        ...
        min_platform_version="6.0.0",
        ...
    )
```

### Error Handling

Never raise uncaught exceptions from plugin methods. Return error dictionaries instead:

```python
async def verify(self, context: dict) -> dict:
    if "model_before" not in context:
        return {
            "passed": False,
            "confidence": 0.0,
            "error": "Missing required context key: model_before",
        }
    # ... verification logic ...
```

### Event Publishing

Use the `PluginContext.event_bus` to publish events that integrate with the platform's event-driven architecture:

```python
async def initialize(self, context: PluginContext) -> bool:
    self._event_bus = context.event_bus
    return True

async def execute(self, model, data, config) -> dict:
    # ... execute algorithm ...
    if self._event_bus:
        await self._event_bus.emit(
            "plugin.algorithm.completed",
            data={"plugin_id": self.metadata.plugin_id, "result": result},
            source=f"plugin.{self.metadata.plugin_id}",
        )
    return result
```
