"""
Reasoning Trace Logger - Captures intermediate reasoning steps from agent execution.

Records all 6 steps of the agentic loop (UNDERSTAND, PLAN, RETRIEVE, EXECUTE, VALIDATE, ADJUST)
to enable introspection, debugging, and understanding agent decision-making.
"""

import json
import logging
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Any
from datetime import datetime
import os

logger = logging.getLogger(__name__)


@dataclass
class TraceStep:
    """Single step in reasoning trace."""
    step_number: int
    step_name: str  # "UNDERSTAND", "PLAN", "RETRIEVE", "EXECUTE", "VALIDATE", "ADJUST"
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    reasoning: str  # Human-readable explanation of what happened


@dataclass
class ReasoningTrace:
    """Complete trace of agent reasoning for one query."""
    query: str
    timestamp: str
    steps: List[TraceStep]
    validation_score: float
    final_playlist_size: int
    total_unique_songs: int

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "query": self.query,
            "timestamp": self.timestamp,
            "steps": [asdict(step) for step in self.steps],
            "validation_score": self.validation_score,
            "final_playlist_size": self.final_playlist_size,
            "total_unique_songs": self.total_unique_songs,
        }

    def to_markdown(self) -> str:
        """Convert to markdown for human reading."""
        md = f"""## Query: "{self.query}"
**Timestamp:** {self.timestamp}

### Reasoning Trace

"""
        for step in self.steps:
            md += f"""#### Step {step.step_number}: {step.step_name}
**Input:** {json.dumps(step.input_data, indent=2)[:200]}...
**Output:** {json.dumps(step.output_data, indent=2)[:200]}...
**Reasoning:** {step.reasoning}

"""
        md += f"""### Results
- **Validation Score:** {self.validation_score:.2f} / 1.0
- **Playlist Size:** {self.final_playlist_size} songs
- **Unique Songs:** {self.total_unique_songs}

---

"""
        return md


class TraceCollector:
    """Collects reasoning steps during agent execution."""

    def __init__(self):
        """Initialize empty trace."""
        self.steps: List[TraceStep] = []
        self.query: Optional[str] = None

    def set_query(self, query: str) -> None:
        """Set the query being traced."""
        self.query = query

    def add_step(
        self,
        step_number: int,
        step_name: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        reasoning: str,
    ) -> None:
        """Add a reasoning step to the trace."""
        step = TraceStep(
            step_number=step_number,
            step_name=step_name,
            input_data=input_data,
            output_data=output_data,
            reasoning=reasoning,
        )
        self.steps.append(step)
        logger.debug(f"Trace: Step {step_number} ({step_name}) - {reasoning[:100]}")

    def finalize(
        self,
        validation_score: float,
        final_playlist_size: int,
        total_unique_songs: int,
    ) -> ReasoningTrace:
        """Finalize the trace and create ReasoningTrace object."""
        return ReasoningTrace(
            query=self.query or "unknown",
            timestamp=datetime.now().isoformat(),
            steps=self.steps,
            validation_score=validation_score,
            final_playlist_size=final_playlist_size,
            total_unique_songs=total_unique_songs,
        )


class TraceLogger:
    """Saves reasoning traces to log files."""

    def __init__(self, log_dir: str = "logs/reasoning_traces"):
        """Initialize trace logger with log directory.

        Args:
            log_dir: Directory to save trace logs (created if doesn't exist)
        """
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        logger.info(f"Trace logger initialized: {log_dir}")

    def save_trace(self, trace: ReasoningTrace, format: str = "both") -> str:
        """Save trace to file(s).

        Args:
            trace: ReasoningTrace object to save
            format: "json", "markdown", or "both"

        Returns:
            Path to saved file(s)
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"trace_{timestamp}"

        files_saved = []

        if format in ["json", "both"]:
            json_path = os.path.join(self.log_dir, f"{base_filename}.json")
            with open(json_path, "w") as f:
                json.dump(trace.to_dict(), f, indent=2)
            files_saved.append(json_path)
            logger.info(f"Saved JSON trace: {json_path}")

        if format in ["markdown", "both"]:
            md_path = os.path.join(self.log_dir, f"{base_filename}.md")
            with open(md_path, "w") as f:
                f.write(trace.to_markdown())
            files_saved.append(md_path)
            logger.info(f"Saved markdown trace: {md_path}")

        return files_saved[0] if len(files_saved) == 1 else files_saved

    def get_latest_traces(self, count: int = 5) -> List[str]:
        """Get paths to latest trace files.

        Args:
            count: Number of recent traces to return

        Returns:
            List of file paths sorted by recency (newest first)
        """
        if not os.path.exists(self.log_dir):
            return []

        files = []
        for f in os.listdir(self.log_dir):
            if f.startswith("trace_") and f.endswith(".md"):
                path = os.path.join(self.log_dir, f)
                files.append((path, os.path.getmtime(path)))

        # Sort by modification time (newest first)
        files.sort(key=lambda x: x[1], reverse=True)
        return [path for path, _ in files[:count]]
